# Model Control & Model Controller — Integration Guide

> **Services:** `model-controller` (inference) · `model-control` (scheduler)  
> **Version:** 1.0.0  
> **Ports:** `model-controller:8080` · `model-control:8081`  
> **Language / Framework:** Python 3.11 · FastAPI · Stable-Baselines3 (TD3) + PyTorch  
> **Object Storage:** MinIO shared instance (bucket `mlbucket`)  
> **Messaging:** NATS (subjects `telemetry.ingest` + `telemetry.batch`)  
> **Status:** Production-ready

---

## 1. Overview

The Aeroponic Model Control Subsystem consists of two FastAPI microservices that together replace static misting schedules with adaptive RL policy execution:

- **model-controller** — pure stateless inference service. Loads TD3 model binary (`aeroponic_td3.zip`) + `VecNormalize` parameters (`vec_normalize_td3.pkl`) from `/app/models` on startup. Exposes `POST /predict` which maps a 10D state vector to a 3D action vector (`D_mist`, `interval_sec`, `A_valve`).
- **model-control** — scheduler loop and telemetry consumer. Subscribes to NATS `telemetry.ingest` + `telemetry.batch`, assembles the 10D state vector from telemetry cache + MinIO metadata, queries `model-controller` for inference, and applies actuation parameters to the Control Service **at cycle boundaries**.

### 1.1 Key Responsibilities

| Responsibility | Service | Description |
|---|---|---|
| Policy inference | model-controller | Load SB3 TD3 model, normalize observations via `VecNormalize`, return action vector. |
| Telemetry aggregation | model-control | Subscribe to NATS ingest and batch subjects; maintain in-memory `TelemetryCache`. |
| State assembly | model-control | Retrieve MinIO vision metadata (`root_length_cm`, `condition`) + cached metrics (`T_in`, `H_in`, `T_out`, `H_out`, `EC`, `pH`, `T_nut`) + diurnal solar index. |
| Cycle-boundary actuation | model-control | Periodically execute tick, but apply schedule updates to Control Service only when the current ON+OFF cycle completes. |
| Schedule management | model-control | Issue `PUT /control/schedules/{id}` and valve direct commands to update pump interval and valve state. |

---

## 2. State Space (10D)

Assembled in `services/model-control/app/ppo_loop.py:assemble_state()`:

| Index | Field | Source | Default | Range / Clamp |
|---|---|---|---|---|
| 0 | `L_root` | MinIO metadata `root_length_cm` | 10.0 | [0, 300] |
| 1 | `U_status` | MinIO metadata `condition` → mapped | 0.5 | [0, 1] |
| 2 | `T_in` | NATS `telemetry.modbus.cwt2.temp` | 25.0 | [15, 30] |
| 3 | `H_in` | NATS `telemetry.modbus.cwt2.hum` | 70.0 | [20, 100] |
| 4 | `T_out` | NATS `telemetry.modbus.cwt1.temp` | 28.0 | [15, 30] |
| 5 | `H_out` | NATS `telemetry.modbus.cwt1.hum` | 65.0 | [20, 100] |
| 6 | `EC` | NATS `telemetry.modbus.npk.ec_nutrisi` | 1.5 | [0.5, 3.5] |
| 7 | `pH` | NATS `telemetry.modbus.npk.ph_nutrisi` | 6.5 | [4, 9] |
| 8 | `T_nut` | NATS `telemetry.modbus.npk.temp_nutrisi` | 25.0 | [18, 25] |
| 9 | `I_day` | Computed diurnal sunlight index | time-based | [0, 1] |

---

## 3. Action Space (3D)

Returned by `model-controller` as JSON:

| Field | Type | Physical Range | SB3 Action Mapping |
|---|---|---|---|
| `D_mist` | int | [10, 240] seconds | `_clamp(round(action[0]), 10, 240)` |
| `interval_sec` | int | [60, 540] seconds | `_clamp(round(action[1]), 60, 540)` |
| `A_valve` | int | 0 or 1 | `1 if action[2] >= 0 else 0` |

---

## 4. REST API Endpoints

### 4.1 model-controller Endpoints

| Method | Path (via Gateway) | Auth | Description |
|--------|---------------------|------|-------------|
| `GET` | `/v1/model_controller/health` | None | Service health + model load status |
| `POST` | `/v1/model_controller/predict` | None | Direct inference endpoint |
| `GET` | `/metrics` | None | Prometheus metrics |

#### `POST /v1/model_controller/predict`

**Request:**
```json
{
  "state": [10.0, 0.5, 25.0, 70.0, 28.0, 65.0, 1.5, 6.5, 25.0, 0.9]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "D_mist": 120,
    "interval_sec": 360,
    "A_valve": 1
  }
}
```

### 4.2 model-control Endpoints

| Method | Path (via Gateway) | Auth | Description |
|--------|---------------------|------|-------------|
| `GET` | `/v1/model_control/health` | None | Scheduler service health + config |
| `POST` | `/v1/model_control/trigger-predict` | None | Trigger immediate loop tick |
| `GET` | `/metrics` | None | Prometheus metrics |

#### Error Response Envelope

All non-2xx responses from `model-control` use the standard platform envelope:

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "prediction loop is not running; please wait for initialization or restart the service"
  }
}
```

| Status | Code | Message |
|--------|------|---------|
| `503` | `SERVICE_UNAVAILABLE` | Loop not started or initialization incomplete |
| `500` | `INTERNAL_ERROR` | Prediction tick failed (generic; internal details are logged only) |

---

## 5. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MODEL_CONTROLLER_URL` | `http://model-controller:8080` | URL of the model-controller inference service |
| `PPO_CONTROLLER_URL` | `http://model-controller:8080` | Backwards-compatible URL alias |
| `NODE_ID` | `node-00` | Target node ID for telemetry lookup |
| `MODULE_ID` | `ee8831ff-c2dd-45c9-abb6-fb3def8fd513` | Module ID for MinIO vision metadata lookup |
| `PUMP_SCHEDULE_ID` | `35461f5f-d6ef-4c30-abfc-9eb680b5dfe7` | Control schedule UUID to update |
| `VALVE_OUTPUT_NAME` | `load2` | Actuator output tag for valve |
| `PREDICTION_INTERVAL_SEC` | `5` | Loop prediction evaluation tick interval |
