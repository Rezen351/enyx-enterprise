package handler

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"strings"

	"github.com/almuzky/iot/services/control/internal/middleware"
	"github.com/almuzky/iot/services/control/internal/model"
	"github.com/almuzky/iot/services/control/internal/module"
	"github.com/almuzky/iot/services/control/internal/service"
	"github.com/go-chi/chi/v5"
)

type Handler struct {
	svc       *service.ControlService
	moduleURL string
}

func New(svc *service.ControlService, moduleURL string) *Handler {
	return &Handler{svc: svc, moduleURL: moduleURL}
}

// actuatorSourceFor builds an ActuatorSource using the caller's bearer token so
// reads from the Module Service tag-mapping are authenticated identically.
func (h *Handler) actuatorSourceFor(r *http.Request) service.ActuatorSource {
	token := bearerToken(r)
	return service.NewModuleActuatorSource(h.moduleURL, token)
}

func bearerToken(r *http.Request) string {
	const prefix = "Bearer "
	header := r.Header.Get("Authorization")
	if !strings.HasPrefix(header, prefix) {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(header, prefix))
}

// nodePaired checks the Module Service whether nodeID is paired to a module.
// Used to reject commands/schedules targeted at unpaired or unregistered nodes.
func (h *Handler) nodePaired(r *http.Request, nodeID string) (bool, error) {
	token := bearerToken(r)
	c := module.NewClient(h.moduleURL, token)
	return c.IsNodePaired(r.Context(), nodeID)
}

// ─── Health ───────────────────────────────────────────────────────────────────

func Health(w http.ResponseWriter, r *http.Request) {
	respond(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ─── Manual command ───────────────────────────────────────────────────────────

// PostCommand handles a manual control command (published immediately).
func (h *Handler) PostCommand(w http.ResponseWriter, r *http.Request) {
	var req model.CommandRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	// Use the tag set the dashboard rendered (if supplied) so manual commands
	// stay consistent with what the user saw; otherwise resolve from Module.
	var src service.ActuatorSource
	if len(req.Targets) > 0 {
		src = &service.StaticActuatorSource{Targets: req.Targets}
	} else {
		src = h.actuatorSourceFor(r)
	}
	// Reject commands targeted at an unpaired node (prevents control of unassigned hardware).
	if req.NodeID != "" {
		paired, err := h.nodePaired(r, req.NodeID)
		if err != nil {
			respondError(w, http.StatusBadGateway, "failed to verify node pairing status")
			return
		}
		if !paired {
			respondError(w, http.StatusBadRequest, "node is not paired to a module; please pair the node before issuing control commands")
			return
		}
	}
	issuedBy := middleware.UserIDFromContext(r.Context())
	cmds, err := h.svc.HandleManualCommand(r.Context(), req, issuedBy, src)
	if err != nil {
		log.Printf("[handler] HandleManualCommand error node=%s output=%s type=%s: %v", req.NodeID, req.Output, req.Type, err)
		switch {
		case errors.Is(err, service.ErrNodeRequired):
			respondError(w, http.StatusBadRequest, "node_id is required")
		case errors.Is(err, service.ErrOutputRequired):
			respondError(w, http.StatusBadRequest, "output is required")
		case errors.Is(err, service.ErrValueRequired):
			respondError(w, http.StatusBadRequest, "value is required")
		case errors.Is(err, service.ErrValueOutOfRange):
			respondError(w, http.StatusBadRequest, "value is out of range (0..255)")
		case errors.Is(err, service.ErrNodeAutoMode):
			respondError(w, http.StatusConflict, "node is in automatic mode; switch to Manual to override")
		case errors.Is(err, service.ErrNodeEmergency):
			respondError(w, http.StatusConflict, "node is in emergency stop; resume control first")
		case errors.Is(err, service.ErrUnknownType):
			respondError(w, http.StatusBadRequest, "unknown control type")
		case errors.Is(err, service.ErrMQTTUnavailable):
			respondError(w, http.StatusServiceUnavailable, "mqtt broker unavailable")
		default:
			respondError(w, http.StatusInternalServerError, "failed to dispatch command")
		}
		return
	}
	respond(w, http.StatusAccepted, map[string]any{"commands": cmds, "count": len(cmds)})
}

// ─── Commands log ─────────────────────────────────────────────────────────────

func (h *Handler) ListCommands(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	limit, _ := strconv.Atoi(q.Get("limit"))
	cmds, err := h.svc.ListCommands(r.Context(), q.Get("node_id"), limit)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list commands")
		return
	}
	respond(w, http.StatusOK, map[string]any{"commands": cmds, "count": len(cmds)})
}

// ─── Targets ──────────────────────────────────────────────────────────────────

func (h *Handler) ListTargets(w http.ResponseWriter, r *http.Request) {
	targets, err := h.svc.ListTargets(r.Context(), r.URL.Query().Get("node_id"), h.actuatorSourceFor(r))
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list targets: "+err.Error())
		return
	}
	respond(w, http.StatusOK, map[string]any{"targets": targets, "count": len(targets)})
}

// ListOutputs returns the firmware outputs discovered from telemetry for a node
// so the dashboard can offer them when the user attaches an actuator tag.
func (h *Handler) ListOutputs(w http.ResponseWriter, r *http.Request) {
	outs := h.svc.GetOutputs(r.URL.Query().Get("node_id"))
	respond(w, http.StatusOK, map[string]any{"outputs": outs, "count": len(outs)})
}

// ─── Modes ────────────────────────────────────────────────────────────────────

func (h *Handler) SetMode(w http.ResponseWriter, r *http.Request) {
	nodeID := chi.URLParam(r, "node_id")
	output := chi.URLParam(r, "output")
	var req model.ModeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.svc.SetMode(r.Context(), nodeID, output, req); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}
	respond(w, http.StatusOK, map[string]string{"node_id": nodeID, "output": output, "mode": req.Mode})
}

// ─── Node-level control mode ────────────────────────────────────────────

func (h *Handler) SetNodeMode(w http.ResponseWriter, r *http.Request) {
	nodeID := chi.URLParam(r, "node_id")
	var req model.ModeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.svc.SetNodeMode(r.Context(), nodeID, req.Mode); err != nil {
		respondError(w, http.StatusBadRequest, err.Error())
		return
	}
	respond(w, http.StatusOK, map[string]string{"node_id": nodeID, "mode": strings.ToUpper(req.Mode)})
}

func (h *Handler) GetNodeMode(w http.ResponseWriter, r *http.Request) {
	nodeID := chi.URLParam(r, "node_id")
	respond(w, http.StatusOK, map[string]string{"node_id": nodeID, "mode": h.svc.GetNodeMode(r.Context(), nodeID)})
}

func (h *Handler) ResumeNode(w http.ResponseWriter, r *http.Request) {
	nodeID := chi.URLParam(r, "node_id")
	mode, err := h.svc.ResumeNode(r.Context(), nodeID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to resume: "+err.Error())
		return
	}
	respond(w, http.StatusOK, map[string]string{"node_id": nodeID, "mode": mode})
}

// ─── Schedules ────────────────────────────────────────────────────────────────

func (h *Handler) CreateSchedule(w http.ResponseWriter, r *http.Request) {
	var req model.ScheduleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.NodeID != "" {
		paired, err := h.nodePaired(r, req.NodeID)
		if err != nil {
			respondError(w, http.StatusBadGateway, "failed to verify node pairing status")
			return
		}
		if !paired {
			respondError(w, http.StatusBadRequest, "node is not paired to a module; please pair the node before issuing control commands")
			return
		}
	}
	sc, err := h.svc.CreateSchedule(r.Context(), req)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrNodeRequired):
			respondError(w, http.StatusBadRequest, "node_id is required")
		case errors.Is(err, service.ErrOutputRequired):
			respondError(w, http.StatusBadRequest, "output_name is required")
		default:
			respondError(w, http.StatusInternalServerError, "failed to create schedule")
		}
		return
	}
	respond(w, http.StatusCreated, sc)
}

func (h *Handler) ListSchedules(w http.ResponseWriter, r *http.Request) {
	scs, err := h.svc.ListSchedules(r.Context(), r.URL.Query().Get("node_id"))
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list schedules")
		return
	}
	respond(w, http.StatusOK, map[string]any{"schedules": scs, "count": len(scs)})
}

func (h *Handler) GetSchedule(w http.ResponseWriter, r *http.Request) {
	sc, err := h.svc.GetSchedule(r.Context(), chi.URLParam(r, "id"))
	if err != nil {
		if errors.Is(err, service.ErrScheduleNotFound) {
			respondError(w, http.StatusNotFound, "schedule not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to get schedule")
		return
	}
	respond(w, http.StatusOK, sc)
}

func (h *Handler) UpdateSchedule(w http.ResponseWriter, r *http.Request) {
	var req model.ScheduleRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	sc, err := h.svc.UpdateSchedule(r.Context(), chi.URLParam(r, "id"), req)
	if err != nil {
		if errors.Is(err, service.ErrScheduleNotFound) {
			respondError(w, http.StatusNotFound, "schedule not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to update schedule")
		return
	}
	respond(w, http.StatusOK, sc)
}

func (h *Handler) EnableSchedule(w http.ResponseWriter, r *http.Request) {
	h.setEnabled(w, r, true)
}

func (h *Handler) DisableSchedule(w http.ResponseWriter, r *http.Request) {
	h.setEnabled(w, r, false)
}

func (h *Handler) setEnabled(w http.ResponseWriter, r *http.Request, enabled bool) {
	id := chi.URLParam(r, "id")
	if err := h.svc.SetScheduleEnabled(r.Context(), id, enabled); err != nil {
		if errors.Is(err, service.ErrScheduleNotFound) {
			respondError(w, http.StatusNotFound, "schedule not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to update schedule")
		return
	}
	respond(w, http.StatusOK, map[string]any{"id": id, "enabled": enabled})
}

func (h *Handler) DeleteSchedule(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteSchedule(r.Context(), id); err != nil {
		if errors.Is(err, service.ErrScheduleNotFound) {
			respondError(w, http.StatusNotFound, "schedule not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to delete schedule")
		return
	}
	respond(w, http.StatusOK, map[string]string{"message": "schedule deleted"})
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	// Standard API response wrapper (AGENTS.md §4.4): { success, data }.
	_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": v})
}

// respondError emits the standard error envelope (AGENTS.md §4.4):
// { success:false, error:{ code, message } }. It writes the envelope directly
// so the error payload is not re-wrapped by respond().
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
