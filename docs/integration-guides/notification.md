# Notification Service — Integration Guide

> **Service:** Notification Service  
> **Module path:** `services/notification`  
> **Status:** Implemented (Fase 1-5 complete)

---

## 1. Overview

The Notification Service is the unified multi-channel delivery sink for the IoT platform (the former standalone Webhook Service has been merged into it). It consumes alert events from the NATS event bus and dispatches notifications through four channels:

- **Telegram** — Bot API (`sendMessage`)
- **Email** — SMTP (plain-text RFC 822)
- **Push** — Generic HTTP push gateway (Bearer token)
- **Webhook** — Outbound HTTP POST to a configurable callback URL

The service is designed to be resilient: jobs are persisted in Redis before delivery, retried up to a configurable maximum, and throttled to avoid spamming downstream channels. Channel secrets (bot tokens, SMTP passwords, push server keys) are encrypted at rest using AES-GCM and are never exposed through the API or logs.

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
| **MariaDB** | Settings + delivery log persistence | `mariadb-notification:3306` (DB `notification_db`) |
| **Redis** | Async delivery work queue | `redis-shared:6379` (logical DB `0`) |
| **NATS** | Alert event ingestion | `nats://nats:4222` |
| **SMTP host** | Email delivery (optional) | Configured via env |
| **Telegram Bot API** | Telegram delivery (optional) | `https://api.telegram.org` |
| **Push gateway** | Push delivery (optional) | Configured via env |

---

## 2. REST API Endpoints

All endpoints (except `/health`) return a standardized response wrapper:

```jsonc
// Success (2xx)
{ "success": true, "data": <payload> }

// Error (4xx / 5xx)
{ "success": false, "error": { "code": "<ERROR_CODE>", "message": "<english_message>" } }
```

Authentication uses shared JWT HMAC (`Authorization: Bearer <token>`). When `JWT_SECRET` is empty (dev mode), validation is skipped — but Kong still fronts the service.

### 2.1 `GET /health`

| Attribute | Value |
|---|---|
| **Auth** | None (public) |
| **Response** | `200 OK` |

```json
{ "success": true, "data": { "status": "ok" } }
```

---

### 2.2 `GET /notifications/settings`

| Attribute | Value |
|---|---|
| **Auth** | Any authenticated user (`Bearer` token) |
| **Response** | `200 OK` — public view (no secrets) |

```json
{
  "success": true,
  "data": {
    "telegram": { "enabled": true, "target": "123456789" },
    "email": { "enabled": false, "target": "" },
    "push": { "enabled": true, "target": "device-token-abc" },
    "webhook": { "enabled": false, "target": "" }
  }
}
```

> **Note:** Secrets (bot token, SMTP password, push server key, webhook signature) are **never** returned by this endpoint.

---

### 2.3 `PUT /notifications/settings`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required (`Bearer` token + `roles` containing `admin`) |
| **Request body** | `SettingsPatch` — per-channel config, secrets encrypted server-side |
| **Response** | `200 OK` — updated settings DTO (no secrets) |

```json
{
  "telegram": { "enabled": true, "target": "123456789", "secret": "bot-token-here" },
  "email": { "enabled": true, "target": "admin@example.com", "secret": "smtp-password" },
  "push": { "enabled": false, "target": "", "secret": "" },
  "webhook": { "enabled": false, "target": "", "secret": "" }
}
```

**Validation rules:**

| Field | Rule |
|---|---|
| `telegram.target` | Must match `^-?\d+$` (numeric chat ID) |
| `email.target` | Must match email regex |
| `push.target` | Non-empty when `push.enabled` is true |
| `webhook.target` | Non-empty URL when `webhook.enabled` is true |

---

### 2.4 `GET /notifications/logs`

| Attribute | Value |
|---|---|
| **Auth** | Any authenticated user |
| **Query params** | `channel` (optional), `status` (optional), `limit` (1–500, default 50), `offset` (default 0) |
| **Response** | `200 OK` — paginated log entries, newest first |

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
        "error": "",
        "alert_id": "",
        "user_id": "admin",
        "created_at": "2026-07-21T12:00:00Z"
      }
    ],
    "total": 1,
    "limit": 50,
    "offset": 0
  }
}
```

---

### 2.5 `POST /notifications/test`

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Request body** | `{ "channel": "telegram" \| "email" \| "push" \| "webhook" \| "" }` — omit channel to test all enabled channels |
| **Response** | `202 Accepted` |

```json
{
  "success": true,
  "data": { "enqueued": 2, "message": "test notification(s) queued for delivery" }
}
```

---

### 2.6 `POST /notifications/receive/*` (Inbound Webhook Receivers)

| Attribute | Value |
|---|---|
| **Auth** | Admin role required |
| **Endpoints** | `/notifications/receive/telegram`, `/notifications/receive/email`, `/notifications/receive/generic`, `/notifications/receive/delivery` |
| **Response** | `202 Accepted` |

These endpoints let external systems (or other services) push a payload that is enqueued as a delivery job:

- `/receive/telegram` and `/receive/email` accept an arbitrary JSON body and store it as a `telegram` / `email` delivery (useful for bridging inbound chat/email into the platform).
- `/receive/generic` stores the body as a `webhook` delivery.
- `/receive/delivery` accepts a full `DeliveryEvent` JSON (`{ "channel", "target", "subject", "body", "alert_id", "user_id" }`) for explicit fan-out control.

```json
// POST /notifications/receive/delivery
{
  "channel": "webhook",
  "target": "https://example.com/hook",
  "subject": "External Event",
  "body": "payload",
  "alert_id": "",
  "user_id": "admin"
}
```

---

### 3.1 NATS — Alert Event Ingestion

The service subscribes to **`alert.*`** using a NATS queue group (`notification-workers`). Any service can publish to this subject to trigger notifications. It also subscribes to **`webhook.delivery`** (core queue group `notification-delivery-workers`) for explicit delivery jobs and **`webhook.retry`** (JetStream durable `notification-retry-processor`) which republishes failed jobs back onto `webhook.delivery`. External producers (or the inbound receive endpoints) publish a `DeliveryEvent` JSON to these subjects.

**Subject pattern:** `alert.*`

**Queue group:** `notification-workers`

**Expected JSON payload:**

```json
{
  "node_id": "node-1",
  "metric": "temperature",
  "severity": "critical",
  "message": "Temperature exceeded 35°C threshold"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `node_id` | string | Yes | Device / sensor node identifier |
| `metric` | string | Yes | Metric name that triggered the alert |
| `severity` | string | Yes | Alert severity (e.g. `info`, `warning`, `critical`) |
| `message` | string | No | Human-readable description. Falls back to `"Alert on node {node_id} metric {metric}"` if empty |

**Fan-out behavior:** On receipt of an `alert.*` event, the service creates one delivery job per **enabled** channel (telegram, email, push, webhook). A `webhook.delivery` event already specifies its own channel and target, so it produces a single job.

---

## 4. Output Contracts

### 4.1 Delivery Channels

| Channel | Transport | Required config |
|---|---|---|
| **Telegram** | HTTPS POST to `https://api.telegram.org/bot<token>/sendMessage` | `telegram_secret` (bot token), `telegram_target` (chat ID) |
| **Email** | SMTP (plain-text) | `smtp_host`, `smtp_port`, `smtp_user`, `smtp_from`, `email_secret` (SMTP password), `email_target` (recipient) |
| **Push** | HTTPS POST to `PUSH_URL` with `Authorization: Bearer <secret>` | `push_url`, `push_secret` (server key), `push_target` (device token) |
| **Webhook** | HTTPS POST to the configured callback URL with `subject`/`body` (and optional `signature`) | `webhook_target` (callback URL), `webhook_secret` (signature token) |

### 4.2 Delivery Log (`notification_logs`)

Every delivery attempt is persisted. Status lifecycle:

```
queued → retrying → sent
              ↘ failed (after max attempts)
```

| Column | Type | Description |
|---|---|---|
| `id` | `char(36)` | UUID primary key |
| `channel` | `varchar(16)` | `telegram`, `email`, or `push` |
| `target` | `varchar(512)` | Chat ID, email address, or device token |
| `subject` | `varchar(255)` | Notification subject (SMTP Subject / Telegram message prefix) |
| `body` | `text` | Full message body |
| `status` | `varchar(16)` | `queued`, `retrying`, `sent`, `failed` |
| `attempts` | `int` | Number of send attempts so far |
| `error` | `varchar(512)` | Transport error message (never contains secrets) |
| `alert_id` | `varchar(64)` | Linked alert ID (optional, empty for test notifications) |
| `user_id` | `varchar(64)` | User who triggered / configured the notification |
| `created_at` | `datetime` | Auto-set on insert |
| `updated_at` | `datetime` | Auto-updated on change |

---

## 5. Integration Steps

### 5.1 Triggering Notifications from Another Service

Publish an alert event to the NATS subject `alert.*`. The Notification Service will:

1. Parse the event.
2. Load current channel settings from in-memory cache.
3. Enqueue one job per enabled channel into the Redis work queue.
4. The background worker will dequeue jobs, decrypt the relevant channel secret, and attempt delivery.
5. If delivery fails, the job is re-enqueued (up to `MaxAttempts` times with `RetryDelay` backoff).
6. Every state transition is persisted in `notification_logs`.

**Example (Go, using nats.go):**

```go
import "github.com/nats-io/nats.go"

nc, _ := nats.Connect(nats.DefaultURL)
event := map[string]string{
  "node_id":   "node-1",
  "metric":    "temperature",
  "severity":  "critical",
  "message":   "Temperature exceeded threshold",
}
payload, _ := json.Marshal(event)
nc.Publish("alert.node-1", payload)
```

> **Tip:** Use a specific subject like `alert.node-1` or `alert.system` — the wildcard `alert.*` ensures the Notification Service receives it.

### 5.2 Configuring Channels

1. Obtain an admin JWT token from the Auth Service.
2. `PUT /notifications/settings` with the desired channel configurations.
3. Secrets are encrypted server-side — you can update them at any time without downtime.

### 5.3 Verifying Delivery

- Query `GET /notifications/logs` to inspect recent delivery attempts.
- Use `POST /notifications/test` to enqueue a dummy notification for all enabled channels.

---

## 6. Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | No | `8080` | HTTP listen port |
| `DB_DSN` | Yes | `notification_user:notification_pass@tcp(mariadb-notification:3306)/notification_db?parseTime=true&charset=utf8mb4` | MariaDB DSN |
| `REDIS_ADDR` | Yes | `redis-shared:6379` | Redis address |
| `REDIS_PASSWORD` | No | `""` | Redis password |
| `REDIS_DB` | No | `0` | Redis logical database index |
| `NATS_URL` | Yes | `nats://nats:4222` | NATS server URL |
| `JWT_SECRET` | Yes (prod) | `""` | Shared HMAC secret for JWT validation |
| `NOTIFICATION_SECRET_KEY` | No | Falls back to `JWT_SECRET` | AES-256 key material for encrypting channel secrets |
| `SMTP_HOST` | No (email) | `""` | SMTP server hostname |
| `SMTP_PORT` | No (email) | `587` | SMTP server port |
| `SMTP_USER` | No (email) | `""` | SMTP authentication username |
| `SMTP_FROM` | No (email) | `""` | Envelope From address (falls back to `SMTP_USER`) |
| `PUSH_URL` | No (push) | `""` | Push gateway endpoint URL |
| `NOTIFICATION_MAX_ATTEMPTS` | No | `3` | Maximum delivery retries before marking failed |
| `NOTIFICATION_RETRY_DELAY_MS` | No | `1000` | Delay between retries |
| `NOTIFICATION_SEND_INTERVAL_MS` | No | `100` | Throttle between consecutive sends |
| `NOTIFICATION_DEV` | No | `1` | When set to `1` (default), simulates delivery if transport is unconfigured |
| `NOTIFICATION_FORCE_FAIL` | No | `""` | When `1`, forces every send to fail (for testing retries) |

---

## 7. Database Schema Overview

The service uses GORM auto-migration on boot (`migrate.go`).

### `notification_settings` (singleton)

| Column | Type | Constraints |
|---|---|---|
| `id` | `varchar(36)` | Primary key, fixed value `"singleton"` |
| `telegram_enabled` | `bool` | Default `false` |
| `telegram_target` | `varchar(64)` | Chat ID |
| `telegram_secret` | `varchar(512)` | AES-GCM encrypted bot token |
| `email_enabled` | `bool` | Default `false` |
| `email_target` | `varchar(255)` | Recipient address |
| `email_secret` | `varchar(512)` | AES-GCM encrypted SMTP password |
| `push_enabled` | `bool` | Default `false` |
| `push_target` | `varchar(512)` | Device token |
| `push_secret` | `varchar(512)` | AES-GCM encrypted push server key |
| `webhook_enabled` | `bool` | Default `false` |
| `webhook_target` | `varchar(1024)` | Callback URL |
| `webhook_secret` | `varchar(512)` | AES-GCM encrypted signature token |
| `updated_at` | `datetime` | Auto-updated |
| `updated_by` | `varchar(64)` | User ID of last updater |

### `notification_logs`

| Column | Type | Constraints |
|---|---|---|
| `id` | `char(36)` | Primary key, UUID |
| `channel` | `varchar(16)` | Indexed, `telegram` / `email` / `push` / `webhook` |
| `target` | `varchar(512)` | Destination address |
| `subject` | `varchar(255)` | Message subject / title |
| `body` | `text` | Full message body |
| `status` | `varchar(16)` | `queued` / `retrying` / `sent` / `failed` |
| `attempts` | `int` | Default `0` |
| `error` | `varchar(512)` | Error message (no secrets) |
| `alert_id` | `varchar(64)` | Optional linked alert ID |
| `user_id` | `varchar(64)` | Triggering or configuring user |
| `created_at` | `datetime` | Auto-set |
| `updated_at` | `datetime` | Auto-updated |

**Redis key:** `notification:queue` (LPUSH / BRPOP list of JSON-serialized `Job` objects)

---

## 8. Example curl Commands

Replace `$TOKEN` with a valid JWT access token from the Auth Service. Replace `$BASE` with the service host (e.g. `http://localhost:8080` or via Kong `https://api.example.com`).

### 8.1 Health Check

```bash
curl -s $BASE/health
```

### 8.2 Get Current Settings

```bash
curl -s -H "Authorization: Bearer $TOKEN" $BASE/notifications/settings
```

### 8.3 Update Settings (admin)

```bash
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "telegram": { "enabled": true, "target": "123456789", "secret": "123456:ABC-DEF..." },
    "email":    { "enabled": true, "target": "admin@example.com", "secret": "smtp-pass" },
    "push":     { "enabled": false, "target": "", "secret": "" },
    "webhook":  { "enabled": false, "target": "", "secret": "" }
  }' \
  $BASE/notifications/settings
```

### 8.4 List Delivery Logs

```bash
# All logs, first page
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/notifications/logs?limit=20"

# Filter by channel and status
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/notifications/logs?channel=telegram&status=failed&limit=10"
```

### 8.5 Send Test Notification (admin)

```bash
# Test a specific channel
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram"}' \
  $BASE/notifications/test

# Test all enabled channels
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' \
  $BASE/notifications/test
```

### 8.7 Post an Inbound Webhook (admin)

```bash
# Generic inbound webhook (stored as a webhook delivery)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event": "something happened"}' \
  $BASE/notifications/receive/generic

# Explicit delivery event with channel + target
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "webhook", "target": "https://example.com/hook", "subject": "External", "body": "payload"}' \
  $BASE/notifications/receive/delivery
```

---

## 9. Security Considerations

- **Secrets at rest:** Channel secrets are encrypted with AES-GCM using a key derived from `NOTIFICATION_SECRET_KEY` (or `JWT_SECRET`). They are never logged, never returned by the API, and only decrypted in memory immediately before a send attempt.
- **JWT validation:** The service validates `Bearer` tokens using the shared HMAC secret. In dev mode (`JWT_SECRET=""`), validation is skipped, but Kong still provides an external gateway layer.
- **Role-based access:** Settings mutations and test sends require the `admin` role. Logs and settings reads require any authenticated user.
- **No secret leakage in errors:** Transport error messages returned by channel senders are scrubbed; the worker enforces that `notification_logs.error` never contains a secret.

---

## 10. Resilience & Operational Notes

| Feature | Implementation |
|---|---|
| **Queue persistence** | Redis list `notification:queue` — jobs survive service restarts |
| **Retry** | Bounded by `NOTIFICATION_MAX_ATTEMPTS` (default 3) with `NOTIFICATION_RETRY_DELAY_MS` backoff |
| **Throttling** | `NOTIFICATION_SEND_INTERVAL_MS` pause between sends to avoid downstream rate limits |
| **Dev mode** | When a channel transport is unconfigured, `DevMode` simulates success so the full pipeline can be tested without external credentials |
| **Graceful shutdown** | NATS connection is drained; in-flight jobs in Redis are not lost |
| **Idempotency** | Each log entry has a UUID `id`. Duplicate NATS messages will create new log rows (no deduplication at this layer — the Alert Service should avoid re-publishing the same event). |
