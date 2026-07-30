# TD3 Aeroponic Controller — Integration Guide

> **Services:** `model-controller` (inference) · `model-control` (scheduler)  
> **Version:** 1.0.0  
> **Ports:** `model-controller:8080` · `model-control:8081`  
> **Language / Framework:** Python 3.11 · FastAPI · Stable-Baselines3 (TD3) + PyTorch  
> **Object Storage:** MinIO shared instance (bucket `mlbucket`)  
> **Messaging:** NATS (subjects `telemetry.ingest` + `telemetry.batch`)  
> **Status:** Production-ready (Fase 6e/6f)

---

## 1. Overview

The TD3 Aeroponic Controller consists of two FastAPI services that together replace rule-based misting schedules with a learned policy:

- **model-controller** — pure stateless inference. Loads `aeroponic_td3.zip` + `vec_normalize_td3.pkl` on startup. Exposes `POST /predict` which maps a 10D state vector to a 3D action (`D_mist`, `interval_sec`, `A_valve`).
- **model-control** — scheduler and telemetry consumer. Subscribes to NATS `telemetry.ingest` + `telemetry.batch`, assembles the 10D state from cache + MinIO metadata, calls model-controller for prediction, and applies the action to Control Service **only at cycle boundaries**.

### 1.1 Key Responsibilities

| Responsibility | Service | Description |
||---|---|---|
| Policy inference | model-controller | Load SB3 TD3 model, normalize observation via `VecNormalize`, return clipped action. |
| Telemetry aggregation | model-control | Subscribe NATS ingest + batch subjects; maintain in-memory `TelemetryCache` with metric value + timestamp. |
| State assembly | model-control | Read MinIO metadata (`root_length_cm`, `condition`) + cache metrics (`T_in`, `H_in`, `T_out`, `H_out`, `EC`, `pH`, `T_nut`) + sunlight index. |
| Cycle-boundary actuation | model-control | Predict every `PREDICTION_INTERVAL_SEC` (default 5s), but only call Control Service when the current ON+OFF cycle completes. |
| Schedule management | model-control | `PUT /control/schedules/{id}` + `POST /control/command` (bypass=true) to update pump interval and valve state. |

### 1.2 Architecture Diagram

```
Module Service ──NATS──▶ model-control
                             │
                             ├── MinIO (mlbucket) ──▶ L_root, condition
                             │
                             ├── model-controller:8080/predict
                             │
                             └── Control Service ──▶ ESP32
                                     │
                                     └── MQTT smartfarm/actuator/{node_id}
```

---

## 2. State Space (10D)

Assembled in `services/model-control/app/ppo_loop.py:assemble_state()`:

| Index | Field | Source | Default | Clamp |
|---|---|---|---|---|
| 0 | `L_root` | MinIO metadata `root_length_cm` | 10.0 | [0, 300] |
| 1 | `U_status` | MinIO metadata `condition` → mapped to {0.25, 0.5, 0.75, 1.0} | 0.5 | [0, 1] |
| 2 | `T_in` | NATS cache `telemetry.modbus.cwt2.temp` | 25.0 | [15, 30] |
| 3 | `H_in` | NATS cache `telemetry.modbus.cwt2.hum` | 70.0 | [20, 100] |
| 4 | `T_out` | NATS cache `telemetry.modbus.cwt1.temp` | 28.0 | [15, 30] |
| 5 | `H_out` | NATS cache `telemetry.modbus.cwt1.hum` | 65.0 | [20, 100] |
| 6 | `EC` | NATS cache `telemetry.modbus.npk.ec_nutrisi` | 1.5 | [0.5, 3.5] |
| 7 | `pH` | NATS cache `telemetry.modbus.npk.ph_nutrisi` | 6.5 | [4, 9] |
| 8 | `T_nut` | NATS cache `telemetry.modbus.npk.temp_nutrisi` | 25.0 | [18, 25] |
| 9 | `I_day` | Computed sunlight index (06:00–18:00 → 0..1) | time-based | [0, 1] |

`condition` mapping:
- `>= 80` → `1.0` (healthy)
- `>= 60` → `0.75` (moderate)
- `>= 40` → `0.5` (poor)
- `< 40` → `0.25` (critical)

---

## 3. Action Space (3D)

Returned by model-controller as JSON:

| Field | Type | Physical Range | SB3 Mapping |
|---|---|---|---|
| `D_mist` | int | [10, 240] seconds | `_clamp(round(action[0]), 10, 240)` |
| `interval_sec` | int | [60, 540] seconds | `_clamp(round(action[1]), 60, 540)` |
| `A_valve` | int | 0 or 1 | `1 if action[2] >= 0 else 0` |

---

## 4. REST API Endpoints

All responses use the standard envelope:
```json
{ "success": true, "data": ... }
```

### 4.1 model-controller Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Model load status |
| `POST` | `/predict` | None | Inference endpoint |
| `GET` | `/metrics` | None | Prometheus metrics |

#### `POST /predict`

**Request:**
```json
{ "state": [10.0, 0.5, 25.0, 70.0, 28.0, 65.0, 1.5, 6.5, 25.0, 0.9] }
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

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Service health + config |
| `POST` | `/trigger-predict` | None | Force immediate tick |
| `GET` | `/metrics` | None | Prometheus metrics |

#### `GET /health`

```json
{
  "status": "ok",
  "node_id": "node-00",
  "schedule_id": "35461f5f-...",
  "valve_output": "valve",
  "interval_sec": 5
}
```

#### `POST /trigger-predict`

```json
{ "status": "tick executed" }
```

---

## 5. Cycle-Boundary Update Behavior

`model-control` evaluates TD3 every `PREDICTION_INTERVAL_SEC` (compose default: `5` seconds), but only applies actions to Control Service when one full cycle completes:

1. Tick assembles 10D state and calls `model-controller/predict`.
2. Result is stored in `pending_action` (overwrites previous pending).
3. On each tick, check: `elapsed = now - last_schedule_update`.
4. If `elapsed >= current_D_mist + current_interval` → apply `pending_action` to Control Service.
5. After successful apply, reset `last_schedule_update = now` and clear `pending_action`.

This ensures the pump/valve completes its full ON→OFF cycle before the next schedule change. If no cycle has completed, ticks are skipped with debug log:

```
tick skipped cycle_done=False pending=True elapsed=5.4s cycle=120s
```

---

## 6. NATS Contract

| Subject | Direction | Payload Schema | Consumer |
|---|---|---|---|
| `telemetry.ingest` | Module → model-control | `{"node_id":"...","metric":"telemetry.modbus.cwt2.temp","value":25.0,"ts":1690000000000}` | Core NATS fan-out; model-control keeps latest per metric |
| `telemetry.batch` | Module → model-control | `{"rows":[{"node_id":"...","metric":"...","last":25.0,"last_ts":1690000000000,...}], "ts":...}` | JetStream `TELEMETRY_BATCH`; fallback when ingest is missed |

model-control stores both raw ingest values and batch `last` values in the same in-memory cache, preferring the most recent timestamp.

### Cache Debug Logging

Every tick logs cache freshness at DEBUG level:

```json
{
  "T_in": {"value": 25.0, "age_s": 3.4},
  "H_in": {"value": 70.0, "age_s": Infinity},
  "T_out": {"value": 28.0, "age_s": 3.6},
  "H_out": {"value": 65.0, "age_s": 3.8},
  "EC": {"value": 1.5, "age_s": 3.2},
  "pH": {"value": 6.5, "age_s": 2.9},
  "T_nut": {"value": 25.0, "age_s": 3.1}
}
```

`age_s: Infinity` means the metric has never been received from NATS. In production, `H_in` typically comes from `telemetry.modbus.cwt2.hum`; if absent, it falls back to `DEFAULT_H_IN=70.0`.

---

## 7. MinIO Dependency

model-control reads vision/stream metadata from MinIO bucket `mlbucket`:

- **File:** `services/model-control/app/minio_client.py`
- **Bucket:** `mlbucket`
- **Key pattern:** latest metadata for `settings.MODULE_ID` (e.g., `module-00/latest/metadata.json`)
- **Fields used:** `root_length_cm` (float), `condition` (float 0-100)

If MinIO is unreachable or metadata is missing, both `L_root` and `U_status` fall back to hardcoded defaults (`DEFAULT_L_ROOT=10.0`, `DEFAULT_U_STATUS=0.5`).

---

## 8. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NODE_ID` | `node-00` | Node identifier for telemetry cache lookup |
| `MODULE_ID` | `module-00` | Module identifier for MinIO metadata lookup |
| `PUMP_SCHEDULE_ID` | (from compose) | Schedule UUID to update in Control Service |
| `VALVE_OUTPUT_NAME` | `valve` | Actuator tag name for valve command |
| `PREDICTION_INTERVAL_SEC` | `3600` | Tick interval in seconds (compose overrides to `5`) |
| `DEFAULT_*` | various | Fallback values for missing telemetry/metadata |

---

## 9. Monitoring

| Signal | How to Observe |
|---|---|
| Prediction loop health | `docker logs model-control` — look for `TD3 loop started interval=5s` |
| State evolution | `docker logs model-control` — `state=[...]` every tick |
| Cycle-boundary logic | `docker logs model-control` — `schedule update ok=...` (only at cycle end) or `tick skipped cycle_done=False` |
| Inference latency | `curl model-controller:8080/metrics` → `predict_latency_seconds` histogram |
| Prediction throughput | `curl model-controller:8080/metrics` → `predictions_total` counter |
| Cache freshness | `docker logs model-control` (DEBUG level) — `cache metrics: {"T_in": {"value": 25.0, "age_s": 3.4}, ...}` |

---

## 10. Known Limitations

- `H_in` (internal humidity) may be `Infinity` age if the module firmware does not publish `telemetry.modbus.cwt2.hum`. model-control falls back to `DEFAULT_H_IN=70.0`.
- MinIO metadata is only as fresh as the last ML/vision analysis. If Stream/ML stops running, `L_root` and `U_status` become stale.
- model-controller has no fallback if the model file is corrupted; it fails at startup and returns 503 on `/predict`.
