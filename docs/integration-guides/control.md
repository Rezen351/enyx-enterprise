# Control Service — Integration Guide

> **Service:** Control Service  
> **Version:** 1.0.0  
> **Port:** `8080` (configurable via `PORT`)  
> **Protocol:** REST (HTTP) + MQTT (actuator commands) + NATS (event bus / audit)  
> **Database:** MariaDB (`control_db`)  
> **Dependencies:** Kong (API Gateway), NATS, MQTT (Mosquitto), Module Service, MariaDB  
> **ADR References:** ADR-007 (Transactional Outbox)

---

## 1. Overview

The Control Service is the actuator command layer for the IoT aeroponics system. It receives high-level manual control commands and automatic schedule definitions from the Dashboard (via Kong), translates them into low-level `set_output` MQTT messages destined for ESP32 firmware, and tracks the full command lifecycle (pending → sent → acked / timeout / failed). It also runs a server-side scheduler engine that can automatically drive actuators on interval, time-of-day, threshold, duration, ramp, and window-pulse schedules.

### Key responsibilities

| Responsibility | Description |
|---|---|
| Manual command dispatch | Accept `set_state`, `set_level`, `toggle`, `pulse`, `emergency_stop` commands from the Dashboard and publish them to MQTT. |
| Command lifecycle tracking | Persist every command with a UUID `req_id`, update status (`pending` → `sent` → `acked` / `timeout` / `failed`), and expose a command log API. |
| Schedule CRUD & execution | Create, update, enable, disable, and delete automatic schedules. A built-in scheduler engine evaluates them server-side and dispatches `set_output` MQTT messages. |
| Mode arbitration | Per-node control mode (`MANUAL`, `AUTO`, `EMERGENCY`) determines whether manual commands or schedules are allowed. `EMERGENCY` forces all outputs OFF. |
| Firmware ACK correlation | Firmware ACKs arrive on MQTT `/confirm`; the service correlates them by `req_id` and marks the matching command `acked`. |
| Audit trail | All lifecycle events are written to a local `outbox` table and relayed to NATS subject `audit.log` via the Transactional Outbox (ADR-007). |
| Actuator tag resolution | Reads the Module Service tag-mapping (same schema as sensors) to resolve friendly output names to firmware targets. |

### Ports & addresses

| Component | Address | Notes |
|---|---|---|
| HTTP API | `:8080` | Behind Kong (`/v1/control/...`). |
| Health check | `:8080/health` | Public, no auth. |
| Prometheus metrics | `:8080/metrics` | Public, no auth. |
| MQTT publish | `smartfarm/actuator/{node_id}` | QoS 1, payload `{"action":"set_output","target":"...","value":N,"req_id":"..."}`. |
| MQTT subscribe | `smartfarm/{node_id}/confirm` | Firmware ACK payload `{"req_id":"...","target":"...","value":N,"status":"executed"}`. |
| MQTT subscribe | `smartfarm/{node_id}/telemetry` | Raw telemetry cached for threshold evaluation and output discovery. |
| NATS publish (outbox relay) | `audit.log` | Events: `control.command.sent`, `control.command.acked`, `control.command.failed`, `control.emergency_stop`, `control.schedule.created`, `control.schedule.updated`, `control.schedule.enabled`, `control.schedule.disabled`, `control.schedule.deleted`. |
| Module Service dependency | `http://module:8080` | Used to resolve actuator tags (`/nodes/{id}/actuators`) and verify node registration (`/nodes/{id}`). |

---

## 2. REST API Endpoints

All endpoints are mounted under `/control` (Kong strips `/v1`). All responses follow the standard envelope:

```jsonc
// Success (2xx)
{ "success": true, "data": <payload> }

// Error (4xx/5xx)
{ "success": false, "error": { "code": "<ERROR_CODE>", "message": "<english_message>" } }
```

### 2.1 Health

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/health` |
| **Auth** | None |

**Response:**

```json
{ "success": true, "data": { "status": "ok" } }
```

---

### 2.2 List Commands

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/commands` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `string` | Filter commands by node ID. |
| `limit` | `int` | Max 500, default 100. |

**Response:**

```json
{
  "success": true,
  "data": {
    "commands": [
      {
        "id": "uuid",
        "req_id": "uuid",
        "node_id": "node-1",
        "target": "pump",
        "tag_name": "Pump",
        "control_type": "set_state",
        "value": 1,
        "source": "manual",
        "schedule_id": null,
        "status": "acked",
        "issued_by": "user-123",
        "created_at": "2026-07-21T04:00:00Z",
        "acked_at": "2026-07-21T04:00:02Z"
      }
    ],
    "count": 1
  }
}
```

---

### 2.3 Send Manual Command

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/control/command` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body (`CommandRequest`):**

```json
{
  "node_id": "node-1",
  "output": "pump",
  "type": "set_state",
  "value": 1,
  "duration_sec": 0,
  "targets": [],
  "bypass": false
}
```

**Field descriptions:**

| Field | Type | Required | Description |
|---|---|---|---|
| `node_id` | `string` | Yes | Target node ID. Must be registered in Module Service. |
| `output` | `string` | Yes (except `emergency_stop`) | Firmware output name (e.g. `pump`) or friendly tag name. |
| `type` | `string` | Yes | `set_state`, `set_level`, `toggle`, `pulse`, `emergency_stop`. |
| `value` | `int` | Yes (`set_state`, `set_level`) | 0–255. For `set_state` use `1` (ON) or `0` (OFF). |
| `duration_sec` | `int` | No (for `pulse`) | Pulse duration in seconds. Default `5`. |
| `targets` | `array` | No | Optional actuator tag set rendered by the dashboard (keeps command consistent with UI). |
| `bypass` | `bool` | No | If `true`, command is allowed even when node is in `AUTO` mode. Intended for AI/automation services (e.g. TD3 controller) that need to override specific outputs without switching the node to MANUAL. |

**Response:**

```json
{
  "success": true,
  "data": {
    "commands": [
      {
        "id": "uuid",
        "req_id": "uuid",
        "node_id": "node-1",
        "target": "pump",
        "tag_name": "Pump",
        "control_type": "set_state",
        "value": 1,
        "source": "manual",
        "status": "sent",
        "created_at": "2026-07-21T04:00:00Z",
        "acked_at": null
      }
    ],
    "count": 1
  }
}
```

**Error codes:**

| HTTP Status | Error Code | Condition |
|---|---|---|
| `400` | `BAD_REQUEST` | `node_id` missing, `output` missing, `value` missing, value out of range (0–255), unknown type. |
| `409` | `CONFLICT` | Node is in `AUTO` mode and request did not set `bypass: true`; or `EMERGENCY` stop (resume required). |
| `502` | `UPSTREAM_ERROR` | Failed to verify node registration with Module Service. |
| `503` | `INTERNAL_ERROR` | MQTT broker unavailable. |

---

### 2.4 List Targets

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/targets` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `string` | Filter by node ID. |

**Response:**

```json
{
  "success": true,
  "data": {
    "targets": [
      {
        "id": "tag-uuid",
        "node_id": "node-1",
        "source_key": "outputs.pump",
        "tag_name": "Pump",
        "label": "Water Pump",
        "output_type": "DIGITAL",
        "last_value": 1,
        "last_seen_at": "2026-07-21T04:00:00Z",
        "created_at": "2026-07-21T03:00:00Z",
        "updated_at": "2026-07-21T03:00:00Z"
      }
    ],
    "count": 1
  }
}
```

---

### 2.5 List Outputs

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/outputs` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `string` | Filter by node ID. |

**Response:**

```json
{
  "success": true,
  "data": {
    "outputs": [
      { "name": "pump", "type": "DIGITAL", "value": 1 },
      { "name": "fan", "type": "PWM", "value": 128 }
    ],
    "count": 2
  }
}
```

---

### 2.6 Schedules

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/schedules` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `node_id` | `string` | Filter by node ID. |

**Response:**

```json
{
  "success": true,
  "data": {
    "schedules": [
      {
        "id": "uuid",
        "node_id": "node-1",
        "output_name": "pump",
        "tag_name": "Pump",
        "type": "interval",
        "params": { "on_sec": 10, "off_sec": 5, "value_on": 1, "value_off": 0 },
        "enabled": true,
        "next_run_at": "2026-07-21T04:00:10Z",
        "created_at": "2026-07-21T03:00:00Z",
        "updated_at": "2026-07-21T03:00:00Z"
      }
    ],
    "count": 1
  }
}
```

---

### 2.7 Get Schedule

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/schedules/{id}` |
| **Auth** | JWT required (any authenticated user) |

**Response:** Single `Schedule` object (same shape as above).

**Error codes:** `404 NOT_FOUND` if schedule does not exist.

---

### 2.8 Create Schedule

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/control/schedules` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body (`ScheduleRequest`):**

```json
{
  "node_id": "node-1",
  "output_name": "pump",
  "type": "interval",
  "params": { "on_sec": 10, "off_sec": 5, "value_on": 1, "value_off": 0 },
  "enabled": true
}
```

**Schedule types and their `params` shapes:**

| Type | Params fields | Description |
|---|---|---|
| `interval` | `on_sec`, `off_sec`, `value_on` (default 1), `value_off` (default 0) | Repeating ON/OFF cycle. |
| `schedule` | `on_at` (`"HH:MM"`), `off_at` (`"HH:MM"`), `days` (0=Sun..6=Sat, empty=every day), `value_on`, `value_off` | Time-of-day ON/OFF (cron-like). |
| `threshold` | `source_key` (telemetry dot-path), `threshold_high`, `threshold_low`, `value_on`, `value_off` | Sensor-driven with hysteresis. |
| `duration` | `total_sec`, `value_on`, `value_off` | ON for `total_sec` once, then OFF (one-shot). |
| `ramp` | `from`, `to`, `duration_sec`, `steps` | Linear PWM ramp. |
| `window_pulse` | `on_at`, `off_at`, `days`, `on_sec`, `off_sec`, `value_on`, `value_off` | Pulse only inside a time window. |

**Response:** `201 Created` with the created `Schedule` object.

---

### 2.9 Update Schedule

| | |
|---|---|
| **Method** | `PUT` |
| **Path** | `/control/schedules/{id}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body:** Same `ScheduleRequest` shape as create (partial update supported).

**Response:** `200 OK` with updated `Schedule` object.

---

### 2.10 Enable / Disable Schedule

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/control/schedules/{id}/enable` | 
| **Auth** | JWT required + role `admin` or `operator` |

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/control/schedules/{id}/disable` |
| **Auth** | JWT required + role `admin` or `operator` |

**Response:**

```json
{ "success": true, "data": { "id": "uuid", "enabled": true } }
```

---

### 2.11 Delete Schedule

| | |
|---|---|
| **Method** | `DELETE` |
| **Path** | `/control/schedules/{id}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Response:**

```json
{ "success": true, "data": { "message": "schedule deleted" } }
```

---

### 2.12 Get Node Mode

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/control/modes/{node_id}` |
| **Auth** | JWT required (any authenticated user) |

**Response:**

```json
{ "success": true, "data": { "node_id": "node-1", "mode": "AUTO" } }
```

Mode defaults to `AUTO` if no record exists.

---

### 2.13 Set Node Mode

| | |
|---|---|
| **Method** | `PUT` |
| **Path** | `/control/modes/{node_id}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body (`ModeRequest`):**

```json
{ "mode": "MANUAL" }
```

Allowed values: `MANUAL`, `AUTO`, `EMERGENCY`.

**Response:**

```json
{ "success": true, "data": { "node_id": "node-1", "mode": "MANUAL" } }
```

---

### 2.14 Resume Node

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/control/modes/{node_id}/resume` |
| **Auth** | JWT required + role `admin` or `operator` |

Exits `EMERGENCY` and restores the mode that was active before emergency (defaults to `AUTO`).

**Response:**

```json
{ "success": true, "data": { "node_id": "node-1", "mode": "AUTO" } }
```

---

### 2.15 Set Output Mode

| | |
|---|---|
| **Method** | `PUT` |
| **Path** | `/control/modes/{node_id}/{output}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body:**

```json
{ "mode": "AUTO", "schedule_id": "schedule-uuid" }
```

**Response:**

```json
{ "success": true, "data": { "node_id": "node-1", "output": "pump", "mode": "AUTO" } }
```

---

## 3. Input Contracts

### 3.1 From Dashboard / REST

The Dashboard sends two kinds of input:

1. **Manual commands** — `POST /control/command` with a `CommandRequest` body.
   - The service validates `node_id` against the Module Service to prevent spoofing.
   - `value` must be `0–255`.
   - `targets` array (optional) is the exact actuator tag set the dashboard rendered; when present, it bypasses the Module Service lookup for tag resolution.

2. **Schedule definitions** — `POST /control/schedules` with a `ScheduleRequest` body.
   - `params` is a JSON object whose shape depends on `type`.
   - The service resolves `tag_name` by looking up the output in the Module Service tag-mapping.

### 3.2 To MQTT (Mosquitto)

Every command dispatch results in one MQTT publish:

**Topic:** `{topic_prefix}/actuator/{node_id}`  
**QoS:** 1 (at-least-once)  
**Payload:**

```json
{
  "action": "set_output",
  "target": "pump",
  "value": 1,
  "req_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Description |
|---|---|
| `action` | Always `"set_output"` (firmware contract). |
| `target` | Firmware output name (e.g. `"pump"`), derived from `source_key` in the tag-mapping. |
| `value` | Integer `0–255`. |
| `req_id` | UUID used to correlate the firmware `/confirm` ACK back to the command row. |

The service **subscribes** to:
- `{topic_prefix}/{node_id}/confirm` — firmware execution ACK.
- `{topic_prefix}/{node_id}/telemetry` — raw telemetry (cached for threshold evaluation and output discovery).

---

## 4. Output Contracts

### 4.1 MQTT Inbound (Firmware → Control)

**Topic:** `{topic_prefix}/{node_id}/confirm`

**Payload:**

```json
{
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "pump",
  "value": 1,
  "status": "executed"
}
```

The `OnConfirm` handler looks up the command by `req_id` and transitions it from `pending`/`sent` → `acked`.

---

### 4.2 Command Status Lifecycle

| Status | Meaning |
|---|---|
| `pending` | Command row created, about to publish to MQTT. |
| `sent` | Published to MQTT successfully, awaiting firmware ACK. |
| `acked` | Firmware `/confirm` received and correlated. |
| `timeout` | No ACK within `ACK_TIMEOUT_SECONDS` (default 8s). Marked by a periodic sweep goroutine. |
| `failed` | MQTT publish error or broker unavailable. |

---

### 4.3 NATS Subjects (Outbox Relay)

All events are written to the local `outbox` table and relayed to NATS by a background worker (ADR-007). The relay publishes with header `Nats-Msg-Id: <uuid>` for publisher-side deduplication.

| Subject | Event | Payload shape |
|---|---|---|
| `audit.log` | `control.command.sent` | `{"event":"control.command.sent","service":"control","data":{"node_id":"...","target":"...","value":"1","source":"manual","type":"set_state","msg_id":"..."}}` |
| `audit.log` | `control.command.acked` | `{"event":"control.command.acked","service":"control","data":{"node_id":"...","target":"...","req_id":"...","msg_id":"..."}}` |
| `audit.log` | `control.command.failed` | `{"event":"control.command.failed","service":"control","data":{"node_id":"...","target":"...","reason":"mqtt_unavailable","msg_id":"..."}}` |
| `audit.log` | `control.emergency_stop` | `{"event":"control.emergency_stop","service":"control","data":{"node_id":"...","by":"user-123","msg_id":"..."}}` |
| `audit.log` | `control.schedule.created` | `{"event":"control.schedule.created","service":"control","data":{"schedule_id":"...","node_id":"...","type":"interval","msg_id":"..."}}` |
| `audit.log` | `control.schedule.updated` | `{"event":"control.schedule.updated","service":"control","data":{"schedule_id":"...","msg_id":"..."}}` |
| `audit.log` | `control.schedule.enabled` | `{"event":"control.schedule.enabled","service":"control","data":{"schedule_id":"...","msg_id":"..."}}` |
| `audit.log` | `control.schedule.disabled` | `{"event":"control.schedule.disabled","service":"control","data":{"schedule_id":"...","msg_id":"..."}}` |
| `audit.log` | `control.schedule.deleted` | `{"event":"control.schedule.deleted","service":"control","data":{"schedule_id":"...","msg_id":"..."}}` |

---

### 4.4 ACK Timeout Sweep

A background goroutine runs every 10 seconds and flips commands older than `ACK_TIMEOUT_SECONDS` (default 8s) from `pending`/`sent` → `timeout`. This prevents stale commands from remaining in limbo if firmware goes offline.

---

## 5. Integration Steps

### 5.1 Calling the Control Service from a Dashboard / Frontend

1. **Obtain a JWT** from the Auth Service (`POST /auth/login`).
2. **Call read endpoints** with `Authorization: Bearer <token>`:
   - `GET /control/targets?node_id=...` — discover controllable outputs.
   - `GET /control/outputs?node_id=...` — discover firmware outputs from telemetry.
   - `GET /control/modes/{node_id}` — check current mode.
   - `GET /control/schedules?node_id=...` — list active schedules.
   - `GET /control/commands?node_id=...` — view command history.
3. **Send commands** with a token that has role `admin` or `operator`:
   - `POST /control/command` with `{ node_id, output, type, value }`.
   - If the node is in `AUTO` mode, the API returns `409 CONFLICT`. Switch to `MANUAL` first via `PUT /control/modes/{node_id}`.
   - If the node is in `EMERGENCY`, the API returns `409 CONFLICT`. Resume via `POST /control/modes/{node_id}/resume`.

### 5.2 Consuming Control Events

Subscribe to `audit.log` on NATS to receive all Control Service lifecycle events. Use the `msg_id` field (present in every event payload) for consumer-side idempotency (dedupe in Redis).

### 5.3 Adding a New Schedule Type

1. Add a new `SchedXxx` constant and `XxxParams` struct in `internal/model/model.go`.
2. Add a `runXxx` method in `internal/scheduler/scheduler.go`.
3. Register the new type in `runSchedule` switch.
4. Document the `params` shape in this guide and in any OpenAPI spec.

### 5.4 Integrating a New Downstream Service

If a new service needs to react to Control events:
1. Subscribe to `audit.log` on NATS.
2. Filter by `event` prefix `control.`.
3. Deduplicate using `msg_id` (store in Redis with TTL > NATS retry window).
4. The existing payload contract does not need to change.

---

## 6. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | HTTP listen port. |
| `DB_DSN` | `control_user:control_pass@tcp(mariadb-control:3306)/control_db?parseTime=true&charset=utf8mb4` | MariaDB DSN. |
| `NATS_URL` | `nats://nats:4222` | NATS server URL. |
| `MQTT_URL` | `tcp://mosquitto:1883` | MQTT broker URL. |
| `MQTT_USER` | `""` | MQTT username (optional). |
| `MQTT_PASS` | `""` | MQTT password (optional). |
| `MQTT_CLIENT_ID` | `control-svc` | MQTT client ID. |
| `MQTT_TOPIC_PREFIX` | `smartfarm` | MQTT topic prefix. |
| `JWT_SECRET` | `""` | Shared HMAC secret for JWT validation (same as Auth Service). Empty = skip validation (dev only). |
| `TIMEZONE` | `UTC` | IANA timezone for schedule/window evaluation (e.g. `Asia/Jakarta`). |
| `ACK_TIMEOUT_SECONDS` | `8` | Seconds before a `sent` command is marked `timeout`. |
| `MODULE_URL` | `http://module:8080` | Module Service base URL (for tag-mapping and node registration). |

---

## 7. Database Schema Overview

The Control Service owns `control_db` with four tables, managed by GORM AutoMigrate in `migrate.go`.

### 7.1 `control_modes`

Stores per-node and per-output control modes. A sentinel row with `output_name = '*'` stores the node-level mode.

| Column | Type | Key | Description |
|---|---|---|---|
| `node_id` | `varchar(100)` | PK (with `output_name`) | Node identifier. |
| `output_name` | `varchar(100)` | PK (with `node_id`) | Output name, or `'*'` for node-level sentinel. |
| `mode` | `varchar(16)` | — | `MANUAL`, `AUTO`, or `EMERGENCY`. Default `MANUAL`. |
| `prev_mode` | `varchar(16)` | — | Mode active before `EMERGENCY` (used by `ResumeNode`). |
| `active_schedule_id` | `char(36)` | — | Currently active schedule for this output (when `AUTO`). |
| `updated_at` | `timestamp` | — | Auto-updated on row change. |

### 7.2 `schedules`

Automatic schedule definitions.

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | `char(36)` | PK | UUID. |
| `node_id` | `varchar(100)` | Index | Target node. |
| `output_name` | `varchar(100)` | — | Target output. |
| `tag_name` | `varchar(128)` | — | Friendly tag name (resolved from Module Service). |
| `type` | `varchar(16)` | — | `interval`, `schedule`, `threshold`, `duration`, `ramp`, `window_pulse`. |
| `params` | `longtext` | — | JSON object, shape depends on `type`. |
| `enabled` | `bool` | — | Default `0` (disabled). |
| `next_run_at` | `timestamp` | — | Next scheduled execution time. |
| `created_at` | `timestamp` | Index | Creation time. |
| `updated_at` | `timestamp` | — | Last update time. |

### 7.3 `commands`

Command audit log with lifecycle status.

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | `char(36)` | PK | UUID. |
| `req_id` | `varchar(64)` | Index | Correlation ID (echoed in MQTT payload). |
| `node_id` | `varchar(100)` | Index | Target node. |
| `target` | `varchar(100)` | — | Firmware output name. |
| `tag_name` | `varchar(128)` | — | Friendly tag name. |
| `control_type` | `varchar(24)` | — | `set_state`, `set_level`, `toggle`, `pulse`, `emergency_stop`, or schedule type. |
| `value` | `int` | — | Command value (0–255). |
| `source` | `varchar(16)` | — | `manual` or `schedule`. |
| `schedule_id` | `char(36)` | — | Parent schedule ID (if dispatched by scheduler). |
| `status` | `varchar(16)` | Index | `pending`, `sent`, `acked`, `timeout`, `failed`. Default `pending`. |
| `issued_by` | `varchar(64)` | — | User ID (manual commands only). |
| `created_at` | `timestamp` | Index | Dispatch time. |
| `acked_at` | `timestamp` | — | Set when firmware confirms. |

### 7.4 `outbox`

Transactional Outbox table (ADR-007).

| Column | Type | Key | Description |
|---|---|---|---|
| `id` | `char(36)` | PK | UUID. |
| `msg_id` | `varchar(64)` | Unique index | Idempotency key (also sent as NATS `Nats-Msg-Id` header). |
| `subject` | `varchar(128)` | Index | NATS subject (e.g. `audit.log`). |
| `payload` | `longtext` | — | JSON event payload. |
| `sent` | `bool` | Index | `0` = pending, `1` = delivered. Default `0`. |
| `created_at` | `timestamp` | — | Row creation time. |
| `sent_at` | `timestamp` | — | Set after successful NATS publish. |

---

## 8. Example curl Commands

Assume Kong is reachable at `http://localhost:8000` and JWT token is stored in `$TOKEN`.

```bash
# Health
curl -s http://localhost:8000/health | jq

# List commands for a node
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/control/commands?node_id=node-1&limit=10" | jq

# Send manual ON command
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","output":"pump","type":"set_state","value":1}' \
  http://localhost:8000/v1/control/command | jq

# Send PWM level command
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","output":"fan","type":"set_level","value":128}' \
  http://localhost:8000/v1/control/command | jq

# Toggle output
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","output":"pump","type":"toggle"}' \
  http://localhost:8000/v1/control/command | jq

# Pulse (ON for 10 seconds then OFF)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","output":"pump","type":"pulse","value":1,"duration_sec":10}' \
  http://localhost:8000/v1/control/command | jq

# Emergency stop (all outputs OFF)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"node_id":"node-1","type":"emergency_stop"}' \
  http://localhost:8000/v1/control/command | jq

# Resume from emergency
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/modes/node-1/resume | jq

# List targets (actuator tags from Module Service)
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/control/targets?node_id=node-1" | jq

# List firmware outputs discovered from telemetry
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/control/outputs?node_id=node-1" | jq

# Get node mode
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/modes/node-1 | jq

# Set node to MANUAL
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"MANUAL"}' \
  http://localhost:8000/v1/control/modes/node-1 | jq

# Set node to AUTO
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"AUTO"}' \
  http://localhost:8000/v1/control/modes/node-1 | jq

# Create an interval schedule (ON 10s, OFF 5s)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-1",
    "output_name": "pump",
    "type": "interval",
    "params": {"on_sec": 10, "off_sec": 5, "value_on": 1, "value_off": 0},
    "enabled": true
  }' \
  http://localhost:8000/v1/control/schedules | jq

# Create a time-of-day schedule
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-1",
    "output_name": "pump",
    "type": "schedule",
    "params": {"on_at":"06:00","off_at":"18:00","days":[],"value_on":1,"value_off":0},
    "enabled": true
  }' \
  http://localhost:8000/v1/control/schedules | jq

# Create a threshold schedule (sensor-driven)
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "node_id": "node-1",
    "output_name": "pump",
    "type": "threshold",
    "params": {"source_key":"sensors.humidity","threshold_high":80.0,"threshold_low":60.0,"value_on":1,"value_off":0},
    "enabled": true
  }' \
  http://localhost:8000/v1/control/schedules | jq

# List schedules
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/v1/control/schedules?node_id=node-1" | jq

# Get a schedule by ID
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/schedules/<schedule-id> | jq

# Update a schedule
curl -s -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"params":{"on_sec":15,"off_sec":5,"value_on":1,"value_off":0}}' \
  http://localhost:8000/v1/control/schedules/<schedule-id> | jq

# Enable a schedule
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/schedules/<schedule-id>/enable | jq

# Disable a schedule
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/schedules/<schedule-id>/disable | jq

# Delete a schedule
curl -s -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/v1/control/schedules/<schedule-id> | jq
```

---

## 9. Error Reference

| HTTP Status | Error Code | Meaning |
|---|---|---|
| `400` | `BAD_REQUEST` | Invalid input (missing fields, value out of range, unknown type, invalid mode). |
| `401` | `UNAUTHORIZED` | Missing or invalid JWT. |
| `403` | `FORBIDDEN` | Authenticated but insufficient role (write endpoints require `admin` or `operator`). |
| `404` | `NOT_FOUND` | Schedule not found. |
| `409` | `CONFLICT` | Node is in `AUTO` mode (manual override blocked) or `EMERGENCY` stop. |
| `502` | `UPSTREAM_ERROR` | Failed to verify node registration with Module Service. |
| `503` | `INTERNAL_ERROR` | MQTT broker unavailable; command could not be dispatched. |
| `500` | `INTERNAL_ERROR` | Unexpected server error. |

---

## 10. Resilience & Operational Notes

- **MQTT unavailability:** If the MQTT broker is down, commands are still persisted in MariaDB with status `failed` and an audit event is emitted. The Dashboard should treat `503` as "retry later".
- **NATS unavailability:** Audit events are buffered in the `outbox` table and relayed once NATS recovers (ADR-007). No events are lost.
- **Module Service dependency:** Actuator tag resolution and node registration verification require the Module Service. If it is down, `targets` and `outputs` endpoints may fail with `502`.
- **Scheduler reconciliation:** The scheduler engine reloads enabled schedules every 15 seconds. Mutations (create/enable/disable/update/delete) trigger an immediate reconcile via `NotifyScheduleChanged()`.
- **Mode arbitration:** Schedules only run in `AUTO` mode. Switching to `MANUAL` or `EMERGENCY` pauses the scheduler for that node.
- **Graceful shutdown:** The service drains in-flight requests, cancels the scheduler context, stops the outbox relay, and disconnects MQTT/NATS cleanly on `SIGINT`/`SIGTERM`.
