package handler

import (
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/almuzky/iot/services/audit/internal/model"
	"github.com/almuzky/iot/services/audit/internal/repository"
)

type Handler struct {
	store *repository.Store
}

func New(store *repository.Store) *Handler {
	return &Handler{store: store}
}

// Health reports service liveness.
func Health(w http.ResponseWriter, r *http.Request) {
	respond(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ListLogs returns paginated audit logs with optional event + free-text search
// filters, restricted to an optional time window (from/to, RFC3339).
func (h *Handler) ListLogs(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	limit := atoiDefault(q.Get("limit"), 50)
	if limit < 1 || limit > 500 {
		limit = 50
	}
	offset := atoiDefault(q.Get("offset"), 0)
	if offset < 0 {
		offset = 0
	}
	event := q.Get("event")
	search := q.Get("search")
	from, to := parseTimeParam(q.Get("from")), parseTimeParam(q.Get("to"))

	logs, total, err := h.store.List(r.Context(), event, search, from, to, limit, offset)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "INTERNAL_ERROR", "failed to query audit logs")
		return
	}
	dtos := make([]model.AuditLogDTO, 0, len(logs))
	for _, l := range logs {
		dtos = append(dtos, model.ToDTO(l))
	}
	respond(w, http.StatusOK, map[string]any{
		"logs":   dtos,
		"total":  total,
		"limit":  limit,
		"offset": offset,
	})
}

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

// parseTimeParam parses an RFC3339 timestamp; returns zero time when empty/invalid.
func parseTimeParam(s string) time.Time {
	if s == "" {
		return time.Time{}
	}
	t, err := time.Parse(time.RFC3339, s)
	if err != nil {
		return time.Time{}
	}
	return t
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// Standard API response wrapper (AGENTS.md §4.4): { success, data }.
	_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": v})
}

// respondError emits the standard error envelope (AGENTS.md §4.4):
// { success:false, error:{ code, message } }.
func respondError(w http.ResponseWriter, status int, code, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"success": false,
		"error":   map[string]string{"code": code, "message": msg},
	})
}
