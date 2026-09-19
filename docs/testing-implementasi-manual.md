# 🧪 Dokumentasi Pengujian Implementasi — IoT-Modular-Microservice

> **Versi:** 1.3  
> **Tanggal:** 2026-07-31  
> **Tujuan:** Panduan pengujian backend terotomatisasi (via folder `test/`) dan checklist pengujian visual UI/UX manual (via Dashboard React).  
> **Sumber Acuan:** `roadmap.md`, `planning.md`, `test/unit_test.py`, `test/stress_test.py`, `test/resilience_test.py`.  
> **Bahasa:** UI & API Response = **English**, Dokumentasi & Panduan = **Bahasa Indonesia**.

---

## 📋 Ringkasan Test Coverage (`test/unit_test.py`)

Logika backend dan koneksi API untuk seluruh domain telah diuji secara otomatis (total **106 test cases**). Laporan pengujian backend beserta payload HTTP tersimpan di `test/results/05_unit_test_payloads.json` dan `test/results/05_unit_test_payloads.md`.

| Service | Test Class | Jumlah Case | Cakupan Fitur Backend (Teruji Otomatis) |
|---------|------------|-------------|------------------------------------------|
| SystemHealth | `TestSystemHealth` | 1 | Gateway health check (`/v1/health`) |
| Auth | `TestAuthService` | 13 | Register, Login, Refresh, Logout, Profil, Sessions, Users CRUD, Roles, Password change, Deactivate |
| Module | `TestModuleService` | 16 | Modules CRUD, Nodes list/detail, Pair/Unpair, Discovered nodes, Sensor tags, Actuator mapping |
| Analytics | `TestAnalyticsService` | 6 | Multi-metric query, Downsampling, Rollup, Summary statistics, Export CSV, Time-range cap guard |
| Control | `TestControlService` | 15 | Direct command (`set_state`, `set_level`, `toggle`, `pulse`), Arbitrasi mode (MANUAL/AUTO/EMERGENCY), Schedules CRUD |
| Alert | `TestAlertService` | 6 | Alerts list/detail, Thresholds CRUD, Acknowledge alert status |
| Audit | `TestAuditService` | 5 | Log list, Filter by event, Free-text search, Time-range filter, Pagination |
| Notification | `TestNotificationService` | 5 | Settings get/put, Delivery logs, Test dispatch notification |
| Stream | `TestStreamService` | 12 | Stream CRUD, Playback URL, Snapshot capture, Recording start/stop, MinIO storage proxy |
| ML / Vision | `TestMLService` | 10 | Models registry, Upload weights, Detect base64/file, Bounding box output, Detection history |
| Export | `TestExportService` | 4 | Telemetry CSV export, Nodes export, Metadata export, OpenAPI spec discovery |
| WS Gateway | `TestWSGateway` | 2 | WS handshake `/ws/nodes/{id}/live` & `/ws/system-status` |
| Webhook | `TestWebhookService` | 5 | Webhook logs, Settings update, Telegram notification receiver |
| DLQ | `TestDLQService` | 2 | Dead-Letter Queue message listing & stream filtering |
| Model AI (TD3/PPO) | `TestModelService` | 4 | Model inference predict (`/v1/model_controller/predict`), Model control trigger (`/v1/model_control/trigger-predict`) |

---

## 🛠️ Panduan Eksekusi Program Testing (Terminal & Test Tools)

Seluruh logika backend, koneksi API, autentikasi, validasi data, event streaming, dan error handling **telah disediakan program test otomatisnya** di folder `test/`.

### Persyaratan Pra-Pengujian
- Pastikan seluruh container microservice berjalan dan berstatus `healthy`:
  ```bash
  docker compose up -d
  docker compose ps
  ```

### Perintah Eksekusi Master Test Suite

| Tujuan Pengujian | Perintah Terminal |
|------------------|-------------------|
| **Jalankan Unit & Feature Test** | `python3 test/unit_test.py` |
| **Jalankan Stress Test** | `python3 test/stress_test.py` |
| **Jalankan Chaos/Resilience Test** | `python3 test/resilience_test.py` |

### Perintah Eksekusi Spesifik per Service Test Class

```bash
# 1. Auth Service Backend Test
python3 -m unittest test.unit_test.TestAuthService

# 2. Module & Node Service Backend Test
python3 -m unittest test.unit_test.TestModuleService

# 3. Analytics Service Backend Test
python3 -m unittest test.unit_test.TestAnalyticsService

# 4. Control Service Backend Test
python3 -m unittest test.unit_test.TestControlService

# 5. Stream Service Backend Test
python3 -m unittest test.unit_test.TestStreamService

# 6. ML / Vision Service Backend Test
python3 -m unittest test.unit_test.TestMLService

# 7. Alert Service Backend Test
python3 -m unittest test.unit_test.TestAlertService

# 8. Audit Service Backend Test
python3 -m unittest test.unit_test.TestAuditService

# 9. Notification Service Backend Test
python3 -m unittest test.unit_test.TestNotificationService

# 10. Export Service Backend Test
python3 -m unittest test.unit_test.TestExportService

# 11. WS-Gateway Backend Test
python3 -m unittest test.unit_test.TestWSGateway

# 12. Model AI (TD3/PPO) Service Backend Test
python3 -m unittest test.unit_test.TestModelService
```

### Verifikasi API Manual via cURL (Opsional)

```bash
# Login & dapatkan token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@smartfarm.local","password":"AdminPassword123!"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Cek profil pengguna
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me
```

---

## ⚡ Performance & Chaos Audit

```bash
# 1. Jalankan pengujian unit & feature test
python3 test/unit_test.py

# 2. Jalankan pengujian batis beban throughput (Breakpoint Stress Test)
python3 test/stress_test.py

# 3. Jalankan pengujian ketahanan & pemulihan keruntuhan (Chaos Resilience Audit)
python3 test/resilience_test.py
```

### Grafik Artefak yang Dihasilkan (`test/results/`)
1. `01_unit_test_summary.png` & `01_unit_test_detailed.png` — Ringkasan unit test & durasi eksekusi per service.
2. `02_stress_test_throughput.png` & `02_stress_test_detailed.png` — Grafik RPS, Latency (p50, p95, p99), dan Error Rate.
3. `03_resilience_chaos_audit.png` & `03_resilience_detailed.png` — Grafik waktu pemulihan (recovery time) tiap service saat dihantam chaos failure.
4. `04_overall_system_dashboard.png` & `04_overall_system_dashboard_detailed.png` — Master visual dashboard kesehatan sistem.

---

## 🔄 Siklus Pengujian & Kesiapan Produksi

Pengujian disarankan mengikuti 4 siklus berulang:

| Siklus | Nama Siklus | Fokus Utama | Target Ketercapaian |
|--------|-------------|-------------|---------------------|
| **Pass 1** | Automated & Functional | Eksekusi `unit_test.py` + Verifikasi visual UI pertama | Seluruh test backend LULUS (100% PASS) |
| **Pass 2** | Fix & Re-test | Memperbaiki kecacatan tampilan UI / bug yang ditemukan | Tidak ada item checklist UI yang gagal |
| **Pass 3** | Stress & Stability | Menjalankan stress test & soak test durasi panjang | Sistem tidak mengalami memory leak atau crash |
| **Pass 4** | Production Gate | Pengujian akhir sebelum rilis resmi | Lulus seluruh kriteria Production Gate |

### Gate Kesiapan Produksi (Production Gate)

- **G1. Automated Tests:** 100% test cases backend di `test/unit_test.py` berstatus PASS.
- **G2. UI Visual Completeness:** Seluruh checklist manual UI/UX telah diperiksa dan disetujui Pengguna.
- **G3. Security Compliance:** Otorisasi RBAC, validasi JWT, dan rate-limiting berfungsi tanpa celah.
- **G4. Performance Approval:** Latensi API Gateway berada dalam ambang batas wajar pada pengujian stress.
- **G5. Resilience Certified:** Pemulihan otomatis (auto-healing) container terbukti sukses pada pengujian chaos.

---

## End-to-End (E2E) Verification

| # | Skenario E2E Flow | Langkah Alur Pengujian Visual | Ekspektasi Hasil Akhir UI |
|---|-------------------|------------------------------|---------------------------|
| E2E1 | Device Telemetry to Chart | Nyalakan simulator sensor / ESP32 | Data telemetry mengalir dari MQTT -> ditampilkan di Chart Analytics real-time. |
| E2E2 | Manual Control to Actuator | Klik ON pada toggle aktuator di Dashboard | Perintah terkirim via MQTT -> status aktuator di UI berubah menjadi active. |
| E2E3 | Camera to AI Detection | Ambil snapshot dari live video -> trigger AI | Hasil deteksi tanaman/objek muncul di galeri snapshot dengan bbox visual. |

---

## Chaos Scenarios

| # | Skenario Chaos | Mekanisme | Ekspektasi |
|---|---------------|-----------|------------|
| C1 | Container crash (Module Service) | `docker stop <container>` | Service recover otomatis via restart policy; data tidak hilang (NATS + Redis) |
| C2 | NATS JetStream down | `docker stop nats` | Subscriber tetap berjalan; pesan di-*replay* saat NATS kembali |
| C3 | MQTT Broker down | `docker stop mosquitto` | ESP32 auto-reconnect; telemetry di-*queue* dan terkirim saat broker pulih |
| C4 | Database (TimescaleDB) down | `docker stop timescaledb` | API mengembalikan error 503; data tidak corrupt; service pulih saat DB online |
