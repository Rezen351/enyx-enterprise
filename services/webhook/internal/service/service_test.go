package service

import (
	"context"
	"testing"

	"github.com/almuzky/iot/services/webhook/internal/config"
	"github.com/almuzky/iot/services/webhook/internal/model"
	"github.com/almuzky/iot/services/webhook/internal/repository"
	"github.com/almuzky/iot/services/webhook/internal/testdriver"
	"gorm.io/driver/mysql"
	"gorm.io/gorm"
)

func newTestService(t *testing.T) (*Service, *testdriver.FakeDB) {
	t.Helper()
	sqldb, fake := testdriver.Open()
	gdb, err := gorm.Open(mysql.New(mysql.Config{
		Conn:                      sqldb,
		SkipInitializeWithVersion: true,
	}), &gorm.Config{})
	if err != nil {
		t.Fatalf("gorm open: %v", err)
	}
	cfg := &config.Config{WebhookSecret: "test-secret"}
	return New(cfg, repository.New(gdb), nil, nil), fake
}

func TestReloadSettings(t *testing.T) {
	svc, fake := newTestService(t)
	fake.CountValue = 1
	fake.SetSelectRows([]testdriver.Row{
		testdriver.NewRow([]string{"id", "telegram_enabled"}, "singleton", 1),
	})
	err := svc.ReloadSettings(context.Background())
	if err != nil {
		t.Fatalf("ReloadSettings err: %v", err)
	}
	if !svc.Settings().TelegramEnabled {
		t.Fatalf("expected telegram enabled after reload")
	}
}

func TestGetSettingsDTO(t *testing.T) {
	svc, _ := newTestService(t)
	svc.settings = &model.WebhookSetting{TelegramEnabled: true, TelegramTarget: "123", EmailEnabled: false, EmailTarget: "", WebhookEnabled: true, WebhookURL: "https://example.com"}
	dto := svc.GetSettingsDTO()
	if !dto.Telegram.Enabled || dto.Telegram.Target != "123" {
		t.Fatalf("unexpected telegram dto: %+v", dto.Telegram)
	}
	if !dto.Webhook.Enabled || dto.Webhook.Target != "https://example.com" {
		t.Fatalf("unexpected webhook dto: %+v", dto.Webhook)
	}
}

func TestGetSettingsDTOFallsBackToEnv(t *testing.T) {
	cfg := &config.Config{WebhookSecret: "test-secret", TelegramChatID: "env-chat", SMTPFrom: "env-from", SMTPUser: "env-user"}
	svc := New(cfg, nil, nil, nil)
	svc.settings = &model.WebhookSetting{TelegramEnabled: true, TelegramTarget: "", EmailEnabled: true, EmailTarget: "", WebhookEnabled: false, WebhookURL: ""}
	dto := svc.GetSettingsDTO()
	if dto.Telegram.Target != "env-chat" {
		t.Fatalf("expected telegram target from env, got %q", dto.Telegram.Target)
	}
	if dto.Email.Target != "env-from" {
		t.Fatalf("expected email target from env SMTPFrom, got %q", dto.Email.Target)
	}
}
