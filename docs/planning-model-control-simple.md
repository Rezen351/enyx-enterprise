# TD3 Control Integration — Simple Custom Implementation Plan

> **Feature:** TD3 Control sebagai dua service terpisah yang reusable:
> - `model-controller` = pure inference service (single responsibility: menerima state 10D → return aksi)
> - `model-control` = scheduler/cron loop yang mengumpulkan telemetry + mengambil metadata MinIO untuk vision data, memanggil `model-controller`, dan memperbarui kontrol akturator (pump + valve)

---

## 1. Tujuan

Membuat kontrol TD3 yang **sederhana khusus untuk deployment ini** tanpa menambahkan mode baru di Control Service atau tabel konfigurasi baru. TD3 Control:
- Mengambil data telemetry dari Module Service
- Mengambil data vision (`root_length`, `condition`) dari metadata MinIO bucket `ml`
- Memanggil `model-controller` untuk mendapatkan aksi
- Langsung memperbarui kontrol akturator di Control Service:
  - **Pump/load1**: update interval schedule (`on_sec`, `off_sec`)
  - **Valve/load2**: kirim direct command `set_state` (ON/OFF) sesuai `A_valve`

**Kontrol Akturator:**
- **Pump/load1** — di-update oleh TD3 via interval schedule (`on_sec`, `off_sec`)
- **Valve/load2** — di-control oleh TD3 via direct command `set_state` (ON/OFF) sesuai `A_valve`, semua event tercatat log dan audit

---

## 2. Arsitektur Dua Service (Single Responsibility)

```
model-control service (cron/scheduler loop)
   │
   ├── Background Loop (setiap N detik)
   │     ├── Ambil telemetry terbaru dari Module Service/cache
   │     ├── Ambil root_length + condition dari metadata MinIO bucket `ml`
   │     ├── Assemble state 10D
   │     ├── Call model-controller /predict
   │     ├── Update jadwal interval PUMP/LOAD1 (on_sec/off_sec)
   │     ├── Kirim direct command VALVE/LOAD2 (set_state ON/OFF)
   │     └── Semua event dicatat log + audit
   │
   └── OUTPUT: Update pump/load1 schedule + valve/load2 direct command


model-controller service (pure inference)
   │
   └── POST /predict
         Input:  state 10D
         Output: D_mist, interval_sec, A_valve
```

**Tidak ada:**
- Perubahan tabel `control_modes`
- Tabel `model_control_config`
- Mode baru di dashboard
- Endpoint baru di Control Service

---

## 3. State Assembly

### 3.1 Telemetry Fields

| State Field | Sumber | Fallback |
|---|---|---|
| `L_root` | MinIO `ml` bucket metadata | `DEFAULT_L_ROOT` |
| `U_status` | MinIO `ml` bucket metadata (`condition` → score) | `DEFAULT_U_STATUS` |
| `T_in` | Module Service telemetry | `DEFAULT_T_IN` |
| `H_in` | Module Service telemetry | `DEFAULT_H_IN` |
| `T_out` | Module Service telemetry | `DEFAULT_T_OUT` |
| `H_out` | Module Service telemetry | `DEFAULT_H_OUT` |
| `EC` | Module Service telemetry | `DEFAULT_EC` |
| `pH` | Module Service telemetry | `DEFAULT_PH` |
| `T_nut` | Module Service telemetry | `DEFAULT_T_NUT` |
| `I_day` | Hitung dari jam lokal | 0.5 |

### 3.2 Metadata Source — MinIO

Semua data `root_length` dan `status umbi` diambil dari **MinIO bucket `ml`**:
- Prefix: `results/{module_id}/detection_*.json`
- Baca `user_metadata.root_length_cm`, `user_metadata.condition`, `user_metadata.confidence`
- Ambil object terbaru berdasarkan `last_modified`
- Fallback ke hardcoded default jika tidak ada metadata

---

## 4. Prediction Loop Flow

```
Background Loop (setiap PREDICTION_INTERVAL_SEC)
   │
   ├── Step 1: Collect state
   │     ├── Ambil telemetry terbaru dari cache
   │     └── Ambil root_length + condition dari metadata MinIO bucket `ml`
   │
   ├── Step 2: Assemble 10D state
   │     └── [L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]
   │
   ├── Step 3: Predict action
   │            └── POST /predict ke model-controller
   │         Input: state 10D
   │         Output: D_mist, interval_sec, A_valve
   │
   ├── Step 4: Update pump/load1 schedule
   │     ├── Cek apakah PUMP_SCHEDULE_ID masih enabled
   │     │     └── Jika disabled: log WARNING, skip update, kirim alert NATS
   │     └── PUT /control/schedules/{PUMP_SCHEDULE_ID}
   │           Params: on_sec=D_mist, off_sec=interval_sec, value_on=1, value_off=0
   │
   ├── Step 5: Control valve/load2
   │     └── POST /control/commands
   │           {
   │             "node_id": "node-1",
   │             "type": "set_state",
   │             "output": "valve",
   │             "value": A_valve  # 1 = ON, 0 = OFF
   │           }
   │
   └── Step 6: Audit & logging
```

---

## 5. Konfigurasi

### 5.1 `model-controller` — Pure Inference Service

Hanya config untuk model dan network:
- Model path: `aeroponic_td3.zip`, `vec_normalize_td3.pkl`
- Device: `cpu` atau `cuda`
- Port: `8080`

### 5.2 `model-control` — Scheduler/Cron Service

**Deployment-specific (via env):**
- `NODE_ID` — node target
- `OUTPUT_NAME` — output actuator yang dikontrol (misal `pump`)
- `PUMP_SCHEDULE_ID` — schedule interval pump/load1 yang akan di-update
- `VALVE_OUTPUT_NAME` — nama output valve/load2 untuk direct command (misal `valve`)
- `PREDICTION_INTERVAL_SEC` — seberapa sering loop berjalan (default 3600 = 1 jam)
- `CONTROL_URL` — URL Control Service
- `MODEL_CONTROLLER_URL` — URL model-controller
- `NATS_URL` — URL NATS server

**Hardcoded defaults (di kode):**
- `MODULE_ID` — module id untuk telemetry
- Telemetry fallback defaults: `DEFAULT_T_IN`, `DEFAULT_H_IN`, `DEFAULT_EC`, `DEFAULT_PH`, `DEFAULT_T_NUT`, `DEFAULT_T_OUT`, `DEFAULT_H_OUT`
- ML fallback: `ML_FALLBACK_L_ROOT`, `ML_FALLBACK_CONDITION`
- Condition → U_status mapping: `CONDITION_SCORE_HEALTHY=0.95`, `CONDITION_SCORE_MODERATE=0.75`, `CONDITION_SCORE_POOR=0.5`
- Actuator mapping: `PUMP_ACTUATOR=load1`, `VALVE_ACTUATOR=load2`
- Valve command timeout: `VALVE_CMD_TIMEOUT_SEC=5`
- MinIO config: `MINIO_BUCKET=ml`
