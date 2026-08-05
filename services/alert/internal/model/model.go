package model

import "time"

// Threshold defines the acceptable min/max range for a (node, metric) pair.
// A wildcard node_id ("*") applies the threshold to every node for that metric.
type Threshold struct {
	ID          string    `gorm:"column:id;type:char(36);primaryKey"`
	NodeID      string    `gorm:"column:node_id;type:varchar(64);not null;index:idx_node_metric"`
	Metric      string    `gorm:"column:metric;type:varchar(128);not null;index:idx_node_metric"`
	Min         *float64  `gorm:"column:min"`
	Max         *float64  `gorm:"column:max"`
	Enabled     bool      `gorm:"column:enabled;not null;default:true"`
	Severity    string    `gorm:"column:severity;type:varchar(16);not null;default:'warning'"`
	Message     string    `gorm:"column:message;type:varchar(512)"`
	DurationSec *int      `gorm:"column:duration_sec;default:0"`
	CooldownSec *int      `gorm:"column:cooldown_sec;default:0"`
	Hysteresis  *float64  `gorm:"column:hysteresis;default:0"`
	CreatedAt   time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt   time.Time `gorm:"column:updated_at;autoUpdateTime"`
}

func (Threshold) TableName() string { return "thresholds" }

// Alert is a single threshold-violation event. Status transitions:
// active → resolved (value returns to range) or active → acked (operator acks).
type Alert struct {
	ID             string     `gorm:"column:id;type:char(36);primaryKey"`
	NodeID         string     `gorm:"column:node_id;type:varchar(64);not null;index:idx_alert_node_metric"`
	Metric         string     `gorm:"column:metric;type:varchar(128);not null;index:idx_alert_node_metric"`
	Value          float64    `gorm:"column:value;not null"`
	ThresholdValue *float64   `gorm:"column:threshold_value"`
	Severity       string     `gorm:"column:severity;type:varchar(16);not null;default:'warning'"`
	Status         string     `gorm:"column:status;type:varchar(16);not null;default:'active'"`
	Message        string     `gorm:"column:message;type:varchar(512)"`
	ThresholdID    *string    `gorm:"column:threshold_id;type:char(36)"`
	AckedBy        *string    `gorm:"column:acked_by;type:varchar(64)"`
	AckedAt        *time.Time `gorm:"column:acked_at"`
	TriggeredAt    time.Time  `gorm:"column:triggered_at;not null"`
	ResolvedAt     *time.Time `gorm:"column:resolved_at"`
	CreatedAt      time.Time  `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt      time.Time  `gorm:"column:updated_at;autoUpdateTime"`
}

func (Alert) TableName() string { return "alerts" }

// Outbox is the Transactional Outbox table (ADR-007). Each alert/event the
// Alert Service would previously publish directly to NATS is first written here
// within the same DB transaction as the business row. A relay worker drains
// unsent rows and publishes them to NATS with a Nats-Msg-Id header.
type Outbox struct {
	ID        string     `gorm:"column:id;type:char(36);primaryKey"`
	MsgID     string     `gorm:"column:msg_id;type:varchar(64);not null;uniqueIndex"` // idempotency key (Nats-Msg-Id)
	Subject   string     `gorm:"column:subject;type:varchar(128);not null;index"`
	Payload   string     `gorm:"column:payload;type:longtext;not null"`
	Sent      bool       `gorm:"column:sent;not null;default:false;index"`
	CreatedAt time.Time  `gorm:"column:created_at;autoCreateTime"`
	SentAt    *time.Time `gorm:"column:sent_at"`
}

func (Outbox) TableName() string { return "outbox" }

// ThresholdDTO is the API representation of a threshold configuration.
type ThresholdDTO struct {
	ID          string   `json:"id"`
	NodeID      string   `json:"node_id"`
	Metric      string   `json:"metric"`
	Min         *float64 `json:"min"`
	Max         *float64 `json:"max"`
	Enabled     bool     `json:"enabled"`
	Severity    string   `json:"severity"`
	Message     string   `json:"message"`
	DurationSec *int     `json:"duration_sec"`
	CooldownSec *int     `json:"cooldown_sec"`
	Hysteresis  *float64 `json:"hysteresis"`
}

// ToThresholdDTO converts a Threshold to its DTO.
func ToThresholdDTO(t Threshold) ThresholdDTO {
	return ThresholdDTO{
		ID:          t.ID,
		NodeID:      t.NodeID,
		Metric:      t.Metric,
		Min:         t.Min,
		Max:         t.Max,
		Enabled:     t.Enabled,
		Severity:    t.Severity,
		Message:     t.Message,
		DurationSec: t.DurationSec,
		CooldownSec: t.CooldownSec,
		Hysteresis:  t.Hysteresis,
	}
}

// AlertDTO is the API representation of an alert event.
type AlertDTO struct {
	ID             string     `json:"id"`
	NodeID         string     `json:"node_id"`
	Metric         string     `json:"metric"`
	Value          float64    `json:"value"`
	ThresholdValue *float64   `json:"threshold_value"`
	Severity       string     `json:"severity"`
	Status         string     `json:"status"`
	Message        string     `json:"message"`
	AckedBy        *string    `json:"acked_by"`
	AckedAt        *time.Time `json:"acked_at"`
	TriggeredAt    time.Time  `json:"triggered_at"`
	ResolvedAt     *time.Time `json:"resolved_at"`
}

// ToAlertDTO converts an Alert to its DTO.
func ToAlertDTO(a Alert) AlertDTO {
	return AlertDTO{
		ID:             a.ID,
		NodeID:         a.NodeID,
		Metric:         a.Metric,
		Value:          a.Value,
		ThresholdValue: a.ThresholdValue,
		Severity:       a.Severity,
		Status:         a.Status,
		Message:        a.Message,
		AckedBy:        a.AckedBy,
		AckedAt:        a.AckedAt,
		TriggeredAt:    a.TriggeredAt,
		ResolvedAt:     a.ResolvedAt,
	}
}
