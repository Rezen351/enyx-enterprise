# Webhook Service — Integration Guide

> **Service:** Webhook Service  
> **Module path:** `services/webhook`  
> **Status:** Implemented (2026-07-22)

---

## 1. Overview

The Webhook Service is a delivery dispatcher that receives webhook payloads (via HTTP POST or NATS) and forwards them to **Telegram** (Bot API) and **Email** (SMTP). It complements the Notification Service by providing a webhook-first ingestion path: external systems that can only send HTTP webhooks can deliver events here, while internal services can also publish to NATS subjects `webhook.delivery` / `webhook.retry`.

### Port & Entry Point

| Attribute | Value |
|---|---|
| **Default port** | `8080` (env `PORT`) |
| **Health endpoint** | `GET /health` |
| **Metrics endpoint** | `GET /metrics` (Prometheus) |
| **Protocol** | HTTP/1.1 REST (Chi router) |

### External Dependencies

| Dependency | Purpose | Default address |
|---|---|---|
| **MariaDB** | Webhook log persistence | `mariadb-webhook:3306` (DB `webhook_db`) |
| **Redis** | Async delivery queue (logical DB `4`) | `redis-shared:6379` |
| **NATS** | Event ingestion (`webhook.delivery`, `webhook.retry`) | `nats://nats:4222` |
| **SMTP host** | Email delivery | Configured via env |
| **Telegram Bot API** | Telegram delivery | `https://api.telegram.org` |

---

## 2. Database Schema

### `webhook_settings` (singleton)

| Column | Type | Constraints |
|---|---|---|
| `id` | `varchar(36)` | Primary key, fixed value `"singleton"` |
| `telegram_enabled` | `bool` | Default `false` |
| `telegram_target` | `varchar(64)` | Chat ID |
| `telegram_secret` | `varchar(512)` | AES-GCM encrypted bot token |
| `email_enabled` | `bool` | Default `false` |
| `email_target` | `varchar(255)` | Recipient address |
| `email_secret` | `varchar(512)` | AES-GCM encrypted SMTP password |
| `webhook_enabled` | `bool` | Default `false` |
| `webhook_url` | `varchar(1024)` | Generic webhook endpoint URL |
| `webhook_secret` | `varchar(512)` | AES-GCM encrypted webhook bearer/header |
| `updated_at` | `datetime` | Auto-updated |
| `updated_by` | `varchar(64)` | User ID of last updater |

### `webhook_logs`

| Column | Type | Description |
|---|---|---|
| `id` | `char(36)` | UUID primary key |
| `channel` | `varchar(16)` | Indexed (`telegram`, `email`, `webhook`) |
| `target` | `varchar(512)` | Destination address/URL |
| `subject` | `varchar(255)` | Notification subject / title |
| `body` | `text` | Full message body / payload |
| `status` | `varchar(16)` | `queued` / `retrying` / `sent` / `failed` |
| `attempts` | `int` | Number of send attempts so far |
| `error` | `varchar(512)` | Transport error message (never contains secrets) |
| `alert_id` | `varchar(64)` | Optional linked alert ID |
| `user_id` | `varchar(64)` | User who triggered / configured the webhook |
| `created_at` | `datetime` | Auto-set |
| `updated_at` | `datetime` | Auto-updated |

**Redis key:** `webhook:queue` — LPUSH / BRPOP list of JSON-serialized jobs.

---

## 3. REST API Endpoints

### 3.1 `GET /health`

| Attribute | Value |
|---|---|
| **Auth** | None (public) |
| **Response** | `200 OK` |

```json
{ "success": true, "data": { "status": "ok" } }
```

### 3.2 `GET /webhook/settings`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required (`Bearer` token + `roles` containing `admin`) |
| **Response** | `200 OK` — public view (no secrets); empty `target` fields fall back to env defaults (`TELEGRAM_CHAT_ID`, `SMTP_FROM`/`SMTP_USER`) |

```json
{
  "success": true,
  "data": {
    "telegram": { "enabled": true, "target": "123456789" },
    "email": { "enabled": false, "target": "" },
    "webhook": { "enabled": true, "target": "https://example.com/hook" }
  }
}
```

### 3.3 `PUT /webhook/settings`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Request body** | `SettingsPatch` — per-channel config, secrets encrypted server-side |
| **Response** | `200 OK` |

```json
{
  "telegram": { "enabled": true, "target": "123456789", "secret": "bot-token" },
  "email":    { "enabled": true, "target": "admin@example.com", "secret": "smtp-pass" },
  "webhook":  { "enabled": true, "target": "https://example.com/hook", "secret": "header-secret" }
}
```

### 3.4 `GET /webhook/logs`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Query** | `channel`, `status`, `limit` (1–500), `offset` |
| **Response** | `200 OK` |

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": "uuid",
        "channel": "telegram",
        "target": "123456789",
        "subject": "[CRITICAL] node-1/temperature",
        "status": "sent",
        "attempts": 1,
        "error": ""
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
}
```

### 3.5 `POST /webhook/test`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Body** | `{ "channel": "telegram" \| "email" \| "webhook" \| "" }` |
| **Response** | `202 Accepted` |

```json
{ "success": true, "data": { "enqueued": 2, "message": "test webhook queued for delivery" } }
```

### 3.6 `POST /webhook/receive/telegram`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Body** | Arbitrary JSON payload from Telegram update |
| **Response** | `202 Accepted` |

Accepts Telegram Bot API webhook updates, forwards payload to internal queue.

### 3.7 `POST /webhook/receive/email`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Body** | Arbitrary JSON payload from email webhook (SendGrid/Mailgun inbound parse) |
| **Response** | `202 Accepted` |

### 3.8 `POST /webhook/receive/generic`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Body** | Arbitrary JSON payload |
| **Response** | `202 Accepted` |

Generic inbound webhook receiver. All three endpoints enqueue the payload into `webhook:queue` for processing.

---

## 4. NATS Subjects

| Subject | Direction | Pattern | Payload | Status |
|---|---|---|---|---|
| `webhook.delivery` | Inbound / Event | Core NATS (Pub/Sub) | `deliveryEvent` | ✅ Active |
| `webhook.retry` | Inbound / Retry | JetStream Queue (durable consumer `webhook-retry-processor`) | `deliveryEvent` | ✅ Active |

### 4.1 `webhook.delivery` Payload

```json
{
  "channel": "telegram",
  "target": "123456789",
  "subject": "[CRITICAL] node-1/temperature",
  "body": "Temperature exceeded 35C threshold",
  "alert_id": "",
  "user_id": "admin"
}
```

### 4.2 `webhook.retry` Behavior

When delivery fails after `MaxAttempts` retries (or when an internal retry needs to be surfaced externally), the service republishes the failed payload to `webhook.retry`. A JetStream durable consumer `webhook-retry-processor` (queue group `webhook-retry-workers`) picks it up and re-injects it into the local Redis queue for another round of delivery attempts.

```bash
nats pub webhook.retry '{
  "channel": "telegram",
  "target": "123456789",
  "subject": "[CRITICAL] node-1/temperature",
  "body": "Temperature exceeded 35C threshold",
  "alert_id": "",
  "user_id": "admin"
}'
```

---

## 5. OpenAPI Specification

The full OpenAPI 3.0 spec is available at [`docs/openapi/webhook.yaml`](file:///home/almuzky/TA/Microservices/docs/openapi/webhook.yaml).

---

## 6. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | No | `8080` | HTTP listen port |
| `DB_DSN` | Yes | `webhook_user:webhook_pass@tcp(mariadb-webhook:3306)/webhook_db?parseTime=true&charset=utf8mb4` | MariaDB DSN |
| `REDIS_ADDR` | Yes | `redis-shared:6379` | Redis address |
| `REDIS_PASSWORD` | No | `""` | Redis password |
| `REDIS_DB` | No | `4` | Redis logical DB for webhook queue |
| `NATS_URL` | Yes | `nats://nats:4222` | NATS server URL |
| `JWT_SECRET` | Yes (prod) | `""` | Shared HMAC secret for JWT validation |
| `WEBHOOK_SECRET` | No | Falls back to `JWT_SECRET` | AES-256 key + webhook signing secret |
| `SMTP_HOST` | No (email) | `""` | SMTP server hostname |
| `SMTP_PORT` | No (email) | `587` | SMTP server port |
| `SMTP_USER` | No (email) | `""` | SMTP authentication username |
| `SMTP_FROM` | No (email) | `""` | Envelope From address |
| `WEBHOOK_MAX_ATTEMPTS` | No | `3` | Max delivery retries |
| `WEBHOOK_RETRY_DELAY_MS` | No | `1000` | Delay between retries |
| `WEBHOOK_SEND_INTERVAL_MS` | No | `100` | Throttle between consecutive sends |
| `WEBHOOK_DEV` | No | `1` | Simulate delivery in dev mode |
| `WEBHOOK_FORCE_FAIL` | No | `""` | Force failure for testing |

---

## 6. Integration Examples

### 6.1 Publish a webhook delivery event via NATS

```bash
nats pub webhook.delivery '{
  "channel": "telegram",
  "target": "123456789",
  "subject": "[CRITICAL] node-1/temperature",
  "body": "Temperature exceeded 35C",
  "alert_id": "",
  "user_id": "admin"
}'
```

### 6.2 Trigger via REST

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram", "target": "123456789", "subject": "test", "body": "hello"}' \
  http://localhost:8080/webhook/test
```

### 6.3 Receive external Telegram webhook

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"update_id": 123, "message": {"chat": {"id": 123456789}, "text": "/status"}}' \
  http://localhost:8080/webhook/receive/telegram
```

---

## 7. Security Notes

- **Secrets at rest:** Channel secrets encrypted with AES-GCM using `WEBHOOK_SECRET` (or fallback to `JWT_SECRET`). Never logged or returned by API.
- **Inbound webhook auth:** All `POST /webhook/receive/*` endpoints require JWT Bearer token. For external callback URLs, use a shared secret header or signature check.
- **Rate limits:** Not enforced at the webhook service level (Kong rate-limiting applies externally).
- **No secret leakage in errors:** `webhook_logs.error` never contains a secret.

---

## 8. Operational Notes

| Feature | Implementation |
|---|---|
| **Queue persistence** | Redis list `webhook:queue` — jobs survive restarts |
| **Retry** | Bounded by `WEBHOOK_MAX_ATTEMPTS` (default 3) with `WEBHOOK_RETRY_DELAY_MS` backoff |
| **Throttling** | `WEBHOOK_SEND_INTERVAL_MS` pause between sends |
| **Dev mode** | Unconfigured transports simulate success for pipeline testing |
| **Graceful shutdown** | NATS drained; in-flight Redis jobs persist |

---

## 9. Testing & Coverage

### 9.1 Go Unit Tests

The service includes repository and service-layer tests using the in-memory `testdriver` fake DB (no MariaDB required):

- `internal/repository/repository_test.go` — `TestGetSettingsReturnsExisting`, `TestUpsertSettingsPersists`, `TestCreateLog`, `TestUpdateLog`, `TestListLogsDefault`, `TestListLogsFilterChannel`
- `internal/service/service_test.go` — `TestReloadSettings`, `TestGetSettingsDTO`

Run tests:
```bash
cd services/webhook && go test ./...
```

### 9.2 Integration Test Suite (Python)

`test/unit_test.py` includes `TestWebhookService` with three API smoke tests via Kong:
- `test_01_webhook_logs`
- `test_02_get_webhook_settings`
- `test_03_dispatch_test_webhook`
