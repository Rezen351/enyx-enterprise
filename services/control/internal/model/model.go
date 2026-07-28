package model

import (
	"encoding/json"
	"time"
)

// ─── Enums / constants ────────────────────────────────────────────────────────

// Command lifecycle status.
const (
	StatusPending = "pending" // logged, about to publish
	StatusSent    = "sent"    // published to MQTT, awaiting /confirm
	StatusAcked   = "acked"   // firmware confirmed execution
	StatusTimeout = "timeout" // no /confirm within AckTimeout
	StatusFailed  = "failed"  // publish error / rejected
)

// Command source.
const (
	SourceManual   = "manual"
	SourceSchedule = "schedule"
)

// Per-target control mode.
const (
	ModeManual = "MANUAL" // commands published on demand only
	ModeAuto   = "AUTO"   // an active schedule drives the output
)

// Manual control types (high-level). All resolve to firmware action "set_output".
const (
	TypeSetState      = "set_state"      // ON/OFF digital
	TypeSetLevel      = "set_level"      // PWM 0..255 (or 0..100% mapped by caller)
	TypeToggle        = "toggle"         // flip last known state
	TypePulse         = "pulse"          // ON for duration_sec then OFF
	TypeEmergencyStop = "emergency_stop" // all outputs of a node → 0
)

// Automatic schedule types (server-side scheduler).
const (
	SchedInterval    = "interval"     // ON on_sec / OFF off_sec, repeating
	SchedSchedule    = "schedule"     // time-of-day ON/OFF (cron-like)
	SchedThreshold   = "threshold"    // sensor value + hysteresis
	SchedDuration    = "duration"     // ON for total_sec once, then OFF
	SchedRamp        = "ramp"         // PWM ramp from → to over duration
	SchedWindowPulse = "window_pulse" // pulse (on_sec/off_sec) only inside a time-of-day window
)

// Output hardware types.
const (
	OutDigital = "DIGITAL"
	OutPWM     = "PWM"
)

// ─── Domain models ────────────────────────────────────────────────────────────

// ControlTarget is a controllable output on a node, derived from the node's
// telemetry tag-mapping managed in the Module Service (same schema used by the
// Sensor/Analytics pages). The firmware "output name" is SourceKey
// (e.g. "outputs.pump" → firmware target "pump"); TagName is the friendly DB
// tag the user attached via the tag editor.
type ControlTarget struct {
	ID         string     `json:"id"`
	NodeID     string     `json:"node_id"`
	SourceKey  string     `json:"source_key"`  // telemetry dot-path, e.g. outputs.pump
	TagName    string     `json:"tag_name"`    // friendly DB tag (from Module tag-mapping)
	Label      string     `json:"label"`       // display name
	OutputType string     `json:"output_type"` // DIGITAL | PWM (from tag data_type/value)
	LastValue  int        `json:"last_value"`
	LastSeenAt *time.Time `json:"last_seen_at,omitempty"`
	CreatedAt  time.Time  `json:"created_at"`
	UpdatedAt  time.Time  `json:"updated_at"`
}

// ControlMode holds the active mode for a (node, output) pair.
type ControlMode struct {
	NodeID           string    `json:"node_id"`
	OutputName       string    `json:"output_name"`
	Mode             string    `json:"mode"` // MANUAL | AUTO
	ActiveScheduleID *string   `json:"active_schedule_id,omitempty"`
	UpdatedAt        time.Time `json:"updated_at"`
}

// Schedule is an automatic control definition executed by the scheduler engine.
type Schedule struct {
	ID         string          `json:"id"`
	NodeID     string          `json:"node_id"`
	OutputName string          `json:"output_name"`
	TagName    string          `json:"tag_name"`
	Type       string          `json:"type"`   // interval|schedule|threshold|duration|ramp|window_pulse
	Params     json.RawMessage `json:"params"` // type-specific JSON
	Enabled    bool            `json:"enabled"`
	NextRunAt  *time.Time      `json:"next_run_at,omitempty"`
	CreatedAt  time.Time       `json:"created_at"`
	UpdatedAt  time.Time       `json:"updated_at"`
}

// Command is a single dispatched actuator command (audit + status tracking).
type Command struct {
	ID          string     `json:"id"`
	ReqID       string     `json:"req_id"`
	NodeID      string     `json:"node_id"`
	Target      string     `json:"target"`       // firmware output name (tag SourceKey)
	TagName     string     `json:"tag_name"`     // friendly DB tag (from tag-mapping)
	ControlType string     `json:"control_type"` // set_state|set_level|... or schedule type
	Value       int        `json:"value"`
	Source      string     `json:"source"` // manual | schedule
	ScheduleID  *string    `json:"schedule_id,omitempty"`
	Status      string     `json:"status"`
	IssuedBy    string     `json:"issued_by,omitempty"` // user id (manual)
	CreatedAt   time.Time  `json:"created_at"`
	AckedAt     *time.Time `json:"acked_at,omitempty"`
}

// ─── Request / response DTOs ──────────────────────────────────────────────────

// CommandRequest is the manual command payload from the dashboard/API.
type CommandRequest struct {
	NodeID      string `json:"node_id"`
	Output      string `json:"output"`       // target output name (empty for emergency_stop → all)
	Type        string `json:"type"`         // set_state|set_level|toggle|pulse|emergency_stop
	Value       *int   `json:"value"`        // required for set_state/set_level
	DurationSec int    `json:"duration_sec"` // for pulse
	// Targets (optional) is the actuator tag set the dashboard rendered. When
	// provided, manual commands use it directly instead of re-reading the
	// Module Service tag-mapping — keeps the command consistent with the UI.
	Targets []ControlTarget `json:"targets,omitempty"`
	// Bypass allows the command to execute even when the node is in AUTO mode.
	// This is intended for AI/automation services (e.g. PPO controller) that
	// need to override specific outputs without requiring a manual mode switch.
	Bypass bool `json:"bypass,omitempty"`
}

// ScheduleRequest is the create/update payload for automatic schedules.
type ScheduleRequest struct {
	NodeID     string          `json:"node_id"`
	OutputName string          `json:"output_name"`
	Type       string          `json:"type"`
	Params     json.RawMessage `json:"params"`
	Enabled    *bool           `json:"enabled"`
}

// Control node modes (server-side arbitration between manual & scheduled).
const (
	ModeEmergency = "EMERGENCY" // all outputs forced OFF; schedules paused
)

// ModeRequest switches the control mode for a (node, output) pair.
type ModeRequest struct {
	Mode       string  `json:"mode"`                  // MANUAL | AUTO | EMERGENCY
	ScheduleID *string `json:"schedule_id,omitempty"` // schedule to activate when AUTO
}

// ─── Scheduler param shapes (parsed from Schedule.Params) ─────────────────────

// IntervalParams: repeating ON on_sec / OFF off_sec cycle.
type IntervalParams struct {
	OnSec    int `json:"on_sec"`
	OffSec   int `json:"off_sec"`
	ValueOn  int `json:"value_on"`  // default 1 (or PWM level)
	ValueOff int `json:"value_off"` // default 0
}

// DurationParams: ON for TotalSec once, then OFF (one-shot).
type DurationParams struct {
	TotalSec int `json:"total_sec"`
	ValueOn  int `json:"value_on"`
	ValueOff int `json:"value_off"`
}

// ScheduleParams: time-of-day ON/OFF. Times are "HH:MM" (24h, service local time).
type ScheduleParams struct {
	OnAt     string `json:"on_at"`  // "06:00"
	OffAt    string `json:"off_at"` // "18:00"
	Days     []int  `json:"days"`   // 0=Sun..6=Sat; empty = every day
	ValueOn  int    `json:"value_on"`
	ValueOff int    `json:"value_off"`
}

// ThresholdParams: sensor-driven ON/OFF with hysteresis.
type ThresholdParams struct {
	SourceKey     string  `json:"source_key"`     // dot-path into telemetry payload
	ThresholdHigh float64 `json:"threshold_high"` // >= high → ON
	ThresholdLow  float64 `json:"threshold_low"`  // <= low  → OFF (hysteresis)
	ValueOn       int     `json:"value_on"`
	ValueOff      int     `json:"value_off"`
}

// RampParams: linearly move PWM from → to across DurationSec in Steps steps.
type RampParams struct {
	From        int `json:"from"`
	To          int `json:"to"`
	DurationSec int `json:"duration_sec"`
	Steps       int `json:"steps"`
}

// WindowPulseParams: an ON/OFF pulse (on_sec/off_sec) that only runs
// while inside a time-of-day window (on_at..off_at, optional days).
// Outside the window the output is forced OFF. Combines a day/night
// schedule with a repeating pulse within that window.
type WindowPulseParams struct {
	OnAt     string `json:"on_at"`   // "06:00" window start
	OffAt    string `json:"off_at"`  // "18:00" window end
	Days     []int  `json:"days"`    // 0=Sun..6=Sat; empty = every day
	OnSec    int    `json:"on_sec"`  // pulse ON duration (sec)
	OffSec   int    `json:"off_sec"` // pulse OFF duration (sec)
	ValueOn  int    `json:"value_on"`
	ValueOff int    `json:"value_off"`
}
