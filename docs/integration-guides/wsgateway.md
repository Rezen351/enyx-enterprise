# WS-Gateway Integration Guide

> **Service:** WebSocket NATS-to-Dashboard Bridge  
> **Language:** Go (Chi, Gorilla WebSocket, NATS Go Client)  
> **Status:** Production-Ready

---

## 1. Overview

**WS-Gateway** is a stateless microservice that bridges real-time telemetry and system notifications from the NATS event bus to the Dashboard's WebSocket connections. It eliminates the need for the dashboard to poll REST APIs for live data.

| Aspect | Detail |
|---|---|
| **Purpose** | Subscribe to NATS subjects and forward payloads to authenticated WebSocket clients (the Dashboard). |
| **Port** | `8090` (internal; exposed to Dashboard via Kong route `/ws`) |
| **Dependencies** | NATS (`nats://nats:4222`), Auth Service (shared `JWT_SECRET` for token validation) |
| **Process Model** | Per-connection goroutine pair (`writePump` + `pingPump`) + NATS subscription callbacks. No local state beyond an in-memory latest-payload cache. |
| **Resilience** | NATS auto-reconnect (up to 10 attempts, 3s wait). Graceful WebSocket close on client disconnect. Slow-client frame dropping to prevent back-pressure on NATS. |

---

## 2. WebSocket Protocol

### 2.1 Connection Flow

```
Dashboard (React) 
    → Kong (route /ws/*) 
    → WS-Gateway (:8090) 
    → Upgrades to WebSocket 
    → Subscribes to NATS subject(s) 
    → Pushes JSON frames to Dashboard
```

Both endpoints require JWT authentication during the HTTP-to-WebSocket upgrade handshake.

### 2.2 Authentication

The Dashboard must supply a valid JWT access token issued by the **Auth Service**. Two transport options are accepted because browsers cannot set custom headers on WebSocket upgrade requests:

| Transport | Example |
|---|---|
| **Authorization Header** | `Authorization: Bearer <token>` |
| **Query Parameter** | `?token=<token>` |

**Token Claims expected by WS-Gateway:**

```json
{
  "uid": "user-uuid",
  "username": "admin",
  "roles": ["admin"],
  "exp": 1750000000,
  "iat": 1749996400,
  "iss": "auth-service"
}
```

The signing algorithm must be **HS256** and the secret must match `JWT_SECRET` in the Auth Service.

### 2.3 Endpoints

| Endpoint | Description |
|---|---|
| `GET /ws/nodes/{node_id}/live` | Streams live MQTT telemetry for a specific node. |
| `GET /ws/system-status` | Streams system-level notifications (alerts, status changes). |

Both endpoints return `HTTP 401` if the token is missing or invalid, and `HTTP 400` if the `node_id` path parameter is missing or contains invalid characters. All HTTP error responses use the standard platform envelope:

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "missing or invalid Authorization header"
  }
}
```

| Status | Code | Message |
|--------|------|---------|
| `401` | `UNAUTHORIZED` | Missing token, or token is invalid/expired |
| `400` | `BAD_REQUEST` | `node_id` is required or contains invalid characters |

### 2.4 Message Framing

All messages are sent as **WebSocket TextMessage** containing raw JSON bytes. WS-Gateway does **not** wrap messages in an additional envelope — it forwards the exact payload published to NATS.

### 2.5 Keep-Alive & Connection Lifecycle

| Feature | Behavior |
|---|---|
| **Ping interval** | `25s` (sends `PingMessage`; client should respond with `PongMessage`) |
| **Pong handler** | No-op (connection is kept alive) |
| **Replay on connect** | For `/ws/nodes/{node_id}/live`, the most recent cached payload for that node is sent immediately upon upgrade, before live frames begin. |
| **Slow client handling** | If the client's send buffer (128 messages) is full, the incoming NATS frame is dropped and a warning is logged. |

---

## 3. Input Contracts (NATS Subscriptions)

WS-Gateway subscribes to the following NATS subjects to receive data that it forwards to Dashboard clients.

### 3.1 Node Live Telemetry

| Property | Value |
|---|---|
| **Subscription Pattern** | `mqtt.>` (wildcard cache) and `mqtt.{node_id}` (per-client) |
| **Publisher** | Module Service (after receiving MQTT payload from Mosquitto) |
| **Payload** | Raw sensor/actuator JSON published by the device. Typical shape: |

```json
{
  "node_id": "node-001",
  "temperature": 26.5,
  "humidity": 68.2,
  "light": 420,
  "timestamp": "2026-07-21T04:30:00Z"
}
```

- The **cache** subscription (`mqtt.>`) stores the latest payload per node in memory so that newly connected dashboard clients receive an immediate frame instead of waiting for the next telemetry tick.
- The **per-client** subscription (`mqtt.{node_id}`) streams only messages for the requested node.

### 3.2 System Status Notifications

| Property | Value |
|---|---|
| **Subscription Pattern** | `system.status`, `alert.triggered`, `alert.resolved` |
| **Publisher** | Alert Service, Monitor Service, or any internal service that emits system events |
| **Payload** | Service-defined JSON. Typical shapes: |

**`alert.triggered`:**
```json
{
  "alert_id": "alt-123",
  "node_id": "node-001",
  "type": "temperature_high",
  "message": "Temperature exceeds 30C threshold",
  "severity": "critical",
  "timestamp": "2026-07-21T04:30:00Z"
}
```

**`alert.resolved`:**
```json
{
  "alert_id": "alt-123",
  "node_id": "node-001",
  "resolved_at": "2026-07-21T04:35:00Z"
}
```

**`system.status`:**
```json
{
  "service": "module",
  "status": "degraded",
  "message": "High NATS publish latency detected",
  "timestamp": "2026-07-21T04:30:00Z"
}
```

---

## 4. Output Contracts (WebSocket to Dashboard)

WS-Gateway forwards the exact payload bytes received from NATS to the connected WebSocket client. There is no envelope wrapping or field transformation.

| Endpoint | Output Trigger | Output Format |
|---|---|---|
| `/ws/nodes/{node_id}/live` | Any message on `mqtt.{node_id}` | Raw telemetry JSON (see Section 3.1) |
| `/ws/nodes/{node_id}/live` | Client connect (replay) | Last cached payload for `{node_id}` (if any) |
| `/ws/system-status` | Any message on `system.status`, `alert.triggered`, or `alert.resolved` | Raw notification JSON (see Section 3.2) |

---

## 5. Integration Steps for New Services

If you are developing a new service that needs to push real-time data to the Dashboard through WS-Gateway, follow these steps:

### Step 1: Publish to a known NATS subject

Ensure your service has a NATS connection and publishes to one of the subjects that WS-Gateway already subscribes to, or to a new subject that the Dashboard is configured to consume.

```go
// Example: Publishing a telemetry event to WS-Gateway's live stream
nc.Publish("mqtt."+nodeID, jsonPayload)
```

```python
# Example (Python service, e.g. ML Vision or Alert)
nats_client.publish("alert.triggered", json.dumps(payload).encode())
```

### Step 2: Match the payload schema

- The payload must be valid JSON.
- Do **not** add a wrapper envelope; WS-Gateway forwards bytes as-is.
- For telemetry, match the schema expected by the Dashboard's Live MQTT Monitor (typically includes `node_id`, sensor readings, and `timestamp`).
- For alerts, include `alert_id`, `node_id`, `type`, `message`, `severity`, and `timestamp`.

### Step 3: Dashboard consumption

The Dashboard (React) opens a WebSocket connection via Kong:

```
ws://<kong-host>/v1/ws/nodes/<node_id>/live?token=<jwt>
ws://<kong-host>/v1/ws/system-status?token=<jwt>
```

No changes to WS-Gateway are required if you reuse existing subjects. If you introduce new subjects, you must add a new handler or extend an existing subscription list in `internal/handler/handler.go`.

### Step 4: (Optional) Extend WS-Gateway

If new subjects are needed, add them to the `SystemStatus` handler's subject slice, or create a new handler in `main.go` following the existing `NodeLive` / `SystemStatus` pattern:

```go
r.Get("/ws/<new-path>", h.NewHandler)
```

---

## 6. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8090` | HTTP listen port for WS-Gateway. |
| `NATS_URL` | `nats://nats:4222` | NATS server URL. Use `nats://nats:4222` inside Docker Compose. |
| `JWT_SECRET` | _(empty)_ | HMAC secret used to validate dashboard JWTs. **Must match** the `JWT_SECRET` used by the Auth Service. |

### Docker Compose snippet

```yaml
services:
  wsgateway:
    build: ./services/wsgateway
    ports:
      - "8090:8090"
    environment:
      - PORT=8090
      - NATS_URL=nats://nats:4222
      - JWT_SECRET=${JWT_SECRET}
    depends_on:
      nats:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8090/health"]
      interval: 15s
      timeout: 5s
      retries: 3
```

---

## 7. Example WebSocket Connection and Message Format

### 7.1 Connecting with JavaScript (Browser)

```javascript
const token = "<jwt_access_token>";
const nodeID = "node-001";

// Live telemetry stream
const ws = new WebSocket(
  `ws://${window.location.host}/ws/nodes/${nodeID}/live?token=${token}`
);

ws.onopen = () => {
  console.log("WebSocket connected");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Live telemetry:", data);
  // Example output:
  // { node_id: "node-001", temperature: 26.5, humidity: 68.2, light: 420, timestamp: "2026-07-21T04:30:00Z" }
};

ws.onerror = (err) => console.error("WebSocket error:", err);
ws.onclose = () => console.log("WebSocket closed");
```

### 7.2 Connecting with Python (Testing)

```python
import asyncio
import json
import nats
import websockets

NATS_SERVER = "nats://localhost:4222"
NODE_ID = "node-001"

async def publish_test_telemetry():
    nc = await nats.connect(NATS_SERVER)
    payload = json.dumps({
        "node_id": NODE_ID,
        "temperature": 26.5,
        "humidity": 68.2,
        "light": 420,
        "timestamp": "2026-07-21T04:30:00Z"
    }).encode()
    await nc.publish(f"mqtt.{NODE_ID}", payload)
    await nc.flush()
    await nc.close()
    print(f"Published telemetry to mqtt.{NODE_ID}")

async def listen_ws(token):
    uri = f"ws://localhost:8000/ws/nodes/{NODE_ID}/live?token={token}"
    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        print("Received:", json.loads(msg))

async def main():
    await publish_test_telemetry()
    # Then connect WS with valid token from Auth Service

asyncio.run(main())
```

### 7.3 System Status Example

```javascript
const token = "<jwt_access_token>";
const ws = new WebSocket(
  `ws://${window.location.host}/ws/system-status?token=${token}`
);

ws.onmessage = (event) => {
  const notification = JSON.parse(event.data);
  console.log("Notification:", notification);
  // Example alert.triggered:
  // { alert_id: "alt-123", node_id: "node-001", type: "temperature_high", severity: "critical", timestamp: "..." }
};
```

### 7.4 Health Check

```bash
curl http://localhost:8090/health
# Response: {"status":"ok"}
```

---

## 8. NATS Subject Reference

| Subject | Direction | WS-Gateway Role | Typical Publisher |
|---|---|---|---|
| `mqtt.>` | Inbound | Subscribes (cache) | Module Service |
| `mqtt.{node_id}` | Inbound | Subscribes (per-client stream) | Module Service |
| `system.status` | Inbound | Subscribes | Alert Service / Monitor Service |
| `alert.triggered` | Inbound | Subscribes | Alert Service |
| `alert.resolved` | Inbound | Subscribes | Alert Service |

> **Note:** WS-Gateway currently supports **inbound** only (NATS → WebSocket). The outbound path (WebSocket → NATS) is not yet implemented; messages received from clients are discarded.

---

## 9. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `401 Unauthorized` on WS upgrade | Missing or expired JWT; `JWT_SECRET` mismatch | Verify token is valid and `JWT_SECRET` in WS-Gateway matches Auth Service. Pass token via `?token=` query param. |
| `400 Bad Request: node_id contains invalid characters` | `node_id` contains characters outside `[A-Za-z0-9_.:*-]` or is longer than 64 chars | Sanitize `node_id` before constructing the WS URL. |
| No frames received | NATS connection down; Module Service not publishing; wrong `node_id` | Check NATS connectivity (`docker compose logs wsgateway`), verify Module Service is publishing to `mqtt.<node_id>`, confirm exact `node_id`. |
| Frames arrive intermittently | Device reports infrequently; cache is working but cache miss | The cached replay should prevent "Loading" stalls. If still stalling, verify `StartLatestCache()` initialized without error. |
| `dropping frame (slow client)` | Dashboard client is too slow to read WebSocket messages | Increase client read buffer or reduce publish frequency. WS-Gateway drops frames to avoid blocking NATS readers. |
