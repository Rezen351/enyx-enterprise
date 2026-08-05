package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/almuzky/iot/services/alert/internal/model"
	"github.com/almuzky/iot/services/alert/internal/repository"
	"github.com/almuzky/iot/services/alert/internal/service"
	"github.com/go-chi/chi/v5"
)

// withURLParam injects chi URL params into the request context so that
// chi.URLParam works in handler unit tests.
func withURLParam(req *http.Request, params map[string]string) *http.Request {
	rctx := chi.NewRouteContext()
	for k, v := range params {
		rctx.URLParams.Add(k, v)
	}
	return req.WithContext(context.WithValue(req.Context(), chi.RouteCtxKey, rctx))
}

// fakeStore implements service.Store for handler tests.
type fakeStore struct {
	alerts     []model.Alert
	thresholds []model.Threshold
	err        error
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

func (f *fakeStore) CreateAlert(ctx context.Context, a *model.Alert) error { return f.err }
func (f *fakeStore) ResolveActive(ctx context.Context, nodeID, metric string, resolvedAt time.Time) error {
	return f.err
}
func (f *fakeStore) GetLatestActive(ctx context.Context, nodeID, metric string) (*model.Alert, error) {
	return nil, f.err
}
func (f *fakeStore) AckAlert(ctx context.Context, id, userID string, ackedAt time.Time) (*model.Alert, error) {
	if f.err != nil {
		return nil, f.err
	}
	for i := range f.alerts {
		if f.alerts[i].ID == id {
			a := f.alerts[i]
			a.Status = "acked"
			return &a, nil
		}
	}
	return nil, repository.ErrNotFound
}
func (f *fakeStore) GetThresholdForNodeMetric(ctx context.Context, nodeID, metric string) (*model.Threshold, error) {
	return nil, f.err
}
func (f *fakeStore) ListThresholds(ctx context.Context, nodeID, metric string, enabledOnly bool) ([]model.Threshold, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.thresholds, nil
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

// resolve converts fakeSvc to *service.Service is not possible; instead we
// re-declare the handler accepting the concrete service. The handler.New
// signature requires a *service.Service. To exercise the handler in isolation
// we construct a real *service.Service backed by a fake store/cache and a
// stubbed error path via the store. So we use fakeStore + a fakeCache wired
// into a *service.Service, and force error cases through store errors.

func newTestService(st service.Store, cc service.Cache) *service.Service {
	return service.New(st, cc, nil)
}

type fakeCache struct {
	thresholds map[string]*model.Threshold
	active     map[string]bool
}

func (c *fakeCache) GetCachedThreshold(ctx context.Context, nodeID, metric string) *model.Threshold {
	return c.thresholds[nodeID+":"+metric]
}
func (c *fakeCache) SetCachedThreshold(ctx context.Context, nodeID, metric string, t *model.Threshold) {
}
func (c *fakeCache) ClearThreshold(ctx context.Context, nodeID, metric string) {}
func (c *fakeCache) ActiveExists(ctx context.Context, nodeID, metric string) bool {
	return c.active[nodeID+":"+metric]
}
func (c *fakeCache) SetActive(ctx context.Context, nodeID, metric string) {
	c.active[nodeID+":"+metric] = true
}
func (c *fakeCache) ClearActive(ctx context.Context, nodeID, metric string) {
	c.active[nodeID+":"+metric] = false
}

func (c *fakeCache) GetViolationStart(ctx context.Context, nodeID, metric string) (time.Time, bool) {
	return time.Time{}, false
}

func (c *fakeCache) SetViolationStart(ctx context.Context, nodeID, metric string, t time.Time) {}

func (c *fakeCache) ClearViolationStart(ctx context.Context, nodeID, metric string) {}

func (c *fakeCache) GetLastTriggered(ctx context.Context, nodeID, metric string) (time.Time, bool) {
	return time.Time{}, false
}

func (c *fakeCache) SetLastTriggered(ctx context.Context, nodeID, metric string, t time.Time) {}

func TestHealth(t *testing.T) {
	rec := httptest.NewRecorder()
	Health(rec, httptest.NewRequest(http.MethodGet, "/health", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestListAlertsSuccess(t *testing.T) {
	st := &fakeStore{alerts: []model.Alert{{ID: "a1"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/alerts?limit=10", nil)
	h.ListAlerts(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d (%s)", rec.Code, rec.Body.String())
	}
	var body map[string]any
	_ = json.Unmarshal(rec.Body.Bytes(), &body)
	d := body["data"].(map[string]any)
	if d["total"].(float64) != 1 {
		t.Errorf("expected total 1, got %v", d["total"])
	}
}

func TestListAlertsDBError(t *testing.T) {
	st := &fakeStore{err: errors.New("db")}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/alerts", nil)
	h.ListAlerts(rec, req)
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("expected 500, got %d", rec.Code)
	}
}

func TestAckAlertNotFound(t *testing.T) {
	st := &fakeStore{}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/alerts/x/ack", nil), map[string]string{"id": "x"})
	h.AckAlert(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func TestAckAlertSuccess(t *testing.T) {
	st := &fakeStore{alerts: []model.Alert{{ID: "a1"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/alerts/a1/ack", nil), map[string]string{"id": "a1"})
	h.AckAlert(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestAckAlertEmptyID(t *testing.T) {
	st := &fakeStore{}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)
	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/alerts//ack", nil), map[string]string{"id": ""})
	h.AckAlert(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}

func TestListThresholdsSuccess(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/thresholds", nil)
	h.ListThresholds(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestCreateThresholdSuccess(t *testing.T) {
	st := &fakeStore{}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	body := `{"node_id":"n1","metric":"temp","min":10,"max":50,"severity":"warning"}`
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/thresholds", bytes.NewBufferString(body))
	h.CreateThreshold(rec, req)
	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d (%s)", rec.Code, rec.Body.String())
	}
}

func TestCreateThresholdValidationErrors(t *testing.T) {
	cases := []struct {
		name string
		body string
	}{
		{"missing node_id", `{"metric":"temp","min":1}`},
		{"missing metric", `{"node_id":"n1","min":1}`},
		{"bad node_id", `{"node_id":"n1!","metric":"temp","min":1}`},
		{"bad metric", `{"node_id":"n1","metric":"tem p","min":1}`},
		{"no minmax", `{"node_id":"n1","metric":"temp"}`},
		{"minmax inverted", `{"node_id":"n1","metric":"temp","min":50,"max":10}`},
		{"bad severity", `{"node_id":"n1","metric":"temp","min":1,"severity":"loud"}`},
		{"bad json", `not json`},
	}
	for _, tc := range cases {
		st := &fakeStore{}
		svc := newTestService(st, &fakeCache{active: map[string]bool{}})
		h := New(st, svc)
		rec := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodPost, "/thresholds", bytes.NewBufferString(tc.body))
		h.CreateThreshold(rec, req)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("%s: expected 400, got %d (%s)", tc.name, rec.Code, rec.Body.String())
		}
	}
}

func TestUpdateThresholdSuccess(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1", NodeID: "n1", Metric: "temp"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/thresholds/t1", bytes.NewBufferString(`{"max":99}`)), map[string]string{"id": "t1"})
	h.UpdateThreshold(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d (%s)", rec.Code, rec.Body.String())
	}
}

func TestUpdateThresholdNotFound(t *testing.T) {
	st := &fakeStore{err: repository.ErrNotFound}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/thresholds/missing", bytes.NewBufferString(`{"max":99}`)), map[string]string{"id": "missing"})
	h.UpdateThreshold(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func TestUpdateThresholdNoFields(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodPut, "/thresholds/t1", bytes.NewBufferString(`{}`)), map[string]string{"id": "t1"})
	h.UpdateThreshold(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}
}

func TestDeleteThresholdSuccess(t *testing.T) {
	st := &fakeStore{thresholds: []model.Threshold{{ID: "t1"}}}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodDelete, "/thresholds/t1", nil), map[string]string{"id": "t1"})
	h.DeleteThreshold(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestDeleteThresholdNotFound(t *testing.T) {
	st := &fakeStore{err: repository.ErrNotFound}
	svc := newTestService(st, &fakeCache{active: map[string]bool{}})
	h := New(st, svc)

	rec := httptest.NewRecorder()
	req := withURLParam(httptest.NewRequest(http.MethodDelete, "/thresholds/missing", nil), map[string]string{"id": "missing"})
	h.DeleteThreshold(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}
