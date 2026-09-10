package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/almuzky/iot/services/notification/internal/channels"
	"github.com/almuzky/iot/services/notification/internal/config"
	"github.com/almuzky/iot/services/notification/internal/crypto"
	"github.com/almuzky/iot/services/notification/internal/model"
	"github.com/almuzky/iot/services/notification/internal/queue"
	"github.com/almuzky/iot/services/notification/internal/repository"
	"github.com/google/uuid"
	"github.com/nats-io/nats.go"
	"github.com/redis/go-redis/v9"
)

const alertSubject = "alert.*"
const webhookDeliverySubject = "webhook.delivery"
const webhookRetrySubject = "webhook.retry"

// Service orchestrates settings, the delivery queue/worker, and the NATS
// alert.* subscription that triggers notifications.
type Service struct {
	cfg      *config.Config
	store    *repository.Store
	rdb      *redis.Client
	queue    *queue.Queue
	nc       *nats.Conn
	key      []byte
	settings *model.NotificationSetting
}

func New(cfg *config.Config, store *repository.Store, rdb *redis.Client, nc *nats.Conn) *Service {
	return &Service{
		cfg:      cfg,
		store:    store,
		rdb:      rdb,
		queue:    queue.New(rdb),
		nc:       nc,
		key:      crypto.DeriveKey(cfg.SecretKey),
		settings: &model.NotificationSetting{ID: model.SettingsID},
	}
}

// SetNATS wires the (already-connected) NATS connection.
func (s *Service) SetNATS(nc *nats.Conn) { s.nc = nc }

// ReloadSettings loads the singleton settings row into the in-memory cache so
// the worker can read targets/secrets without a DB round-trip per send.
func (s *Service) ReloadSettings(ctx context.Context) error {
	st, err := s.store.GetSettings(ctx)
	if err != nil {
		return err
	}
	s.settings = st
	return nil
}

func (s *Service) Settings() *model.NotificationSetting {
	if s.settings == nil {
		s.settings = &model.NotificationSetting{ID: model.SettingsID}
	}
	return s.settings
}

// GetSettingsDTO returns the non-secret public view of settings.
func (s *Service) GetSettingsDTO() model.SettingsDTO {
	st := s.Settings()
	return model.SettingsDTO{
		Telegram: model.ChannelSettings{Enabled: st.TelegramEnabled, Target: st.TelegramTarget},
		Email:    model.ChannelSettings{Enabled: st.EmailEnabled, Target: st.EmailTarget},
		Push:     model.ChannelSettings{Enabled: st.PushEnabled, Target: st.PushTarget},
		Webhook:  model.ChannelSettings{Enabled: st.WebhookEnabled, Target: st.WebhookTarget},
	}
}

// SeedFromEnv populates empty settings from environment variables on first
// startup, so the service is usable without manual PUT /settings when env
// vars are present.
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
		st.EmailTarget = cfg.SMTPFrom
		if st.EmailTarget == "" {
			st.EmailTarget = cfg.SMTPUser
		}
		st.EmailSecret, _ = crypto.Encrypt(s.key, cfg.SMTPPass)
		changed = true
	}
	if !changed {
		return nil
	}
	st.UpdatedBy = "env-seed"
	return s.store.UpsertSettings(ctx, st)
}

// UpdateSettings applies a validated patch, encrypts any provided secrets,
// persists, and refreshes the in-memory cache.
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

	st.PushEnabled = patch.Push.Enabled
	st.PushTarget = patch.Push.Target
	if patch.Push.Secret != "" {
		enc, err := crypto.Encrypt(s.key, patch.Push.Secret)
		if err != nil {
			return nil, fmt.Errorf("encrypt push secret: %w", err)
		}
		st.PushSecret = enc
	}

	st.WebhookEnabled = patch.Webhook.Enabled
	st.WebhookTarget = patch.Webhook.Target
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

// enqueueChannel persists a log row (status queued) and pushes a job.
func (s *Service) enqueueChannel(ctx context.Context, channel, target, subject, body, alertID, userID string) error {
	logID := uuid.NewString()
	l := &model.NotificationLog{
		ID:       logID,
		Channel:  channel,
		Target:   target,
		Subject:  subject,
		Body:     body,
		Status:   "queued",
		Attempts: 0,
		AlertID:  alertID,
		UserID:   userID,
	}
	if err := s.store.CreateLog(ctx, l); err != nil {
		return err
	}
	job := queue.Job{
		LogID:    logID,
		Channel:  channel,
		Target:   target,
		Subject:  subject,
		Body:     body,
		AlertID:  alertID,
		UserID:   userID,
		Attempts: 0,
	}
	return s.queue.Enqueue(ctx, job)
}

// SendTest enqueues a dummy notification for the requested channel (or all
// enabled channels when channel is empty). Returns the number enqueued.
func (s *Service) SendTest(ctx context.Context, channel, userID string) (int, error) {
	st := s.Settings()
	want := func(name string) bool {
		return channel == "" || channel == name
	}
	count := 0
	if want("telegram") && st.TelegramEnabled && st.TelegramTarget != "" {
		if err := s.enqueueChannel(ctx, "telegram", st.TelegramTarget, "SmartFarm Test Notification", "This is a test notification from the SmartFarm IoT platform.", "", userID); err != nil {
			return count, err
		}
		count++
	}
	if want("email") && st.EmailEnabled && st.EmailTarget != "" {
		if err := s.enqueueChannel(ctx, "email", st.EmailTarget, "SmartFarm Test Notification", "This is a test notification from the SmartFarm IoT platform.", "", userID); err != nil {
			return count, err
		}
		count++
	}
	if want("push") && st.PushEnabled && st.PushTarget != "" {
		if err := s.enqueueChannel(ctx, "push", st.PushTarget, "SmartFarm Test Notification", "This is a test notification from the SmartFarm IoT platform.", "", userID); err != nil {
			return count, err
		}
		count++
	}
	if want("webhook") && st.WebhookEnabled && st.WebhookTarget != "" {
		if err := s.enqueueChannel(ctx, "webhook", st.WebhookTarget, "SmartFarm Test Notification", "This is a test notification from the SmartFarm IoT platform.", "", userID); err != nil {
			return count, err
		}
		count++
	}
	return count, nil
}

// ListLogs returns delivery logs (delegates to the repository).
func (s *Service) ListLogs(ctx context.Context, channel, status string, limit, offset int) ([]model.NotificationLog, int64, error) {
	return s.store.ListLogs(ctx, repository.LogFilter{Channel: channel, Status: status}, limit, offset)
}

// RunSubscriber subscribes to alert.* AND webhook.delivery/webhook.retry on
// queue groups so multiple replicas share the load. alert.* events fan out to
// every enabled channel; webhook.delivery carries explicit delivery jobs
// (e.g. inbound webhook receivers or external producers), with webhook.retry
// re-publishing failed jobs back onto webhook.delivery via JetStream.
func (s *Service) RunSubscriber(nc *nats.Conn) error {
	if _, err := nc.QueueSubscribe(alertSubject, "notification-workers", func(m *nats.Msg) {
		s.handleAlert(m.Data)
	}); err != nil {
		log.Printf("WARN: notification: alert subscriber failed: %v", err)
		return err
	}
	log.Printf("notification subscriber listening on %q", alertSubject)

	if _, err := nc.QueueSubscribe(webhookDeliverySubject, "notification-delivery-workers", func(m *nats.Msg) {
		s.handleDelivery(m.Data)
	}); err != nil {
		log.Printf("WARN: notification: webhook.delivery subscriber failed: %v", err)
		return err
	}
	log.Printf("notification subscriber listening on %q", webhookDeliverySubject)

	js, err := nc.JetStream()
	if err != nil {
		return fmt.Errorf("jetstream context: %w", err)
	}
	if _, err := js.QueueSubscribe(webhookRetrySubject, "notification-retry-workers", func(m *nats.Msg) {
		_ = nc.Publish(webhookDeliverySubject, m.Data)
		_ = m.Ack()
	}, nats.Durable("notification-retry-processor")); err != nil {
		log.Printf("WARN: notification: webhook.retry subscriber failed: %v", err)
		return err
	}
	log.Printf("notification JetStream subscriber listening on %q", webhookRetrySubject)
	return nil
}

type alertEvent struct {
	NodeID   string `json:"node_id"`
	Metric   string `json:"metric"`
	Severity string `json:"severity"`
	Message  string `json:"message"`
}

// handleAlert triggers notifications for a single alert.* event.
func (s *Service) handleAlert(body []byte) {
	var ev alertEvent
	if err := json.Unmarshal(body, &ev); err != nil {
		log.Printf("WARN: notification: alert event not JSON: %v", err)
		return
	}
	if ev.NodeID == "" {
		return
	}
	subject := fmt.Sprintf("[%s] %s/%s", strings.ToUpper(ev.Severity), ev.NodeID, ev.Metric)
	bodyText := ev.Message
	if bodyText == "" {
		bodyText = fmt.Sprintf("Alert on node %s metric %s", ev.NodeID, ev.Metric)
	}
	ctx := context.Background()
	st := s.Settings()
	if st.TelegramEnabled && st.TelegramTarget != "" {
		_ = s.enqueueChannel(ctx, "telegram", st.TelegramTarget, subject, bodyText, "", "")
	}
	if st.EmailEnabled && st.EmailTarget != "" {
		_ = s.enqueueChannel(ctx, "email", st.EmailTarget, subject, bodyText, "", "")
	}
	if st.PushEnabled && st.PushTarget != "" {
		_ = s.enqueueChannel(ctx, "push", st.PushTarget, subject, bodyText, "", "")
	}
	if st.WebhookEnabled && st.WebhookTarget != "" {
		_ = s.enqueueChannel(ctx, "webhook", st.WebhookTarget, subject, bodyText, "", "")
	}
}

// DeliveryEvent is the payload published on webhook.delivery / posted to the
// inbound receive endpoints. Channel selects the delivery transport.
type DeliveryEvent struct {
	Channel string `json:"channel"`
	Target  string `json:"target"`
	Subject string `json:"subject"`
	Body    string `json:"body"`
	AlertID string `json:"alert_id"`
	UserID  string `json:"user_id"`
}

// HandleIncoming enqueues a delivery job from an inbound webhook receiver
// (telegram/email/generic) or an explicit delivery event.
func (s *Service) HandleIncoming(ctx context.Context, channel, target, subject, body, alertID, userID string) error {
	return s.enqueueChannel(ctx, channel, target, subject, body, alertID, userID)
}

// handleDelivery processes a webhook.delivery NATS message.
func (s *Service) handleDelivery(body []byte) {
	var ev DeliveryEvent
	if err := json.Unmarshal(body, &ev); err != nil {
		log.Printf("WARN: notification: bad delivery payload: %v", err)
		return
	}
	if ev.Channel == "" {
		return
	}
	_ = s.enqueueChannel(context.Background(), ev.Channel, ev.Target, ev.Subject, ev.Body, ev.AlertID, ev.UserID)
}

// StartWorker launches the background delivery worker. It blocks on the queue,
// applies send throttling, and retries failed jobs up to MaxAttempts.
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
				log.Printf("WARN: notification: dequeue error: %v", err)
				time.Sleep(time.Second)
				continue
			}
			if job == nil {
				continue
			}
			// Throttle sends to avoid spamming downstream channels.
			time.Sleep(s.cfg.SendInterval)
			s.process(ctx, job)
		}
	}()
}

// process delivers one job, handling retry via re-enqueue and bounded attempts.
func (s *Service) process(ctx context.Context, job *queue.Job) {
	st := s.Settings()
	var secret, target string
	switch job.Channel {
	case "telegram":
		secret, target = st.TelegramSecret, st.TelegramTarget
	case "email":
		secret, target = st.EmailSecret, st.EmailTarget
	case "push":
		secret, target = st.PushSecret, st.PushTarget
	case "webhook":
		secret, target = st.WebhookSecret, st.WebhookTarget
	default:
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts, "failed", "unknown channel")
		return
	}

	// Decrypt the secret in memory only — never log it.
	dec, err := crypto.Decrypt(s.key, secret)
	if err != nil {
		_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts, "failed", "secret decrypt error")
		return
	}

	var res channels.SenderResult
	if s.cfg.ForceFail {
		res = channels.SenderResult{Err: "forced failure (NOTIFICATION_FORCE_FAIL)"}
	} else {
		switch job.Channel {
		case "telegram":
			res = channels.SendTelegram(s.cfg, target, job.Body, dec)
		case "email":
			res = channels.SendEmail(s.cfg, target, job.Subject, job.Body, dec)
		case "push":
			res = channels.SendPush(s.cfg, target, job.Body, dec)
		case "webhook":
			res = channels.SendWebhookHTTP(s.cfg, target, job.Subject, job.Body, dec)
		}
		// DevMode: when a transport is unconfigured/unreachable, simulate a
		// successful delivery to the log sink so the full path is exercisable
		// without external credentials. Real transport errors (e.g. bad host)
		// still surface as failures and trigger retry.
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
		time.Sleep(s.cfg.RetryDelay)
		_ = s.queue.Enqueue(ctx, *job)
		return
	}
	_ = s.store.UpdateLog(ctx, job.LogID, job.Attempts+1, "failed", res.Err)
}

// isUnconfiguredError reports whether a send failure is due to a missing
// transport (not a genuine delivery error), used by DevMode simulation.
func isUnconfiguredError(msg string) bool {
	switch {
	case strings.Contains(msg, "not configured"):
		return true
	case strings.Contains(msg, "missing"):
		return true
	}
	return false
}
