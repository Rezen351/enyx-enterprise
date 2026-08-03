package handler

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"regexp"
	"strings"

	"github.com/almuzky/iot/services/stream/internal/model"
	"github.com/almuzky/iot/services/stream/internal/service"
	"github.com/go-chi/chi/v5"
)

type Handler struct {
	svc *service.StreamService
}

func New(svc *service.StreamService) *Handler {
	return &Handler{svc: svc}
}

// Health is a public liveness probe (no JWT required at the service; Kong
// also exposes it, but the container healthcheck hits it directly).
func Health(w http.ResponseWriter, r *http.Request) {
	respond(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ListStreams returns all registered streams with live status + playback URLs,
// optionally scoped to a single module via the `module_id` query param.
func (h *Handler) ListStreams(w http.ResponseWriter, r *http.Request) {
	moduleID := r.URL.Query().Get("module_id")
	streams, err := h.svc.ListStreams(r.Context(), moduleID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list streams")
		return
	}
	respond(w, http.StatusOK, map[string]any{"streams": streams, "count": len(streams)})
}

// CreateStream registers a new CCTV stream (DB + MediaMTX path).
func (h *Handler) CreateStream(w http.ResponseWriter, r *http.Request) {
	var req model.CreateStreamRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.Name == "" {
		respondError(w, http.StatusBadRequest, "name is required")
		return
	}
	view, err := h.svc.CreateStream(r.Context(), req)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrDuplicateName):
			respondError(w, http.StatusConflict, "stream name already exists")
		case errors.Is(err, service.ErrInvalidName):
			respondError(w, http.StatusBadRequest, "invalid stream name (allowed: letters, digits, _ . -; max 64 chars)")
		case errors.Is(err, service.ErrMediaMTX):
			respondError(w, http.StatusBadGateway, "failed to register path with MediaMTX")
		default:
			respondError(w, http.StatusInternalServerError, "failed to create stream")
		}
		return
	}
	respond(w, http.StatusCreated, view)
}

// GetStream returns metadata + status + playback URLs for a single stream.
func (h *Handler) GetStream(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	view, err := h.svc.GetStream(r.Context(), id)
	if err != nil {
		if errors.Is(err, service.ErrNotFound) {
			respondError(w, http.StatusNotFound, "stream not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to get stream")
		return
	}
	respond(w, http.StatusOK, view)
}

// UpdateStream patches label/location/enabled.
func (h *Handler) UpdateStream(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	var req model.UpdateStreamRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	view, err := h.svc.UpdateStream(r.Context(), id, req)
	if err != nil {
		if errors.Is(err, service.ErrNotFound) {
			respondError(w, http.StatusNotFound, "stream not found")
			return
		}
		if errors.Is(err, service.ErrInvalidName) {
			respondError(w, http.StatusBadRequest, "invalid stream name (allowed: letters, digits, _ . -; max 64 chars)")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to update stream")
		return
	}
	respond(w, http.StatusOK, view)
}

// DeleteStream unregisters a stream (MediaMTX path + DB row).
func (h *Handler) DeleteStream(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteStream(r.Context(), id); err != nil {
		if errors.Is(err, service.ErrNotFound) {
			respondError(w, http.StatusNotFound, "stream not found")
			return
		}
		if errors.Is(err, service.ErrMediaMTX) {
			respondError(w, http.StatusBadGateway, "failed to remove path from MediaMTX")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to delete stream")
		return
	}
	respond(w, http.StatusOK, map[string]string{"message": "stream deleted"})
}

// CaptureSnapshot grabs the current frame and stores it in MinIO. When the
// `detect` query param is "true" the frame is also sent to the AI vision model
// and the detection result is stored as a "detection" snapshot.
func (h *Handler) CaptureSnapshot(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	detect := r.URL.Query().Get("detect") == "true" || r.URL.Query().Get("detect") == "1"
	view, err := h.svc.CaptureSnapshot(r.Context(), id, detect)
	if err != nil {
		switch {
		case errors.Is(err, service.ErrNotFound):
			respondError(w, http.StatusNotFound, "stream not found")
		case errors.Is(err, service.ErrMinIO):
			respondError(w, http.StatusServiceUnavailable, sanitizeMsg(err.Error()))
		case errors.Is(err, service.ErrMediaMTX):
			respondError(w, http.StatusBadGateway, sanitizeMsg(err.Error()))
		default:
			respondError(w, http.StatusInternalServerError, sanitizeMsg(err.Error()))
		}
		return
	}
	respond(w, http.StatusCreated, view)
}

// GetObject serves a MinIO object (snapshot/recording/image) through the
// Stream Service using its scoped credentials. The route is JWT-protected and
// the object path is validated (no bucket/key traversal), so the underlying
// MinIO bucket can stay private.
func (h *Handler) GetObject(w http.ResponseWriter, r *http.Request) {
	raw := chi.URLParam(r, "*")
	raw = strings.TrimPrefix(raw, "/")
	parts := strings.SplitN(raw, "/", 2)
	if len(parts) < 2 {
		respondError(w, http.StatusBadRequest, "invalid storage path (expected /storage/{bucket}/{key})")
		return
	}
	bucket, key := parts[0], parts[1]
	if err := h.svc.ServeObject(w, bucket, key); err != nil {
		respondError(w, http.StatusNotFound, "object not found")
	}
}

// ListSnapshots returns all snapshots/recordings (newest first), optionally
// filtered by `kind` and/or `module_id`.
func (h *Handler) ListSnapshots(w http.ResponseWriter, r *http.Request) {
	kind := r.URL.Query().Get("kind")
	moduleID := r.URL.Query().Get("module_id")
	snaps, err := h.svc.ListSnapshots(r.Context(), kind, moduleID)
	if err != nil {
		respondError(w, http.StatusInternalServerError, "failed to list snapshots")
		return
	}
	respond(w, http.StatusOK, map[string]any{"snapshots": snaps, "count": len(snaps)})
}

// GetSnapshot returns a single snapshot.
func (h *Handler) GetSnapshot(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	view, err := h.svc.GetSnapshot(r.Context(), id)
	if err != nil {
		if errors.Is(err, service.ErrNotFound) {
			respondError(w, http.StatusNotFound, "snapshot not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to get snapshot")
		return
	}
	respond(w, http.StatusOK, view)
}

// DeleteSnapshot removes the snapshot and its MinIO object.
func (h *Handler) DeleteSnapshot(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.DeleteSnapshot(r.Context(), id); err != nil {
		if errors.Is(err, service.ErrNotFound) {
			respondError(w, http.StatusNotFound, "snapshot not found")
			return
		}
		respondError(w, http.StatusInternalServerError, "failed to delete snapshot")
		return
	}
	respond(w, http.StatusOK, map[string]string{"message": "snapshot deleted"})
}

// StartRecording begins MediaMTX recording for the path.
func (h *Handler) StartRecording(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	if err := h.svc.StartRecording(r.Context(), id); err != nil {
		respondError(w, http.StatusBadGateway, err.Error())
		return
	}
	respond(w, http.StatusOK, map[string]string{"message": "recording started"})
}

// StopRecording ends MediaMTX recording and stores a cover snapshot.
func (h *Handler) StopRecording(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	view, err := h.svc.StopRecording(r.Context(), id)
	if err != nil {
		respondError(w, http.StatusBadGateway, err.Error())
		return
	}
	respond(w, http.StatusCreated, view)
}

func respond(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": v})
}

func respondError(w http.ResponseWriter, status int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"success": false,
		"error":   map[string]string{"code": statusCode(status), "message": sanitizeMsg(msg)},
	})
}

// statusCode maps an HTTP status to a stable uppercase error code.
func statusCode(s int) string {
	switch s {
	case 400:
		return "BAD_REQUEST"
	case 401:
		return "UNAUTHORIZED"
	case 403:
		return "FORBIDDEN"
	case 404:
		return "NOT_FOUND"
	case 409:
		return "CONFLICT"
	case 429:
		return "RATE_LIMITED"
	case 502:
		return "BAD_GATEWAY"
	case 503:
		return "SERVICE_UNAVAILABLE"
	default:
		return fmt.Sprintf("ERROR_%d", s)
	}
}

// rtspCredRE matches credentials embedded in a URL of the form
// scheme://user:pass@host so they are never leaked to API clients or
// logs via error messages.
var rtspCredRE = regexp.MustCompile(`([a-zA-Z][a-zA-Z0-9+.-]*)://[^/@\s]+:[^/@\s]*@`)

// sanitizeMsg scrubs any embedded credentials from a message before it is
// returned to the client (e.g. an RTSP source URL with CCTV credentials).
func sanitizeMsg(msg string) string {
	return rtspCredRE.ReplaceAllString(msg, "$1://***:***@")
}
