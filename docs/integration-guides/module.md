# Module Service — Integration Guide

> **Version:** 1.0.0  
> **Date:** 2026-07-21  
> **Service:** `module-svc`  
> **Module:** `github.com/almuzky/iot/services/module`

---

## 1. Overview

The **Module Service** is the IoT device management and telemetry ingestion layer of the aeroponic monitoring system. It owns:

- **Device onboarding** — ESP32 discovery via MQTT, pairing nodes to modules.
- **Telemetry ingest** — Reading MQTT telemetry payloads, resolving them through tag mappings, persisting to TimescaleDB, and publishing to NATS.
- **Sensor / actuator tag mapping** — Declarative configuration that maps MQTT telemetry keys to database metrics, and firmware output names to controllable actuator tags.
- **Live streaming bridge** — Forwarding every MQTT payload to NATS so the WS-Gateway can push it to the Dashboard in real time.

### 1.1 Port

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | HTTP listen port. Exposed by Dockerfile. |

### 1.2 Dependencies

| Dependency | Purpose | Failure Mode |
|------------|---------|--------------|
| **MariaDB** (`mariadb-module`, DB `module_db`) | Source of truth for modules, nodes, tag mappings, outbox | Telemetry ingest degraded; CRUD endpoints fail |
| **TimescaleDB** (`timescaledb-module`, DB `module_ts`) | Time-series telemetry storage (hypertable `telemetry`) | Telemetry not persisted; NATS events still published (best-effort) |
| **Redis** (`redis-shared`, DB0) | Realtime node status cache (`node:status:{node_id}`, `node:latest:{node_id}`) | Status cache unavailable; service continues with stale reads |
| **NATS** (`nats:4222`) | Event bus for telemetry, audit, and live streaming; JetStream for `telemetry.batch` | No live telemetry, no audit logs, no batch telemetry — but REST API still works |
| **Mosquitto MQTT** (`mosquitto:1883`) | Device onboarding signals (discovery, status, telemetry) | No device discovery or telemetry ingest; REST CRUD still works |

### 1.3 Architecture Role

```
ESP32 → MQTT → Module Service → MariaDB (metadata)
                                    → TimescaleDB (time-series)
                                    → Redis (realtime cache)
                                     → NATS (telemetry.ingest + telemetry.batch + mqtt.{node_id} + audit.log)
                                          → Analytics Service
                                          → WS-Gateway → Dashboard
```

The Module Service is the **ingress boundary** for all device data. No other service reads from MQTT directly.

---

## 2. REST API Endpoints

All routes are mounted under `/v1` (the prefix is stripped by Kong before reaching the service). Responses follow the standard wrapper:

- **Success (2xx):** `{ "success": true, "data": <payload> }`
- **Error (4xx/5xx):** `{ "success": false, "error": { "code": "<CODE>", "message": "<english_message>" } }`

### 2.1 Health

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/health` | Public |

**Response:**

```json
{ "success": true, "data": { "status": "ok" } }
```

### 2.2 Modules

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/modules` | admin / operator | Create a new module |
| `GET` | `/modules` | any authenticated user | List all modules |
| `GET` | `/modules/{id}` | any authenticated user | Get module detail with nested nodes |
| `PUT` | `/modules/{id}` | admin / operator | Update module fields |
| `DELETE` | `/modules/{id}` | admin / operator | Delete module; nodes are unpaired but not deleted |

#### POST /modules

**Request Body:**

```json
{
  "name": "Greenhouse A",
  "description": "Main aeroponic greenhouse"
}
```

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Greenhouse A",
    "description": "Main aeroponic greenhouse",
    "created_at": "2026-07-21T12:00:00Z",
    "updated_at": "2026-07-21T12:00:00Z",
    "nodes": []
  }
}
```

#### GET /modules

**Response:**

```json
{
  "success": true,
  "data": {
    "modules": [ { /* module objects */ } ],
    "count": 2
  }
}
```

#### GET /modules/{id}

**Response:** Module object with `nodes` array populated.

#### PUT /modules/{id}

**Request Body (all fields optional):**

```json
{
  "name": "Updated Name",
  "description": "Updated description"
}
```

#### DELETE /modules/{id}

**Response:**

```json
{ "success": true, "data": { "message": "module deleted; its nodes were unpaired" } }
```

### 2.3 Nodes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/nodes` | any authenticated user | List nodes (filterable) |
| `GET` | `/nodes/discovered` | any authenticated user | List unpaired nodes (onboarding candidates) |
| `GET` | `/nodes/{node_id}` | any authenticated user | Get node detail |
| `POST` | `/nodes/{node_id}/pair` | admin / operator | Pair a discovered node to a module |
| `POST` | `/nodes/{node_id}/unpair` | admin / operator | Unpair a node |
| `DELETE` | `/nodes/{node_id}` | admin / operator | Delete node permanently |

#### GET /nodes (query parameters)

| Parameter | Type | Description |
|-----------|------|-------------|
| `paired` | boolean | Filter by paired state (`true`/`false`) |
| `module_id` | string | Filter by module UUID |
| `status` | string | Filter by status (`online`/`offline`/`unknown`) |

**Response:**

```json
{
  "success": true,
  "data": {
    "nodes": [ { /* node objects */ } ],
    "count": 5
  }
}
```

#### GET /nodes/discovered

Returns only unpaired nodes (where `paired = 0`). Used by the Dashboard to show onboarding candidates.

#### POST /nodes/{node_id}/pair

**Request Body:**

```json
{
  "module_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "East Bed Sensor"
}
```

`module_id` must reference an existing module. `name` is optional (defaults to existing node name).

**Response (200 OK):** Updated node object with `paired: true` and `module_id` set.

#### POST /nodes/{node_id}/unpair

**Response:** Node object with `paired: false` and `module_id: null`.

#### DELETE /nodes/{node_id}

**Response:**

```json
{ "success": true, "data": { "message": "node deleted" } }
```

### 2.4 Node Tags (Sensor / Telemetry Mapping)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/nodes/{node_id}/tags` | any authenticated user | List sensor tag mappings for a node |
| `PUT` | `/nodes/{node_id}/tags` | admin / operator | Replace all sensor tag mappings (idempotent) |

#### GET /nodes/{node_id}/tags

**Response:**

```json
{
  "success": true,
  "data": {
    "node_id": "node-001",
    "tags": [
       {
         "id": "tag-001",
         "node_id": "node-001",
         "kind": "sensor",
         "source_key": "telemetry.temp",
         "tag_name": "temperature",
         "display_name": "Air Temperature",
         "unit": "°C",
         "data_type": "float",
         "enabled": true,
         "created_at": "2026-07-21T12:00:00Z",
         "updated_at": "2026-07-21T12:00:00Z"
       }
    ]
  }
}
```

#### PUT /nodes/{node_id}/tags

Replaces the complete set of sensor-kind tag mappings. Actuator tags are **not** affected.

**Request Body (array):**

```json
[
  {
    "id": "tag-001",
    "kind": "sensor",
    "source_key": "telemetry.temp",
    "tag_name": "temperature",
    "display_name": "Air Temperature",
    "unit": "°C",
    "data_type": "float",
    "enabled": true
  },
  {
    "source_key": "telemetry.humidity",
    "tag_name": "humidity",
    "display_name": "Humidity",
    "unit": "%",
    "data_type": "float",
    "enabled": true
  }
]
```

- If `tag_name` is omitted, it defaults to `source_key`.
- `id` is optional on create (UUID generated server-side). Existing IDs are matched for update.
- Rows omitted from the array are **deleted** (true replace semantics).

**Response:**

```json
{
  "success": true,
  "data": {
    "node_id": "node-001",
    "tags": [ /* saved tags */ ]
  }
}
```

#### Telemetry Mapping UI Workflow (MQTT Key)

The Dashboard exposes telemetry mapping in **Node Configuration** (`NodeConfigPage`). This section maps raw MQTT telemetry keys to database metrics.

**MQTT Key Format:**

- Use the full dot-path as it appears in the MQTT payload.
- Examples: `telemetry.temp`, `telemetry.humidity`, `telemetry.modbus.cwt1.temp`.
- The key must match the exact JSON field path in the incoming telemetry message.

**Fields:**

| Field | Description |
|-------|-------------|
| `source_key` | MQTT key path (e.g., `telemetry.temp`) |
| `tag_name` | Database metric name (defaults to `source_key` if empty) |
| `display_name` | Dashboard display name |
| `unit` | Unit string (e.g., `°C`, `%`, `m/s`) |
| `data_type` | One of: `float`, `int`, `bool` |
| `enabled` | Toggle to enable/disable ingestion |

**Detect Keys:**

- Click **Detect keys** to open a 5-second WebSocket live stream (`/ws/nodes/{nodeId}/live`).
- The UI walks every leaf value in the received JSON and extracts unique key paths.
- Auto-detected keys are added as draft rows ready for review and save.

**Key difference from Actuator Mapping:**

- Telemetry `source_key` uses **full MQTT paths** (`telemetry.temp`).
- Actuator `source_key` uses the **bare firmware output name** (`load1`, `pump`).
- Actuator keys are normalized automatically and stored without the `outputs.` prefix.

### 2.5 Actuator Tags (Control Output Mapping)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/nodes/{node_id}/actuators` | any authenticated user | List actuator tags |
| `POST` | `/nodes/{node_id}/actuators` | admin / operator | Create actuator tag |
| `DELETE` | `/nodes/{node_id}/actuators/{id}` | admin / operator | Delete actuator tag |

#### GET /nodes/{node_id}/actuators

Returns only tags where `kind = 'actuator'`.

#### POST /nodes/{node_id}/actuators

**Request Body:**

```json
{
  "source_key": "pump",
  "tag_name": "water_pump",
  "display_name": "Water Pump",
  "unit": "",
  "data_type": "bool",
  "enabled": true
}
```

`source_key` is the firmware output name (required). `data_type` defaults to `"int"` if omitted.

**Response (201 Created):** Created `NodeTag` object.

#### DELETE /nodes/{node_id}/actuators/{id}

**Response:**

```json
{ "success": true, "data": { "message": "actuator tag deleted" } }
```

### 2.6 Metrics

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/metrics` | Public (Prometheus scrape) |

Exposes `module_http_requests_total`, `module_http_request_duration_seconds`, and `module_http_requests_in_flight`.

---

## 3. Input Contracts

### 3.1 MQTT Topics (from Mosquitto)

The Module Service subscribes to `{prefix}/#` (default prefix: `smartfarm`). This is a wildcard subscription covering all device topics.

| Topic Pattern | Direction | Payload | Handler |
|--------------|-----------|---------|---------|
| `{prefix}/discovery` | Inbound | `DiscoveryMessage` (see §3.1.1) | `HandleDiscovery` → upsert node |
| `{prefix}/status/{node_id}` | Inbound | `StatusMessage` (see §3.1.2) | `HandleStatus` → update status + cache; also marks node alive via `TouchNode` |
| `{prefix}/{node_id}/telemetry` | Inbound | Raw JSON telemetry (arbitrary structure) | `IngestTelemetry` → tag-resolve → TimescaleDB + NATS; also marks node alive via `TouchNode` and forwards to live monitor via `PublishLive` |
| `{prefix}/{node_id}/alert` | Inbound | Raw JSON | No active handler |
| `{prefix}/{node_id}/confirm` | Inbound | Raw JSON | No active handler |
| `{prefix}/actuator/{node_id}` | Inbound | Raw JSON | No active handler |

For all topics except `discovery` and `status/{node_id}`, the service:
1. Extracts `node_id` from the topic path.
2. For `telemetry` only: calls `TouchNode(node_id)` (batched `last_seen_at` update) and `PublishLive` to NATS for Dashboard live streaming.
3. For `alert`, `confirm`, and `actuator`: no handler is currently registered; these topics are subscribed via wildcard but ignored by the service layer.

#### 3.1.1 DiscoveryMessage

```json
{
  "node_id": "esp32-001",
  "mac": "AA:BB:CC:DD:EE:FF",
  "ip": "192.168.1.100",
  "fw_version": "1.2.3",
  "status": "online"
}
```

- Published by firmware on `{prefix}/discovery` (typically **retained**).
- Triggers `UpsertDiscovered`: inserts a new node if `node_id` is unknown, or refreshes mutable fields (mac, ip, fw_version, status) if the node already exists.
- Publishes `node.discovered` audit event only on first insert.

#### 3.1.2 StatusMessage

```json
{
  "status": "online",
  "mac": "AA:BB:CC:DD:EE:FF",
  "fw": "1.2.3",
  "ip": "192.168.1.100"
}
```

- Published on `{prefix}/status/{node_id}` (typically **retained**, used as LWT).
- If the node is unknown, it is registered from this payload.
- If the node exists, only `status`, `last_seen_at`, and `ip` are updated (ip is only overwritten when non-empty).

### 3.2 REST API (from Dashboard / Kong)

All REST requests arrive via Kong, which strips the `/v1` prefix and forwards to the service on port 8080.

| Source | Protocol | Auth |
|--------|----------|------|
| Dashboard (React) | HTTP → Kong → Module Service | Bearer JWT (`Authorization: Bearer <token>`) |

The service validates JWT locally using the shared secret (`JWT_SECRET`). When the secret is empty (development), validation is skipped.

---

## 4. Output Contracts

All outbound events flow through the **Transactional Outbox** (ADR-007). Events are first written to the `outbox` table in MariaDB within the same transaction as the business write. A relay worker drains unsent rows and publishes them to NATS with a `Nats-Msg-Id` header for consumer-side deduplication.

### 4.1 NATS Subjects Published

| Subject | Trigger | Payload | Consumer(s) |
|---------|---------|---------|-------------|
| `telemetry.ingest` | Every mapped telemetry reading | `{"node_id":"...","metric":"...","value":23.5,"ts":1690000000000,"msg_id":"<uuid>"}` | Analytics Service, Alert Service |
| `telemetry.batch` | Every 1 minute (JetStream durable stream `TELEMETRY_BATCH`) | `{"window":"1m","rows":[...],"row_count":42,"ts":1690000000000}` | Analytics Service |
| `mqtt.{node_id}` | Every MQTT message for a known node (except discovery/status) | `{"topic":"smartfarm/node-001/telemetry","payload":{...},"ts":1690000000000,"msg_id":"<uuid>"}` | WS-Gateway → Dashboard (live stream) |
| `audit.log` | Module/node/tag mutations | `{"event":"module.created","service":"module","data":{"module_id":"...","name":"..."},"msg_id":"<uuid>"}` | Audit Service (future), Notification Service |

### 4.2 Telemetry.ingest Payload

Published per reading (after tag resolution and type coercion):

```json
{
  "node_id": "esp32-001",
  "metric": "temperature",
  "value": 26.5,
  "ts": 1690000000000,
  "msg_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

- `value` is coerced to `float64` according to the tag's `data_type` (float, int, bool).
- Only enabled tags are emitted.
- The full raw payload is always stored in TimescaleDB regardless of mapping.

### 4.3 Telemetry.batch Payload

Published every 1 minute via JetStream (with JetStream fallback to core NATS):

```json
{
  "window": "1m",
  "rows": [
    {
      "node_id": "esp32-001",
      "module_id": "mod-001",
      "metric": "temperature",
      "count": 60,
      "sum": 1590.0,
      "min": 24.5,
      "max": 27.0,
      "avg": 26.5,
      "last": 26.8,
      "first_ts": 1689999000000,
      "last_ts": 1690000000000
    }
  ],
  "row_count": 1,
  "ts": 1690000000000
}
```

### 4.4 MQTT.{node_id} Payload

Raw MQTT message forwarded for Dashboard live view:

```json
{
  "topic": "smartfarm/esp32-001/telemetry",
  "payload": {"temp": 26.5, "humidity": 68.0},
  "ts": 1690000000000,
  "msg_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

### 4.5 Audit.log Payload

Examples of audit events:

- `module.created` — `{ "module_id": "...", "name": "..." }`
- `module.updated` — `{ "module_id": "..." }`
- `module.deleted` — `{ "module_id": "..." }`
- `node.discovered` — `{ "node_id": "...", "mac": "...", "fw_version": "..." }`
- `node.paired` — `{ "node_id": "...", "module_id": "..." }`
- `node.unpaired` — `{ "node_id": "..." }`
- `node.deleted` — `{ "node_id": "..." }`

---

## 5. Integration Steps

### 5.1 Consuming REST API from a New Service

1. **Route through Kong** — All external REST traffic must pass through Kong. Register a new route/service in Kong pointing to `module-svc:8080` (or use the existing upstream).
2. **Obtain JWT** — Call the Auth Service `/v1/auth/login` endpoint to get a Bearer token. Include `Authorization: Bearer <token>` in all requests.
3. **Use `/v1` prefix** — Kong strips the `/v1` prefix before forwarding. Requests to Kong should be `GET /v1/modules`, `POST /v1/nodes/{id}/pair`, etc.
4. **Handle standard response wrapper** — Parse `success` and `data`/`error` fields consistently.

### 5.2 Subscribing to NATS Events

1. **Connect to NATS** — Use `nats://nats:4222` (or the external NATS URL).
2. **Subscribe to `telemetry.ingest`** — For per-reading consumption. Messages arrive with `Nats-Msg-Id` header; deduplicate in Redis/DB using this key (TTL > retry window).
3. **Subscribe to `telemetry.batch`** — For aggregated time-window data. Prefer a JetStream durable consumer on stream `TELEMETRY_BATCH` to survive Analytics restarts.
4. **Subscribe to `mqtt.{node_id}`** — For live raw payload streaming. Use wildcard `mqtt.>` to receive all nodes.
5. **Subscribe to `audit.log`** — For operational audit events.

### 5.3 Publishing Commands to Devices (via MQTT)

The Module Service does **not** publish to MQTT. Commands to devices are sent by the **Control Service** directly to Mosquitto. If a new service needs to command devices, publish to:

- `{prefix}/actuator/{node_id}` — Command payload for a specific node.

### 5.4 Registering Telemetry Tag Mappings

Before telemetry can be persisted, a node must have sensor tags configured:

```http
PUT /v1/nodes/{node_id}/tags
Authorization: Bearer <token>
Content-Type: application/json

[
  {
    "source_key": "telemetry.temp",
    "tag_name": "temperature",
    "unit": "°C",
    "data_type": "float",
    "enabled": true
  }
]
```

- `source_key` supports dot-paths into nested JSON: `"telemetry.modbus.cwt1.temp"`.
- `data_type` must be one of: `float`, `int`, `bool`.
- Actuator tags are managed separately via `/nodes/{node_id}/actuators`.

### 5.5 Reading Realtime Node Status from Redis

Other services may read Redis directly (DB0) for fast status lookups:

- **Key:** `node:status:{node_id}` (hash)
  - Fields: `status`, `last_seen`
- **Key:** `node:latest:{node_id}` (string, TTL 5m)
  - Value: raw JSON telemetry payload

TTL for status is 90 seconds; if the key expires, the node is considered stale.

---

## 6. Environment Variables

All variables are loaded from environment with dev-friendly defaults in [config.go](file:///home/almuzky/TA/Microservices/services/module/internal/config/config.go:38).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8080` | HTTP listen port |
| `DB_DSN` | Yes | `module_user:module_pass@tcp(mariadb-module:3306)/module_db?parseTime=true&charset=utf8mb4` | MariaDB DSN |
| `TIMESCALE_DSN` | Yes | `postgres://module_user:module_pass@timescaledb-module:5432/module_ts?sslmode=disable` | TimescaleDB DSN |
| `REDIS_ADDR` | No | `redis-shared:6379` | Redis address |
| `REDIS_PASSWORD` | No | `""` | Redis password |
| `REDIS_DB` | No | `0` | Redis logical database (0 = module) |
| `NATS_URL` | No | `nats://nats:4222` | NATS server URL |
| `JWT_SECRET` | No | `""` | Shared JWT secret for HS256 validation. Empty = dev mode (no auth) |
| `MQTT_URL` | No | `tcp://mosquitto:1883` | Mosquitto broker URL |
| `MQTT_USER` | No | `""` | MQTT username |
| `MQTT_PASS` | No | `""` | MQTT password |
| `MQTT_CLIENT_ID` | No | `module-svc` | MQTT client ID |
| `MQTT_TOPIC_PREFIX` | No | `smartfarm` | MQTT topic prefix for device topics |

---

## 7. Database Schema

### 7.1 MariaDB (`module_db`)

Schema is managed via GORM AutoMigrate at startup ([migrate.go](file:///home/almuzky/TA/Microservices/services/module/migrate.go:79)).

#### `modules`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `char(36)` | Primary key (UUID) |
| `name` | `varchar(100)` | Unique, not null |
| `description` | `varchar(255)` | — |
| `created_at` | `datetime` | Auto-created |
| `updated_at` | `datetime` | Auto-updated |

#### `nodes`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `char(36)` | Primary key (UUID) |
| `node_id` | `varchar(100)` | Unique, not null (firmware MAC-based ID) |
| `module_id` | `char(36)` | Nullable, indexed (FK to modules.id, not enforced) |
| `name` | `varchar(100)` | Optional friendly name |
| `mac` | `varchar(32)` | MAC address |
| `ip` | `varchar(45)` | IPv4/IPv6 |
| `fw_version` | `varchar(32)` | Firmware version |
| `status` | `varchar(16)` | Not null, default `unknown` (`online`/`offline`/`unknown`) |
| `paired` | `tinyint(1)` | Not null, default 0 |
| `last_seen_at` | `datetime` | Nullable |
| `discovered_at` | `datetime` | Auto-created |
| `created_at` | `datetime` | Auto-created |
| `updated_at` | `datetime` | Auto-updated |

#### `node_tags`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `char(36)` | Primary key (UUID) |
| `node_id` | `varchar(64)` | Not null, indexed |
| `source_key` | `varchar(128)` | Not null, indexed |
| `kind` | `varchar(16)` | Not null, default `sensor` (`sensor`/`actuator`) |
| `tag_name` | `varchar(128)` | Not null |
| `display_name` | `varchar(128)` | Optional |
| `unit` | `varchar(32)` | Optional |
| `data_type` | `varchar(16)` | Default `float` (`float`/`int`/`bool`) |
| `enabled` | `tinyint(1)` | Not null, default 1 |
| `created_at` | `datetime` | Auto-created |
| `updated_at` | `datetime` | Auto-updated |

Unique index: `uq_node_source_kind` on (`node_id`, `source_key`, `kind`).

#### `outbox`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `char(36)` | Primary key (UUID) |
| `msg_id` | `varchar(64)` | Not null, unique (idempotency key, used as `Nats-Msg-Id`) |
| `subject` | `varchar(128)` | Not null, indexed |
| `payload` | `longtext` | Not null |
| `sent` | `tinyint(1)` | Not null, default 0, indexed |
| `created_at` | `datetime` | Auto-created |
| `sent_at` | `datetime` | Nullable |

### 7.2 TimescaleDB (`module_ts`)

#### `telemetry` (hypertable)

| Column | Type | Description |
|--------|------|-------------|
| `time` | `timestamptz` | Hypertable time column |
| `node_id` | `varchar(100)` | Source device |
| `module_id` | `char(36)` | Nullable — FK to module |
| `metric` | `varchar(128)` | Tag name (e.g. `temperature`) |
| `value` | `double precision` | Coerced numeric value |
| `raw` | `jsonb` | Full original payload |

---

## 8. Example curl Commands

> Replace `http://localhost:8080` with your Kong upstream or direct service address. All endpoints except `/health` require `Authorization: Bearer <token>`.

### 8.1 Health Check

```bash
curl -s http://localhost:8080/health
```

### 8.2 Create a Module

```bash
curl -s -X POST http://localhost:8080/v1/modules \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Greenhouse A",
    "description": "Main aeroponic greenhouse"
  }'
```

### 8.3 List Modules

```bash
curl -s http://localhost:8080/v1/modules \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 8.4 Get Module Detail (with nested nodes)

```bash
curl -s http://localhost:8080/v1/modules/MODULE_UUID \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 8.5 List Discovered (Unpaired) Nodes

```bash
curl -s http://localhost:8080/v1/nodes/discovered \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 8.6 Pair a Node to a Module

```bash
curl -s -X POST http://localhost:8080/v1/nodes/esp32-001/pair \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "East Bed Sensor"
  }'
```

### 8.7 Set Sensor Tag Mapping

```bash
curl -s -X PUT http://localhost:8080/v1/nodes/esp32-001/tags \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "source_key": "telemetry.temp",
      "tag_name": "temperature",
      "unit": "°C",
      "data_type": "float",
      "enabled": true
    },
    {
      "source_key": "telemetry.humidity",
      "tag_name": "humidity",
      "unit": "%",
      "data_type": "float",
      "enabled": true
    }
  ]'
```

### 8.8 Add an Actuator Tag

```bash
curl -s -X POST http://localhost:8080/v1/nodes/esp32-001/actuators \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_key": "pump",
    "tag_name": "water_pump",
    "data_type": "bool",
    "enabled": true
  }'
```

### 8.9 List Nodes Filtered by Module and Status

```bash
curl -s "http://localhost:8080/v1/nodes?module_id=550e8400-e29b-41d4-a716-446655440000&paired=true&status=online" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 8.10 Delete a Node

```bash
curl -s -X DELETE http://localhost:8080/v1/nodes/esp32-001 \
  -H "Authorization: Bearer $JWT_TOKEN"
```

---

## 9. Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `BAD_REQUEST` | Invalid request body, missing required field, or validation failure |
| 401 | `UNAUTHORIZED` | Missing, invalid, or expired JWT token |
| 403 | `FORBIDDEN` | Authenticated but insufficient role (needs admin/operator for writes) |
| 404 | `NOT_FOUND` | Module or node does not exist |
| 409 | `CONFLICT` | Name uniqueness violation |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 10. NATS Subscription Reference for Downstream Services

If you are building a new service that consumes Module Service events, subscribe to these subjects:

```text
telemetry.ingest          — per-reading telemetry (fan-out)
telemetry.batch           — 1-minute aggregated windows (JetStream durable)
mqtt.>                    — all live MQTT payloads (wildcard)
audit.log                 — operational audit events
```

For `telemetry.batch`, create a JetStream consumer on stream `TELEMETRY_BATCH`:

```go
js, _ := nc.JetStream()
sub, _ := js.Subscribe("telemetry.batch", "my-consumer", nats.Durable("my-consumer"))
```

This guarantees that batch events survive consumer restarts.

---

## 11. Notes for Implementers

- **JWT is shared** — The `JWT_SECRET` is the same across all services (shared secret pattern per ADR). Do not generate independent secrets.
- **Outbox is the only publish path** — All NATS events go through the outbox table. Do not call `nats.Publish` directly from business code; use `enqueueOutbox` instead.
- **Node status is ephemeral in Redis** — Status entries expire after 90 seconds. Services relying on realtime status should treat a missing Redis key as `offline`/`unknown`.
- **Telemetry ingest is best-effort** — If TimescaleDB or NATS is unavailable, telemetry readings are not persisted but the service does not crash. The outbox relay retries NATS publishes indefinitely.
- **MQTT topics are configurable** — The `MQTT_TOPIC_PREFIX` (default `smartfarm`) allows the same firmware image to work across environments. Always use the prefix when constructing topics.
