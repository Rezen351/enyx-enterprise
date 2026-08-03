# 🧪 Dokumentasi Pengujian Implementasi — IoT-Modular-Microservice

> **Versi:** 1.3  
> **Tanggal:** 2026-07-31  
> **Tujuan:** Panduan pengujian backend terotomatisasi (via folder `test/`) dan checklist pengujian visual UI/UX manual (via Dashboard React).  
> **Sumber Acuan:** `roadmap.md`, `planning.md`, `test/unit_test.py`, `test/run_all_tests.py`.  
> **Bahasa:** UI & API Response = **English**, Dokumentasi & Panduan = **Bahasa Indonesia**.

---

## 📋 Daftar Isi

| # | Topik / Domain | Fokus Utama Pengujian |
|---|----------------|-----------------------|
| 1 | 🛠️ **Panduan Eksekusi Testing** | Perintah terminal & petunjuk menjalankan program test |
| 2 | 🤖 **Ringkasan Test Coverage** | Katalog 102 test cases otomatis di `test/unit_test.py` |
| 3 | 🔴 **Auth Service** | Autentikasi, JWT, RBAC, Profil, User & Role Management |
| 4 | 🟡 **Module & Node Service** | Ingest telemetry, Discovery, Pairing, Mapping Tag & Actuator |
| 5 | 🟡 **Analytics Service** | Rollup metrik, Summary, Downsampling, Filter waktu |
| 6 | 🟡 **WS-Gateway** | Stream telemetri realtime & Notifikasi sistem |
| 7 | ✅ **Control Service** | Perintah manual (ON/OFF/PWM), Arbitrasi mode, Scheduling |
| 8 | 🟢 **Stream Service** | Live HLS/WebRTC streaming, Snapshot, Recording, Storage |
| 9 | 🟢 **ML / Vision API** | Deteksi AI, Bounding box, Manajemen Model & Upload weights |
| 10 | 🔔 **Alert, Audit, Notification, Export** | Ambang batas, Audit trail, Notification Bell, Ekspor CSV |
| 11 | 🔐 **Keamanan & RBAC** | Guard otorisasi, Rate limiting, CORS, Revokasi token |
| 12 | 🔄 **End-to-End (E2E) Verification** | Alur integrasi utuh dari Device/API ke Dashboard UI |
| 13 | ⚡ **Performance & Chaos Audit** | Load test, Throughput breakpoint, & Service resilience |
| 14 | 🚦 **Siklus & Kesiapan Produksi** | Production gate & Kriteria rilis |

---

## 🛠️ 1. Panduan Eksekusi Program Testing (Terminal & Test Tools)

Seluruh logika backend, koneksi API, autentikasi, validasi data, event streaming, dan error handling **telah disediakan program test otomatisnya** di folder `test/`. Pengguna cukup menjalankan perintah terminal di bawah ini untuk memverifikasi backend, kemudian menguji tampilan visual UI/UX pada Dashboard React secara manual.

### 1.1 Persyaratan Pra-Pengujian
- Pastikan seluruh container microservice berjalan dan berstatus `healthy`:
  ```bash
  docker compose up -d
  docker compose ps
  ```

### 1.2 Perintah Eksekusi Master Test Suite

| Tujuan Pengujian | Perintah Terminal | Deskripsi Output |
|------------------|-------------------|------------------|
| **Jalankan Seluruh Suite (Master)** | `python3 test/run_all_tests.py` | Mengeksekusi Unit Test (102 cases), Stress Test, Chaos Test, serta membuat chart visual di `test/results/`. |
| **Backend Unit & Feature Test Only** | `python3 test/unit_test.py` | Menguji seluruh REST endpoint & WebSocket handshake (102 test cases). |
| **Stress & Throughput Test** | `python3 test/stress_test.py` | Menguji throughput API Gateway & titik balik beban. |
| **Resilience & Chaos Test** | `python3 test/resilience_test.py` | Menguji pemulihan otomatis service saat terjadi kegagalan container/koneksi. |

### 1.3 Perintah Eksekusi Spesifik per Service Test Class
Jika Anda ingin menguji logika backend untuk service tertentu sebelum melakukan verifikasi visual UI:

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

### 1.4 Verifikasi API Manual via cURL (Opsional)
Untuk mengambil token atau memeriksa endpoint langsung dari terminal:
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

## 🤖 2. Ringkasan Automated Test Coverage (`test/unit_test.py`)

Logika backend dan koneksi API untuk seluruh domain di bawah ini telah diuji secara otomatis (total **106 test cases**). Laporan pengujian backend beserta payload HTTP tersimpan di `test/results/05_unit_test_payloads.json` dan `test/results/05_unit_test_payloads.md`.

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

## 🔴 3. Auth Service (`/auth`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestAuthService`  
> **Status Logika Backend:** ✅ 100% Lulus (13 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| A1 | Halaman Login | Buka `/` saat belum login | Form login tampil rapi, input email/username & password, tombol submit aktif. | [V] [ ] [ ] |
| A2 | Error Form Login | Input password salah & submit | Notification banner / toast error berbahasa Inggris tampil membalas kredensial salah. | [V] [ ] [ ] |
| A3 | Respon Sukses Login | Input kredensial valid & submit | Redirect mulus ke Dashboard utama (`/dashboard`), profil pengguna tampil di header. | [V] [ ] [ ] |
| A4 | Form Register | Buka halaman register | Form pendaftaran user baru tampil responsif dengan opsi penentuan role. | [V] [ ] [ ] |
| A5 | User Management UI | Buka menu `/users` (sebagai Admin) | Tabel daftar pengguna tampil lengkap dengan status (active/inactive), tombol edit & delete. | [V] [ ] [ ] |
| A6 | Guard Hapus Akun Admin | Coba hapus akun admin terakhir di UI | Modal konfirmasi menolak / disable tombol hapus untuk mencegah hilangnya admin. | [V] [ ] [ ] |
| A7 | Halaman Profil & Sesi | Buka menu `/profile` | Tampil detail akun, form ubah password, dan daftar sesi aktif (IP & User-Agent). | [V] [ ] [ ] |

---

## 🟡 4. Module & Node Service (`/modules`, `/nodes`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestModuleService`  
> **Status Logika Backend:** ✅ 100% Lulus (16 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| M1 | Daftar Modul & Node | Buka menu `/module` | Grid/tabel modul tampil rapi, menampilkan node terikat, status online/offline badge. | [V] [ ] [ ] |
| M2 | Modal Tambah Modul | Klik "Add Module" | Modal form muncul, input nama & deskripsi modul, validasi input berjalan lancar. | [V] [ ] [ ] |
| M3 | Tab Discovered Nodes | Buka tab "Discovered Nodes" | Daftar node baru (unpaired) yang terdeteksi via MQTT tampil dengan tombol "Pair". | [V] [ ] [ ] |
| M4 | Proses Pairing Node | Klik "Pair" pada node terdeteksi | Modal dialog memilih target modul, setelah submit status node berubah menjadi paired. | [V] [ ] [ ] |
| M5 | Konfigurasi Tag Sensor | Buka detail node -> Tab "Sensor Tags" | Pemetaan tag sensor (misal `temp` -> `cwt1_temp`) tampil terstruktur dan dapat diperbarui. | [V] [ ] [ ] |
| M6 | Pemetaan Aktuator | Buka detail node -> Tab "Actuators" | Catalog output aktuator (relay/pump) tampil dengan nama label yang intuitif. | [V] [ ] [ ] |

---

## 🟡 5. Analytics Service (`/analytics`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestAnalyticsService`  
> **Status Logika Backend:** ✅ 100% Lulus (6 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| AN1 | Visualisasi Chart | Buka menu `/analytics` | Line chart (Recharts/Chart.js) merender grafik data sensor secara kontinu & halus. | [V] [ ] [ ] |
| AN2 | Multi-Metric Selector | Pilih beberapa metrik (mis. Suhu & Kelembaban) | Chart menampilkan multiple series dengan warna legend yang kontras dan jelas. | [V] [ ] [ ] |
| AN3 | Filter Rentang Waktu | Pilih preset waktu (1h, 24h, 7d, 30d) | Chart merender ulang data sesuai rentang waktu tanpa lag atau crash visual. | [ ] [ ] [ ] |
| AN4 | Cards Summary Statistik | Amati card Ringkasan di atas chart | Nilai Average, Min, Max, dan Total Data Count terupdate presisi sesuai filter. | [V] [ ] [ ] |

---

## 🟡 6. WS-Gateway (`/ws`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestWSGateway`  
> **Status Logika Backend:** ✅ 100% Lulus (2 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| W1 | Indicator Telemetri Live | Buka detail node / Dashboard Utama | Indicator status WebSocket (mis. "Live Data Connected") berwarna hijau. | [V] [ ] [ ] |
| W2 | Update Nilai Realtime | Amati card telemetri sensor | Angka sensor diperbarui secara instan tanpa perlu melakukan refresh halaman. | [V] [ ] [ ] |
| W3 | Reconnection Feedback | Matikan koneksi internet sebentar lalu nyalakan | UI menampilkan notifikasi "Reconnecting..." dan pulih otomatis setelah online. | [ ] [ ] [ ] |

---

## ✅ 7. Control Service (`/control`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestControlService`  
> **Status Logika Backend:** ✅ 100% Lulus (15 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| C1 | Panel Kontrol Aktuator | Buka menu `/control` | Toggle switch ON/OFF aktuator (relay/pompa) dan slider PWM tampil responsif. | [V] [ ] [ ] |
| C2 | Switching Mode System | Klik toggle mode MANUAL / AUTO | Badge mode berubah warna (mis. Kuning/Biru), tombol manual di-disable saat AUTO. | [V] [ ] [ ] |
| C3 | Visual Emergency Stop | Klik tombol "EMERGENCY STOP" | UI menampilkan banner bahaya merah mencolok, seluruh toggle aktuator terkunci OFF. | [V] [ ] [ ] |
| C4 | Tombol Resume Mode | Klik tombol "Resume System" | Mode pulih dari EMERGENCY ke mode sebelumnya, status indikator kembali normal. | [V] [ ] [ ] |
| C5 | Editor Jadwal (Scheduler) | Buka tab "Schedules" -> Klik "Create" | Modal penjelas jadwal (cron/interval/duration) tampil lengkap dengan preset input. | [V] [ ] [ ] |

---

## 🟢 8. Stream Service (`/streams`, `/snapshots`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestStreamService`  
> **Status Logika Backend:** ✅ 100% Lulus (12 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| S1 | Video Player HLS/WebRTC | Buka menu `/live` | Player video (MediaMTX) memutar feed kamera secara lancar tanpa stuttering. | [ ] [ ] [ ] |
| S2 | Tombol Capture Snapshot | Klik "Take Snapshot" pada video player | Loading indicator muncul sejenak, lalu toast notifikasi sukses snapshot tampil. | [ ] [ ] [ ] |
| S3 | Galeri Snapshot | Buka menu `/snapshot` | Grid foto snapshot tampil teratur dengan filter kategori (ALL, SNAPSHOT, DETECTION). | [ ] [ ] [ ] |
| S4 | Modal View Image | Klik salah satu gambar snapshot | Modal gambar membesar (lightbox) menampilkan metadata waktu dan tombol hapus. | [ ] [ ] [ ] |

---

## 🟢 9. ML / Vision API (`/ml`)

> **Backend Automated Test Command:** `python3 -m unittest test.unit_test.TestMLService`  
> **Status Logika Backend:** ✅ 100% Lulus (10 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| V1 | Registry Model AI | Buka menu `/ml` / AI Management | Tabel model YOLO tampil dengan status active badge, confidence threshold, & class list. | [ ] [ ] [ ] |
| V2 | Upload Weights Model | Klik "Upload Model (.pt)" | File picker menerima file `.pt`, progress bar upload berjalan hingga selesai. | [ ] [ ] [ ] |
| V3 | Bounding Box Overlay | Lakukan AI Detect pada gambar snapshot | Gambar hasil deteksi menampilkan kotak bounding box berwarna beserta label objek. | [ ] [ ] [ ] |

---

## 🔔 10. Alert, Audit, Notification, & Export Services

> **Backend Automated Test Commands:**  
> - Alert: `python3 -m unittest test.unit_test.TestAlertService`  
> - Audit: `python3 -m unittest test.unit_test.TestAuditService`  
> - Notification: `python3 -m unittest test.unit_test.TestNotificationService`  
> - Export: `python3 -m unittest test.unit_test.TestExportService`  
> **Status Logika Backend:** ✅ 100% Lulus (20 Test Cases)

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| AL1 | Halaman History Alert | Buka menu `/alerts` | Tabel peringatan tampil dengan badge tingkat keparahan (CRITICAL/WARNING/INFO). | [ ] [ ] [ ] |
| AL2 | Tombol Acknowledge Alert | Klik "Acknowledge" pada baris alert | Status alert berubah dari UNACKED menjadi ACKED, mencatat nama operator. | [ ] [ ] [ ] |
| AU1 | Tabel Audit Trail | Buka menu `/audit` | Audit log menampilkan kronologi aktivitas user/sistem lengkap dengan pencarian & filter. | [ ] [ ] [ ] |
| N1 | Notification Bell | Klik ikon Lonceng Notifikasi di Header | Dropdown notifikasi realtime muncul menunjukkan alert terbaru yang terpicu. | [ ] [ ] [ ] |
| EX1 | Tombol Download CSV | Buka menu Export / Analytics -> "Export CSV" | File `.csv` terdownload otomatis melalui browser tanpa error CORS. | [ ] [ ] [ ] |

---

## 🔐 11. Keamanan & RBAC (Cross-cutting)

> **Backend Automated Test Command:** `python3 test/unit_test.py` (Mencakup pengujian 401 Unauthorized, 403 Forbidden, 429 Rate Limit, dan JWT Verification)  
> **Status Logika Backend:** ✅ 100% Lulus

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario UI/UX | Langkah Visual di Dashboard React | Ekspektasi Tampilan UI | Status (Pass 1 / 2 / 3) |
|---|----------------|----------------------------------|------------------------|-------------------------|
| SEC1 | Proteksi Route Unauthenticated | Hapus token / logout, lalu akses `/control` langsung | Browser otomatis me-redirect paksa pengguna kembali ke halaman Login (`/`). | [] [ ] [ ] |
| SEC2 | Restriksi Role Viewer | Login sebagai akun ber-role Viewer | Elemen UI tombol mutasi (seperti Delete, Create, Emergency Stop) di-hide / di-disable. | [ ] [ ] [ ] |
| SEC3 | Penanganan Session Expired | Biarkan token kadaluarsa lalu klik menu | Sistem menampilkan toast "Session expired, please login again" dan redirect ke `/`. | [ ] [ ] [ ] |

---

## 🔄 12. End-to-End (E2E) Verification

> **Backend Automated Test Command:** `python3 test/run_all_tests.py`  
> **Status Logika Backend:** ✅ Integrasi terverifikasi otomatis via NATS & MQTT Mock Runner

### Checklist Pengujian Visual UI/UX (Manual oleh User)

| # | Skenario E2E Flow | Langkah Alur Pengujian Visual | Ekspektasi Hasil Akhir UI | Status (Pass 1 / 2 / 3) |
|---|-------------------|------------------------------|---------------------------|-------------------------|
| E2E1 | Device Telemetry to Chart | Nyalakan simulator sensor / ESP32 | Data telemetry mengalir dari MQTT -> ditampilkan di Chart Analytics real-time. | [ ] [ ] [ ] |
| E2E2 | Manual Control to Actuator | Klik ON pada toggle aktuator di Dashboard | Perintah terkirim via MQTT -> status aktuator di UI berubah menjadi active. | [ ] [ ] [ ] |
| E2E3 | Camera to AI Detection | Ambil snapshot dari live video -> trigger AI | Hasil deteksi tanaman/objek muncul di galeri snapshot dengan bbox visual. | [ ] [ ] [ ] |

---

## ⚡ 13. Performance & Chaos Audit

Pengujian performa throughput dan ketahanan sistem (chaos resilience) dapat dieksekusi secara otomatis dari terminal. Hasil pengujian akan menghasilkan grafik analisis beresolusi tinggi di folder `test/results/`.

```bash
# 1. Jalankan pengujian master test suite (Unit & Feature Test Suite)
python3 test/run_all_tests.py

# 2. Jalankan pengujian batas beban throughput (Breakpoint Stress Test)
python3 test/stress_test.py

# 3. Jalankan pengujian ketahanan & pemulihan keruntuhan (Chaos Resilience Audit)
python3 test/resilience_test.py
```

### 📋 Checklist Eksekusi Program Pengujian

- [ ] [ ] [ ] **Pengujian 1 — Master Test Suite & Feature Verification:** Eksekusi `python3 test/run_all_tests.py` untuk menguji seluruh unit & feature test backend (107 test cases) serta menghasilkan ringkasan visual `01_unit_test_summary.png` & `04_overall_system_dashboard.png`.
- [ ] [ ] [ ] **Pengujian 2 — Breakpoint Stress & Throughput Capacity Test:** Eksekusi `python3 test/stress_test.py` untuk mengukur batas throughput RPS & latensi sistem serta menghasilkan grafik `02_stress_test_throughput.png`.
- [ ] [ ] [ ] **Pengujian 3 — Chaos Resilience & Self-Healing Audit:** Eksekusi `python3 test/resilience_test.py` untuk menguji pemulihan otomatis service saat terjadi keruntuhan container/NATS serta menghasilkan grafik `03_resilience_chaos_audit.png`.

### Grafik Artefak yang Dihasilkan (`test/results/`)
1. `01_unit_test_summary.png` & `01_unit_test_detailed.png` — Ringkasan unit test & durasi eksekusi per service.
2. `02_stress_test_throughput.png` & `02_stress_test_detailed.png` — Grafik RPS, Latency (p50, p95, p99), dan Error Rate.
3. `03_resilience_chaos_audit.png` & `03_resilience_detailed.png` — Grafik waktu pemulihan (recovery time) tiap service saat dihantam chaos failure.
4. `04_overall_system_dashboard.png` & `04_overall_system_dashboard_detailed.png` — Master visual dashboard kesehatan sistem.

---

## 🚦 14. Siklus Pengujian & Kesiapan Produksi

Untuk memastikan seluruh sistem siap dirilis ke lingkungan produksi, pengujian disarankan mengikuti 4 siklus berulang (Pass 1 - Pass 4):

| Siklus | Nama Siklus | Fokus Utama | Target Ketercapaian |
|--------|-------------|-------------|---------------------|
| **Pass 1** | Automated & Functional | Eksekusi `run_all_tests.py` + Verifikasi visual UI pertama | Seluruh test backend LULUS (100% PASS) |
| **Pass 2** | Fix & Re-test | Memperbaiki kecacatan tampilan UI / bug yang ditemukan | Tidak ada item checklist UI yang gagal |
| **Pass 3** | Stress & Stability | Menjalankan stress test & soak test durasi panjang | Sistem tidak mengalami memory leak atau crash |
| **Pass 4** | Production Gate | Pengujian akhir sebelum rilis resmi | Lulus seluruh kriteria Production Gate di bawah |

### 🚦 Gate Kesiapan Produksi (Production Gate)

- [ ] [ ] [ ] **G1. Automated Tests:** 100% test cases backend di `test/unit_test.py` berstatus PASS.
- [ ] [ ] [ ] **G2. UI Visual Completeness:** Seluruh checklist manual UI/UX (Bagian 3 - 12) telah diperiksa dan disetujui Pengguna (`[x]`).
- [ ] [ ] [ ] **G3. Security Compliance:** Otorisasi RBAC, validasi JWT, dan rate-limiting berfungsi tanpa celah.
- [ ] [ ] [ ] **G4. Performance Approval:** Latensi API Gateway berada dalam ambang batas wajar pada pengujian stress.
- [ ] [ ] [ ] **G5. Resilience Certified:** Pemulihan otomatis (auto-healing) container terbukti sukses pada pengujian chaos.


---
