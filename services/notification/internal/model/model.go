package model

import "time"

// SettingsID is the fixed primary key for the singleton settings row.
const SettingsID = "singleton"

// NotificationSetting stores per-channel enable flags, delivery targets, and
// ENCRYPTED channel secrets. Secrets are encrypted at rest (AES-GCM) and are
// never returned by the API nor written to logs.
type NotificationSetting struct {
	ID              string    `gorm:"column:id;type:varchar(36);primaryKey"`
	TelegramEnabled bool      `gorm:"column:telegram_enabled;not null;default:false"`
	TelegramTarget  string    `gorm:"column:telegram_target;type:varchar(64)"`
	TelegramSecret  string    `gorm:"column:telegram_secret;type:varchar(512)"`
	EmailEnabled    bool      `gorm:"column:email_enabled;not null;default:false"`
	EmailTarget     string    `gorm:"column:email_target;type:varchar(255)"`
	EmailSecret     string    `gorm:"column:email_secret;type:varchar(512)"`
	PushEnabled     bool      `gorm:"column:push_enabled;not null;default:false"`
	PushTarget      string    `gorm:"column:push_target;type:varchar(512)"`
	PushSecret      string    `gorm:"column:push_secret;type:varchar(512)"`
	WebhookEnabled  bool      `gorm:"column:webhook_enabled;not null;default:false"`
	WebhookTarget   string    `gorm:"column:webhook_target;type:varchar(1024)"`
	WebhookSecret   string    `gorm:"column:webhook_secret;type:varchar(512)"`
	UpdatedAt       time.Time `gorm:"column:updated_at;autoUpdateTime"`
	UpdatedBy       string    `gorm:"column:updated_by;type:varchar(64)"`
}

func (NotificationSetting) TableName() string { return "notification_settings" }

// ChannelSettings is the public (non-secret) view of a single channel.
type ChannelSettings struct {
	Enabled bool   `json:"enabled"`
	Target  string `json:"target"`
}

// ChannelInput is the request shape for a single channel (may include secret).
type ChannelInput struct {
	Enabled bool   `json:"enabled"`
	Target  string `json:"target"`
	Secret  string `json:"secret"`
}

// SettingsPatch is the PUT /notifications/settings request body.
type SettingsPatch struct {
	Telegram ChannelInput `json:"telegram"`
	Email    ChannelInput `json:"email"`
	Push     ChannelInput `json:"push"`
	Webhook  ChannelInput `json:"webhook"`
}

// SettingsDTO is the API representation of notification settings (no secrets).
type SettingsDTO struct {
	Telegram ChannelSettings `json:"telegram"`
	Email    ChannelSettings `json:"email"`
	Push     ChannelSettings `json:"push"`
	Webhook  ChannelSettings `json:"webhook"`
}

// NotificationLog records every delivery attempt. It never stores secrets; the
// Error column holds only a transport/status message (no token/password).
type NotificationLog struct {
	ID        string    `gorm:"column:id;type:char(36);primaryKey"`
	Channel   string    `gorm:"column:channel;type:varchar(16);not null;index"`
	Target    string    `gorm:"column:target;type:varchar(512)"`
	Subject   string    `gorm:"column:subject;type:varchar(255)"`
	Body      string    `gorm:"column:body;type:text"`
	Status    string    `gorm:"column:status;type:varchar(16);not null;default:'queued'"` // queued|retrying|sent|failed
	Attempts  int       `gorm:"column:attempts;not null;default:0"`
	Error     string    `gorm:"column:error;type:varchar(512)"`
	AlertID   string    `gorm:"column:alert_id;type:varchar(64)"`
	UserID    string    `gorm:"column:user_id;type:varchar(64)"`
	CreatedAt time.Time `gorm:"column:created_at;autoCreateTime"`
	UpdatedAt time.Time `gorm:"column:updated_at;autoUpdateTime"`
}

func (NotificationLog) TableName() string { return "notification_logs" }

// LogDTO is the API representation of a notification log entry.
type LogDTO struct {
	ID        string    `json:"id"`
	Channel   string    `json:"channel"`
	Target    string    `json:"target"`
	Subject   string    `json:"subject"`
	Status    string    `json:"status"`
	Attempts  int       `json:"attempts"`
	Error     string    `json:"error"`
	AlertID   string    `json:"alert_id"`
	UserID    string    `json:"user_id"`
	CreatedAt time.Time `json:"created_at"`
}

// ToLogDTO converts a NotificationLog to its DTO.
func ToLogDTO(l NotificationLog) LogDTO {
	return LogDTO{
		ID:        l.ID,
		Channel:   l.Channel,
		Target:    l.Target,
		Subject:   l.Subject,
		Status:    l.Status,
		Attempts:  l.Attempts,
		Error:     l.Error,
		AlertID:   l.AlertID,
		UserID:    l.UserID,
		CreatedAt: l.CreatedAt,
	}
}
