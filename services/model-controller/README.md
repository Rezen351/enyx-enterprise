# PPO Controller Service

Lightweight inference service that wraps the trained PPO aeroponic model and exposes it over HTTP/NATS.

## Endpoints

- `GET /health` — health check including model load state
- `POST /predict` — run inference for one observation

### Request

```json
{
  "state": [8.0, 0.95, 27.0, 82.0, 26.0, 70.0, 1.7, 5.9, 27.0, 1.0]
}
```

`state` is the 10D observation vector in the same order used during training:
`[L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]`

### Response

```json
{
  "success": true,
  "data": {
    "D_mist": 180.0,
    "interval_sec": 600.0,
    "A_valve": 1.0
  }
}
```

## Usage

```bash
docker compose up -d ppo-controller
```

## Integration

Call `POST http://ppo-controller:8080/predict` from Spray Automation Service or ML Service, then map `D_mist` → `on_sec`, `interval_sec` → `off_sec`, and `A_valve` → actuator value.
