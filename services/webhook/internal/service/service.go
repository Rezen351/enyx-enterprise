package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/almuzky/iot/services/webhook/internal/channels"
	"github.com/almuzky/iot/services/webhook/internal/config"
	"github.com/almuzky/iot/services/webhook/internal/crypto"
	"github.com/almuzky/iot/services/webhook/internal/model"
	"github.com/almuzky/iot/services/webhook/internal/queue"
	"github.com/almuzky/iot/services/webhook/internal/repository"
	"github.com/google/uuid"
	"github.com/nats-io/nats.go"
	"github.com/redis/go-redis/v9"
)

const webhookDeliverySubject = "webhook.delivery"
const webhookRetrySubject = "webhook.retry"

type Service struct {
	cfg      *config.Config
	store    *repository.Store
	rdb      *redis.Client
	queue    *queue.Queue
	nc       *nats.Conn
	key      []byte
	settings *model.WebhookSetting
}

func New(cfg *config.Config, store *repository.Store, rdb *redis.Client, nc *nats.Conn) *Service {
	return &Service{
		cfg:      cfg,
		store:    store,
		rdb:      rdb,
		queue:    queue.New(rdb),
		nc:       nc,
		key:      crypto.DeriveKey(cfg.WebhookSecret),
		settings: &model.WebhookSetting{ID: model.SettingsID},
	}
}

func (s *Service) SetNATS(nc *nats.Conn) { s.nc = nc }

func (s *Service) ReloadSettings(ctx context.Context) error {
	st, err := s.store.GetSettings(ctx)
	if err != nil {
		return err
	}
	s.settings = st
	return nil
}

func (s *Service) Settings() *model.WebhookSetting {
	if s.settings == nil {
		s.settings = &model.WebhookSetting{ID: model.SettingsID}
	}
	return s.settings
}

func (s *Service) GetSettingsDTO() model.SettingsDTO {
	st := s.Settings()
	return model.SettingsDTO{
		Telegram: model.ChannelSettings{Enabled: st.TelegramEnabled, Target: firstNonEmpty(st.TelegramTarget, s.cfg.TelegramChatID)},
		Email:    model.ChannelSettings{Enabled: st.EmailEnabled, Target: firstNonEmpty(st.EmailTarget, s.cfg.SMTPFrom, s.cfg.SMTPUser)},
		Webhook:  model.ChannelSettings{Enabled: st.WebhookEnabled, Target: st.WebhookURL},
	}
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}

func (s *Service) SeedFromEnv(ctx context.Context, cfg *config.Config) error {
	st := s.Settings()
	if st.ID != model.SettingsID {
		return nil
	}
	changed := false
	if cfg.TelegramBotToken != "" && !st.TelegramEnabled && st.TelegramTarget == "" {
		st.TelegramEnabled = true
		st.TelegramTarget = cfg.TelegramChatID
		st.TelegramSecret, _ = crypto.Encrypt(s.key, cfg.TelegramBotToken)
		changed = true
	}
	if cfg.SMTPHost != "" && !st.EmailEnabled && st.EmailTarget == "" {
		st.EmailEnabled = true
		st.EmailTarget = cfg.SMTPUser
		if cfg.SMTPFrom != "" {
			st.EmailTarget = cfg.SMTPFrom
		}
		st.EmailSecret, _ = crypto.Encrypt(s.key, "")
		changed = true
	}
	if !changed {
		return nil
	}
	st.UpdatedBy = "env-seed"
	return s.store.UpsertSettings(ctx, st)
}

func (s *Service) UpdateSettings(ctx context.Context, patch model.SettingsPatch, userID string) (*model.SettingsDTO, error) {
	st := s.Settings()
	st.TelegramEnabled = patch.Telegram.Enabled
	st.TelegramTarget = patch.Telegram.Target
	if patch.Telegram.Secret != "" {
		enc, err := crypto.Encrypt(s.key, patch.Telegram.Secret)
		if err != nil {
			return nil, fmt.Errorf("encrypt telegram secret: %w", err)
		}
		st.TelegramSecret = enc
	}
	st.EmailEnabled = patch.Email.Enabled
	st.EmailTarget = patch.Email.Target
	if patch.Email.Secret != "" {
		enc, err := crypto.Encrypt(s.key, patch.Email.Secret)
		if err != nil {
			return nil, fmt.Errorf("encrypt email secret: %w", err)
		}
		st.EmailSecret = enc
	}
	st.WebhookEnabled = patch.Webhook.Enabled
	st.WebhookURL = patch.Webhook.Target
	if patch.Webhook.Secret != "" {
		enc, err := crypto.Encrypt(s.key, patch.Webhook.Secret)
		if err != nil {
			return nil, fmt.Errorf("encrypt webhook secret: %w", err)
		}
		st.WebhookSecret = enc
	}
	st.UpdatedBy = userID
	if err := s.store.UpsertSettings(ctx, st); err != nil {
		return nil, err
	}
	s.settings = st
	dto := s.GetSettingsDTO()
	return &dto, nil
}

func (s *Service) enqueueChannel(ctx context.Context, channel, target, subject, body, alertID, userID string) error {
	logID := uuid.NewString()
	l := &model.WebhookLog{
		ID: logID, Channel: channel, Target: target, Subject: subject, Body: body, Status: "queued", AlertID: alertID, UserID: userID,
	}
	if err := s.store.CreateLog(ctx, l); err != nil {
		return err
	}
	job := queue.Job{LogID: logID, Channel: channel, Target: target, Subject: subject, Body: body, AlertID: alertID, UserID: userID, Attempts: 0}
	return s.queue.Enqueue(ctx, job)
}

func (s *Service) SendTest(ctx context.Context, channel, userID string) (int, error) {
	st := s.Settings()
	want := func(name string) bool { return channel == "" || channel == name }
	count := 0
	if want("telegram") && st.TelegramEnabled && st.TelegramTarget != "" {
		_ = s.enqueueChannel(ctx, "telegram", st.TelegramTarget, "Webhook Test", "webhook test from iot platform", "", userID)
		count++
	}
	if want("email") && st.EmailEnabled && st.EmailTarget != "" {
		_ = s.enqueueChannel(ctx, "email", st.EmailTarget, "Webhook Test", "webhook test from iot platform", "", userID)
		count++
	}
	if want("webhook") && st.WebhookEnabled && st.WebhookURL != "" {
		_ = s.enqueueChannel(ctx, "webhook", st.WebhookURL, "Webhook Test", `{"test":true}`, "", userID)
		count++
	}
	return count, nil
}

func (s *Service) ListLogs(ctx context.Context, channel, status string, limit, offset int) ([]model.WebhookLog, int64, error) {
	return s.store.ListLogs(ctx, repository.LogFilter{Channel: channel, Status: status}, limit, offset)
}

func (s *Service) RunSubscriber(nc *nats.Conn) error {
	for _, subj := range []string{webhookDeliverySubject, webhookRetrySubject} {
		if subj == webhookRetrySubject {
			js, err := nc.JetStream()
			if err != nil {
				return fmt.Errorf("jetstream context: %w", err)
			}
			_, err = js.QueueSubscribe(webhookRetrySubject, "webhook-retry-workers", func(m *nats.Msg) {
				_ = nc.Publish(webhookDeliverySubject, m.Data)
				_ = m.Ack()
			}, nats.Durable("webhook-retry-processor"))
			if err != nil {
				return fmt.Errorf("jetstream subscribe %q: %w", webhookRetrySubject, err)
			}
			log.Printf("webhook JetStream subscriber listening on %q", webhookRetrySubject)
		} else {
			_, err := nc.QueueSubscribe(subj, "webhook-delivery-workers", func(m *nats.Msg) {
				s.handleDelivery(m.Data)
			})
			if err != nil {
				return err
			}
			log.Printf("webhook subscriber listening on %q", subj)
		}
	}
	return nil
}

type deliveryEvent struct {
	Channel string `json:"channel"`
	Target  string `json:"target"`
	Subject string `json:"subject"`
	Body    string `json:"body"`
	AlertID string `json:"alert_id"`
	UserID  string `json:"user_id"`
}

type DeliveryEvent deliveryEvent

func (s *Service) HandleIncoming(ctx context.Context, channel, target, subject, body, alertID, userID string) error {
	return s.enqueueChannel(ctx, channel, target, subject, body, alertID, userID)
}

func (s *Service) handleDelivery(body []byte) {
	var ev deliveryEvent
	if err := json.Unmarshal(body, &ev); err != nil {
		log.Printf("WARN: webhook: bad payload: %v", err)
		return
	}
	if ev.Channel == "" {
		return
	}
	_ = s.enqueueChannel(context.Background(), ev.Channel, ev.Target, ev.Subject, ev.Body, ev.AlertID, ev.UserID)
}

func (s *Service) StartWorker(ctx context.Context) {
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			default:
			}
			job, err := s.queue.Dequeue(ctx)
			if err != nil {
				log.Printf("WARN: webhook: dequeue error: %v", err)
				time.Sleep(time.Second)
				continue
			}
			if job == nil {
				continue
			}
			time.Sleep(time.Duration(s.cfg.SendIntervalMs) * time.Millisecond)
			s.process(ctx, job)
		}
	}()
}

func (s *Service) process(ctx context.Context, job *queue.Job) {
	st := s.Settings()
	var secret, target string
	switch job.Channel {
	case "telegram":
		secret, target = st.TelegramSecret, st.TelegramTarget
	case "email":
		secret, target = st.EmailSecret, st.EmailTarget
	case "webhook":
		secret, target = st.WebhookSecret, st.WebhookURL
	default:
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts, "failed", "unknown channel")
		return
	}
	dec, err := crypto.Decrypt(s.key, secret)
	if err != nil {
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts, "failed", "secret decrypt error")
		return
	}
	var res channels.SenderResult
	if s.cfg.ForceFail {
		res = channels.SenderResult{Err: "forced failure (WEBHOOK_FORCE_FAIL)"}
	} else {
		switch job.Channel {
		case "telegram":
			res = channels.SendTelegram(s.cfg, target, job.Body, dec)
		case "email":
			res = channels.SendEmail(s.cfg, target, job.Subject, job.Body, dec)
		case "webhook":
			res = channels.SendWebhookHTTP(s.cfg, target, job.Subject, job.Body, dec)
		}
		if !res.OK && s.cfg.DevMode && isUnconfiguredError(res.Err) {
			res = channels.SenderResult{OK: true}
		}
	}
	if res.OK {
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts+1, "sent", "")
		return
	}
	if job.Attempts+1 < s.cfg.MaxAttempts {
		job.Attempts++
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts, "retrying", res.Err)
		time.Sleep(time.Duration(s.cfg.RetryDelayMs) * time.Millisecond)
		_ = s.enqueueChannel(ctx, job.Channel, target, job.Subject, job.Body, job.AlertID, job.UserID)
		return
	}
	_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts+1, "failed", res.Err)
}

func isUnconfiguredError(msg string) bool {
	switch {
	case strings.Contains(msg, "not configured"):
		return true
	case strings.Contains(msg, "missing"):
		return true
	}
	return false
}
