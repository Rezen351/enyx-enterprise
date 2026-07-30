# Spray Automation Service — Planning Document (Simplified)

> **Service:** Spray Automation Service  
> **Version:** 1.0.0  
> **Port:** `8080` (configurable via `PORT`)  
> **Protocol:** REST (HTTP) + NATS (event bus) + HTTP (Control Service upstream)  
> **Database:** Redis Shared (`redis-shared` DB4) — no MariaDB  
> **Dependencies:** Kong (API Gateway), NATS, Mosquitto, Module Service, Control Service, Stream Service, ML Service  
> **ADR References:** ADR-007 (Transactional Outbox — optional, can use best-effort NATS)

---

## 1. Overview

The Spray Automation Service is a lightweight AI controller for the aeroponic misting system. It consumes AI detection results from the ML Service, correlates them with real-time telemetry, and **directly writes/overwrites schedules in the Control Service** via REST API. It does **not** maintain its own schedule database — Control Service is the single source of truth for schedules.

### Key Responsibilities

| Responsibility | Description |
|---|---|
| **AI-driven schedule override** | Consume `detection.result` from ML Service, analyze root length and crop condition, then **directly update schedules in Control Service** via REST. |
| **Telemetry-triggered snapshot** | Monitor `telemetry.ingest` for pump OFF events and periodic 8-hour triggers → call Stream Service to capture snapshot. |
| **ML feedback loop** | Send captured snapshots to ML Service for analysis, then use results to update Control Service schedules. |
| **State caching** | Use Redis DB4 to track recent analyses, cooldown timers, and snapshot states (no persistent DB). |
| **Audit trail** | Log all schedule changes, snapshot triggers, and ML analysis results via `audit.log` NATS subject. |

### Architecture Diagram

```
ML Service ──NATS──▶ Spray Automation Service
                              │
                              ├──▶ Control Service (direct schedule write/overwrite)
                              │         │
                              │         ▼
                              │     MariaDB control_db (single source of truth)
                              │
                              ├──▶ Stream Service (trigger snapshot)
                              │         │
                              │         ▼
                              │     MinIO stream bucket
                              │         │
                              │         ▼
                              │     ML Service (analyze)
                              │         │
                              │         ▼
                              │     NATS detection.result
                              │         │
                              └──────────▶ Spray Automation Service (update Control Service)
                              │
Module Service ──NATS──▶ Spray Automation Service (telemetry.ingest)
                              │
                              └──▶ Redis DB4 (state cache: cooldown, last analysis)
```

---

## 2. Data Flow

### 2.1 AI Detection → Control Service Schedule Update

```
1. ML Service publishes detection.result (root_length, potato_condition)
2. Spray Service receives event via NATS
3. Spray Service analyzes:
   - Short root + poor condition → increase misting (longer duration, shorter interval)
   - Long root + good condition → decrease misting (shorter duration, longer interval)
4. Spray Service calls Control Service REST API:
   PUT /control/schedules/{schedule_id}
   { "params": { "on_sec": 15, "off_sec": 250, "value_on": 1, "value_off": 0 } }
5. Control Service updates schedule in MariaDB control_db
6. Spray Service publishes spray.schedule.updated + audit.log
```

### 2.2 Telemetry OFF → Snapshot → AI Analysis → Control Service Update

```
1. Module Service publishes telemetry.ingest (pump value = 0)
2. Spray Service detects pump OFF event
3. Spray Service calls Stream Service POST /streams/{id}/snapshot
4. Stream Service captures frame → MinIO stream bucket
5. Spray Service calls ML Service POST /ml/detect/from-stream
6. ML Service returns detection results
7. Spray Service analyzes results
8. Spray Service calls Control Service REST API to update schedule
9. Spray Service publishes spray.analysis.completed + audit.log
```

### 2.3 Periodic Snapshot (Every 8 Hours)

```
1. Spray Service internal cron triggers every 8 hours
2. Spray Service calls Stream Service POST /streams/{id}/snapshot
3. Same flow as 2.2 from step 4 onwards
```

---

## 3. Database Schema

### No New Database

This service does **not** create a new MariaDB database. It uses:

| Storage | Purpose |
|---|---|
| `redis-shared` DB4 | State cache: last analysis timestamp, cooldown timers, snapshot trigger dedup |
| `control_db` (existing) | Schedule source of truth — written via Control Service REST API |

### Redis DB4 Keys

| Key Pattern | Type | TTL | Description |
|---|---|---|---|
| `spray:last_analysis:{node_id}` | string | 24h | Timestamp of last AI analysis |
| `spray:cooldown:{node_id}` | string | 30m | Cooldown timer to prevent rapid schedule changes |
| `spray:snapshot_dedup:{stream_id}:{ts}` | string | 1h | Prevent duplicate snapshot triggers |
| `spray:pump_off:{node_id}` | string | 60s | Debounce pump OFF events |

---

## 4. REST API Endpoints

All endpoints are mounted under `/spray` (Kong strips `/v1`). All responses follow the standard envelope:

```jsonc
// Success (2xx)
{ "success": true, "data": <payload> }

// Error (4xx/5xx)
{ "success": false, "error": { "code": "<ERROR_CODE>", "message": "<english_message>" } }
```

### 4.1 Health

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/health` |
| **Auth** | None |

**Response:**
```json
{ "success": true, "data": { "status": "ok" } }
```

### 4.2 Get Current AI Status

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/spray/status` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:** `node_id`

**Response:**
```json
{
  "success": true,
  "data": {
    "node_id": "node-1",
    "ai_enabled": true,
    "last_analysis_at": "2026-07-21T04:00:00Z",
    "cooldown_until": "2026-07-21T04:30:00Z",
    "current_schedule": {
      "id": "sched-uuid",
      "type": "interval",
      "params": { "on_sec": 10, "off_sec": 300 }
    },
    "last_recommendation": {
      "interval_sec": 300,
      "duration_sec": 15,
      "reason": "root_length_12cm_healthy"
    }
  }
}
```

### 4.3 Toggle AI Control

| | |
|---|---|
| **Method** | `PUT` |
| **Path** | `/spray/ai/{node_id}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Request body:**
```json
{ "enabled": true }
```

**Response:**
```json
{ "success": true, "data": { "node_id": "node-1", "ai_enabled": true } }
```

### 4.4 Manual Analysis Trigger

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/spray/analyze/{node_id}` |
| **Auth** | JWT required + role `admin` or `operator` |

**Response:**
```json
{
  "success": true,
  "data": {
    "analysis_id": "uuid",
    "root_length_cm": 12.5,
    "potato_condition": "healthy",
    "recommended_interval_sec": 300,
    "recommended_duration_sec": 15,
    "schedule_updated": true,
    "new_params": { "on_sec": 15, "off_sec": 250 }
  }
}
```

### 4.5 List Analysis History

| | |
|---|---|
| **Method** | `GET` |
| **Path** | `/spray/analyses` |
| **Auth** | JWT required (any authenticated user) |

**Query parameters:** `node_id`, `limit` (max 500), `offset`

> **Note:** This endpoint returns in-memory cached history (last 1000 entries). For persistent history, consume NATS events.

---

## 5. NATS Subjects

### 5.1 Subscriptions

| Subject | Pattern | Description |
|---|---|---|
| `telemetry.ingest` | Core NATS | Monitor pump status and sensor data from Module Service |
| `detection.result` | Core NATS | Receive AI analysis results from ML Service |

### 5.2 Publications

| Subject | Event | Payload Shape |
|---|---|---|
| `spray.schedule.updated` | Schedule changed by AI | `{"event":"spray.schedule.updated","service":"spray","data":{"node_id":"...","schedule_id":"...","old_params":{...},"new_params":{...},"reason":"root_analysis","msg_id":"..."}}` |
| `spray.snapshot.captured` | Snapshot triggered | `{"event":"spray.snapshot.captured","service":"spray","data":{"trigger_id":"...","node_id":"...","snapshot_id":"...","trigger_type":"pump_off","msg_id":"..."}}` |
| `spray.analysis.completed` | ML analysis done | `{"event":"spray.analysis.completed","service":"spray","data":{"analysis_id":"...","detection_id":"...","root_length_cm":12.5,"potato_condition":"healthy","recommended_interval_sec":300,"recommended_duration_sec":15,"action_taken":"schedule_updated","msg_id":"..."}}` |
| `audit.log` | Various | Standard audit events |

---

## 6. AI Decision Logic

### 6.1 Root Length Analysis

| Root Length (cm) | Condition | Recommended Action |
|---|---|---|
| < 5 | Short / Poor | Increase misting duration by 20%, decrease interval by 20% |
| 5 – 15 | Normal / Healthy | Maintain current schedule |
| > 15 | Long / Over-watered | Decrease misting duration by 20%, increase interval by 20% |

### 6.2 Potato/Tuber Condition Analysis

| Condition | ML Confidence | Recommended Action |
|---|---|---|
| `healthy` | > 0.7 | Maintain current schedule |
| `moderate` | > 0.5 | Increase misting duration by 10% |
| `poor` | > 0.5 | Increase misting duration by 20%, decrease interval by 10% |
| `diseased` | any | Alert operator + increase misting duration by 30% |

### 6.3 Combined Logic

```
score = (root_factor * 0.6) + (condition_factor * 0.4)

where:
- root_factor: 0.0 (short) → 0.5 (normal) → 1.0 (long)
- condition_factor: 0.0 (diseased) → 0.5 (moderate) → 1.0 (healthy)
```

Then:
- `score < 0.4` → aggressive misting (duration +30%, interval -20%)
- `0.4 ≤ score < 0.6` → moderate misting (duration +10%, interval -10%)
- `0.6 ≤ score < 0.8` → maintain current
- `score ≥ 0.8` → reduce misting (duration -10%, interval +10%)

---

## 7. Direct Control Service Integration

### 7.1 Schedule Lookup

Before updating, the Spray Service queries Control Service to find the active schedule for the target output:

```
GET /control/schedules?node_id={node_id}&output_name={output_name}&enabled=true
```

### 7.2 Schedule Update

The Spray Service **directly writes** to Control Service:

```
PUT /control/schedules/{schedule_id}
{
  "params": {
    "on_sec": 15,
    "off_sec": 250,
    "value_on": 1,
    "value_off": 0
  }
}
```

Control Service validates and persists to `control_db` (MariaDB). Spray Service does **not** maintain its own schedule table.

### 7.3 Schedule Creation (if none exists)

If no active schedule exists, Spray Service creates one:

```
POST /control/schedules
{
  "node_id": "node-1",
  "output_name": "mister",
  "type": "interval",
  "params": { "on_sec": 10, "off_sec": 300, "value_on": 1, "value_off": 0 },
  "enabled": true
}
```

---

## 8. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | HTTP listen port |
| `NATS_URL` | `nats://nats:4222` | NATS server URL |
| `JWT_SECRET` | `""` | Shared HMAC secret for JWT validation |
| `CONTROL_URL` | `http://control:8080` | Control Service base URL |
| `MODULE_URL` | `http://module:8080` | Module Service base URL |
| `STREAM_URL` | `http://stream:8080` | Stream Service base URL |
| `ML_URL` | `http://ml:8080` | ML Service base URL |
| `REDIS_ADDR` | `redis-shared:6379` | Redis address |
| `REDIS_PASSWORD` | `""` | Redis password |
| `REDIS_DB` | `4` | Redis logical DB for spray cache |
| `SNAPSHOT_INTERVAL_HOURS` | `8` | Periodic snapshot interval in hours |
| `PUMP_OFF_TELEMETRY_KEY` | `outputs.pump` | Telemetry key to monitor for OFF events |
| `PUMP_OFF_THRESHOLD` | `0` | Value below which pump is considered OFF |
| `TIMEZONE` | `UTC` | IANA timezone for schedule evaluation |
| `SCHEDULE_UPDATE_COOLDOWN_MIN` | `30` | Minimum minutes between AI schedule updates |
| `AUTO_APPLY_SCHEDULE` | `true` | If `true`, AI updates are applied automatically |
| `DEFAULT_OUTPUT_NAME` | `mister` | Default output name for spray schedules |
| `DEFAULT_INTERVAL_SEC` | `300` | Default misting interval (5 minutes) |
| `DEFAULT_DURATION_SEC` | `10` | Default misting duration (10 seconds) |

---

## 9. Resilience & Operational Notes

- **No database dependency:** Service can start without MariaDB — only requires NATS, Redis, and upstream services.
- **NATS unavailability:** Events are lost if NATS is down (no outbox). For production, consider adding a small local outbox or using NATS JetStream.
- **Control Service dependency:** Schedule updates require Control Service. If unavailable, updates are retried with backoff (max 3 attempts).
- **Stream Service dependency:** Snapshot capture requires Stream Service. If unavailable, trigger is queued in Redis DB4.
- **ML Service dependency:** Analysis requires ML Service. If unavailable, snapshot is captured but analysis is deferred.
- **Schedule cooldown:** Prevents rapid schedule oscillation by enforcing a minimum interval between AI updates (`SCHEDULE_UPDATE_COOLDOWN_MIN`).
- **Graceful shutdown:** Drains in-flight requests, cancels the periodic snapshot cron, stops NATS subscriptions, and disconnects cleanly on `SIGINT`/`SIGTERM`.

---

## 10. Implementation Checklist

| Status | Item | Description | Estimasi |
|---|---|---|---|
| `[ ]` | Scaffold Go service | Struktur `internal/` (config, model, service, handler, middleware, nats, cron) — no repository/DB layer | 0.5 hari |
| `[ ]` | NATS subscriptions | Subscribe `telemetry.ingest` (pump monitoring) + `detection.result` (AI results) | 1 hari |
| `[ ]` | Pump OFF detector | Parse telemetry, detect pump OFF, trigger snapshot via Stream Service | 1 hari |
| `[ ]` | Periodic snapshot cron | Every 8 hours, call Stream Service to capture + detect | 0.5 hari |
| `[ ]` | ML analysis integration | Call ML Service `/ml/detect/from-stream`, parse results (root_length, potato_condition) | 1 hari |
| `[ ]` | AI decision engine | Compute recommended interval/duration from ML results | 1 hari |
| `[ ]` | Control Service integration | **Direct REST calls** to Control Service to update/create schedules | 1 hari |
| `[ ]` | Redis cache (DB4) | State cache: cooldown, last analysis, snapshot dedup | 0.5 hari |
| `[ ]` | REST API | GET /spray/status, PUT /spray/ai/{node_id}, POST /spray/analyze/{node_id}, GET /spray/analyses | 1 hari |
| `[ ]` | Prometheus `/metrics` | Instrumentation HTTP + scrape via Prometheus | 0.5 hari |
| `[ ]` | Dockerfile + healthcheck | Multi-stage + `/health` | 0.5 hari |
| `[ ]` | Kong route + RBAC | `/spray` via Kong, role-based access | 0.5 hari |

**Total estimasi: 5-7 hari (lebih cepat karena tidak ada database migration)**

---

## 11. Comparison: Before vs After

| Aspect | Before (Full Service) | After (Simplified) |
|---|---|---|
| Database | `mariadb-spray` (new) | None — uses existing `control_db` via Control Service REST |
| Schedule storage | `spray_schedules` table | `control_schedules` table (Control Service) |
| State tracking | `ai_analyses`, `snapshot_triggers` tables | Redis DB4 (ephemeral cache) |
| Schedule update | Internal logic → Control Service | Direct REST call to Control Service |
| Complexity | High (4 tables, migrations, repository layer) | Low (no DB, just HTTP client) |
| Failure mode | DB down → service degraded | No DB → service runs normally |
| Deployment | New database container | Just new service container |

---

*Dokumen ini berisi arsitektur simplified untuk Spray Automation Service. Untuk kontrak integrasi detail, lihat `docs/integration-guides/spray.md`.*
