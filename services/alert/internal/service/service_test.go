package service

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/almuzky/iot/services/alert/internal/model"
	"github.com/almuzky/iot/services/alert/internal/repository"
)

// ─── Fakes ──────────────────────────────────────────────────────────────────

type fakeStore struct {
	alerts          []model.Alert
	thresholds      []model.Threshold
	err             error
	getThresholdErr error
	createAlertErr  error
	resolveActive   map[string]int
	activeForNode   *model.Alert
	activeErr       error
	acked           map[string]string
	deleted         map[string]*model.Threshold
}

func (f *fakeStore) ListAlerts(ctx context.Context, filter repository.AlertFilter, limit, offset int) ([]model.Alert, int64, error) {
	if f.err != nil {
		return nil, 0, f.err
	}
	return f.alerts, int64(len(f.alerts)), nil
}

func (f *fakeStore) GetAlert(ctx context.Context, id string) (*model.Alert, error) {
	if f.err != nil {
		return nil, f.err
	}
	for i := range f.alerts {
		if f.alerts[i].ID == id {
			return &f.alerts[i], nil
		}
	}
	return nil, repository.ErrNotFound
}

func (f *fakeStore) CreateAlert(ctx context.Context, a *model.Alert) error {
	if f.createAlertErr != nil {
		return f.createAlertErr
	}
	f.alerts = append(f.alerts, *a)
	return nil
}

func (f *fakeStore) ResolveActive(ctx context.Context, nodeID, metric string, resolvedAt time.Time) error {
	if f.resolveActive == nil {
		f.resolveActive = map[string]int{}
	}
	f.resolveActive[nodeID+"/"+metric]++
	return nil
}

func (f *fakeStore) GetLatestActive(ctx context.Context, nodeID, metric string) (*model.Alert, error) {
	if f.activeErr != nil {
		return nil, f.activeErr
	}
	return f.activeForNode, nil
}

func (f *fakeStore) AckAlert(ctx context.Context, id, userID string, ackedAt time.Time) (*model.Alert, error) {
	if f.err != nil {
		return nil, f.err
	}
	if f.acked == nil {
		f.acked = map[string]string{}
	}
	f.acked[id] = userID
	a := model.Alert{ID: id, Status: "acked", AckedBy: &userID}
	return &a, nil
}

func (f *fakeStore) GetThresholdForNodeMetric(ctx context.Context, nodeID, metric string) (*model.Threshold, error) {
	if f.getThresholdErr != nil {
		return nil, f.getThresholdErr
	}
	for i := range f.thresholds {
		t := f.thresholds[i]
		if t.NodeID == nodeID && t.Metric == metric {
			return &t, nil
		}
		if t.NodeID == "*" && t.Metric == metric {
			return &t, nil
		}
	}
	return nil, nil
}

func (f *fakeStore) ListThresholds(ctx context.Context, nodeID, metric string, enabledOnly bool) ([]model.Threshold, error) {
	if f.err != nil {
		return nil, f.err
	}
	out := make([]model.Threshold, 0, len(f.thresholds))
	for _, t := range f.thresholds {
		if enabledOnly && !t.Enabled {
			continue
		}
		if nodeID != "" && t.NodeID != nodeID {
			continue
		}
		if metric != "" && t.Metric != metric {
			continue
		}
		out = append(out, t)
	}
	return out, nil
}

func (f *fakeStore) GetThreshold(ctx context.Context, id string) (*model.Threshold, error) {
	if f.err != nil {
		return nil, f.err
	}
	for i := range f.thresholds {
		if f.thresholds[i].ID == id {
			return &f.thresholds[i], nil
		}
	}
	return nil, repository.ErrNotFound
}

func (f *fakeStore) CreateThreshold(ctx context.Context, t *model.Threshold) error {
	if f.err != nil {
		return f.err
	}
	f.thresholds = append(f.thresholds, *t)
	return nil
}

func (f *fakeStore) UpdateThreshold(ctx context.Context, id string, patch map[string]any) (*model.Threshold, error) {
	if f.err != nil {
		return nil, f.err
	}
	for i := range f.thresholds {
		if f.thresholds[i].ID == id {
			if v, ok := patch["min"].(float64); ok {
				p := v
				f.thresholds[i].Min = &p
			}
			if v, ok := patch["max"].(float64); ok {
				p := v
				f.thresholds[i].Max = &p
			}
			if v, ok := patch["node_id"].(string); ok {
				f.thresholds[i].NodeID = v
			}
			if v, ok := patch["metric"].(string); ok {
				f.thresholds[i].Metric = v
			}
			if v, ok := patch["severity"].(string); ok {
				f.thresholds[i].Severity = v
			}
			if v, ok := patch["enabled"].(bool); ok {
				f.thresholds[i].Enabled = v
			}
			if v, ok := patch["message"].(string); ok {
				f.thresholds[i].Message = v
			}
			if v, ok := patch["duration_sec"].(int); ok {
				f.thresholds[i].DurationSec = &v
			}
			if v, ok := patch["cooldown_sec"].(int); ok {
				f.thresholds[i].CooldownSec = &v
			}
			if v, ok := patch["hysteresis"].(float64); ok {
				f.thresholds[i].Hysteresis = &v
			}
			return &f.thresholds[i], nil
		}
	}
	return nil, repository.ErrNotFound
}

func (f *fakeStore) DeleteThreshold(ctx context.Context, id string) (*model.Threshold, error) {
	if f.err != nil {
		return nil, f.err
	}
	for i := range f.thresholds {
		if f.thresholds[i].ID == id {
			t := f.thresholds[i]
			if f.deleted == nil {
				f.deleted = map[string]*model.Threshold{}
			}
			f.deleted[id] = &t
			f.thresholds = append(f.thresholds[:i], f.thresholds[i+1:]...)
			return &t, nil
		}
	}
	return nil, repository.ErrNotFound
}

func (f *fakeStore) EnqueueOutbox(ctx context.Context, subject, payload string) error {
	return f.err
}

func (f *fakeStore) ListUnsentOutbox(ctx context.Context, limit int) ([]repository.OutboxRow, error) {
	return nil, f.err
}

func (f *fakeStore) MarkOutboxSent(ctx context.Context, id string) error {
	return f.err
}

type fakeCache struct {
	thresholds   map[string]*model.Threshold
	active       map[string]bool
	cleared      []string
	violationStart map[string]time.Time
	violationSet   map[string]bool
	lastTriggered  map[string]time.Time
	triggeredSet   map[string]bool
}

func newFakeCache() *fakeCache {
	return &fakeCache{
		thresholds:   map[string]*model.Threshold{},
		active:       map[string]bool{},
		violationStart: map[string]time.Time{},
		violationSet:   map[string]bool{},
		lastTriggered:  map[string]time.Time{},
		triggeredSet:   map[string]bool{},
	}
}

func cacheKey(nodeID, metric string) string { return nodeID + ":" + metric }

func (c *fakeCache) GetCachedThreshold(ctx context.Context, nodeID, metric string) *model.Threshold {
	return c.thresholds[cacheKey(nodeID, metric)]
}

func (c *fakeCache) SetCachedThreshold(ctx context.Context, nodeID, metric string, t *model.Threshold) {
	if t == nil {
		return
	}
	c.thresholds[cacheKey(nodeID, metric)] = t
}

func (c *fakeCache) ClearThreshold(ctx context.Context, nodeID, metric string) {
	c.cleared = append(c.cleared, cacheKey(nodeID, metric))
	delete(c.thresholds, cacheKey(nodeID, metric))
	delete(c.thresholds, cacheKey("*", metric))
}

func (c *fakeCache) ActiveExists(ctx context.Context, nodeID, metric string) bool {
	return c.active[cacheKey(nodeID, metric)]
}

func (c *fakeCache) SetActive(ctx context.Context, nodeID, metric string) {
	c.active[cacheKey(nodeID, metric)] = true
}

func (c *fakeCache) ClearActive(ctx context.Context, nodeID, metric string) {
	delete(c.active, cacheKey(nodeID, metric))
}

func (c *fakeCache) GetViolationStart(ctx context.Context, nodeID, metric string) (time.Time, bool) {
	return c.violationStart[cacheKey(nodeID, metric)], c.violationSet[cacheKey(nodeID, metric)]
}

func (c *fakeCache) SetViolationStart(ctx context.Context, nodeID, metric string, t time.Time) {
	if c.violationStart == nil {
		c.violationStart = map[string]time.Time{}
		c.violationSet = map[string]bool{}
	}
	c.violationStart[cacheKey(nodeID, metric)] = t
	c.violationSet[cacheKey(nodeID, metric)] = true
}

func (c *fakeCache) ClearViolationStart(ctx context.Context, nodeID, metric string) {
	if c.violationSet != nil {
		delete(c.violationSet, cacheKey(nodeID, metric))
	}
}

func (c *fakeCache) GetLastTriggered(ctx context.Context, nodeID, metric string) (time.Time, bool) {
	return c.lastTriggered[cacheKey(nodeID, metric)], c.triggeredSet[cacheKey(nodeID, metric)]
}

func (c *fakeCache) SetLastTriggered(ctx context.Context, nodeID, metric string, t time.Time) {
	if c.lastTriggered == nil {
		c.lastTriggered = map[string]time.Time{}
		c.triggeredSet = map[string]bool{}
	}
	c.lastTriggered[cacheKey(nodeID, metric)] = t
	c.triggeredSet[cacheKey(nodeID, metric)] = true
}

// ─── evaluate / buildMessage ─────────────────────────────────────────────────

func TestEvaluate(t *testing.T) {
	min := 10.0
	max := 50.0
	th := &model.Threshold{Min: &min, Max: &max}

	if viol, _ := evaluate(5, th); !viol {
		t.Error("value below min should violate")
	}
	if viol, _ := evaluate(60, th); !viol {
		t.Error("value above max should violate")
	}
	if viol, _ := evaluate(30, th); viol {
		t.Error("value in range should not violate")
	}
	if viol, b := evaluate(5, th); !viol && *b != 10 {
		t.Errorf("boundary should be min, got %v", b)
	}
}

func TestBuildMessage(t *testing.T) {
	min := 10.0
	th := &model.Threshold{NodeID: "n1", Metric: "temp", Severity: "critical", Min: &min}
	msg := buildMessage(th, 5, &min)
	if msg == "" {
		t.Error("message should not be empty")
	}
}

// ─── resolveThreshold ────────────────────────────────────────────────────────

func TestResolveThresholdCacheFirst(t *testing.T) {
	st := &fakeStore{}
	cc := newFakeCache()
	cc.SetCachedThreshold(context.Background(), "n1", "temp", &model.Threshold{NodeID: "n1", Metric: "temp"})

	svc := New(st, cc, nil)
	got := svc.resolveThreshold("n1", "temp")
	if got == nil {
		t.Fatal("expected cached threshold")
	}
}

func TestResolveThresholdStoreFallback(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp"}}}
	cc := newFakeCache()

	svc := New(st, cc, nil)
	got := svc.resolveThreshold("n1", "temp")
	if got == nil || got.ID != "t1" {
		t.Fatal("expected store-backed threshold")
	}
	// Now it should be cached.
	if cc.GetCachedThreshold(context.Background(), "n1", "temp") == nil {
		t.Error("expected threshold to be cached after store lookup")
	}
}

func TestResolveThresholdWildcard(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "w1", NodeID: "*", Metric: "temp"}}}
	cc := newFakeCache()

	svc := New(st, cc, nil)
	got := svc.resolveThreshold("n1", "temp")
	if got == nil || got.ID != "w1" {
		t.Fatal("expected wildcard threshold")
	}
}

func TestResolveThresholdStoreError(t *testing.T) {
	st := &fakeStore{getThresholdErr: errors.New("db down")}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	if got := svc.resolveThreshold("n1", "temp"); got != nil {
		t.Error("expected nil on store error")
	}
}

// ─── handleTelemetry ─────────────────────────────────────────────────────────

func floatPtr(v float64) *float64 { return &v }

func TestHandleTelemetryTriggerAndResolve(t *testing.T) {
	min := 10.0
	max := 50.0
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp", Min: &min, Max: &max, Enabled: true, Severity: "critical"}}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	// Value above max -> active alert created.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if !cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Fatal("expected active marker set")
	}
	if len(st.alerts) != 1 || st.alerts[0].Status != "active" {
		t.Fatalf("expected 1 active alert, got %+v", st.alerts)
	}

	// Second high value -> dedup, no new alert.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":2}`))
	if len(st.alerts) != 1 {
		t.Fatalf("expected dedup, got %d alerts", len(st.alerts))
	}

	// Value back in range -> resolve.
	st.activeForNode = &st.alerts[0]
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":30,"ts":3}`))
	if cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Error("expected active marker cleared after resolve")
	}
}

func TestHandleTelemetryInvalidJSON(t *testing.T) {
	svc := New(&fakeStore{}, newFakeCache(), nil)
	// Should not panic.
	svc.handleTelemetry([]byte("not json"))
}

func TestHandleTelemetryDisabledThreshold(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp", Max: floatPtr(10), Enabled: false}}}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if len(st.alerts) != 0 {
		t.Error("expected no alert for disabled threshold")
	}
}

// ─── Threshold CRUD ──────────────────────────────────────────────────────────

func TestCreateThreshold(t *testing.T) {
	st := &fakeStore{}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	th := &model.Threshold{ID: "t1", NodeID: "n1", Metric: "temp"}
	got, err := svc.CreateThreshold(context.Background(), th, "u1")
	if err != nil {
		t.Fatal(err)
	}
	if got.ID != "t1" {
		t.Error("unexpected threshold")
	}
	if st.thresholds[0].ID != "t1" {
		t.Error("expected threshold persisted")
	}
	if len(cc.cleared) == 0 {
		t.Error("expected cache eviction")
	}
}

func TestUpdateThresholdInvalidRange(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp", Min: floatPtr(10), Max: floatPtr(50)}}}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	_, err := svc.UpdateThreshold(context.Background(), "t1", map[string]any{"max": 5.0}, "u1")
	if !errors.Is(err, ErrInvalidRange) {
		t.Fatalf("expected ErrInvalidRange, got %v", err)
	}
}

func TestUpdateThresholdRenamesCacheKeys(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp", Min: floatPtr(10), Max: floatPtr(50)}}}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	_, err := svc.UpdateThreshold(context.Background(), "t1", map[string]any{"metric": "ph"}, "u1")
	if err != nil {
		t.Fatal(err)
	}
	// Both old and new cache keys evicted.
	if len(cc.cleared) != 2 {
		t.Fatalf("expected 2 cache keys cleared (old+new), got %d", len(cc.cleared))
	}
}

func TestUpdateThresholdNotFound(t *testing.T) {
	st := &fakeStore{err: repository.ErrNotFound}
	svc := New(st, newFakeCache(), nil)
	_, err := svc.UpdateThreshold(context.Background(), "missing", map[string]any{"max": 5.0}, "u1")
	if !errors.Is(err, repository.ErrNotFound) {
		t.Fatalf("expected ErrNotFound, got %v", err)
	}
}

func TestDeleteThreshold(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp"}}}
	cc := newFakeCache()
	svc := New(st, cc, nil)
	if err := svc.DeleteThreshold(context.Background(), "t1", "u1"); err != nil {
		t.Fatal(err)
	}
	if len(st.thresholds) != 0 {
		t.Error("expected threshold removed")
	}
	if len(cc.cleared) == 0 {
		t.Error("expected cache eviction on delete")
	}
}

func TestDeleteThresholdNotFound(t *testing.T) {
	st := &fakeStore{err: repository.ErrNotFound}
	svc := New(st, newFakeCache(), nil)
	if err := svc.DeleteThreshold(context.Background(), "missing", "u1"); err == nil {
		t.Error("expected error for missing threshold")
	}
}

func TestAckAlert(t *testing.T) {
	st := &fakeStore{}
	svc := New(st, newFakeCache(), nil)
	got, err := svc.AckAlert(context.Background(), "a1", "u1")
	if err != nil {
		t.Fatal(err)
	}
	if got.Status != "acked" {
		t.Errorf("expected acked, got %s", got.Status)
	}
	if st.acked["a1"] != "u1" {
		t.Error("expected ack recorded")
	}
}

func TestMapToJSON(t *testing.T) {
	out := mapToJSON(map[string]string{"a": "1", "b": "2"})
	if out == "" {
		t.Error("expected non-empty json")
	}
	// simple structural check
	if out[0] != '{' || out[len(out)-1] != '}' {
		t.Errorf("mapToJSON should be an object, got %s", out)
	}
}

func TestRunSubscriberNilConn(t *testing.T) {
	svc := New(&fakeStore{}, newFakeCache(), nil)
	// With a nil nats conn, RunSubscriber should error gracefully.
	if err := svc.RunSubscriber(nil); err == nil {
		t.Error("expected error with nil conn")
	}
}

// ─── New Threshold Fields: DurationSec, CooldownSec, Hysteresis, Message ──────

func TestHandleTelemetryDurationSec(t *testing.T) {
	min := 10.0
	max := 50.0
	durationSec := 2
	th := &model.Threshold{
		ID: "t1", NodeID: "n1", Metric: "temp",
		Min: &min, Max: &max, Enabled: true,
		Severity: "critical", DurationSec: &durationSec,
	}
	st := &fakeStore{thresholds: []model.Threshold{*th}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	// First violation before duration expires -> no alert yet.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if len(st.alerts) != 0 {
		t.Fatal("expected no alert before duration expires")
	}

	// Second violation still before duration -> still no alert.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":2}`))
	if len(st.alerts) != 0 {
		t.Fatal("expected no alert before duration expires")
	}

	// Simulate time passing by directly setting violation start in the past.
	if start, exists := cc.GetViolationStart(context.Background(), "n1", "temp"); exists {
		cc.SetViolationStart(context.Background(), "n1", "temp", start.Add(-3*time.Second))
	}

	// Now violation has persisted past duration -> alert should fire.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":3}`))
	if len(st.alerts) != 1 {
		t.Fatalf("expected alert after duration expires, got %d alerts", len(st.alerts))
	}
}

func TestHandleTelemetryCooldownSec(t *testing.T) {
	min := 10.0
	max := 50.0
	cooldownSec := 10
	th := &model.Threshold{
		ID: "t1", NodeID: "n1", Metric: "temp",
		Min: &min, Max: &max, Enabled: true,
		Severity: "warning", CooldownSec: &cooldownSec,
	}
	st := &fakeStore{thresholds: []model.Threshold{*th}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	// First violation -> alert.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if len(st.alerts) != 1 {
		t.Fatal("expected first alert")
	}

	// Immediate second violation -> suppressed by cooldown.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":2}`))
	if len(st.alerts) != 1 {
		t.Fatal("expected cooldown to suppress repeat alert")
	}

	// Simulate cooldown expired.
	if last, exists := cc.GetLastTriggered(context.Background(), "n1", "temp"); exists {
		cc.SetLastTriggered(context.Background(), "n1", "temp", last.Add(-11*time.Second))
	}

	// Resolve current alert first so a new one can trigger.
	cc.ClearActive(context.Background(), "n1", "temp")

	// Now after cooldown -> new alert allowed.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":3}`))
	if len(st.alerts) != 2 {
		t.Fatalf("expected alert after cooldown, got %d alerts", len(st.alerts))
	}
}

func TestHandleTelemetryCustomMessage(t *testing.T) {
	min := 10.0
	max := 50.0
	th := &model.Threshold{
		ID: "t1", NodeID: "n1", Metric: "ph",
		Min: &min, Max: &max, Enabled: true,
		Severity: "critical", Message: "Custom pH alert",
	}
	st := &fakeStore{thresholds: []model.Threshold{*th}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"ph","value":99,"ts":1}`))
	if len(st.alerts) != 1 {
		t.Fatal("expected alert")
	}
	if st.alerts[0].Message != "Custom pH alert" {
		t.Errorf("expected custom message, got %q", st.alerts[0].Message)
	}
}

func TestHandleTelemetryHysteresis(t *testing.T) {
	min := 10.0
	max := 50.0
	hyst := 2.0
	th := &model.Threshold{
		ID: "t1", NodeID: "n1", Metric: "temp",
		Min: &min, Max: &max, Enabled: true,
		Severity: "warning", Hysteresis: &hyst,
	}
	st := &fakeStore{thresholds: []model.Threshold{*th}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	// Trigger alert.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if len(st.alerts) != 1 {
		t.Fatal("expected alert triggered")
	}
	if !cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Fatal("expected active marker set")
	}

	// Value drops to 49 (above max-hysteresis=48) -> still outside, alert stays active.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":49,"ts":2}`))
	if !cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Error("expected alert to stay active above hysteresis boundary")
	}

	// Value drops to 47 (inside [min+hyst=12, max-hyst=48]) -> resolve.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":47,"ts":3}`))
	if cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Error("expected alert resolved inside hysteresis band")
	}
}

func TestHandleTelemetryHysteresisOnlyMax(t *testing.T) {
	max := 50.0
	hyst := 3.0
	th := &model.Threshold{
		ID: "t1", NodeID: "n1", Metric: "temp",
		Max: &max, Enabled: true,
		Severity: "warning", Hysteresis: &hyst,
	}
	st := &fakeStore{thresholds: []model.Threshold{*th}}
	cc := newFakeCache()
	svc := New(st, cc, nil)

	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":99,"ts":1}`))
	if len(st.alerts) != 1 {
		t.Fatal("expected alert triggered")
	}

	// Value 48 is above max-hyst=47 -> still outside, alert stays active.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":48,"ts":2}`))
	if !cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Error("expected alert active above hysteresis boundary")
	}

	// Value 47 is exactly at boundary -> should still be considered outside or boundary case.
	// Implementation checks `value > *th.Max - *th.Hysteresis`, so 47 > 47 is false -> resolves.
	svc.handleTelemetry([]byte(`{"node_id":"n1","metric":"temp","value":47,"ts":3}`))
	if cc.ActiveExists(context.Background(), "n1", "temp") {
		t.Error("expected alert resolved at hysteresis boundary")
	}
}
