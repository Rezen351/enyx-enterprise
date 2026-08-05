package handler

import (
	"encoding/json"
	"errors"
	"net/http"
	"regexp"
	"strconv"
	"time"

	"github.com/almuzky/iot/services/alert/internal/middleware"
	"github.com/almuzky/iot/services/alert/internal/model"
	"github.com/almuzky/iot/services/alert/internal/repository"
	"github.com/almuzky/iot/services/alert/internal/service"
	"github.com/go-chi/chi/v5"
	"github.com/google/uuid"
)

// Input-validation constraints for threshold configuration. node_id allows a
// "*" wildcard (applies the threshold to every node for that metric). These
// reject spaces, quotes, angle brackets, and SQL/HTML metacharacters to prevent
// stored XSS/injection and to reject malformed identifiers with 400 (not 500).
var (
	nodeIDRe = regexp.MustCompile(`^[A-Za-z0-9_.:*-]{1,64}$`)
	metricRe = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,128}$`)
)

// allowedSeverity is the closed set of severities the API accepts.
var allowedSeverity = map[string]bool{"info": true, "warning": true, "critical": true}

type Handler struct {
	store service.Store
	svc   *service.Service
}

func New(store service.Store, svc *service.Service) *Handler {
	return &Handler{store: store, svc: svc}
}

// Health reports service liveness.
func Health(w http.ResponseWriter, r *http.Request) {
	respond(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ─── Alerts ─────────────────────────────────────────────────────────────────

// ListAlerts returns paginated alert history with optional filters.
func (h *Handler) ListAlerts(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	limit := atoiDefault(q.Get("limit"), 50)
	if limit < 1 || limit > 500 {
		limit = 50
	}
	offset := atoiDefault(q.Get("offset"), 0)
	if offset < 0 {
		offset = 0
	}

	f := repository.AlertFilter{
		NodeID:   q.Get("node_id"),
		Metric:   q.Get("metric"),
		Status:   q.Get("status"),
		Severity: q.Get("severity"),
		From:     parseTime(q.Get("from")),
		To:       parseTime(q.Get("to")),
	}

	alerts, total, err := h.store.ListAlerts(r.Context(), f, limit, offset)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to query alerts")
		return
	}
	dtos := make([]model.AlertDTO, 0, len(alerts))
	for _, a := range alerts {
		dtos = append(dtos, model.ToAlertDTO(a))
	}
	respond(w, http.StatusOK, map[string]any{
		"alerts": dtos,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

// AckAlert acknowledges an active/resolved alert (operator/admin only).
func (h *Handler) AckAlert(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if id == "" {
		respondError(w, http.StatusBadRequest, "alert id required")
		return
	}
	userID := middleware.UserIDFromContext(r.Context())
	if userID == "" {
		userID = "system"
	}
	alert, err := h.svc.AckAlert(r.Context(), id, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			respondError(w, http.StatusNotFound, "alert not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to acknowledge alert")
		return
	}
	respond(w, http.StatusOK, model.ToAlertDTO(*alert))
}

// ─── Thresholds ───────────────────────────────────────────────────────────

// ListThresholds returns threshold configurations (optional filters).
func (h *Handler) ListThresholds(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	ts, err := h.store.ListThresholds(r.Context(), q.Get("node_id"), q.Get("metric"), false)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to query thresholds")
		return
	}
	dtos := make([]model.ThresholdDTO, 0, len(ts))
	for _, t := range ts {
		dtos = append(dtos, model.ToThresholdDTO(t))
	}
	respond(w, http.StatusOK, map[string]any{"thresholds": dtos, "total": len(dtos)})
}

type thresholdRequest struct {
	NodeID      string   `json:"node_id"`
	Metric      string   `json:"metric"`
	Min         *float64 `json:"min"`
	Max         *float64 `json:"max"`
	Enabled     *bool    `json:"enabled"`
	Severity    string   `json:"severity"`
	Message     string   `json:"message"`
	DurationSec *int     `json:"duration_sec"`
	CooldownSec *int     `json:"cooldown_sec"`
	Hysteresis  *float64 `json:"hysteresis"`
}

// CreateThreshold adds a new threshold configuration.
func (h *Handler) CreateThreshold(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromContext(r.Context())
	if userID == "" {
		userID = "system"
	}
	var req thresholdRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.NodeID == "" || req.Metric == "" {
		respondError(w, http.StatusBadRequest, "node_id and metric are required")
		return
	}
	if !nodeIDRe.MatchString(req.NodeID) {
		respondError(w, http.StatusBadRequest, "node_id contains invalid characters")
		return
	}
	if !metricRe.MatchString(req.Metric) {
		respondError(w, http.StatusBadRequest, "metric contains invalid characters")
		return
	}
	if req.Min == nil && req.Max == nil {
		respondError(w, http.StatusBadRequest, "at least one of min or max is required")
		return
	}
	if req.Min != nil && req.Max != nil && *req.Min > *req.Max {
		respondError(w, http.StatusBadRequest, "min must be less than or equal to max")
		return
	}
	severity := req.Severity
	if severity == "" {
		severity = "warning"
	}
	if !allowedSeverity[severity] {
		respondError(w, http.StatusBadRequest, "severity must be one of: info, warning, critical")
		return
	}
	enabled := true
	if req.Enabled != nil {
		enabled = *req.Enabled
	}
	var durationSec *int
	if req.DurationSec != nil && *req.DurationSec >= 0 {
		durationSec = req.DurationSec
	}
	var cooldownSec *int
	if req.CooldownSec != nil && *req.CooldownSec >= 0 {
		cooldownSec = req.CooldownSec
	}
	var hysteresis *float64
	if req.Hysteresis != nil && *req.Hysteresis >= 0 {
		hysteresis = req.Hysteresis
	}
	if durationSec != nil && *durationSec > 3600 {
		respondError(w, http.StatusBadRequest, "duration_sec must be <= 3600")
		return
	}
	if cooldownSec != nil && *cooldownSec > 86400 {
		respondError(w, http.StatusBadRequest, "cooldown_sec must be <= 86400")
		return
	}
	if hysteresis != nil && *hysteresis > 100 {
		respondError(w, http.StatusBadRequest, "hysteresis seems unreasonably large")
		return
	}
	t := &model.Threshold{
		ID:          uuid.NewString(),
		NodeID:      req.NodeID,
		Metric:      req.Metric,
		Min:         req.Min,
		Max:         req.Max,
		Enabled:     enabled,
		Severity:    severity,
		Message:     req.Message,
		DurationSec: durationSec,
		CooldownSec: cooldownSec,
		Hysteresis:  hysteresis,
	}
	created, err := h.svc.CreateThreshold(r.Context(), t, userID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to create threshold")
		return
	}
	respond(w, http.StatusCreated, model.ToThresholdDTO(*created))
}

// UpdateThreshold patches a threshold configuration.
func (h *Handler) UpdateThreshold(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromContext(r.Context())
	if userID == "" {
		userID = "system"
	}
	id := chi.URLParam(r, "id")
	if id == "" {
		respondError(w, http.StatusBadRequest, "threshold id required")
		return
	}
	var req thresholdRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	patch := map[string]any{}
	if req.NodeID != "" {
		if !nodeIDRe.MatchString(req.NodeID) {
			respondError(w, http.StatusBadRequest, "node_id contains invalid characters")
			return
		}
		patch["node_id"] = req.NodeID
	}
	if req.Metric != "" {
		if !metricRe.MatchString(req.Metric) {
			respondError(w, http.StatusBadRequest, "metric contains invalid characters")
			return
		}
		patch["metric"] = req.Metric
	}
	if req.Min != nil {
		patch["min"] = *req.Min
	}
	if req.Max != nil {
		patch["max"] = *req.Max
	}
	if req.Enabled != nil {
		patch["enabled"] = *req.Enabled
	}
	if req.Severity != "" {
		if !allowedSeverity[req.Severity] {
			respondError(w, http.StatusBadRequest, "severity must be one of: info, warning, critical")
			return
		}
		patch["severity"] = req.Severity
	}
	if req.Message != "" {
		patch["message"] = req.Message
	}
	if req.DurationSec != nil {
		if *req.DurationSec < 0 || *req.DurationSec > 3600 {
			respondError(w, http.StatusBadRequest, "duration_sec must be between 0 and 3600")
			return
		}
		patch["duration_sec"] = *req.DurationSec
	}
	if req.CooldownSec != nil {
		if *req.CooldownSec < 0 || *req.CooldownSec > 86400 {
			respondError(w, http.StatusBadRequest, "cooldown_sec must be between 0 and 86400")
			return
		}
		patch["cooldown_sec"] = *req.CooldownSec
	}
	if req.Hysteresis != nil {
		if *req.Hysteresis < 0 || *req.Hysteresis > 100 {
			respondError(w, http.StatusBadRequest, "hysteresis must be between 0 and 100")
			return
		}
		patch["hysteresis"] = *req.Hysteresis
	}
	if len(patch) == 0 {
		respondError(w, http.StatusBadRequest, "no fields to update")
		return
	}
	updated, err := h.svc.UpdateThreshold(r.Context(), id, patch, userID)
	if err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			respondError(w, http.StatusNotFound, "threshold not found")
			return
		}
		if errors.Is(err, service.ErrInvalidRange) {
			respondError(w, http.StatusBadRequest, "min must be less than or equal to max")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to update threshold")
		return
	}
	respond(w, http.StatusOK, model.ToThresholdDTO(*updated))
}

// DeleteThreshold removes a threshold configuration.
func (h *Handler) DeleteThreshold(w http.ResponseWriter, r *http.Request) {
	userID := middleware.UserIDFromContext(r.Context())
	if userID == "" {
		userID = "system"
	}
	id := chi.URLParam(r, "id")
	if id == "" {
		respondError(w, http.StatusBadRequest, "threshold id required")
		return
	}
	if err := h.svc.DeleteThreshold(r.Context(), id, userID); err != nil {
		if errors.Is(err, repository.ErrNotFound) {
			respondError(w, http.StatusNotFound, "threshold not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to delete threshold")
		return
	}
	respond(w, http.StatusOK, map[string]string{"status": "deleted", "id": id})
}

// ─── Helpers ────────────────────────────────────────────────────────────────

func atoiDefault(s string, def int) int {
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return def
	}
	return n
}

func parseTime(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	if t, err := time.Parse(time.RFC3339, s); err == nil {
		return t
	}
	return time.Time{}
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// Standard API response wrapper (AGENTS.md §4.4): { success, data }.
	_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": v})
}

// respondError emits the standard error envelope (AGENTS.md §4.4):
// { success:false, error:{ code, message } }.
func respondError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"success": false,
		"error":   map[string]string{"code": errorCode(status), "message": msg},
	})
}

// errorCode maps an HTTP status to a stable machine-readable error code.
func errorCode(status int) string {
	switch status {
	case http.StatusBadRequest:
		return "BAD_REQUEST"
	case http.StatusUnauthorized:
		return "UNAUTHORIZED"
	case http.StatusForbidden:
		return "FORBIDDEN"
	case http.StatusNotFound:
		return "NOT_FOUND"
	case http.StatusConflict:
		return "CONFLICT"
	default:
		return "INTERNAL_ERROR"
	}
}
