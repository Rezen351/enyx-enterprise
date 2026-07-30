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
- Dijalankan sebagai standalone service/loop di `model-control` service

**Kontrol Akturator:**
- **Pump/load1** — di-update oleh TD3 via interval schedule (`on_sec`, `off_sec`)
- **Valve/load2** — di-control oleh TD3 via direct command `set_state` (ON/OFF) sesuai `A_valve`, semua event tercatat log dan audit

---

## 2. Arsitektur Dua Service (Single Responsibility)

```
model-control service (cron/scheduler loop)
   │
   ├── Konfigurasi:
   │     ├── node_id, output_name, module_id
   │     ├── pump_schedule_id (interval schedule untuk load1/pump)
   │     ├── valve_schedule_id = None (valve/load2 di-control direct command, bukan schedule)
   │     └── prediction_interval_sec = 3600 (1 jam)
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
   ├── POST /predict
   │     Input:  state 10D
   │     Output: D_mist, interval_sec, A_valve
   │
   └── Tugas SATU: load model + inference, tidak ada loop/state/telemetry
```

**Tidak ada:**
- Perubahan tabel `control_modes`
- Tabel `model_control_config`
- Mode baru di dashboard
- Endpoint baru di Control Service

**Kontrol Akturator:**
- **Pump/load1** (`interval`) → di-update oleh TD3 (`on_sec`, `off_sec`). `value_on/value_off` tetap 1/0.
- **Valve/load2** → di-control oleh TD3 via direct command `set_state` (ON/OFF) sesuai `A_valve`. Semua event dicatat log dan audit.

**Audit & Logging:**
- Semua event Pump dan Valve dicatat di log dan audit trail
- Pump: update interval schedule dari TD3

- Valve: direct command dari TD3, dieksekusi oleh Control Service tanpa perubahan code
**Valve Execution:**
- TD3 hanya menentukan TARGET valve state (A_valve) setiap 1 jam
- Control Service menjalankan valve command setiap misting cycle (tiap D_mist + interval_sec detik)
- Valve di-reset sesuai target sebelum setiap misting ON

---

## 3. Konfigurasi per Service

### 3.1 `model-controller` — Pure Inference Service

Hanya config untuk model dan network:
- Model path: `aeroponic_td3.zip`, `vec_normalize_td3.pkl`
- Device: `cpu` atau `cuda`
- Port: `8080`

### 3.2 `model-control` — Scheduler/Cron Service

Semua konfigurasi ada di sini:

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

---

## 4. State Assembly

### 4.1 Telemetry Fields

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

### 4.2 Metadata Source — MinIO

Semua data `root_length` dan `status umbi` diambil dari **MinIO bucket `ml`**:
- Prefix: `results/{module_id}/detection_*.json`
- Baca `user_metadata.root_length_cm`, `user_metadata.condition`, `user_metadata.confidence`
- Ambil object terbaru berdasarkan `last_modified`
- Fallback ke hardcoded default jika tidak ada metadata

### 4.3 Telemetry Source

- Ambil telemetry terbaru dari Module Service via NATS subscription atau HTTP pull
- Simpan di in-memory cache per node_id
- Fallback ke hardcoded default jika telemetry tidak ada

---

## 5. Prediction Loop Flow

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
    └── Step 6: Audit
          └── Publish NATS: model_control.prediction.completed (pump + valve)
```

**Valve Execution:**

Valve di-control langsung oleh `model-control` via Control Service existing API, tanpa modifikasi Control Service code:

1. `model-control` kirim direct command valve setiap 1 jam:
   ```
   POST /control/commands
   {
     "node_id": "node-1",
     "type": "set_state",
     "output": "valve",
     "value": A_valve  # 1 = ON, 0 = OFF
   }
   ```

2. Control Service menjalankan command seperti biasa, tidak ada perubahan code

3. Valve di-update setiap 1 jam (sesuai TD3 prediction), tidak perlu tunggu misting cycle

Keuntungan:
- Valve di-update setiap 1 jam sesuai TD3 prediction
- Menggunakan Control Service existing API, tidak ada modifikasi code
- Semua event valve tercatat di audit trail Control Service

---

## 6. Integrasi dengan Scheduler yang Sudah Ada

### 6.1 Setup Awal

1. Buat jadwal `interval` via dashboard/API:
   ```
   POST /control/schedules
   {
     "node_id": "node-1",
     "output_name": "pump",
     "type": "interval",
     "params": {
       "on_sec": 180,
       "off_sec": 540,
       "value_on": 1,
       "value_off": 0
     },
     "enabled": true
   }
   ```
2. Dapat `schedule_id` dari response
3. Set `PUMP_SCHEDULE_ID=<schedule_id>` di env model-control
4. Start model-control service

### 6.2 Runtime

- Control Service scheduler menjalankan jadwal `interval` seperti biasa
- `model-control` meng-update `on_sec` dan `off_sec` setiap 1 jam
- `model-control` mengirim direct command valve setiap 1 jam via existing Control Service API
- Semua command dieksekusi oleh Control Service tanpa perubahan code

### 6.3 Safety
- Kalau `model-control` down, jadwal lama tetap jalan dengan nilai terakhir

- Kalau schedule di-disable oleh user, TD3 skip update dan kirim alert

---

## 7. Struktur File

### 7.1 `model-controller` — Pure Inference Service

```
services/model-controller/
├── app/
│   ├── __init__.py
│   ├── config.py           # Settings: model path, device
│   ├── main.py             # FastAPI app: /health, /predict
│   ├── model_loader.py     # Load TD3 + VecNormalize + map action
│   ├── responses.py        # Standard envelope
│   └── schemas.py          # Request/response models
├── models/
│   ├── aeroponic_td3.zip
│   └── vec_normalize_td3.pkl
├── Dockerfile
├── requirements.txt
└── README.md
```

### 7.2 `model-control` — Scheduler/Cron Service

```
services/model-control/
├── app/
│   ├── __init__.py
│   ├── config.py           # Settings: node_id, schedule_id, interval, URLs
│   ├── main.py             # FastAPI app: /health, /trigger-predict
│   ├── ppo_loop.py         # Background TD3 prediction loop
│   ├── telemetry_cache.py  # In-memory telemetry cache
│   ├── minio_client.py     # MinIO client untuk metadata vision
│   ├── model_controller_client.py  # HTTP client ke model-controller
│   └── control_client.py   # HTTP client ke Control Service
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 8. Environment Variables

```bash
# model-controller
MODEL_PATH=/app/models/aeroponic_td3.zip
VEC_NORM_PATH=/app/models/vec_normalize_td3.pkl
DEVICE=cpu
PORT=8080

# model-control
APP_NAME=model-control
PORT=8081
NODE_ID=node-1
OUTPUT_NAME=pump
PUMP_SCHEDULE_ID=schedule-uuid-1234
VALVE_OUTPUT_NAME=valve
PREDICTION_INTERVAL_SEC=3600
CONTROL_URL=http://control:8080
MODEL_CONTROLLER_URL=http://model-controller:8080
NATS_URL=nats://nats:4222
```

---

## 9. Testing Plan
### 9.1 Unit Test
- State assembly dengan telemetry mock
- State assembly dengan MinIO metadata mock
- Schedule update dengan Control Service mock
- Fallback handling saat telemetry/MinIO gagal

### 9.2 Integration Test

1. Start model-control dengan `PREDICTION_INTERVAL_SEC=60` (1 menit untuk testing)
2. Start module service + MinIO dengan metadata sample
3. Verify: setiap 1 menit, schedule pump/load1 di database ter-update
4. Verify: scheduler engine menerapkan jadwal baru ke MQTT untuk pump/load1
5. Verify: direct command valve dikirim setiap 1 jam via Control Service API
6. Verify: kalau model-control di-stop, jadwal lama tetap jalan
7. Verify: MinIO metadata dipakai untuk state assembly
8. Verify: valve/load2 events dicatat di log dan audit trail

### 9.3 Safety Test

- Kill model-control → pastikan firmware tetap running dengan jadwal terakhir
- Start model-control → pastikan ia mengambil jadwal terakhir dan melanjutkan
- Verify: MinIO fallback bekerja jika metadata tidak ada
- Verify: valve manual change tercatat di log dan NATS audit
---

## 10. Kelebihan Pendekatan

| Aspek | Benefit |
|---|---|
| **Simplicity** | Tidak perlu modifikasi Control Service, Module Service, atau ML Service untuk integrasi dasar |
| **Fast prototyping** | Cukup hardcode config di model-control, langsung jalan |
| **No schema migration** | Pakai schedule yang sudah ada, tidak butuh tabel baru |
| **Safe fallback** | Kalau TD3 down, jadwal tetap jalan |
| **Easy debugging** | Semua log di satu service, tidak tersebar |
| **Customizable** | Bisa di-shift ke generic configuration kapan saja jika nanti butuh multi-node |
| **Reusable inference** | model-controller bisa dipakai dashboard, simulasi, unit test |

---

## 11. Kerugian / Trade-off

| Aspek | Catatan |
|---|---|
| **Hardcoded** | Perlu edit code/env var jika ganti node/module/schedule |
| **Single node** | Belum support multi-node secara bersamaan tanpa modifikasi |
| **Tidak ada dashboard UI** | Konfigurasi via env var, bukan via dashboard |
| **Tight coupling** | Bergantung pada format telemetry dan MinIO metadata yang sudah ada |

---

## 12. Implementation Steps

### Week 1
1. Buat `model-control` service structure
2. Implement `telemetry_cache.py` untuk cache telemetry
3. Implement `ppo_loop.py` dengan MinIO metadata + state assembly + pump schedule update + valve direct command
4. Implement `minio_client.py` untuk baca metadata vision dari MinIO

### Week 2
1. Implement `model_controller_client.py` dan `control_client.py`
2. Implement NATS audit logging untuk pump dan valve events
3. Dockerfile + deployment test

### Week 3
1. Integration test dengan real services
2. Safety testing
3. Documentation untuk operator

---

## 13. File Changes Summary

### File Baru
- `services/model-control/app/ppo_loop.py` — Background TD3 prediction loop
- `services/model-control/app/telemetry_cache.py` — In-memory telemetry cache
- `services/model-control/app/minio_client.py` — MinIO client untuk metadata vision
- `services/model-control/app/model_controller_client.py` — HTTP client ke model-controller
- `services/model-control/app/control_client.py` — HTTP client ke Control Service
- `services/model-control/Dockerfile`
- `services/model-control/requirements.txt`
- `services/model-control/README.md`

### File Modified
- `services/model-controller/app/config.py` — Tambah hardcoded config: NODE_ID, SCHEDULE_ID, MODULE_ID, dll
- `services/model-controller/app/main.py` — Start prediction loop on startup
- `services/model-controller/requirements.txt` — Tambah `httpx`, `nats-py`
- `services/model-controller/Dockerfile` — Update jika perlu

### No Changes Needed
- Control Service — tidak ada perubahan
- Module Service — tidak ada perubahan
- ML Service — tidak ada perubahan (vision metadata diambil dari MinIO)
- Dashboard — bisa diintegrasikan nanti sebagai status display

---

## 14. Resolved Questions

1. **Apakah ML Service sudah memiliki endpoint untuk `root_length` dan `condition`?**
   - Tidak perlu. Semua data vision diambil dari metadata MinIO bucket `ml`.

2. **Schedule type apa yang akan di-update?**
   - `interval` (pulse tanpa window).
    - `on_sec` dan `off_sec` diperbarui oleh `model-control`.
    - TD3 yang menentukan timing, bukan fixed window.

3. **Berapa interval yang cocok untuk deployment nyata?**
   - Default: **1 jam** (`PREDICTION_INTERVAL_SEC=3600`).

4. **Apakah TD3 loop perlu membaca data weather (T_out, H_out)?**
   - Tidak perlu tambah weather API.
   - `T_out` dan `H_out` sudah termasuk dalam telemetry; cukup dibaca dari sana.

5. **Bagaimana handling jika schedule yang di-target diubah/nonaktif oleh user?**
    - Sebelum tiap update, `model-control` cek apakah `PUMP_SCHEDULE_ID` masih enabled.
    - Jika disabled: log WARNING, **skip update**, dan kirim alert NATS `model_control.schedule.disabled`.

6. **Bagaimana dengan valve?**
    - Valve/load2 di-control langsung oleh TD3 setiap 1 jam via Control Service existing API.
    - model-control mengirim `POST /control/commands` dengan `type=set_state`, `output=valve`, `value=A_valve`.
   - Tidak ada modifikasi Control Service code.
   - Semua event valve dicatat di log dan audit trail.
   - `VALVE_OUTPUT_NAME` = nama output valve (misal `valve`).

7. **Bagaimana dengan logging dan audit?**
   - Semua event pump/load1 dan valve/load2 dicatat di log.
   - Pump: update interval schedule dari TD3, audit via NATS `model_control.prediction.completed`.
   - Valve: target di-update oleh TD3, dieksekusi oleh Control Service, audit via NATS `model_control.valve.command`.

---

## 15. References

- model-controller service: `services/model-controller/`
- Control Service schedule API: `POST/PUT /control/schedules`
- Control Service integration guide: `docs/integration-guides/control.md`
- Telemetry.ingest NATS subject: `telemetry.ingest`
- MinIO bucket `ml` untuk metadata vision
