package service

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/almuzky/iot/services/control/internal/model"
	"github.com/almuzky/iot/services/control/internal/outbox"
	"github.com/almuzky/iot/services/control/internal/repository"
	"github.com/google/uuid"
)

var (
	ErrNodeRequired     = errors.New("node_id is required")
	ErrOutputRequired   = errors.New("output is required")
	ErrValueRequired    = errors.New("value is required")
	ErrValueOutOfRange  = errors.New("value is out of range")
	ErrUnknownType      = errors.New("unknown control type")
	ErrScheduleNotFound = errors.New("schedule not found")
	ErrMQTTUnavailable  = errors.New("mqtt broker unavailable")
	// ErrNodeAutoMode is returned when a manual command is issued to a node that
	// is under automatic (scheduled) control. The caller must switch the node
	// to MANUAL before overriding (arbitration: MANUAL overrides AUTO).
	ErrNodeAutoMode = errors.New("node is in automatic mode; switch to Manual to override")
	// ErrNodeEmergency is returned when a command is issued while the node is in
	// EMERGENCY stop. The caller must resume control first.
	ErrNodeEmergency = errors.New("node is in emergency stop; resume control first")
)

// NATSPublisher is a minimal interface for publishing audit/events.
type NATSPublisher interface {
	Publish(subject string, data []byte) error
}

// Publisher is the subset of the MQTT client the service needs.
type Publisher interface {
	PublishSetOutput(nodeID, target string, value int, reqID string) error
	IsConnected() bool
}

// Scheduler is the optional control-plane hook the service uses to ask the
// scheduler engine to re-evaluate immediately after a schedule is created,
// enabled, disabled, updated, or deleted — so changes take effect without
// waiting for the next periodic reconcile (important for stop/disarm latency).
type Scheduler interface {
	NotifyScheduleChanged()
}

// ActuatorSource yields the controllable outputs (actuator tags) for a node.
// The real implementation reads the Module Service tag-mapping; the dashboard
// may also inject the exact tag set it rendered so manual commands stay
// consistent with what the user saw.
type ActuatorSource interface {
	GetActuators(ctx context.Context, nodeID string) ([]model.ControlTarget, error)
}

type ControlService struct {
	repo *repository.Repository
	pub  Publisher
	nats NATSPublisher

	// actuatorSource resolves actuator tags (Module Service tag-mapping).
	actuatorSource ActuatorSource

	// sched is the optional hook used to trigger an immediate scheduler
	// reconcile after a schedule mutation (so disable/delete takes effect
	// without waiting for the periodic reconcile).
	sched Scheduler

	// latest telemetry payload per node (for threshold evaluation).
	mu     sync.RWMutex
	latest map[string]map[string]interface{}
	// firmwareOutputs: output name -> (type, current value) per node, discovered
	// from telemetry.outputs. Used to offer the user the selectable outputs when
	// attaching an actuator tag.
	outputs map[string]map[string]outputInfo
	// last known output value per node+source_key (for toggle). In-memory;
	// seeded from telemetry output states, updated after each dispatch.
	state map[string]map[string]int
}

// outputInfo describes a firmware output discovered from telemetry.
type outputInfo struct {
	Type  string // DIGITAL | PWM
	Value int
}

// FirmwareOutput is the public shape returned to the dashboard for selection.
type FirmwareOutput struct {
	Name  string `json:"name"`
	Type  string `json:"type"`
	Value int    `json:"value"`
}

func New(repo *repository.Repository, pub Publisher, nats NATSPublisher, actuatorSource ActuatorSource) *ControlService {
	return &ControlService{
		repo:           repo,
		pub:            pub,
		nats:           nats,
		actuatorSource: actuatorSource,
		latest:         make(map[string]map[string]interface{}),
		outputs:        make(map[string]map[string]outputInfo),
		state:          make(map[string]map[string]int),
	}
}

// GetOutputs returns the firmware outputs discovered from telemetry for a node,
// so the dashboard can offer them when the user attaches an actuator tag.
func (s *ControlService) GetOutputs(nodeID string) []FirmwareOutput {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m := s.outputs[nodeID]
	if len(m) == 0 {
		return []FirmwareOutput{}
	}
	out := make([]FirmwareOutput, 0, len(m))
	for name, info := range m {
		out = append(out, FirmwareOutput{Name: name, Type: info.Type, Value: info.Value})
	}
	return out
}

// SetPublisher lets main wire the concrete MQTT client after construction.
func (s *ControlService) SetPublisher(pub Publisher) { s.pub = pub }

// SetActuatorSource lets main swap the tag source (e.g. per-request module client).
func (s *ControlService) SetActuatorSource(a ActuatorSource) { s.actuatorSource = a }

// SetScheduler lets main wire the scheduler engine so schedule mutations
// (create/enable/disable/update/delete) trigger an immediate reconcile.
func (s *ControlService) SetScheduler(sc Scheduler) { s.sched = sc }

// notifyScheduler asks the engine to reconcile immediately so a schedule
// mutation takes effect without waiting for the periodic reconcile.
func (s *ControlService) notifyScheduler() {
	if s.sched != nil {
		s.sched.NotifyScheduleChanged()
	}
}

// ─── Manual commands ──────────────────────────────────────────────────────────

// HandleManualCommand resolves a high-level manual command into one or more
// set_output dispatches (published immediately).
func (s *ControlService) HandleManualCommand(ctx context.Context, req model.CommandRequest, issuedBy string, src ActuatorSource) ([]model.Command, error) {
	if req.NodeID == "" {
		return nil, ErrNodeRequired
	}
	// Node-mode arbitration: in AUTOMATIC mode a manual override is
	// rejected (schedules own the output); EMERGENCY_STOP always wins.
	// Requests with Bypass=true are allowed even in AUTO mode so that
	// automation services (e.g. PPO controller) can override specific
	// outputs without requiring a manual mode switch.
	nodeMode := s.GetNodeMode(ctx, req.NodeID)
	if req.Type != model.TypeEmergencyStop && !req.Bypass {
		if nodeMode == model.ModeEmergency {
			return nil, ErrNodeEmergency
		}
		if nodeMode == model.ModeAuto {
			return nil, ErrNodeAutoMode
		}
	}
	switch req.Type {
	case model.TypeSetState, model.TypeSetLevel:
		if req.Output == "" {
			return nil, ErrOutputRequired
		}
		if req.Value == nil {
			return nil, ErrValueRequired
		}
		if *req.Value < 0 || *req.Value > 255 {
			return nil, ErrValueOutOfRange
		}
		tag := s.lookupTag(src, req.NodeID, req.Output)
		c, err := s.dispatch(ctx, req.NodeID, req.Output, tag, *req.Value, req.Type, model.SourceManual, nil, issuedBy)
		if err != nil {
			return nil, err
		}
		return []model.Command{*c}, nil

	case model.TypeToggle:
		if req.Output == "" {
			return nil, ErrOutputRequired
		}
		cur, ok := s.getState(req.NodeID, req.Output)
		next := 1
		if ok && cur > 0 {
			next = 0
		}
		tag := s.lookupTag(src, req.NodeID, req.Output)
		c, err := s.dispatch(ctx, req.NodeID, req.Output, tag, next, model.TypeToggle, model.SourceManual, nil, issuedBy)
		if err != nil {
			return nil, err
		}
		return []model.Command{*c}, nil

	case model.TypePulse:
		if req.Output == "" {
			return nil, ErrOutputRequired
		}
		dur := req.DurationSec
		if dur <= 0 {
			dur = 5
		}
		onVal := 1
		if req.Value != nil {
			onVal = *req.Value
		}
		tag := s.lookupTag(src, req.NodeID, req.Output)
		c, err := s.dispatch(ctx, req.NodeID, req.Output, tag, onVal, model.TypePulse, model.SourceManual, nil, issuedBy)
		if err != nil {
			return nil, err
		}
		// Schedule the OFF after the pulse window (server-side timer).
		go func(nodeID, output, tagName string, d int) {
			time.Sleep(time.Duration(d) * time.Second)
			bg, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			if _, err := s.dispatch(bg, nodeID, output, tagName, 0, model.TypePulse, model.SourceManual, nil, issuedBy); err != nil {
				log.Printf("[svc] pulse OFF failed node=%s output=%s: %v", nodeID, output, err)
			}
		}(req.NodeID, req.Output, tag, dur)
		return []model.Command{*c}, nil

	case model.TypeEmergencyStop:
		// Enter EMERGENCY mode so schedules pause and the UI shows it.
		// Persist the pre-emergency mode so Resume can restore it.
		prev := s.GetNodeMode(ctx, req.NodeID)
		if err := s.EnterEmergency(ctx, req.NodeID, prev); err != nil {
			log.Printf("[svc] emergency stop mode set failed %s: %v", req.NodeID, err)
		}
		acts, err := s.resolveActuators(ctx, src, req.NodeID)
		if err != nil {
			return nil, err
		}
		var cmds []model.Command
		for _, t := range acts {
			c, err := s.dispatch(ctx, req.NodeID, t.SourceKey, t.TagName, 0, model.TypeEmergencyStop, model.SourceManual, nil, issuedBy)
			if err != nil {
				log.Printf("[svc] emergency stop %s/%s failed: %v", req.NodeID, t.SourceKey, err)
				continue
			}
			cmds = append(cmds, *c)
		}
		s.publishAudit("control.emergency_stop", map[string]string{"node_id": req.NodeID, "by": issuedBy})
		return cmds, nil

	default:
		return nil, ErrUnknownType
	}
}

// ─── Actuator resolution (from Module Service tag-mapping) ─────────────────────

func (s *ControlService) resolveActuators(ctx context.Context, src ActuatorSource, nodeID string) ([]model.ControlTarget, error) {
	if src != nil {
		return src.GetActuators(ctx, nodeID)
	}
	if s.actuatorSource != nil {
		return s.actuatorSource.GetActuators(ctx, nodeID)
	}
	return nil, errors.New("no actuator source configured")
}

func (s *ControlService) lookupTag(src ActuatorSource, nodeID, output string) string {
	acts, err := s.resolveActuators(context.Background(), src, nodeID)
	if err != nil {
		return ""
	}
	for _, t := range acts {
		if t.SourceKey == output || t.TagName == output {
			return t.TagName
		}
	}
	return ""
}

// ─── Dispatch (low-level) ─────────────────────────────────────────────────────

// Dispatch is the low-level command path used by both manual handlers and the
// scheduler. It logs, publishes set_output, and tracks status.
func (s *ControlService) Dispatch(ctx context.Context, nodeID, target, tagName string, value int, controlType, source string, scheduleID *string) (*model.Command, error) {
	return s.dispatch(ctx, nodeID, target, tagName, value, controlType, source, scheduleID, "")
}

func (s *ControlService) dispatch(ctx context.Context, nodeID, target, tagName string, value int, controlType, source string, scheduleID *string, issuedBy string) (*model.Command, error) {
	reqID := uuid.New().String()
	cmd := &model.Command{
		ID:          uuid.New().String(),
		ReqID:       reqID,
		NodeID:      nodeID,
		Target:      target,
		TagName:     tagName,
		ControlType: controlType,
		Value:       value,
		Source:      source,
		ScheduleID:  scheduleID,
		Status:      model.StatusPending,
		IssuedBy:    issuedBy,
	}
	if err := s.repo.CreateCommand(ctx, cmd); err != nil {
		return nil, err
	}

	if s.pub == nil || !s.pub.IsConnected() {
		_ = s.repo.UpdateCommandStatus(ctx, cmd.ID, model.StatusFailed)
		cmd.Status = model.StatusFailed
		s.publishAudit("control.command.failed", map[string]string{"node_id": nodeID, "target": target, "reason": "mqtt_unavailable"})
		return cmd, ErrMQTTUnavailable
	}

	if err := s.pub.PublishSetOutput(nodeID, target, value, reqID); err != nil {
		_ = s.repo.UpdateCommandStatus(ctx, cmd.ID, model.StatusFailed)
		cmd.Status = model.StatusFailed
		s.publishAudit("control.command.failed", map[string]string{"node_id": nodeID, "target": target, "reason": err.Error()})
		return cmd, err
	}

	_ = s.repo.UpdateCommandStatus(ctx, cmd.ID, model.StatusSent)
	cmd.Status = model.StatusSent
	s.setState(nodeID, target, value)
	s.publishAudit("control.command.sent", map[string]string{
		"node_id": nodeID, "target": target, "value": fmt.Sprintf("%d", value), "source": source, "type": controlType,
	})
	return cmd, nil
}

// ─── MQTT callbacks (wired in main) ───────────────────────────────────────────

// OnConfirm correlates a firmware ACK back to its command via req_id.
func (s *ControlService) OnConfirm(nodeID, reqID, target string, value int) {
	if reqID == "" {
		return
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	ok, err := s.repo.MarkAckedByReqID(ctx, reqID)
	if err != nil {
		log.Printf("[svc] ack update failed req=%s: %v", reqID, err)
		return
	}
	if ok {
		s.publishAudit("control.command.acked", map[string]string{"node_id": nodeID, "target": target, "req_id": reqID})
	}
}

// OnTelemetry caches the payload (for threshold evaluation) and records the
// firmware outputs discovered under telemetry.outputs (name, type, value). The
// controllable outputs themselves are the actuator tags the user attaches via
// the Module Service — this registry just lets the UI offer the selectable
// outputs when creating an actuator tag.
func (s *ControlService) OnTelemetry(nodeID string, payload []byte) {
	var data map[string]interface{}
	if err := json.Unmarshal(payload, &data); err != nil {
		return
	}

	s.mu.Lock()
	s.latest[nodeID] = data
	if outputsRaw, ok := resolvePath(data, "telemetry.outputs"); ok {
		if outputs, ok := outputsRaw.(map[string]interface{}); ok {
			if s.outputs[nodeID] == nil {
				s.outputs[nodeID] = make(map[string]outputInfo)
			}
			if s.state[nodeID] == nil {
				s.state[nodeID] = make(map[string]int)
			}
			for name, v := range outputs {
				val, _ := toInt(v)
				typ := model.OutDigital
				if val > 1 {
					typ = model.OutPWM
				}
				s.outputs[nodeID][name] = outputInfo{Type: typ, Value: val}
				s.state[nodeID][name] = val
			}
		}
	}
	s.mu.Unlock()
}

// SensorValue returns the latest numeric value at a dot-path for a node.
func (s *ControlService) SensorValue(nodeID, sourceKey string) (float64, bool) {
	s.mu.RLock()
	data, ok := s.latest[nodeID]
	s.mu.RUnlock()
	if !ok {
		return 0, false
	}
	v, ok := resolvePath(data, sourceKey)
	if !ok {
		return 0, false
	}
	return toFloat(v)
}

// ─── Targets / modes ──────────────────────────────────────────────────────────

// ListTargets returns the actuator outputs for a node, derived from the Module
// Service telemetry tag-mapping (same source the Sensor/Analytics pages use).
func (s *ControlService) ListTargets(ctx context.Context, nodeID string, src ActuatorSource) ([]model.ControlTarget, error) {
	targets, err := s.resolveActuators(ctx, src, nodeID)
	if err != nil {
		return nil, err
	}
	// Reflect the last commanded state so the dashboard can show ON/OFF.
	for i := range targets {
		if v, ok := s.getState(targets[i].NodeID, targets[i].SourceKey); ok {
			targets[i].LastValue = v
		}
	}
	return targets, nil
}

func (s *ControlService) SetMode(ctx context.Context, nodeID, output string, req model.ModeRequest) error {
	mode := strings.ToUpper(req.Mode)
	if mode != model.ModeManual && mode != model.ModeAuto {
		return fmt.Errorf("invalid mode: %s", req.Mode)
	}
	return s.repo.SetMode(ctx, &model.ControlMode{
		NodeID: nodeID, OutputName: output, Mode: mode, ActiveScheduleID: req.ScheduleID,
	})
}

func (s *ControlService) GetMode(ctx context.Context, nodeID, output string) (string, error) {
	m, err := s.repo.GetMode(ctx, nodeID, output)
	if errors.Is(err, repository.ErrNotFound) {
		return model.ModeManual, nil // default
	}
	if err != nil {
		return "", err
	}
	return m.Mode, nil
}

// ─── Schedules ────────────────────────────────────────────────────────────────

func (s *ControlService) CreateSchedule(ctx context.Context, req model.ScheduleRequest) (*model.Schedule, error) {
	if req.NodeID == "" {
		return nil, ErrNodeRequired
	}
	if req.OutputName == "" {
		return nil, ErrOutputRequired
	}
	enabled := true
	if req.Enabled != nil {
		enabled = *req.Enabled
	}
	tagName := s.lookupTag(nil, req.NodeID, req.OutputName)
	sc := &model.Schedule{
		NodeID: req.NodeID, OutputName: req.OutputName, TagName: tagName, Type: req.Type,
		Params: req.Params, Enabled: enabled,
	}
	if err := s.repo.CreateSchedule(ctx, sc); err != nil {
		return nil, err
	}
	s.publishAudit("control.schedule.created", map[string]string{"schedule_id": sc.ID, "node_id": sc.NodeID, "type": sc.Type})
	s.notifyScheduler()
	return sc, nil
}

func (s *ControlService) ListSchedules(ctx context.Context, nodeID string) ([]model.Schedule, error) {
	return s.repo.ListSchedules(ctx, nodeID, false)
}

func (s *ControlService) GetSchedule(ctx context.Context, id string) (*model.Schedule, error) {
	sc, err := s.repo.GetSchedule(ctx, id)
	if errors.Is(err, repository.ErrNotFound) {
		return nil, ErrScheduleNotFound
	}
	return sc, err
}

func (s *ControlService) UpdateSchedule(ctx context.Context, id string, req model.ScheduleRequest) (*model.Schedule, error) {
	sc, err := s.repo.UpdateSchedule(ctx, id, req)
	if errors.Is(err, repository.ErrNotFound) {
		return nil, ErrScheduleNotFound
	}
	if err != nil {
		return nil, err
	}
	if req.OutputName != "" {
		sc.TagName = s.lookupTag(nil, sc.NodeID, sc.OutputName)
		if err := s.repo.UpdateScheduleTagName(ctx, sc.ID, sc.TagName); err != nil {
			log.Printf("[svc] update schedule tag_name failed id=%s: %v", sc.ID, err)
		}
	}
	s.publishAudit("control.schedule.updated", map[string]string{"schedule_id": id})
	s.notifyScheduler()
	return sc, err
}

func (s *ControlService) SetScheduleEnabled(ctx context.Context, id string, enabled bool) error {
	err := s.repo.SetScheduleEnabled(ctx, id, enabled)
	if errors.Is(err, repository.ErrNotFound) {
		return ErrScheduleNotFound
	}
	if err == nil {
		ev := "control.schedule.enabled"
		if !enabled {
			ev = "control.schedule.disabled"
		}
		s.publishAudit(ev, map[string]string{"schedule_id": id})
		s.notifyScheduler()
	}
	return err
}

func (s *ControlService) DeleteSchedule(ctx context.Context, id string) error {
	err := s.repo.DeleteSchedule(ctx, id)
	if errors.Is(err, repository.ErrNotFound) {
		return ErrScheduleNotFound
	}
	if err == nil {
		s.publishAudit("control.schedule.deleted", map[string]string{"schedule_id": id})
		s.notifyScheduler()
	}
	return err
}

// EnabledSchedules is used by the scheduler to load active definitions.
func (s *ControlService) EnabledSchedules(ctx context.Context) ([]model.Schedule, error) {
	list, err := s.repo.ListSchedules(ctx, "", true)
	if err != nil {
		return nil, err
	}
	// Schedules only run in AUTOMATIC mode. In MANUAL or EMERGENCY
	// the node is under direct/forced control, so pause the scheduler.
	modes, _ := s.repo.GetNodeModeMap(ctx)
	out := make([]model.Schedule, 0, len(list))
	for _, sc := range list {
		if m := modes[sc.NodeID]; m == model.ModeManual || m == model.ModeEmergency {
			continue
		}
		out = append(out, sc)
	}
	return out, nil
}

// ─── Node-level control mode ─────────────────────────────────────────────
// Drives arbitration between manual override and the server-side scheduler.

func (s *ControlService) SetNodeMode(ctx context.Context, nodeID, mode string) error {
	mode = strings.ToUpper(mode)
	switch mode {
	case model.ModeManual, model.ModeAuto, model.ModeEmergency:
	default:
		return fmt.Errorf("invalid mode: %s", mode)
	}
	if mode == model.ModeEmergency {
		prev := s.GetNodeMode(ctx, nodeID)
		return s.repo.EnterEmergency(ctx, nodeID, prev)
	}
	return s.repo.SetNodeMode(ctx, nodeID, mode, nil)
}

func (s *ControlService) EnterEmergency(ctx context.Context, nodeID, prevMode string) error {
	return s.repo.EnterEmergency(ctx, nodeID, prevMode)
}

func (s *ControlService) GetNodeMode(ctx context.Context, nodeID string) string {
	m, err := s.repo.GetNodeMode(ctx, nodeID)
	if err != nil || m == "" {
		return model.ModeAuto // default
	}
	return m
}

// ResumeNode exits EMERGENCY_STOP by restoring the mode that was active before
// the emergency (MANUAL or AUTO), so the scheduler (and manual override) resume
// correctly. Returns the mode restored.
func (s *ControlService) ResumeNode(ctx context.Context, nodeID string) (string, error) {
	return s.repo.ResumeNode(ctx, nodeID)
}

// ─── Commands log ─────────────────────────────────────────────────────────────

func (s *ControlService) ListCommands(ctx context.Context, nodeID string, limit int) ([]model.Command, error) {
	return s.repo.ListCommands(ctx, nodeID, limit)
}

// TimeoutStale flips unacked commands older than the timeout window.
func (s *ControlService) TimeoutStale(ctx context.Context, olderThan time.Duration) {
	n, err := s.repo.TimeoutStaleCommands(ctx, time.Now().Add(-olderThan))
	if err != nil {
		log.Printf("[svc] timeout sweep failed: %v", err)
		return
	}
	if n > 0 {
		log.Printf("[svc] marked %d command(s) as timeout", n)
	}
}

// ─── in-memory output state (for toggle) ──────────────────────────────────────

func (s *ControlService) getState(nodeID, output string) (int, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m, ok := s.state[nodeID]
	if !ok {
		return 0, false
	}
	v, ok := m[output]
	return v, ok
}

func (s *ControlService) setState(nodeID, output string, value int) {
	s.mu.Lock()
	if s.state[nodeID] == nil {
		s.state[nodeID] = make(map[string]int)
	}
	s.state[nodeID][output] = value
	s.mu.Unlock()
}

// ─── Audit ────────────────────────────────────────────────────────────────────

// publishAudit emits a threshold lifecycle event onto the shared audit.log
// subject. Written to the outbox; the relay publishes it to NATS (ADR-007).
func (s *ControlService) publishAudit(event string, fields map[string]string) {
	payload := fmt.Sprintf(`{"event":%q,"service":"control","data":%s}`, event, mapToJSON(fields))
	s.enqueueOutbox("audit.log", payload)
}

// enqueueOutbox writes an outbox row (subject + payload + msg_id) to MariaDB.
// The relay worker publishes it to NATS and marks it sent (ADR-007). Each call
// runs in its own committed transaction so no event is lost even if NATS is
// unavailable — the row persists and the relay retries.
func (s *ControlService) enqueueOutbox(subject, payload string) {
	msgID := outbox.NewMsgID()
	if err := s.repo.Transact(context.Background(), func(tx *sql.Tx) error {
		return s.repo.InsertOutboxTx(context.Background(), tx, subject, payload, msgID)
	}); err != nil {
		log.Printf("[outbox] enqueue failed subject=%s: %v", subject, err)
	}
}

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

// ─── JSON path helpers (shared with firmware telemetry shape) ─────────────────

func resolvePath(data map[string]interface{}, path string) (interface{}, bool) {
	cur := interface{}(data)
	for _, p := range strings.Split(path, ".") {
		m, ok := cur.(map[string]interface{})
		if !ok {
			return nil, false
		}
		v, ok := m[p]
		if !ok {
			return nil, false
		}
		cur = v
	}
	return cur, true
}

func toFloat(v interface{}) (float64, bool) {
	switch n := v.(type) {
	case float64:
		return n, true
	case float32:
		return float64(n), true
	case int:
		return float64(n), true
	case bool:
		if n {
			return 1, true
		}
		return 0, true
	}
	return 0, false
}

func toInt(v interface{}) (int, bool) {
	f, ok := toFloat(v)
	if !ok {
		return 0, false
	}
	return int(f), true
}
