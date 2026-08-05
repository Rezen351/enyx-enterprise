package service

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/almuzky/iot/services/alert/internal/model"
	"github.com/almuzky/iot/services/alert/internal/repository"
	"github.com/google/uuid"
	"github.com/nats-io/nats.go"
)

// ErrInvalidRange is returned when a threshold's effective min exceeds its max
// (including partial updates that invert the range against the stored value).
var ErrInvalidRange = errors.New("min must be less than or equal to max")

const telemetrySubject = "telemetry.ingest"
const auditSubject = "audit.log"

// Store is the persistence seam for alert + threshold data. The concrete
// implementation is *repository.Store; unit tests inject a fake.
type Store interface {
	ListAlerts(ctx context.Context, f repository.AlertFilter, limit, offset int) ([]model.Alert, int64, error)
	GetAlert(ctx context.Context, id string) (*model.Alert, error)
	CreateAlert(ctx context.Context, a *model.Alert) error
	ResolveActive(ctx context.Context, nodeID, metric string, resolvedAt time.Time) error
	GetLatestActive(ctx context.Context, nodeID, metric string) (*model.Alert, error)
	AckAlert(ctx context.Context, id, userID string, ackedAt time.Time) (*model.Alert, error)
	GetThresholdForNodeMetric(ctx context.Context, nodeID, metric string) (*model.Threshold, error)
	ListThresholds(ctx context.Context, nodeID, metric string, enabledOnly bool) ([]model.Threshold, error)
	GetThreshold(ctx context.Context, id string) (*model.Threshold, error)
	CreateThreshold(ctx context.Context, t *model.Threshold) error
	UpdateThreshold(ctx context.Context, id string, patch map[string]any) (*model.Threshold, error)
	DeleteThreshold(ctx context.Context, id string) (*model.Threshold, error)

	// ─── Outbox (ADR-007) ──────────────────────────────────────────────
	// EnqueueOutbox writes an outbox row atomically (own tx) for later relay.
	EnqueueOutbox(ctx context.Context, subject, payload string) error
	// ListUnsentOutbox returns pending (sent=false) outbox rows, oldest first.
	ListUnsentOutbox(ctx context.Context, limit int) ([]repository.OutboxRow, error)
	// MarkOutboxSent marks a single outbox row delivered (idempotent).
	MarkOutboxSent(ctx context.Context, id string) error
}

// Cache is the threshold + active-alert cache seam. The concrete
// implementation is *cache.AlertCache; unit tests inject a fake.
type Cache interface {
	GetCachedThreshold(ctx context.Context, nodeID, metric string) *model.Threshold
	SetCachedThreshold(ctx context.Context, nodeID, metric string, t *model.Threshold)
	ClearThreshold(ctx context.Context, nodeID, metric string)
	ActiveExists(ctx context.Context, nodeID, metric string) bool
	SetActive(ctx context.Context, nodeID, metric string)
	ClearActive(ctx context.Context, nodeID, metric string)
	GetViolationStart(ctx context.Context, nodeID, metric string) (time.Time, bool)
	SetViolationStart(ctx context.Context, nodeID, metric string, t time.Time)
	ClearViolationStart(ctx context.Context, nodeID, metric string)
	GetLastTriggered(ctx context.Context, nodeID, metric string) (time.Time, bool)
	SetLastTriggered(ctx context.Context, nodeID, metric string, t time.Time)
}

// Service evaluates telemetry against thresholds and persists/relays alerts.
type Service struct {
	store Store
	cache Cache
	nc    *nats.Conn
}

// New wires the Alert Service with its store, cache, and NATS connection.
// The store/cache may be real (*repository.Store / *cache.AlertCache) or a
// test fake implementing the Store / Cache interfaces.
func New(store Store, c Cache, nc *nats.Conn) *Service {
	return &Service{store: store, cache: c, nc: nc}
}

// SetNATS wires the (already-connected) NATS connection used for publishing
// alert/notification events. main.go creates the Service before NATS connects
// (so threshold CRUD stays cache-coherent if NATS is briefly unavailable), then
// calls SetNATS once the connection is established so publishAlert/publishSystem
// can relay events to subscribers.
func (s *Service) SetNATS(nc *nats.Conn) { s.nc = nc }

// telemetryMsg is the wire format published by Module Service to telemetry.ingest:
// {"node_id":"...","metric":"...","value":<float>,"ts":<unix ms>}.
type telemetryMsg struct {
	NodeID string  `json:"node_id"`
	Metric string  `json:"metric"`
	Value  float64 `json:"value"`
	Ts     int64   `json:"ts"`
}

// RunSubscriber subscribes to telemetry.ingest on Core NATS. A queue group lets
// multiple Alert Service replicas share the load. The subscription runs on
// NATS-managed goroutines, so the caller's HTTP server keeps the process alive.
func (s *Service) RunSubscriber(nc *nats.Conn) error {
	_, err := nc.QueueSubscribe(telemetrySubject, "alert-workers", func(m *nats.Msg) {
		s.handleTelemetry(m.Data)
	})
	if err != nil {
		log.Printf("WARN: alert subscriber failed: %v", err)
		return err
	}
	log.Printf("alert subscriber listening on %q", telemetrySubject)
	return nil
}

func (s *Service) handleTelemetry(body []byte) {
	var tm telemetryMsg
	if err := json.Unmarshal(body, &tm); err != nil {
		log.Printf("WARN: alert: telemetry.ingest not JSON: %v", err)
		return
	}
	if tm.NodeID == "" || tm.Metric == "" {
		return
	}

	th := s.resolveThreshold(tm.NodeID, tm.Metric)
	if th == nil || !th.Enabled {
		return
	}

	violated, boundary := evaluate(tm.Value, th)
	ctx := context.Background()
	now := time.Now().UTC()

	if violated {
		if s.cache.ActiveExists(ctx, tm.NodeID, tm.Metric) {
			return
		}
		if th.DurationSec != nil && *th.DurationSec > 0 {
			violationStart, exists := s.cache.GetViolationStart(ctx, tm.NodeID, tm.Metric)
			if !exists {
				s.cache.SetViolationStart(ctx, tm.NodeID, tm.Metric, now)
				return
			}
			if now.Sub(violationStart) < time.Duration(*th.DurationSec)*time.Second {
				return
			}
			s.cache.ClearViolationStart(ctx, tm.NodeID, tm.Metric)
		}
		if th.CooldownSec != nil && *th.CooldownSec > 0 {
			if lastTriggered, exists := s.cache.GetLastTriggered(ctx, tm.NodeID, tm.Metric); exists {
				if now.Sub(lastTriggered) < time.Duration(*th.CooldownSec)*time.Second {
					return
				}
			}
		}
		msg := th.Message
		if msg == "" {
			msg = buildMessage(th, tm.Value, boundary)
		}
		alert := &model.Alert{
			ID:             uuid.NewString(),
			NodeID:         tm.NodeID,
			Metric:         tm.Metric,
			Value:          tm.Value,
			ThresholdValue: boundary,
			Severity:       th.Severity,
			Status:         "active",
			Message:        msg,
			ThresholdID:    strPtr(th.ID),
			TriggeredAt:    now,
		}
		if err := s.store.CreateAlert(ctx, alert); err != nil {
			log.Printf("ERROR: alert: persist alert failed node=%s metric=%s: %v", tm.NodeID, tm.Metric, err)
			return
		}
		s.cache.SetActive(ctx, tm.NodeID, tm.Metric)
		if th.CooldownSec != nil && *th.CooldownSec > 0 {
			s.cache.SetLastTriggered(ctx, tm.NodeID, tm.Metric, now)
		}
		s.publishAlert("alert.triggered", alert)
		s.publishSystem(alert, "triggered")
		return
	}

	// Within range: if an active alert exists, resolve it.
	if s.cache.ActiveExists(ctx, tm.NodeID, tm.Metric) {
		if th.Hysteresis != nil && *th.Hysteresis > 0 {
			if th.Min != nil && tm.Value < *th.Min+*th.Hysteresis {
				return
			}
			if th.Max != nil && tm.Value > *th.Max-*th.Hysteresis {
				return
			}
		}
		now := time.Now().UTC()
		active, gerr := s.store.GetLatestActive(ctx, tm.NodeID, tm.Metric)
		if gerr != nil {
			log.Printf("ERROR: alert: get active failed node=%s metric=%s: %v", tm.NodeID, tm.Metric, gerr)
			return
		}
		if err := s.store.ResolveActive(ctx, tm.NodeID, tm.Metric, now); err != nil {
			log.Printf("ERROR: alert: resolve failed node=%s metric=%s: %v", tm.NodeID, tm.Metric, err)
			return
		}
		s.cache.ClearActive(ctx, tm.NodeID, tm.Metric)
		s.cache.ClearViolationStart(ctx, tm.NodeID, tm.Metric)
		if active != nil {
			active.Status = "resolved"
			active.ResolvedAt = &now
			s.publishAlert("alert.resolved", active)
			s.publishSystem(active, "resolved")
		}
	}
}

// resolveThreshold returns the applicable threshold for (node, metric) using the
// cache first, then MariaDB (exact, then wildcard "*"). The result is cached.
func (s *Service) resolveThreshold(nodeID, metric string) *model.Threshold {
	ctx := context.Background()

	if t := s.cache.GetCachedThreshold(ctx, nodeID, metric); t != nil {
		return t
	}
	if t := s.cache.GetCachedThreshold(ctx, "*", metric); t != nil {
		return t
	}

	t, err := s.store.GetThresholdForNodeMetric(ctx, nodeID, metric)
	if err != nil {
		log.Printf("WARN: alert: threshold lookup failed node=%s metric=%s: %v", nodeID, metric, err)
		return nil
	}
	if t != nil {
		s.cache.SetCachedThreshold(ctx, nodeID, metric, t)
	}
	return t
}

// evaluate reports whether value is outside [min, max] and which boundary it hit.
func evaluate(value float64, th *model.Threshold) (bool, *float64) {
	if th.Min != nil && value < *th.Min {
		return true, th.Min
	}
	if th.Max != nil && value > *th.Max {
		return true, th.Max
	}
	return false, nil
}

func buildMessage(th *model.Threshold, value float64, boundary *float64) string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "[%s] node %s metric %q value %v", th.Severity, th.NodeID, th.Metric, value)
	switch {
	case th.Min != nil && th.Max != nil:
		fmt.Fprintf(&sb, " outside range [%v, %v]", *th.Min, *th.Max)
	case th.Min != nil:
		fmt.Fprintf(&sb, " below min %v", *th.Min)
	case th.Max != nil:
		fmt.Fprintf(&sb, " above max %v", *th.Max)
	}
	return sb.String()
}

// ─── Publishing ────────────────────────────────────────────────────────────

func (s *Service) publishAlert(subject string, a *model.Alert) {
	payload, err := json.Marshal(map[string]any{
		"id":              a.ID,
		"node_id":         a.NodeID,
		"metric":          a.Metric,
		"value":           a.Value,
		"threshold_value": a.ThresholdValue,
		"severity":        a.Severity,
		"status":          a.Status,
		"message":         a.Message,
		"triggered_at":    a.TriggeredAt,
	})
	if err != nil {
		return
	}
	s.enqueueOutbox(subject, string(payload))
}

// publishSystem relays a human-friendly notification onto system.status so the
// WS-Gateway can push it to the dashboard NotificationContext.
func (s *Service) publishSystem(a *model.Alert, event string) {
	payload, err := json.Marshal(map[string]any{
		"type":    "alert",
		"level":   a.Severity,
		"node_id": a.NodeID,
		"metric":  a.Metric,
		"value":   a.Value,
		"message": a.Message,
		"status":  event,
		"event":   event,
		"ts":      time.Now().UnixMilli(),
	})
	if err != nil {
		return
	}
	s.enqueueOutbox("system.status", string(payload))
}

// publishAudit emits a threshold lifecycle event onto the shared audit.log
// subject so the Audit Service can persist an immutable compliance record.
func (s *Service) publishAudit(event string, fields map[string]string) {
	payload := fmt.Sprintf(`{"event":%q,"service":"alert","data":%s}`, event, mapToJSON(fields))
	s.enqueueOutbox(auditSubject, payload)
}

// enqueueOutbox writes the event to the outbox table for the relay to publish
// to NATS (ADR-007). Replaces the previous direct s.nc.Publish so events are
// never lost on a NATS outage.
func (s *Service) enqueueOutbox(subject, payload string) {
	if s.store == nil {
		return
	}
	if err := s.store.EnqueueOutbox(context.Background(), subject, payload); err != nil {
		log.Printf("[outbox] enqueue failed subject=%s: %v", subject, err)
	}
}

// mapToJSON renders a string map as a compact JSON object (key/value quoted).
func mapToJSON(m map[string]string) string {
	out := "{"
	first := true
	for k, v := range m {
		if !first {
			out += ","
		}
		out += fmt.Sprintf(`%q:%q`, k, v)
		first = false
	}
	return out + "}"
}

// ─── Threshold management (cache-coherent) ─────────────────────────────────

// CreateThreshold persists a threshold and evicts any cached copy.
func (s *Service) CreateThreshold(ctx context.Context, t *model.Threshold, by string) (*model.Threshold, error) {
	if err := s.store.CreateThreshold(ctx, t); err != nil {
		return nil, err
	}
	s.cache.ClearThreshold(ctx, t.NodeID, t.Metric)
	s.publishAudit("alert.threshold.created", map[string]string{
		"threshold_id": t.ID,
		"node_id":      t.NodeID,
		"metric":       t.Metric,
		"severity":     t.Severity,
		"by":           by,
	})
	return t, nil
}

// UpdateThreshold patches a threshold and evicts the cache. It validates the
// effective min/max range (even for single-field updates) and evicts BOTH the
// old and new (node_id, metric) cache keys so a rename cannot leave a stale
// threshold cached under the previous key.
func (s *Service) UpdateThreshold(ctx context.Context, id string, patch map[string]any, by string) (*model.Threshold, error) {
	old, err := s.store.GetThreshold(ctx, id)
	if err != nil {
		return nil, err
	}
	effMin, effMax := old.Min, old.Max
	if v, ok := patch["min"].(float64); ok {
		effMin = &v
	}
	if v, ok := patch["max"].(float64); ok {
		effMax = &v
	}
	if effMin != nil && effMax != nil && *effMin > *effMax {
		return nil, ErrInvalidRange
	}
	t, err := s.store.UpdateThreshold(ctx, id, patch)
	if err != nil {
		return nil, err
	}
	s.cache.ClearThreshold(ctx, old.NodeID, old.Metric)
	s.cache.ClearThreshold(ctx, t.NodeID, t.Metric)
	s.publishAudit("alert.threshold.updated", map[string]string{
		"threshold_id": t.ID,
		"node_id":      t.NodeID,
		"metric":       t.Metric,
		"severity":     t.Severity,
		"by":           by,
	})
	return t, nil
}

// DeleteThreshold removes a threshold and evicts the cache.
func (s *Service) DeleteThreshold(ctx context.Context, id string, by string) error {
	t, err := s.store.DeleteThreshold(ctx, id)
	if err != nil {
		return err
	}
	s.cache.ClearThreshold(ctx, t.NodeID, t.Metric)
	s.publishAudit("alert.threshold.deleted", map[string]string{
		"threshold_id": t.ID,
		"node_id":      t.NodeID,
		"metric":       t.Metric,
		"by":           by,
	})
	return nil
}

// AckAlert acknowledges an alert by the given user.
func (s *Service) AckAlert(ctx context.Context, id, userID string) (*model.Alert, error) {
	return s.store.AckAlert(ctx, id, userID, time.Now().UTC())
}

func strPtr(s string) *string { return &s }
