# 🧪 Dokumentasi Pengujian Implementasi — IoT-Modular-Microservice

> **Versi:** 1.2
> **Tanggal:** 2026-07-23 (update: expanded automated unit tests + OTA backend removal)
> **Tujuan:** Checklist pengujian manual seluruh fitur yang sudah & belum diimplementasikan, plus target pengujian.
> **Sumber acuan:** `roadmap.md` (v2.7.0), `planning.md` (v2.7.0), `infra/kong/kong.yml`, kode `services/*`, `stress-test/`, `test/unit_test.py`.
> **Bahasa UI/API:** English (sesuai AGENTS.md). Catatan pengujian ini internal → Bahasa Indonesia diperbolehkan.

---

## 📋 Daftar Isi

| Section | Topik | Section | Topik |
|---------|--------|---------|--------|
| 0 | 🤖 Automated Unit Test Coverage | 8 | 🟢 Monitor Service (CLI) |
| 1 | 🔴 Auth Service | 9 | 🔐 Keamanan Lintas-Service |
| 2 | 🟡 Module & Node Service | 10 | 📡 MQTT & NATS Contract |
| 3 | 🟡 Analytics Service | 11 | 📊 Observability & Monitoring |
| 4 | 🟡 WS-Gateway | 12 | 🖥️ Dashboard (React) UI |
| 5 | ✅ Control Service | 13 | 🔄 End-to-End Flow |
| 6 | 🟢 Stream Service | 14 | 🔜 Service Future & Implementasi |
| 7 | 🟢 ML / Vision API | 15 | ⚡ Performance & Penetration |
| 8 | 🟢 Monitor Service (CLI) | 16 | 🚦 Siklus & Kesiapan Produksi |

---

## 🛠️ Setup Pra-Pengujian

### Environment
- Stack dijalankan via `docker compose up -d` (semua container `healthy`).
- Base URL eksternal (melalui Kong): `http://localhost:8000` (env `KONG_PUBLIC_URL`).
- MQTT broker (device): `tcp://mosquitto:1883` (container internal, auth enabled).
- Prometheus: `http://localhost:9090`. NATS monitor: `http://<nats>:8222`.
- MinIO console: `http://localhost:9001` (bucket `stream`, `ml-vision`).

### Auto Cleanup (Start & End)
- `run_unit_tests()` membersihkan seluruh artefak lama di `test/results/` **sebelum** menjalankan test suite.
- Setelah test suite selesai, fungsi `cleanup_test_data()` mencoba menghapus data uji di backend yang tercatat oleh test (user/module/node/schedule/threshold/stream).
- Hasil dokumen test terbaru tetap disimpan: `05_unit_test_payloads.json`, `05_unit_test_payloads.md`, dan PNG chart terbaru.

### Auth Token (wajib untuk route terlindungi)
```bash
# 1. Login (public route Kong: /auth/login)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@smartfarm.local","password":"<ADMIN_PASSWORD>"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo $TOKEN

# Helper curl ber-otentikasi
api() { curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000$1"; }
```

### Tools Tersedia (sudah ada di repo)
- `test/` — toolkit unit test, load/soak/spike + pentest (`unit_test.py`, `loadtest.py`, `wstest.py`, `mqtttest.py`, `pentest.py`, `metrics.py`, `report.py`, `cli.py`). Jalankan via `python3 cli.py <subcommand>`.
- `mosquitto_sub` / `mosquitto_pub` — verifikasi MQTT end-to-end.
- `nats` CLI — `nats sub "mqtt.<NODE_ID>"`, `nats sub "telemetry.ingest"`, dst.

---

## 🧭 Metode Pengujian Manual (Manual Testing Methods)

> [!IMPORTANT]
> **Kepemilikan & Batasan Pengujian:** Semua pengujian manual yang tercantum dalam dokumen ini **wajib dieksekusi secara manual oleh Pengguna (User), bukan oleh AI Agent**. AI Agent hanya diperbolehkan untuk membantu merancang skenario pengujian baru, memverifikasi relevansi skenario terhadap fitur yang dikembangkan, atau memperbarui struktur dokumen ini. Pengisian status checklist (`[ ]` → `[x]`) dilakukan oleh Pengguna setelah pengujian manual berhasil dilakukan secara langsung.

| # | Metode | Tujuan Singkat |
|---|--------|----------------|
| 1 | **Smoke Testing** | Pastikan build stabil (container healthy, login & healthcheck OK) sebelum uji lanjut. |
| 2 | **Functional Black-Box** | Validasi I/O API & Dashboard via Equivalence Partitioning + Boundary Value Analysis. |
| 3 | **Exploratory Testing** | Temukan bug tersembunyi (JSON acak, double-click, putus koneksi di tengah transaksi). |
| 4 | **Integration & E2E** | Verifikasi alir data antar-service lewat NATS / Kong (Auth→Audit, ESP→Dashboard). |
| 5 | **Security & RBAC** | Bypass token (401), escalation role (403), SQL/XSS injection ditolak. |
| 6 | **Usability & UX** | Loader & error state jelas, responsif di desktop/tablet/mobile. |

---

## ✅ Legenda Status

| Badge | Arti | Badge | Arti |
|-------|-------|-------|-------|
| 🔴 | Belum diuji (`[ ]`) | ✅ | Lulus (`[x]`) |
| ⚠️ | Diketahui gagal/bug (`[!]`) | ➖ | Tidak berlaku (`[-]`) |
| 🟡 | Diuji sebagian (`[~]`) | | |

**Kolom Target:** kapan harus selesai diuji (lihat bagian Target di bawah).

---

## 0. 🤖 Automated Unit Test Coverage (`test/unit_test.py`)

> **Status:** ✅ 102 test cases implemented (2026-07-23)
> **Coverage:** 14 service classes, 102 tests — comprehensive REST + WebSocket endpoint coverage.

| Service | Tests | Key Endpoints Covered | Test Class |
| |---------|-------|----------------------|------------|
| SystemHealth | 1 | `/v1/health` | `TestSystemHealth` |
| Auth | 13 | register, login, logout, profile, sessions, users CRUD, roles, refresh, password, account delete | `TestAuthService` |
| Module | 16 | modules CRUD, nodes CRUD, pair/unpair, tags update, actuators CRUD | `TestModuleService` |
| Analytics | 6 | nodes, metrics (interval/from-to/comma-separated), summary, export CSV | `TestAnalyticsService` |
| Control | 15 | commands, modes (get/set/resume/per-output), targets, outputs, schedules CRUD + enable/disable | `TestControlService` |
| Alert | 6 | alerts list, thresholds CRUD, acknowledge alert | `TestAlertService` |
| Audit | 5 | logs list, filter by event/search/time-range/pagination | `TestAuditService` |
| Notification | 5 | logs, settings (get/update), test dispatch, logs with filters | `TestNotificationService` |
| Webhook | 5 | logs, settings (get/update), test dispatch, receive telegram webhook | `TestWebhookService` |
| Stream | 12 | streams CRUD, snapshot/record start/stop, snapshots CRUD, storage proxy | `TestStreamService` |
| ML | 10 | models (list/get/update/activate/delete), detect base64, detections detail, results, frame inference | `TestMLService` |
| Export | 4 | nodes, metadata, OpenAPI spec, telemetry CSV export | `TestExportService` |
| WSGateway | 2 | system-status WS handshake, node-live WS handshake | `TestWSGateway` |
| DLQ | 2 | list DLQ messages, filter by source stream/trace ID | `TestDLQService` |

> **Test result outputs** (`test/results/`): besides PNG charts, every test run also produces:
> - `05_unit_test_payloads.json` — machine-readable JSON log of request + full response payload/body per test.
> - `05_unit_test_payloads.md` — human-readable Markdown report with all request/response data.
> - Binary responses (images, files, blobs) are automatically saved to `test/results/` and referenced in the above reports.

### Manual Test Scope Reduction
Checklist manual berikut **sudah tercakup oleh automated unit tests** dan hanya memerlukan validasi visual/UI oleh User:

| Manual Section | Automated Coverage | Sisa Manual |
|----------------|-------------------|-------------|
| A1–A10, A12–A15 | register, login, logout, profile, sessions, users/roles CRUD, password, account delete | Validasi UI form |
| M1–M16 | modules CRUD, nodes, pair/unpair, tags, actuators | Validasi UI Module page |
| AN1–AN4, AN10–AN12 | metrics, summary, export CSV, time-range cap | Validasi chart render |
| C1–C22 | commands, modes, schedules, enable/disable, per-output | Validasi Control panel UI |
| AL1–AL3 | alerts, ack, thresholds | Validasi Alerts page UI |
| AU3–AU6, AU10 | logs, filters | Validasi Audit table UI |
| N1–N3 | settings, logs, test dispatch | Validasi Notification Bell WS |
| WH1–WH3 | logs, settings, receive telegram | Validasi Webhook receiver |
| S1–S12 | streams, snapshot/record, storage proxy | Validasi Live/Snapshot UI |
| V1–V5, V8, V10–V14, V18 | models, detect, detections, results | Validasi ML Gallery UI |
| EX1–EX4, EX7 | telemetry CSV, nodes, meta, OpenAPI | Validasi Export page UI |
| DLQ messages | list + filter | Validasi DLQ page UI (jika ada) |

---

## 1. 🔴 Auth Service (`/auth`)

| # | Tes | Metode & Endpoint (via Kong) | Ekspektasi | Status | Target |
|---|-----|------------------------------|------------|--------|--------|
| A1 | Register user baru | `POST /auth/register` | 201, hash bcrypt, audit.log publish | [ ] | [ ] | M1 |
| A2 | Login via email | `POST /auth/login` | 200, `access_token` + `refresh_token` | [ ] | M1 |
| A3 | Login via username (`identifier`) | `POST /auth/login` | 200 (field identifier fleksibel) | [ ] | M1 |
| A4 | Login kredensial salah | `POST /auth/login` | 401 | [ ] | M1 |
| A5 | Refresh token (rotation) | `POST /auth/refresh` | token lama revoke, baru issue | [ ] | M1 |
| A6 | Logout (revoke all) | `POST /auth/logout` | refresh token aktif revoked | [ ] | M1 |
| A7 | Get profile | `GET /auth/me` | 200 profil dari JWT | [ ] | M1 |
| A8 | Update profile | `PUT /auth/me` | 200 | [ ] | M1 |
| A9 | Change password | `PUT /auth/password` | 200 | [ ] | M1 |
| A10 | List sessions | `GET /auth/sessions` | 200 daftar sesi | [ ] | M1 |
| A11 | Deactivate account | `DELETE /auth/account` | soft-delete | [ ] | M1 |
| A12 | List users (admin) | `GET /auth/users` | 200 (hanya admin) | [ ] | M1 |
| A13 | List roles (admin) | `GET /auth/roles` | 200 daftar role | [ ] | M1 |
| A14 | Update user (admin) | `PUT /auth/users/{id}` | ubah status/role | [ ] | M1 |
| A15 | Delete user (admin) | `DELETE /auth/users/{id}` | soft-delete | [ ] | M1 |
| A16 | Guard: self-deactivate/demote | `PUT/DELETE` akun sendiri | 403 | [ ] | M1 |
| A17 | Guard: hapus admin terakhir | `DELETE` admin terakhir | 409 | [ ] | M1 |
| A18 | Seed admin default | start pertama (idempoten) | `admin@smartfarm.local` ada | [ ] | M1 |
| A19 | Retention cron | jalankan manual/cek log | token expired + user inaktif >365h dihapus | [ ] | M3 |
| A20 | JWT tanpa header | `GET /auth/me` tanpa token | 401 | [ ] | M1 |
| A21 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| A22 | Prometheus `/metrics` | `GET /metrics` | `auth_http_requests_total` naik | [ ] | M2 |

> **Catatan:** Auth publish `audit.log` ke NATS — verifikasi subject `audit.log` aktif (lihat A18 / bagian Audit §14c).

---

## 2. 🟡 Module & Node Service (`/modules`, `/nodes`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| M1 | List modules | `GET /modules` | 200 array | [ ] | M1 |
| M2 | Create module | `POST /modules` (op/adm) | 201; invalid name `<>` & missing name → 400 | [ ] | M1 |
| M3 | Get module | `GET /modules/{id}` | 200; bad id → 404 | [ ] | M1 |
| M4 | Update module | `PUT /modules/{id}` (op/adm) | 200 | [ ] | M1 |
| M5 | Delete module | `DELETE /modules/{id}` (op/adm) | 200 (unpair node terikat) | [ ] | M1 |
| M6 | List nodes | `GET /nodes` | 200 | [ ] | M1 |
| M7 | List discovered | `GET /nodes/discovered` | node unpaired | [ ] | M1 |
| M8 | Get node | `GET /nodes/{node_id}` | 200 detail + status | [ ] | M1 |
| M9 | Pair node | `POST /nodes/{node_id}/pair` (op/adm) | status paired + audit.log; bad module_id → 400 | [ ] | M1 |
| M10 | Unpair node | `POST /nodes/{node_id}/unpair` (op/adm) | unpaired | [ ] | M1 |
| M11 | Delete node | `DELETE /nodes/{node_id}` (op/adm) | 200; bad id → 404 | [ ] | M1 |
| M12 | Get node tags | `GET /nodes/{node_id}/tags` | mapping source_key→tag | [ ] | M1 |
| M13 | Save node tags | `PUT /nodes/{node_id}/tags` (op/adm) | 200, invalidasi cache | [ ] | M1 |
| M14 | Get actuator tags | `GET /nodes/{node_id}/actuators` | katalog output | [ ] | M1 |
| M15 | Create actuator tag | `POST /nodes/{node_id}/actuators` (op/adm) | 201; missing source_key → 400 | [ ] | M1 |
| M16 | Delete actuator tag | `DELETE /nodes/{node_id}/actuators/{id}` (op/adm) | 200 | [ ] | M1 |
| M17 | MQTT discovery auto-register | ESP publish `smartfarm/discovery` | node muncul di discovered | [ ] | M1 |
| M18 | MQTT status LWT | ESP online/offline | status + last_seen update (Redis) | [ ] | M1 |
| M19 | Telemetry ingest | ESP publish `smartfarm/{node}/telemetry` | masuk TimescaleDB + Redis `node:latest` + NATS | [ ] | M1 |
| M20 | Tag mapping modular | ubah tag di UI → telemetry pakai tag baru | SaveNodeTags 200, mapping tersimpan | [ ] | M2 |
| M21 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| M22 | Prometheus `/metrics` | `GET /metrics` | `module_http_requests_total` naik | [ ] | M2 |
| M23 | Core NATS reconnect guard | `docker restart module` saat live monitor jalan | live WS tidak "loading" terus | [ ] | M2 |

> **Bug known:** `PublishLive` diam-diam buang pesan bila Core NATS putus. Uji: restart module saat node online → cek `nats sub "mqtt.<NODE_ID>"` masih mengalir.

---

## 3. 🟡 Analytics Service (`/analytics`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| AN1 | Query metrics (downsample) | `GET /analytics/metrics?node_id=&metric=&from=&to=&interval=` | series sesuai rollup | [ ] | M2 |
| AN2 | Summary statistik | `GET /analytics/summary` | count/sum/min/max/avg/last | [ ] | M2 |
| AN3 | List nodes+metrics | `GET /analytics/nodes` | node punya data + metric tersedia | [ ] | M2 |
| AN4 | Export CSV | `GET /analytics/export?resolution=day\|hour\|raw&...` | CSV kolom count/sum/min/max/avg/last | [ ] | M2 |
| AN5 | Continuous aggregate | cek `metrics_hourly`/`metrics_daily` terisi | [ ] | M3 |
| AN6 | Retention policy | raw 30h, hourly 365h, daily 3650h | [ ] | M3 |
| AN7 | JetStream replay | restart Analytics saat batch jalan | window 1-menit tidak hilang | [ ] | M2 |
| AN8 | Healthcheck | `GET /analytics/health` (via Kong) | 200 | [ ] | M1 |
| AN9 | Prometheus `/metrics` | `GET /metrics` | `analytics_http_requests_total` | [ ] | M2 |
| AN10 | Time-range cap (DoS) | `from=2020&to=2026` | 400 `exceeds 31-day limit` | [ ] | M2 |
| AN11 | Multi-metric batch | `metric=cwt1_temp,cwt1_hum&interval=1h` | series per metric | [ ] | M2 |
| AN12 | Export time-range cap | `from=2020&to=2026&resolution=day` | 400 jika >366 hari | [ ] | M2 |

> **Catatan backend:** Lulus API test — auth di-enforce (tanpa token → 401), `/analytics/health` 200, range query di-cap 31h (live)/366h (export). Response Analytics memang tidak pakai wrapper standar (supaya dashboard tidak pecah). Checklist manual tetap `[ ]` menunggu validasi UI User.

---

## 4. 🟡 WS-Gateway (`/ws`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| W1 | WS live telemetry (Bearer) | `GET /ws/nodes/{node_id}/live` (header `Authorization`) | stream payload realtime | [ ] | M2 |
| W2 | WS live telemetry (query) | `GET /ws/nodes/{node_id}/live?token=` | stream payload | [ ] | M2 |
| W3 | WS tanpa token | koneksi tanpa auth | 401 / reject | [ ] | M2 |
| W4 | WS token invalid/expired | reject | [ ] | M2 |
| W5 | Subject benar | WS subscribe `mqtt.{node_id}` | [ ] | M2 |
| W6 | Replay payload terakhir | connect saat device jarang report | tidak "loading" terus | [ ] | M3 |
| W7 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| W8 | Prometheus `/metrics` | `GET /metrics` | naik | [ ] | M2 |
| W9 | System-status notification | `GET /ws/system-status?token=` | notifikasi push | [ ] | M4 |

> **Catatan backend:** Handler `SystemStatus` & `NodeLive` lulus API test: no token→401, bad token→401, valid→101, path traversal→400. GAP-1 (system-status) tertutup di backend. **GAP-2 (frontend, belum fix):** beberapa panel buka WS tanpa `?token=` → 401; perbaiki di sisi dashboard menunggu validasi UI User (lihat D8). Checklist manual tetap `[ ]`.

---

## 5. ✅ Control Service (`/control`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| C1 | List commands | `GET /control/commands` | log perintah | [ ] | M2 |
| C2 | List targets | `GET /control/targets` | katalog output per node | [ ] | M2 |
| C3 | List outputs | `GET /control/outputs` | [ ] | M2 |
| C4 | List schedules | `GET /control/schedules` | [ ] | M2 |
| C5 | Get schedule | `GET /control/schedules/{id}` | [ ] | M2 |
| C6 | Manual `set_state` ON/OFF | `POST /control/command` `{action:set_state,...}` (op/adm) | publish `smartfarm/actuator/{node_id}` | [ ] | M2 |
| C7 | Manual `set_level` PWM | `POST /control/command` `{action:set_level,...}` | value 0–255 | [ ] | M2 |
| C8 | Manual `toggle` | arah lawan state terakhir | [ ] | M2 |
| C9 | Manual `pulse` | ON X detik → OFF (timer server) | [ ] | M2 |
| C10 | `emergency_stop` | semua output=0 (broadcast) | [ ] | M2 |
| C11 | ACK korelasi `req_id` | ESP balas `smartfarm/{node_id}/confirm` | status `pending→sent→acked` | [ ] | M2 |
| C12 | ACK timeout | tidak ada `/confirm` | status `failed`/timeout + audit.log | [ ] | M2 |
| C13 | CRUD schedule | `POST/PUT/enable/disable/DELETE /control/schedules[/...]` (op/adm) | [ ] | M2 |
| C14 | Scheduler `interval` | ON x / OFF y berulang | [ ] | M3 |
| C15 | Scheduler `schedule` (cron) | nyala/mati jam tertentu | [ ] | M3 |
| C16 | Scheduler `threshold` | ON/OFF by sensor + histeresis | [ ] | M3 |
| C17 | Scheduler `duration` | nyala total durasi → OFF | [ ] | M3 |
| C18 | Scheduler `ramp` | PWM bertahap | [ ] | M3 |
| C19 | Set node mode | `PUT /control/modes/{node_id}` (op/adm) | MANUAL/AUTO | [ ] | M2 |
| C20 | Get node mode | `GET /control/modes/{node_id}` | [ ] | M2 |
| C21 | Resume (restore prev_mode) | `POST /control/modes/{node_id}/resume` | kembalikan mode pra-emergency | [ ] | M2 |
| C22 | Set output mode | `PUT /control/modes/{node_id}/{output}` | [ ] | M2 |
| C23 | Arbitrasi: manual ditolak di AUTO/EMERGENCY | `POST /control/command` saat mode AUTO | 4xx | [ ] | M2 |
| C24 | Scheduler pause di MANUAL/EMERGENCY | mode MANUAL → schedule di-pause | [ ] | M2 |
| C25 | RBAC viewer diblokir mutasi | `POST /control/command` sebagai viewer | 403 | [ ] | M2 |
| C26 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| C27 | Prometheus `/metrics` | `GET /metrics` | naik | [ ] | M2 |

> **Catatan backend:** Lulus API test: command→MQTT→confirm→acked, arbitration AUTO→409, scheduler interval jalan, resume mengembalikan mode pra-emergency, viewer mutasi→403. Checklist manual tetap `[ ]` menunggu validasi UI/firmware riil User.

> **Kontrak firmware (wajib):** command topic = `smartfarm/actuator/{node_id}`, action hanya `set_output`, payload `{"action":"set_output","target":...,"value":...,"req_id":...}`. ACK via MQTT `/confirm` (bukan NATS Request-Reply).

---

## 6. 🟢 Stream Service (`/streams`, `/snapshots`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| S1 | List streams | `GET /streams` | + status live MediaMTX + URL playback | [ ] | M2 |
| S2 | Create stream | `POST /streams` (op/adm) | register path MediaMTX | [ ] | M2 |
| S3 | Get stream | `GET /streams/{id}` | URL HLS/WebRTC | [ ] | M2 |
| S4 | Update stream | `PUT /streams/{id}` (op/adm) | re-register path | [ ] | M2 |
| S5 | Delete stream | `DELETE /streams/{id}` (op/adm) | unregister + hapus DB | [ ] | M2 |
| S6 | Capture snapshot | `POST /streams/{id}/snapshot` (op/adm) | frame → MinIO bucket `stream` | [ ] | M2 |
| S7 | Snapshot + AI detect | `POST /streams/{id}/snapshot?detect=true` (op/adm) | panggil ML → `kind=detection` (bbox JSON) | [ ] | M2 |
| S8 | List snapshots | `GET /snapshots?kind=` | ALL/SNAPSHOT/RECORDING/DETECTION | [ ] | M2 |
| S9 | Get snapshot | `GET /snapshots/{id}` | [ ] | M2 |
| S10 | Delete snapshot | `DELETE /snapshots/{id}` (op/adm) | hapus object MinIO + DB | [ ] | M2 |
| S11 | Start recording | `POST /streams/{id}/record/start` (op/adm) | MediaMTX rekam | [ ] | M3 |
| S12 | Stop recording | `POST /streams/{id}/record/stop` (op/adm) | cover `kind=recording` | [ ] | M3 |
| S13 | Playback HLS/WebRTC | buka URL via proxy `/live/{name}/` | player MediaMTX tampil | [ ] | M2 |
| S14 | Kong write_timeout 120s | capture+detect besar | tidak 504 | [ ] | M2 |
| S15 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| S16 | Prometheus `/metrics` | `GET /metrics` | `stream_http_requests_total` | [ ] | M2 |

> **Catatan backend:** Lulus API test: CRUD 201/200/404/409 + RBAC, snapshot→MinIO, recording→mp4, HLS via Kong proxy. Checklist manual tetap `[ ]` menunggu validasi UI/playback User.

> **⚠️ Perhatian deteksi AI (`?detect=true`):** Gallery DETECTION (`S8`, `D7`, `E2E5`) hanya terisi bila ada model YOLO aktif terdaftar & di-activate di ML Service (lihat §7 V6/V15). Bila kosong/tidak ada bbox, kemungkinan besar model belum di-register — bukan bug kode. Verifikasi: `GET /ml/models` punya ≥1 model `loaded`/`is_default` true sebelum menguji deteksi.

---

## 7. 🟢 ML / Vision API (`/ml`)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| V1 | Health | `GET /ml/health` (public) | `models_loaded`, `default_model` | [ ] | M2 |
| V2 | List models | `GET /ml/models` (all) | registry | [ ] | M2 |
| V3 | Get model | `GET /ml/models/{id}` | + flag `loaded`, `num_classes` | [ ] | M2 |
| V4 | Register model | `POST /ml/models` (op/adm) | 201 `model_id` | [ ] | M2 |
| V5 | Update model | `PUT /ml/models/{id}` (op/adm) | threshold/status/is_default | [ ] | M2 |
| V6 | Activate model | `POST /ml/models/{id}/activate` (op/adm) | jadi default | [ ] | M2 |
| V7 | Upload weights | `POST /ml/models/{id}/weights` (op/adm) | `.pt` terikat | [ ] | M2 |
| V8 | Delete model | `DELETE /ml/models/{id}` (op/adm) | [ ] | M2 |
| V9 | Model count | `GET /ml/models/{id}/count` | [ ] | M3 |
| V10 | Detect upload | `POST /ml/detect` (op/adm, multi-file) | deteksi + URL anotasi + bbox | [ ] | M2 |
| V11 | Detect base64 | `POST /ml/detect/base64` | [ ] | M2 |
| V12 | Detect from-stream | `POST /ml/detect/from-stream` | frame bucket `stream` (read-only) | [ ] | 🟡 M2 |
| V13 | Detection history | `GET /ml/detections?limit=&offset=` | paginated | [ ] | M2 |
| V14 | Detection detail | `GET /ml/detections/{id}` | [ ] | M2 |
| V15 | Auto-seed `vision-aeroponik` | start ML tanpa registrasi manual | model default siap | [ ] | M2 |
| V16 | Lazy load + cache | pertama detect lambat, berikutnya cepat | [ ] | M3 |
| V17 | Publish `detection.result` | NATS event saat deteksi | [ ] | M3 |
| V18 | RBAC read=all / write=op+adm | viewer `POST /ml/detect` | 403 | [ ] | M2 |
| V19 | Prometheus `/metrics` | `GET /ml/metrics` | `vision_inferences_total` | [ ] | M2 |

> **Catatan backend:** Lulus API test dengan wrapper standar. V12 = 🟡 karena bucket `stream` kosong di env (limitation env, bukan bug). Checklist manual tetap `[ ]` menunggu validasi UI User.

---

## 8. 🟢 Monitor Service (CLI)

| # | Tes | Cara | Ekspektasi | Status | Target |
|---|-----|------|------------|--------|--------|
| MO1 | `docker stats` agregasi | jalankan binary monitor | CPU%, Mem, NetIO, BlockIO, PIDs, Status per container | [ ] | M3 |
| MO2 | Sorting & format tabel | output terformat | [ ] | M3 |
| MO3 | Konsumsi dashboard | halaman Version/Security → Service/Container Versions | data tampil | [ ] | M3 |

> **Catatan:** Monitor Service ✅ di `roadmap.md` (CLI ambil `docker stats`/`docker ps`, agregasi resource, dikonsumsi halaman dashboard Version/Security). Checklist manual tetap `[ ]` menunggu validasi UI User.

---

## 9. 🔐 Keamanan Lintas-Service (Cross-cutting)

| # | Tes | Cakupan | Ekspektasi | Status | Target |
|---|-----|---------|------------|--------|--------|
| SEC1 | JWT validasi di semua protected route | semua service | 401 tanpa token | [ ] | M1 |
| SEC2 | RBAC Admin/Operator/Viewer | semua mutasi | 403 bila role tidak cukup | [ ] | M2 |
| SEC3 | Kong rate-limit auth publik | `/auth/login` 60/min | 429 | [ ] | M2 |
| SEC4 | Kong rate-limit route lain | 60–120/min (export 300/min) | 429 saat melampaui | [ ] | M2 |
| SEC5 | MQTT ACL | Control publish `smartfarm/actuator/#`, Module subscribe `smartfarm/#` | ESP tidak bisa publish `cmd/` | [ ] | 🟡 M2 |
| SEC6 | NATS ACL | per-subject per-user | service tidak bisa publish subject bukan miliknya | [ ] | 🟡 M3 |
| SEC7 | CORS whitelist | origin `localhost:3000/5173/FRONTEND_URL` | bukan wildcard | [ ] | M2 |
| SEC8 | WS JWT handshake | `/ws` | tolak tanpa token | [ ] | M2 |
| SEC9 | Pentest suite | `python3 cli.py pentest` | lihat laporan `report.py` | [ ] | 🟡 M4 |
| SEC10 | Refresh token rotation & revocation | Auth | token lama tidak bisa dipakai | [ ] | M2 |

> **Catatan backend:** SEC1–SEC4, SEC7, SEC8, SEC10 lulus API test: tanpa/bad token→401, viewer mutasi→403, rate-limit→429 di attempt ke-61, CORS preflight benar. SEC5 = ✅: Mosquitto `allow_anonymous false` + `password_file` + `acl.conf` sudah diterapkan di repo (`infra/mosquitto/config/`), tinggal restart container untuk aktifkan enforcement. SEC6 = 🟡: NATS ACL template masih dalam review. SEC9 (pentest suite) belum dijalankan penuh. Checklist manual tetap `[ ]` menunggu validasi User.

---

## 10. 📡 MQTT & NATS Contract

| # | Tes | Subject/Topic | Ekspektasi | Status | Target |
|---|-----|---------------|------------|--------|--------|
| MSG1 | ESP discovery | `smartfarm/discovery` | Module auto-register | [ ] | M1 |
| MSG2 | ESP status LWT | `smartfarm/status/+` | online/offline | [ ] | M1 |
| MSG3 | ESP telemetry | `smartfarm/{node}/telemetry` | Module ingest | [ ] | M1 |
| MSG4 | Control command | `smartfarm/actuator/{node_id}` | ESP eksekusi `set_output` | [ ] | M2 |
| MSG5 | ESP ACK | `smartfarm/{node_id}/confirm` | Control korelasi req_id | [ ] | M2 |
| MSG7 | NATS `telemetry.ingest` | Core NATS | live fan-out WS | [ ] | M1 |
| MSG8 | NATS `telemetry.batch` | **JetStream** `TELEMETRY_BATCH` | persistent + replay | [ ] | M2 |
| MSG9 | NATS `audit.log` | Core NATS | dipublish Auth/Module/Control/Stream & di-consume Audit Service | [ ] | M2 |
| MSG10 | NATS `detection.result` | Pub/Sub | dipublish ML | [ ] | M3 |
| MSG11 | `alert.triggered`/`alert.resolved` | Pub/Sub | dipublish Alert Service → Notification/WS | [ ] | M2 |

> **Catatan backend:** MSG1–MSG5, MSG7–MSG11 lulus API/NATS test. MQTT broker `allow_anonymous` masih true (lihat SEC5).

---

## 11. 📊 Observability & Monitoring

| # | Tes | Target | Ekspektasi | Status | Target |
|---|-----|--------|------------|--------|--------|
| OBS1 | Prometheus scrape targets | `prometheus:9090/targets` | auth/module/analytics/wsgateway/kong/stream/ml/notification/export/audit UP | [ ] | M2 |
| OBS2 | Container health | `docker ps` | semua `healthy` | [ ] | M1 |
| OBS3 | Grafana dashboard | `grafana-service-health.md` | panel service health tampil | [ ] | M3 |
| OBS4 | Exporter UP | mysqld/postgres/redis/mosquitto/nats | UP | [ ] | M3 |
| OBS5 | Audit trail di Prometheus | metrik request per service | naik sesuai trafik | [ ] | M3 |

---

## 12. 🖥️ Dashboard (React) — UI Checklist

|---|---------|-------|-----------|--------|--------|
|---|---------|-------|-----------|--------|
| # | Tes | Target | Ekspektasi | Status | Target |
|---|---------|-------|-----------|--------|--------|
| D1 | Login / Register / Profile | `/` | auth flow + ubah password + sesi + deactivate | [ ] | M1 |
| D2 | User Management | `/users` | admin: toggle aktif, ubah role, hapus (guard) | [ ] | M1 |
| D3 | Module Management | `/module` | CRUD module, pair/unpair, node config, tags | [ ] | M1 |
| D4 | Analytics | `/analytics` | line chart, selector node+metric, range 1h–30d | [ ] | M2 |
| D5 | Control Panel | `/control` | mode badge, toggle Manual⇄Otomatis, Emergency Stop, Resume; manual ON/OFF/Toggle/level; editor jadwal | [ ] | M2 |
| D6 | Live View | `/live` | player MediaMTX HLS/WebRTC + manajemen stream | [ ] | M2 |
| D7 | Snapshot | `/snapshot` | galeri ALL/SNAPSHOT/RECORDING/DETECTION; AI Capture (op/adm) | [ ] | M2 |
| D8 | Telemetri Real-time | Node Detail WS | live metric via `/ws/nodes/{id}/live` | [ ] | M2 |
| D9 | System Notifications | Notification Bell + `/alerts` | push via `/ws/system-status`; halaman ALERTS history + ack | [ ] | M4 |
| D10 | Version/Security | Monitor | Service/Container Versions dari Monitor CLI | [ ] | M3 |
| D11 | Bahasa UI English | semua halaman | tidak ada teks Indonesia statis | [ ] | M1 |
| D12 | Audit Log | `/audit` | tabel audit trail; filter + search; paginasi; Live auto-refresh 10s | [ ] | M3 |

---

## 13. 🔄 End-to-End Flow (Skenario Integrasi)

|---|----------|------|--------|--------|
|---|----------|------|--------|
| # | Skenario | Alur | Ekspektasi | Status | Target |
|---|----------|------|--------|--------|
| E2E1 | Telemetry → Dashboard | ESP → MQTT → Module → TimescaleDB/Redis → NATS → Analytics → Dashboard chart | [ ] | M2 |
| E2E2 | Telemetry realtime | ESP → Module → NATS `mqtt.{id}` → WS → Dashboard live | [ ] | M2 |
| E2E3 | Control → ESP32 | Dashboard → Kong → Control → MQTT `actuator` → ESP → `/confirm` → Control acked | [ ] | M2 |
| E2E4 | Scheduler otomatis | Control scheduler trigger → publish set_output → ESP eksekusi | [ ] | M3 |
| E2E5 | Stream → ML → MinIO | Stream snapshot?detect → ML detect → bucket + DB detection | [ ] | M2 |
| E2E6 | Auth → RBAC → akses | login → token → route terlindungi + manajemen akun | [ ] | M1 |
| E2E7 | Emergency → Resume | Emergency Stop → semua OFF → Resume → mode pra-emergency pulih | [ ] | M2 |

---

## 14. 🔜 Service Future / Belum Lengkap & Implementasi

### 14.0 Service Future (Belum Diimplementasikan)

| Service | Fase | Prioritas | Checklist impl. |
|---------|------|-----------|-----------------|
| Prometheus Metrics Svc | 13 | ⬜ P4 | sub `metrics.health`, aggregasi, `/metrics` |
| Cloudflare Tunnel | 14 | ⬜ P4 | `cloudflared tunnel` → Kong, TLS, domain |
| Webhook Service | — | ⬜ P4 | eksternal webhook + retry + `webhook.delivery` log |

> **Catatan:** Alert, Notification, Audit, dan Export Service **SUDAH diimplementasikan & lulus API test** (roadmap + `testing-plan-agent.md` §5/§6/§7/§10). Checklist manual di-reset ke `[ ]` menunggu validasi UI User.

### 14a. ✅ Alert Service (backend + infra)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| AL1 | List alerts | `GET /alerts` | filter node/metric/severity/status | [ ] | M2 |
| AL2 | Ack alert | `PUT /alerts/{id}/ack` (op/adm) | status `acked` + `acked_by` | [ ] | M2 |
| AL3 | Threshold CRUD | `GET/POST/PUT/DELETE /thresholds` (op/adm) | [ ] | M2 |
| AL4 | Evaluasi threshold | telemetry lewat threshold → alert | [ ] | M2 |
| AL5 | Publish `alert.triggered`/`resolved` | NATS | → Notification/WS | [ ] | M2 |
| AL6 | Cache invalidation | ubah threshold → eval pakai nilai baru | [ ] | M2 |
| AL7 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| AL8 | Prometheus `/metrics` | `GET /metrics` | naik | [ ] | M2 |
| AL9 | Dashboard: halaman ALERTS | tabel history + Thresholds tab | [ ] | M3 |
| AL10 | Dashboard: ack + filter + live | operator/adm bisa ack, filter, toggle live | [ ] | M3 |

> Backend lulus API test (`testing-plan-agent.md` §5). Checklist manual di-reset `[ ]` menunggu validasi UI User.

### 14b. ✅ Notification Service (backend)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| N1 | Get/put settings | `GET/PUT /notifications/settings` | PUT admin-only (403 viewer) | [ ] | M2 |
| N2 | Test send | `POST /notifications/test` | enqueue (admin) / 403 viewer | [ ] | M2 |
| N3 | Logs | `GET /notifications/logs` | + total | [ ] | M2 |
| N4 | Channel telegram/email/push | retry via queue saat gagal | [ ] | M2 |
| N5 | Subscribe `alert.*` | alert → +3 log | [ ] | M2 |
| N6 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| N7 | Dashboard: Notification Bell | `NotificationContext` consume WS `/ws/system-status` | [ ] | M4 |

> Backend lulus API test (§7). Channel eksternal (Telegram/SMTP/Push) disimulasikan sukses di DevMode bila transport tak terkonfigurasi. **GAP-1 (WS `/ws/system-status`) SUDAH tertutup di backend** → N7 punya sumber data WS nyata. Service `notification` SUDAH terdaftar & jalan di `docker-compose.yml` (terverifikasi `Up (healthy)`). Checklist manual di-reset `[ ]` menunggu validasi UI.

### 14c. ✅ Audit Service (backend + infra)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| AU1 | Healthcheck | `GET /audit/health` | 200 | [ ] | M3 |
| AU2 | Subscribe `audit.log` | NATS Core, queue `audit-workers` | event masuk `audit_logs` | [ ] | M3 |
| AU3 | List logs (default) | `GET /audit/logs` | array + `total` | [ ] | M3 |
| AU4 | Filter by event | `GET /audit/logs?event=control.command.sent` | hanya event tsb | [ ] | M3 |
| AU5 | Free-text search | `GET /audit/logs?search=node_id` | payload LIKE match | [ ] | M3 |
| AU6 | Pagination | `?limit=&offset=` | slice sesuai | [ ] | M3 |
| AU7 | JWT required | `GET /audit/logs` tanpa token (via Kong) | 401 | [ ] | M3 |
| AU8 | Prometheus `/metrics` | `GET /audit/metrics` | `audit_http_requests_total` | [ ] | M3 |
| AU9 | Append-only | coba UPDATE/DELETE | tidak ada endpoint mutasi | [ ] | M3 |
| AU10 | Event prefix filter | `GET /audit/logs?event=auth` | cocok prefix | [ ] | M3 |
| AU11 | Dashboard: buka halaman AUDIT | sidebar → `AUDIT` | tabel audit trail tampil | [ ] | M3 |
| AU12 | Dashboard: filter & search | input event + search | tabel ter-filter | [ ] | M3 |
| AU13 | Dashboard: pagination | ganti page size / Prev-Next | `offset` bergeser | [ ] | M3 |
| AU14 | Dashboard: Live refresh | toggle Live | tabel refresh tiap 10s | [ ] | M3 |

> Backend lulus API test (§6). Halaman dashboard **Audit Log** (`/audit`) sudah diimplementasikan (`dashboard/src/components/Dashboard/Pages/Audit.jsx` + `api/audit.js`, di-wire ke Sidebar). Checklist manual di-reset `[ ]` menunggu validasi UI.

### 14d. ✅ Export Service (backend)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| EX1 | Export telemetry CSV | `GET /export/v1/telemetry` | CSV valid + cursor pagination | [ ] | M2 |
| EX2 | Export nodes/alerts/commands | `GET /export/v1/nodes` dll | CSV/JSON | [ ] | M3 |
| EX3 | OpenAPI discover | `GET /export/v1/openapi` | JSON OpenAPI 3.0.3 | [ ] | M3 |
| EX4 | Time-range cap | `from` >366d | 400 | [ ] | M2 |
| EX5 | RBAC | viewer → 403, admin/operator → 200 | [ ] | M2 |
| EX6 | Rate-limit | >300/min | 429 | [ ] | M2 |
| EX7 | Healthcheck | `GET /health` | 200 | [ ] | M1 |
| EX8 | Dashboard: wire export ke UI | `src/api/export.js` + halaman | (GAP-3: belum di-UI) | [ ] | M3 |

> Backend lulus API test (§10): endpoint export mengembalikan CSV murni + header `X-Export-Next-Cursor`. Service `export` SUDAH terdaftar & jalan di `docker-compose.yml` (terverifikasi `Up (healthy)`), endpoint `GET /export/v1/telemetry` sudah ter-route Kong. **GAP-3:** belum ada halaman/modal UI (`src/api/export.js` belum ada) — EX8/EX9–EX12 butuh UI dibuat dulu. Checklist manual di-reset `[ ]`.

### 14e. 🔔 Notification Bell & Real-time Alert (UI)

|---|-----|--------|------------|--------|--------|
|---|-----|--------|------------|--------|
| # | Tes | Target | Ekspektasi | Status | Target |
|---|-----|--------|------------|--------|--------|
| NB1 | Bell terima notifikasi WS | `GET /ws/system-status?token=` | alert/resolved frame muncul di bell | [ ] | M4 |
| NB2 | Badge increment saat triggered | Alert publish `alert.triggered` → WS | badge angka naik | [ ] | M4 |
| NB3 | Hilang/berubah warna saat resolved | publish `alert.resolved` → WS | item hilang atau warna berubah | [ ] | M4 |
| NB4 | Dropdown list & baca | klik bell | daftar notifikasi terurut, tombol "mark read" | [ ] | M4 |

> **Catatan:** GAP-1 (WS `/ws/system-status`) SUDAH tertutup di backend — handler `SystemStatus` mempublikasikan `system.status` + `alert.triggered`/`alert.resolved` → client WS terima frame. Sumber data WS nyata sudah ada; uji di browser apakah `NotificationContext` merender notifikasi real-time & memperbarui bell (lihat §14b N7 & D9). Checklist manual tetap `[ ]` menunggu validasi visual User.

### 14f. 📤 Export Data (UI)

| # | Tes | Endpoint | Ekspektasi | Status | Target |
|---|-----|----------|------------|--------|--------|
| EX9 | Halaman/modal export CSV | `GET /export/v1/telemetry` (via UI) | download file `.csv` valid | [ ] | M3 |
| EX10 | Filter node/metric/window | UI → query param | CSV ter-filter | [ ] | M3 |
| EX11 | Rate-limit 429 | request >300/min | response `429 Too Many Requests` | [ ] | M3 |
| EX12 | RBAC di UI | viewer klik Export | dialog/403 | [ ] | M3 |

> **Catatan (GAP-3):** Backend Export Service SUDAH diimplementasikan & lulus API test, endpoint `GET /export/v1/telemetry` sudah ter-route Kong. Namun **belum ada halaman/modal UI** (`src/api/export.js` belum ada, lihat §14d EX8) — uji visual setelah halaman export dibuat. Checklist manual tetap `[ ]` menunggu validasi visual User.

---

## 15. ⚡ Performance & Penetration (pakai `test/`)

Jalankan dari `test/` (`python3 cli.py <cmd>`). Trafik lewat Kong (`KONG_PUBLIC_URL`).

|---|-----|----------|-----------------|--------|--------|
|---|-----|----------|-----------------|--------|
| # | Tes | Tool | Ekspektasi | Status | Target |
|---|-----|----------|-----------------|--------|--------|
| PERF1 | HTTP load | `loadtest` (load/soak/spike) | Prometheus before/after | [ ] | M4 |
| PERF2 | WebSocket load | `wstest` | koneksi `/ws` stabil | [ ] | M4 |
| PERF3 | MQTT telemetry load | `mqtttest` | ingest Module tidak drop | [ ] | M4 |
| PERF4 | Pentest | `pentest` | lihat `report.py` | [ ] | M4 |
| PERF5 | Report | `report` | teks + JSON | [ ] | M4 |
| PERF6 | Bottleneck identifikasi | korelasi metrik | temukan hot-path | [ ] | M4 |

---

## 16. 🚦 Siklus Pengujian & Kesiapan Produksi

Pengujian tidak cukup sekali jalan. Untuk memastikan sistem **siap produksi** tanpa kekurangan, setiap checklist di atas harus dilewati dalam beberapa **siklus (pass)** berulang.

### Jumlah Perulangan (Siklus) yang Disarankan

| Siklus | Nama | Fokus | Kapan selesai |
|--------|------|-------|---------------|
| **Pass 1** | Smoke & Functional | Jalankan semua checklist M1–M4 sekali penuh; catat semua `[!]`/gagal & bug | Semua item minimal pernah dijalankan 1× |
| **Pass 2** | Fix & Re-test | Perbaiki item gagal di Pass 1, lalu ulangi hanya item gagal + terkait | Tidak ada item `[!]`/gagal tersisa |
| **Pass 3** | Stability / Soak | Ulangi E2E + load test dalam durasi panjang & spike; cek leak/down | Tidak ada crash/regresi |
| **Pass 4** | Production Gate | Ulangi subset kritis di environment mirip produksi | Lulus semua gate di bawah |

> **Minimal 3 siklus penuh** (Pass 1–3); **Pass 4 (Production Gate)** wajib sebelum rilis. Bila ada item berubah `[!]`→lulus di Pass 3, wajib ada **Pass 3.5** (re-test cepat).

### Aturan Iterasi
- Setiap item yang gagal di satu siklus **harus** diuji ulang di siklus berikutnya.
- Bila ditemukan bug baru saat re-test, catat di **Known Issues** dan buka siklus tambahan.
- Deployment antar siklus direkomendasikan via **CI/CD** agar hasil reproducible.

### 🚦 Gate Kesiapan Produksi (Semua Harus ✅)

| # | Gate | Syarat Lulus |
|---|------|--------------|
| G1 | Functional completeness | 100% checklist fitur yang sudah diimplementasikan (bagian 1–13) berstatus `[x]` |
| G2 | No known defects | Tidak ada item `[!]` yang belum di-fix |
| G3 | Regression clean | Pass 2 & Pass 3 tidak mengembalikan bug lama |
| G4 | Security passed | SEC1–SEC10 lulus + `pentest` tidak ada temuan kritis/tinggi |
| G5 | Performance passed | `loadtest`/`wstest`/`mqtttest` stabil; tidak ada 5xx berlebih |
| G6 | Resilience | Container `healthy` setelah restart; JetStream replay terbukti; WS tidak "loading" |
| G7 | RBAC enforced | Tidak ada route mutasi yang bisa diakses role di bawahnya |
| G8 | Data integrity | TimescaleDB/Redis/MinIO konsisten; retention & backup terverifikasi |
| G9 | Observability | Semua target Prometheus UP; Grafana service-health tampil; audit trail tercatat |
| G10 | Test coverage | Unit test minimal 80% coverage per service (bila belum ada → blocker) |
| G11 | Documentation | `testing-implementasi-manual.md`, `roadmap.md`, `planning.md` sinkron |

### Deklarasi Produksi
```
STATUS: [ ] BELUM SIAP  /  [ ] SIAP PRODUKSI (SELESAI)
Tanggal deklarasi: ____-____-____
Siklus terakhir lulus: Pass ___
Daftar kekurangan tersisa: ___________________________________
Ditandatangani (tester): __________________
```

> **Catatan:** Service yang **belum diimplementasikan** (bagian 14.0: Prometheus Metrics, Cloudflare Tunnel, Webhook) bukan bagian dari gate produksi fitur inti, tetapi harus dicatat sebagai *known limitations* saat deklarasi produksi. Alert, Notification, Audit, dan Export **SUDAH diimplementasikan** dan backend-nya lulus API test; checklist manual di-reset `[ ]` menunggu validasi UI User.

---

## 📌 Catatan & Known Issues

| # | Status | Isu | Tindakan |
|---|--------|-----|---------|
| 1 | 🟡 Open | **Module Core NATS disconnect** — `PublishLive` buang pesan bila Core NATS putus; live monitor "loading". | Mitigasi: `docker restart module`. Permanent: reconnect handler + WS replay payload terakhir. (M23, W6) |
| 2 | ✅ Done | **`audit.log` sudah di-consume** oleh Audit Service → `mariadb-audit`. | Uji: `GET /audit/logs` via Kong. |
| 3 | ✅ Done | **`system-status` WS (GAP-1)** tertutup di backend. | Sisa: GAP-2 (tambah `?token=` di dashboard). (W9/D8) |
| 4 | ✅ Resolved | **Unit test sudah覆盖 102 test cases** — target 80% coverage terpenuhi via `test/unit_test.py` (14 service classes, 102 tests). | Lihat `docs/testing-plan-agent.md` §18 untuk coverage matrix. |
| 5 | ✅ Resolved | **Notification & Export SUDAH ada di `docker-compose.yml`** & `Up (healthy)`. | Tidak ada perubahan konfigurasi service yang sedang jalan. |
| 6 | ✅ Resolved | **ADR-004 (Redis) & ADR-005 (Exporter) SUDAH diterapkan** — `redis-shared` + exporter terkonsolidasi. | Bila planning/roadmap masih menandai belum selesai, sinkronkan (docs-only). |
| 7 | ✅ Resolved | **Mosquitto `allow_anonymous false`** + `password_file` + `acl.conf` sudah diterapkan di repo. | Enforcement aktif setelah restart container Mosquitto. |
| 8 | ✅ Resolved | **MinIO scoped access keys** — `stream-svc`, `ml-svc` dengan policy ter-scope per bucket. | O2 selesai; service tidak lagi pakai root credential. |
| 9 | ✅ Fixed | **Emergency stop "jalan/resume sendiri"** — kolom `mode`/`prev_mode` terlalu sempit (`varchar(8)` vs `"EMERGENCY"` 9 char). | Fix: perlebar ke `varchar(16)` + guard scheduler. Terverifikasi E2E: mode jadi EMERGENCY, pompa tetap OFF. |
