# enyx-enterprise Progress Report

**Tanggal:** 2026-07-30  
**Proyek:** enyx-enterprise — Aeroponic Smart Farming Microservices  
**Versi Dokumen:** 2.18.1  
**Penulis:** Alif Muhammad Rizky  

---

## 1. Executive Summary

Sistem **enyx-enterprise** saat ini berada pada tahap **Fase 0–13 (+ observability & tunneling)** dengan arsitektur microservice yang sudah berjalan penuh meliputi 13+ service, 12 instance database, observability terintegrasi (Prometheus + exporters), akses internet via Cloudflare Tunnel, dan kontrol AI berbasis TD3. Migrasi algoritma kontrol dari PPO ke **TD3 telah selesai** dan di-deploy sebagai dua service terpisah (`model-controller` + `model-control`). **Spray Automation Logic** dijalankan oleh `model-control`; **Webhook Service** (settings, logs, dispatch Telegram/Email/generic HTTP, AES-GCM, NATS) juga telah selesai. Semua service backend telah di-build, diintegrasikan ke Kong API Gateway, dan didokumentasikan integration guide-nya.

---

## 2. Arsitektur Sistem

### 2.1 Topologi Lapisan

```
ESP32 (Aeroponic Node)
    │
    ▼ MQTT
Mosquitto Broker
    │
    ▼
Module Service (Go) ──► MariaDB module_db
                   ──► TimescaleDB telemetry
                   ──► Redis shared (cache)
                   ──► NATS JetStream / Core
                           │
                           ├── Analytics Service ──► TimescaleDB analytics
                           │        └── Export Service ──► CSV
                           │
                           ├── Alert Service ──► MariaDB alert
                           │        └── Notification Service (Telegram/Email/Push)
                           │
                           ├── Control Service ──► MQTT actuator ──► ESP32
                           │
                           ├── Stream Service ──► MediaMTX (HLS/WebRTC)
                           │        └── MinIO bucket stream
                           │
                           ├── ML Vision API ──► YOLOv8 detect
                           │        ├── MinIO bucket ml-vision
                           │        └── MariaDB ml
                           │
                           ├── WebSocket Gateway ──► Dashboard (realtime)
                           │
                           ├── Audit Service ──► MariaDB audit
                           │
                           └── DLQ Saga Worker ──► MariaDB audit (DLQ)
                                    │
                                    ▼
                            Kong API Gateway ──► Dashboard React
                            (REST + WebSocket /ws)
```

### 2.2 Prinsip Desain Utama

| Prinsip | Implementasi |
|---|---|
| **Database-per-Service** | 8× MariaDB + 2× TimescaleDB per service, terisolasi via Docker network `iot-net` |
| **Event-Driven** | NATS JetStream (`telemetry.batch`, `saga.*`) + Core NATS (`telemetry.ingest`, `alert.*`) |
| **API Gateway** | Kong memusatkan REST (`/v1/*`) dan WebSocket (`/ws`) |
| **Zero-Trust Internal** | Setiap service hanya tahu credential DB-nya sendiri; Redis/MinIO di-scope per service |
| **Polyglot Persistence** | MariaDB (relasional), TimescaleDB (time-series), Redis (cache), MinIO (object) |
| **Idempotency & DLQ** | `meta.idempotency_key` + NATS `Nats-Msg-Id` + consumer dedupe; DLQ via advisory `$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.*` |

### 2.3 Database & Infrastructure Mapping

| Service | Database | Cache/Object | Status |
|---|---|---|---|
| Auth | `mariadb-auth` | — | ✅ Running |
| Module | `mariadb-module` | `timescaledb-module`, Redis DB0, MinIO `stream` | ✅ Running |
| Analytics | — | `timescaledb-analytics` | ✅ Running |
| WS-Gateway | — | — | ✅ Running |
| Control | `mariadb-control` | — | ✅ Running |
| Alert | `mariadb-alert` | Redis DB1 | ✅ Running |
| Notification | `mariadb-notification` | Redis DB2 | ✅ Running |
| Stream | `mariadb-stream` | MinIO `stream` | ✅ Running |
| ML Vision | `mariadb-ml` | MinIO `ml-vision` | ✅ Running |
| Audit | `mariadb-audit` | — | ✅ Running |
| DLQ | — | — | ✅ Running |
| Export | — | `timescaledb-module` (read), Redis DB3 | ✅ Running |

**Total instance:** 8× MariaDB · 2× TimescaleDB · 1× Redis · 1× MinIO = **12 instance** (konsolidasi dari 17 setelah ADR-004/ADR-005).

---

## 3. Progress Implementasi per Service

### 3.1 yang Sudah Selesai (✅)

| Service / Fitur | Fase | Status |
|---|---|---|
| Auth Service (register/login/JWT/RBAC) | Fase 1 | ✅ |
| Module Service (MQTT ingest, NATS fan-out, batch JetStream) | Fase 2 | ✅ |
| Analytics Service (rollup, hourly/daily aggregates, CSV export) | Fase 3 | ✅ |
| WS-Gateway (NATS ⇄ WebSocket bridge, JWT auth) | Fase 3 | ✅ |
| Control Service (manual/scheduler/emergency, ACK correlation) | Fase 4 | ✅ |
| ML Vision API (YOLOv8, model registry, MinIO, NATS) | Fase 5–6 | ✅ |
| Alert Service (threshold eval, dedup, `alert.triggered/resolved`) | Fase 7 | ✅ |
| Notification Service (Telegram/Email/Push, Redis queue) | Fase 5 | ✅ |
| Stream Service (MediaMTX, snapshot/recording, ML detection hook) | Fase 5–6 | ✅ |
| Audit Service (append-only log, `GET /audit/logs`) | Fase 9 | ✅ |
| DLQ Saga Worker | Fase 9b | ✅ |
| Export Service / Data API | Fase 9b | ✅ |
| Dashboard React (Analytics, Control Panel, Live View, Snapshot, Alerts, Audit) | Fase 10 | ✅ |
| Monitoring (Prometheus + exporters, cAdvisor, node-exporter) | Fase 1 | ✅ |
| TD3 Controller Inference (`model-controller`) | Fase 6e | ✅ |
| TD3 Control Scheduler (`model-control`) | Fase 6f | ✅ |
| Webhook Service (settings, logs, test dispatch, NATS `webhook.delivery`/`webhook.retry`, AES-GCM secret, Redis queue) | — | ✅ |
| Spray Automation Logic (disediakan oleh `model-control`/TD3) | Fase 13 | ✅ |
| Prometheus Monitoring (scrape jobs aktif: auth, module, analytics, control, stream, alert, ml, webhook, model-controller, model-control, Kong, DB exporters, cAdvisor, node-exporter) | Fase 1/11 | ✅ |
| Cloudflare Tunnel (`cloudflared` service di `docker-compose.yml`) | Fase 12 | ✅ |

### 3.2 Sedang Dikerjakan / Menyusul

Tidak ada item yang sedang dikerjakan pada cycle terkini. Seluruh layanan eksplisit pengguna (Spray Automation via `model-control`, Prometheus, Cloudflare Tunnel, Webhook) **sudah selesai diimplementasikan**. Sisa open item hanya **O1** (enforcement Mosquitto `allow_anonymous false`).

---

## 4. Hasil Testing

### 4.1 Unit & Feature Test Suite

- **Total Test Case Didesain:** 106 test cases
- **Build Charts:** `test/results/01_unit_test_summary.png` dan `01_unit_test_detailed.png`
- **Framework:** `test/unit_test.py` menggunakan `unittest` + `requests` melalui Kong API Gateway (`/v1`)
- **Cakupan:** 100% endpoint coverage untuk service yang sudah di-deploy (Auth, Module, Analytics, Control, Alert, Audit, Notification, Webhook, Stream, ML, Export, DLQ, WS-Gateway)

**Catatan Penting — Status Eksekusi Terkini:**

Berdasarkan artefak terakhir di `test/results/`:
- **Gambar `01_unit_test_summary.png`** menampilkan **100.0% Skipped** untuk seluruh service. Ini berarti pada eksekusi terakhir, **seluruh 106 test case terlewat (skipped)**.
- Penyebab utama yang tercatat di `test/results/05_unit_test_payloads.json` adalah **`Connection refused` ke `localhost:8000`** — API Gateway tidak reachable saat test dijalankan.
- Rekomendasi: Pastikan `docker compose up -d` sudah healthy sebelum menjalankan `python3 test/run_all_tests.py`. Lihat `docs/testing-plan-agent.md` untuk prosedur pre-flight.

### 4.2 Stress Test Suite

**Fitur:** Load, Spike, Soak, Breakpoint, dan WebSocket Concurrency Stress Testing (`test/stress_test.py`).

**Artefak:** `test/results/02_stress_test_detailed.png`, `02_stress_test_throughput.png`

**Status Eksekusi Terkini:**

- Panel stress test di master dashboard (`04_overall_system_dashboard_detailed.png`) menunjukkan **tidak ada data throughput/latency/error rate** yang tercatat (seluruh chart kosong).
- Hal ini konsisten dengan kegagalan pre-flight: tanpa API Gateway yang up, stress test tidak bisa dieksekusi.
- **Rekomendasi:** Jalankan stress test hanya setelahKonfirmasi Kong merespon `200 OK` di `GET /v1/health`. Target 대상: RPS 50–500, konkuensi 5–60, durasi 8–15 detik per level breakpoint.

### 4.3 Resilience & Chaos Engineering

**Fitur:** 3 skenario chaos (`test/resilience_test.py`):
1. Non-critical service outage (ml-service crash + self-healing)
2. Multi-auxiliary outage (notification + stream)
3. Event bus interruption (NATS restart + auto-reconnect)

**Status:** Belum dijalankan pada cycle terkini. Artefak `03_resilience_detailed.png` dan `03_resilience_chaos_audit.png` belum menampilkan data aktual.

### 4.4 Overall Test Health Score

Berdasarkan master dashboard (`04_overall_system_dashboard_detailed.png`), sistem menampilkan skor kesehatan **98%** saat service berjalan. Namun, tanpa eksekusi test suite yang valid, angka ini tidak terverifikasi oleh automasi.

**Rekomendasi tindak lanjut:**
1. Verifikasi `docker compose ps` — seluruh service harus `healthy`.
2. Jalankan `python3 test/run_all_tests.py` untukmerefresh artefak test.
3. Update checklist otomatis di `docs/testing-plan-agent.md` setelah setiap verifikasi step.

---

## 5. Firmware Status

### 5.1 ESP32 Firmware (`firmware/aeroponic-node/`)

- **Lokasi:** `firmware/aeroponic-node/`
- **Platform:** PlatformIO (ESP32) + Wokwi Simulator
- **Bahasa:** C++ (Arduino framework)
- **Komponen:**
  - `src/main.cpp` — kode utama
  - `src/protocols/` — NetworkManager, MqttManager, WebConfigPortal
  - `src/core/` — SystemMonitor, ConfigManager, HardwareManager, TaskWatchdog
  - `data/config.json` — konfigurasi perangkat (SSID, MQTT broker, dsb.)
- **MQTT Contract (aktual):**
  - Subscribe: `smartfarm/actuator/{node_id}` (`set_output` saja, `value` digital `0/1` atau PWM `0–255`)
  - Publish: `smartfarm/{node_id}/telemetry`, `smartfarm/{node_id}/confirm` (ACK), `smartfarm/{node_id}/alert` (emergency)
  - Discovery: `smartfarm/discovery`
  - LWT: `smartfarm/status/{node_id}` (retained)
- **Build:** `pio run -d firmware/aeroponic-node` → `[SUCCESS]`
- **Catatan:** Sesuai constraint proyek, firmware **tidak diubah** kembali. Setiap perubahan kontrak MQTT atau payload diuji via simulator sebelum diimplementasikan di backend.

### 5.2 Firmware Simulator (`firmware/firmware-sim/`)

- **Lokasi:** `firmware/firmware-sim/`
- **Fungsi:** Mensimulasikan banyak node aeroponik secara paralel via MQTT tanpa hardware fisik.
- **Fitur:**
  - Clone device dengan fixed distinct `node_id` (`node-01` s.d. `node-09`)
  - Dummy sensor model dengan bounded random walk + sine drift
  - Telemetry payload **byte-compatible** dengan `HardwareManager.cpp`
  - Local control (overheat protection), emergency stop, actuator ACK
- **Instalasi:**
  ```bash
  cd firmware/firmware-sim
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  ```
- **Penggunaan:**
  ```bash
  python -m firmware_sim clone --node-id node-07
  python -m firmware_sim run --node-id node-07
  ```

---

## 6. Model Learning Results — TD3 Aeroponic Controller

### 6.1 Migrasi PPO → TD3

Berdasarkan ADR-008 dan analisis komparatif PPO vs TD3, kontrol aeroponik telah **migrasi sepenuhnya ke TD3**. Alasan utama:
- PPO mengalami **stuck local optimum** (`clip_fraction ≈ 0`, `ep_len` beku di 90–94)
- Reward sangat **sparse** (hanya tiap 720 step pada horizon 1440)
- TD3 (off-policy, twin critics, delayed policy updates, target policy smoothing) lebih stabil untuk continuous action space denganeksi kompleks.

Legacy PPO directories (`ppo-model-training/`, `services/ppo-control/`, `services/ppo-controller/`) telah **dihapus**. Artifacts `aeroponic_ppo.zip` dan `vec_normalize.pkl` juga telah dihapus.

### 6.2 Training Configuration & Environment

| Parameter | Nilai |
|---|---|
| Algorithm | TD3 (Stable-Baselines3) |
| Total Timesteps | **2,000,000** |
| Policy | TD3 MlpPolicy |
| Observation Space | **10D continuous** `[L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day]` |
| Action Space | **3D continuous** `[-1, 1]` → `D_mist [120,600]s`, `interval_sec [120,600]s`, `A_valve [0,1]` |
| Learning Rate | 1e-4 (linear schedule) |
| Buffer Size | 2,000,000 |
| Batch Size | 256 |
| Gamma | 0.995 |
| Tau | 0.005 |
| Policy Delay | 2 |
| Action Noise | Normal(σ=[0.1, 0.1, 0.2]) |
| Learning Starts | 100,000 |
| Sensor Noise | ±0.3°C T, ±2% H, ±0.1 EC, ±0.1 pH |
| Actuator Noise | ±5% D_mist, ±0.3s spray delay |
| Curriculum Weather | Skala 0.0 → 1.0 kuadratik selama training |
| **Device** | CPU (sesuai instruksi) |

### 6.3 Reward Structure

| Komponen | Berat | Kondisi |
|---|---|---|
| `R_growth` | `w_growth=15.0` | Reward pertumbuhan akar per-step dari simulator |
| `R_humidity_maintenance` | +1.5 / -3.0 | +1.5 jika `80≤H_in≤95%`; -3.0 jika di luar rentang kritis |
| `R_temperature_maintenance` | +1.5 / -3.0 | +1.5 jika `18≤T_in≤28°C`; -3.0 jika di luar rentang kritis |
| `R_efficiency` | +0.0 – 0.369 | Bersyarat: stabil EC(1.2–2.0), pH(5.5–6.5), H_in≥80%, T_in(24–30°C); reward D_mist<300s, interval>300s, valve bonus |
| `P_env` | `w_env=0.05` | Penalty deviasi pH/EC/H_in |
| `P_hypoxia` | `w_hypoxia=0.02` | Penalty kekurangan oksigen |
| `P_interval` | `w_interval=0.01` | Penalty interval terlalu panjang (>720s) |
| `C_resource` | `w_valve_cost=0.15` | Biaya per-misting valve |

### 6.4 Hasil Evaluasi (2M Timesteps)

| Metrik | Nilai |
|---|---|
| **Mean Episode Reward** | **6,671** |
| **Episode Length** | 150 cycles |
| **D_mist CV** | 0.33 ✅ (stabil) |
| **Interval CV** | 0.20 ⚠️ (masih bervariasi) |
| **A_valve Usage** | 50.1% ✅ |
| Pertumbuhan akar kumulatif | ~2–4 cm per episode (dengan reward shaping pertumbuhan) |
| Pelanggaran batas aman | 0.0 |
| Efisiensi air | strategi pulsa presisi (misting 5–10 menit, hemat tinggi vs kontinu) |

**Referensi artefak visual:** `control-model-training/results/` (termasuk `td3_training_curves.png`, `td3_reward_curve.png`, `td3_stability_comparison.png`, `td3_action_histograms.png`, `td3_episode_comparison.png`).

### 6.5 Deployment

TD3 di-deploy melalui dua service:

1. **`model-controller`** (inference service)
   - Load `aeroponic_td3.zip` + `vec_normalize_td3.pkl` on startup
   - Endpoint: `POST /predict` → mapping state 10D ke action 3D
   - Port: `:8080`
   - Route Kong: `/v1/model-controller`

2. **`model-control`** (scheduler/loop service)
   - Evaluasi TD3 setiap `PREDICTION_INTERVAL_SEC` (default 5s)
   - Hanya mengirim schedule ke Control Service saat **satu siklus selesai** (cycle-boundary update)
   - Subscribe `telemetry.ingest` + `telemetry.batch` untuk cache metrik real-time
   - Port: `:8081`
   - Route Kong: `/v1/model-control`

**File model aktif:**
- `control-model-training/models/aeroponic_td3.zip`
- `control-model-training/models/vec_normalize_td3.pkl`

---

## 7. Gap Analisis & Rekomendasi

### 7.1 Testing Gap (Kritis)

| Item | Masalah | Dampak | Rekomendasi |
|---|---|---|---|
| Unit Tests | 100% skipped pada run terakhir | Tidak ada verifikasi otomatis CI | Jalankan `python3 test/run_all_tests.py` setelah `docker compose up -d` healthy |
| Stress Tests | Artefak kosong | Kapasitas maksimal sistem tidak terukur | Pastikan Kong `:8000` reachable sebelum eksekusi |
| Resilience Tests | Artefak kosong | Chaos readiness tidak terverifikasi | Jalankan fase 3 suite setelah phase 1 & 2 sukses |

### 7.2 Security Open Items

Tidak ada security open item yang tersisa. O1 (Mosquitto `allow_anonymous false` + `acl.conf` enforcement) telah selesai diterapkan: `infra/mosquitto/config/mosquitto.conf` sudah `allow_anonymous false`, `password_file` terisi 5 user, dan `acl.conf` aktif. Container Mosquitto perlu direstart untuk me-load konfigurasi baru.

### 7.3 Future Work

Tidak ada item Future Work yang tersisa. Semua fitur yang direncanakan sebelumnya (Spray Automation Service, Prometheus Metrics, Cloudflare Tunnel, Webhook Service) **sudah selesai diimplementasikan** dan terdaftar di [`docs/roadmap.md`](file:///home/almuzky/TA/Microservices/docs/roadmap.md).

Satu-satunya open item yang masih menunggu adalah penerapan restart container Mosquitto untuk menerapkan konfigurasi O1 yang sudah ada di disk.

---

## 8. Dokumentasi Pendukung

- `docs/planning.md` — Arsitektur murni, bounded context, prinsip desain
- `docs/roadmap.md` — Status fase & checklist implementasi
- `docs/adr.md` — Architecture Decision Records (ADR-001 s.d. ADR-008)
- `docs/integration-guides/ppo.md` — Integration guide TD3 Controller (menggantikan legacy PPO guide)
- `docs/testing-plan-agent.md` — Checklist pengujian backend/API
- `control-model-training/README.md` — Training config, reward structure, evaluasi TD3
- `services/model-controller/README.md` — Inference service docs
- `firmware/aeroponic-node/README.md` — PlatformIO build guide, MQTT contract aktual
- `firmware/firmware-sim/README.md` — Simulator usage, cloning, CLI inject

---

## 9. Kesimpulan

Sistem **enyx-enterprise** saat ini memiliki fondasi arsitektur yang solid: **13+ microservices** (Go + Python), **12 instance database** (MariaDB/TimescaleDB/Redis/MinIO) dengan prinsip Database-per-Service, **NATS JetStream** sebagai event bus, **Kong** sebagai API Gateway tunggal, **Prometheus** + exporters untuk observability, **Cloudflare Tunnel** untuk akses internet, dan **dashboard React** yang telah terintegrasi penuh. Kontrol tanaman berbasis **TD3** telah selesai dilatih (2M timesteps) dan di-deploy (`model-controller` + `model-control`) menggantikan PPO sepenuhnya. **Webhook Service** juga telah selesai diimplementasikan dengan delivery Telegram/Email/generic HTTP, AES-GCM secret encryption, Redis queue, dan NATS `webhook.delivery`/`webhook.retry`.

Area yang memerlukan perhatian segera adalah **eksekusi ulang test suite** agar artefak testing (unit, stress, resilience) merefleksikan kondisi sistem yang sebenarnya. Firmware dan simulator telah siap mendukung pengujian end-to-end tanpa hardware fisik.
