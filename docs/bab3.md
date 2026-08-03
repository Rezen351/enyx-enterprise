# BAB III — METODE PENELITIAN DAN PERANCANGAN SISTEM

---

## 3.1 Metode Penelitian

### 3.1.1 Pendekatan dan Jenis Penelitian

Penelitian ini bersifat **terapan dan rekayasa sistem** (*applied engineering research*) yang bertujuan merancang, membangun, dan mengevaluasi sistem pemantauan serta kontrol lingkungan tanaman aeroponik berbasis arsitektur *microservice*. Metode yang digunakan mengikuti siklus *Design Science Research* (DSR) (Hevner et al., 2004), yang terdiri dari fase:

1. **Identifikasi masalah dan motivasi** — analisis kebutuhan pemantauan aeroponik presisi
2. **Pendefinisian tujuan solusi** — spesifikasi kebutuhan fungsional dan non-fungsional
3. **Perancangan dan pengembangan** — desain arsitektur, implementasi komponen
4. **Demonstrasi** — pengujian sistem secara integrasi
5. **Evaluasi** — pengukuran terhadap kriteria performa dan keberhasilan
6. **Komunikasi** — dokumentasi hasil dalam laporan ini

---

### 3.1.2 Tahapan Penelitian (Alur Kerja)

| Tahap | Kegiatan | Output |
|-------|----------|--------|
| 1. Studi Literatur | Kajian arsitektur microservice, IoT, reinforcement learning (TD3), sistem aeroponik | Dasar teori (Bab II) |
| 2. Analisis Kebutuhan | Identifikasi kebutuhan fungsional dan non-fungsional sistem | Spesifikasi kebutuhan (§3.2) |
| 3. Perancangan Arsitektur | Desain topologi layanan, protokol komunikasi, skema database | Diagram arsitektur (§3.3) |
| 4. Implementasi | Pembangunan microservices, firmware, dashboard, model AI | Kode sumber dan layanan berjalan |
| 5. Pengujian | Unit test, stress test, resilience test, uji integrasi end-to-end | Hasil pengujian (Bab IV) |
| 6. Evaluasi dan Analisis | Analisis kinerja, akurasi kontrol, reliabilitas | Pembahasan (Bab IV) |

---

### 3.1.3 Alat dan Bahan

**Perangkat Keras:**

| Komponen | Fungsi |
|----------|--------|
| Komputer Server / Host | Menjalankan seluruh kontainer Docker Compose (layanan backend, database, broker, monitoring) |
| ESP32 Microcontroller | Node sensor aeroponik — mengumpulkan data telemetri dan menjalankan aktuator |
| Sensor Lingkungan | Suhu, kelembapan, EC (Electrical Conductivity), pH, suhu larutan nutrisi |
| Aktuator | Pompa misting (pump/load1), valve nutrisi (valve/load2) |
| Kamera IP / ESP32-CAM | Sumber umpan visual (RTSP) untuk deteksi kondisi tanaman |

**Perangkat Lunak:**

| Kategori | Teknologi | Versi |
|----------|-----------|-------|
| Backend Services | Go | 1.26 |
| AI/ML Service | Python + FastAPI | 3.11 |
| Frontend Dashboard | React + Vite | 18.x |
| Container Orchestration | Docker Compose | v2.20+ |
| API Gateway | Kong | 3.6 |
| Message Broker (IoT) | Eclipse Mosquitto (MQTT) | 2.x |
| Event Bus (Inter-Service) | NATS JetStream | 2.10 |
| Database Relasional | MariaDB | 10.11 |
| Database Time-Series | TimescaleDB (PostgreSQL) | 2.17 |
| Cache | Redis | 7.x |
| Object Storage | MinIO | latest |
| Video Streaming | MediaMTX | latest |
| Monitoring | Prometheus + Grafana | 3.4 / 11.x |
| RL Framework | Stable-Baselines3 + PyTorch | latest |

---

## 3.2 Analisis Kebutuhan Sistem

### 3.2.1 Kebutuhan Fungsional

Berdasarkan permasalahan yang diidentifikasi (Bab I) dan studi literatur (Bab II), berikut kebutuhan fungsional yang harus dipenuhi sistem:

| Kode | Kebutuhan Fungsional | Prioritas |
|------|----------------------|-----------|
| KF-01 | Sistem dapat menerima data telemetri sensor dari node ESP32 secara berkala melalui protokol MQTT | P1 |
| KF-02 | Sistem menyimpan data telemetri dalam database time-series untuk analisis historis | P1 |
| KF-03 | Sistem menampilkan data telemetri secara real-time pada dashboard melalui koneksi WebSocket | P1 |
| KF-04 | Sistem mendukung autentikasi pengguna berbasis JWT dengan tiga tingkat akses (Admin, Operator, Viewer) | P1 |
| KF-05 | Sistem dapat mengirim perintah kontrol aktuator (pompa/valve) ke perangkat ESP32 melalui MQTT | P1 |
| KF-06 | Sistem mendukung mode kontrol manual, penjadwalan otomatis, dan kontrol berbasis AI (TD3) | P1 |
| KF-07 | Sistem mengevaluasi ambang batas sensor dan membangkitkan notifikasi peringatan secara otomatis | P1 |
| KF-08 | Sistem menyediakan analitik agregat data telemetri dengan resolusi berbeda (per jam, per hari) | P2 |
| KF-09 | Sistem mendukung streaming video dari kamera (RTSP → HLS/WebRTC) dan deteksi visual berbasis YOLO | P2 |
| KF-10 | Sistem mengontrol jadwal misting secara adaptif menggunakan model reinforcement learning (TD3) berdasarkan kondisi tanaman dan telemetri | P2 |
| KF-11 | Sistem menyediakan ekspor data telemetri dalam format CSV | P3 |
| KF-12 | Sistem mencatat audit trail setiap tindakan kritis ke dalam log terpusat | P2 |
| KF-13 | Sistem menangani kegagalan pengiriman pesan melalui mekanisme Dead Letter Queue (DLQ) | P2 |

### 3.2.2 Kebutuhan Non-Fungsional

| Kode | Kebutuhan Non-Fungsional | Tolok Ukur |
|------|--------------------------|------------|
| KNF-01 | Ketersediaan (Availability) | Sistem dapat di-restart secara otomatis bila terjadi kegagalan (restart policy: unless-stopped) |
| KNF-02 | Performa / Latensi | Latensi telemetri ESP32 → Dashboard ≤ 2 detik (p95); latensi REST via gateway ≤ 300 ms (p95) |
| KNF-03 | Skalabilitas | Arsitektur mendukung penambahan node sensor tanpa perubahan struktural layanan inti |
| KNF-04 | Keamanan | Autentikasi JWT pada semua protected route; enkripsi kredensial di variabel lingkungan; RBAC tiga level; isolasi jaringan Docker |
| KNF-05 | Isolasi Kegagalan | Kegagalan satu layanan tidak merambat ke layanan lain (bounded context + Database-per-Service) |
| KNF-06 | Keterpantauan (Observability) | Metrik Prometheus tersedia dari semua layanan; audit trail dapat dilacak berdasarkan correlation ID |
| KNF-07 | Kemudahan Pengelolaan | Seluruh infrastruktur diorkestrasi via docker-compose.yml tunggal; konfigurasi via variabel lingkungan (.env) |
| KNF-08 | Ketepatan Kontrol AI | Model TD3 menghasilkan jadwal misting yang menjaga kelembapan zona akar (H_in) ≥ 85% dari waktu berada dalam rentang [80%, 95%] |

---

## 3.3 Perancangan Arsitektur Sistem

Dengan kebutuhan yang telah terdefinisi, bagian ini menjelaskan bagaimana sistem dirancang untuk memenuhi kebutuhan tersebut. Arsitektur adalah "blue print" yang menghubungkan semua komponen.

### 3.3.1 Gambaran Umum Arsitektur

Sistem dirancang menggunakan **Arsitektur Microservice** dengan pola **Database-per-Service** dan komunikasi **Event-Driven** melalui NATS JetStream. Seluruh akses eksternal dikelola oleh satu **API Gateway** (Kong), sehingga klien hanya berinteraksi melalui satu titik masuk.

Secara topologis, sistem terdiri dari tujuh lapisan:

| Lapisan | Komponen Utama | Peran |
|---------|----------------|-------|
| Device Layer | ESP32 + Sensor/Aktuator | Pengumpulan data lingkungan dan eksekusi perintah fisik |
| Edge Layer | Mosquitto MQTT Broker | Penghubung antara perangkat IoT dan layanan backend |
| Ingestion Layer | Module Service | Penerimaan telemetri MQTT, penyimpanan, dan publikasi ke event bus |
| Processing Layer | Analytics, Alert, ML, Control, Stream | Pemrosesan data: agregasi, evaluasi threshold, inferensi AI, kontrol |
| Gateway Layer | Kong API Gateway | Satu titik masuk untuk semua traffic REST dan WebSocket |
| Presentation Layer | Dashboard (React) + WS-Gateway | Antarmuka pengguna real-time |
| Observability Layer | Prometheus + Grafana | Pemantauan kesehatan seluruh layanan |

Prinsip **single-responsibility** dan **Database-per-Service** menjamin bahwa setiap layanan dapat diskalakan, diperbarui, atau diganti secara independen tanpa mengganggu layanan lainnya.

Gambar arsitektur sistem dapat direpresentasikan dalam satu diagram berlapis (*layered diagram*) yang menunjukkan tujuh lapisan utama dan tiga jalur komunikasi. Diagram ini sebaiknya dibuat dalam format draw.io atau Word dengan susunan sebagai berikut: **Device Layer** (ESP32) mengirimkan data ke **Edge Layer** (Mosquitto), yang selanjutnya diteruskan ke **Ingestion Layer** (Module Service). Dari Module Service, data memisah menjadi dua aliran: (1) telemetri batch mengalir melalui **Processing Layer** (Analytics/Alert/Control/ML) untuk diproses, dan (2) data real-time diteruskan ke **Presentation Layer** (WS-Gateway + Dashboard). Semua akses REST dari dashboard melewati **Gateway Layer** (Kong). **Observability Layer** (Prometheus + Grafana) menjangkau seluruh lapisan melalui sidecar metrics. Tiga jalur komunikasi yang perlu digambarkan secara eksplisit adalah: *Jalur 1 — REST API* (panah dua arah antara Dashboard dan Kong, serta antara Kong dan setiap service), *Jalur 2 — WebSocket* (panah dari WS-Gateway ke Dashboard), dan *Jalur 3 — Event Bus NATS* (panah publish/subscribe antar service di Processing Layer).

### 3.3.2 Pola Komunikasi

Terdapat tiga jalur komunikasi utama yang digunakan secara konsisten dalam sistem:

**Jalur 1 — REST API (Request-Response):**
Semua operasi CRUD dan kueri mengalir dari Dashboard/Client → Kong → Service tujuan. Kong memvalidasi token JWT sebelum meneruskan permintaan. Setiap service juga memvalidasi JWT secara mandiri (defense-in-depth).

**Jalur 2 — Real-Time WebSocket:**
Data telemetri real-time mengalir dari NATS → WS-Gateway → Kong (route `/ws`) → Dashboard. WS-Gateway berperan sebagai jembatan dua arah antara NATS dan klien browser. Koneksi WebSocket diautentikasi dengan JWT pada fase handshake.

**Jalur 3 — Inter-Service Event Bus (NATS):**
Semua komunikasi antar-layanan dilakukan secara asinkron melalui NATS JetStream. Tidak ada panggilan HTTP langsung antar layanan backend (kecuali untuk operasi sinkron tertentu). Pola ini memastikan isolasi temporal antar layanan.

### 3.3.3 Rancangan Database (Database-per-Service)

Setiap layanan memiliki database terisolasi sesuai kebutuhan datanya. Prinsip ini mencegah coupling pada level data dan memungkinkan evolusi skema secara independen.

| Layanan | Database | Justifikasi Pemilihan |
|---------|----------|-----------------------|
| Auth | MariaDB (auth_db) | Data relasional: user, role, permission, refresh token |
| Module | MariaDB + TimescaleDB | Metadata perangkat (relasional) + telemetri time-series |
| Analytics | TimescaleDB (analytics_ts) | Khusus agregasi time-series dengan continuous aggregate |
| Control | MariaDB (control_db) | Riwayat perintah, jadwal, dan konfigurasi aktuator |
| Alert | MariaDB (alert_db) | Konfigurasi threshold dan riwayat alert |
| Notification | MariaDB (notification_db) | Log pengiriman notifikasi |
| Audit | MariaDB (audit_db) | Append-only audit trail |
| ML | MariaDB (ml_db) | Registri model YOLO dan metadata inferensi |
| Stream | MariaDB (stream_db) | Metadata stream kamera dan snapshot |
| Export | TimescaleDB (read) + Redis | Antrian pekerjaan ekspor + cache |
| Redis (shared) | 1 instance, multi-DB logis | Cache/ephemeral store (module=DB0, alert=DB1, dst.) |
| MinIO (shared) | 2 bucket: stream, mlbucket | Snapshot/recording (Stream) + hasil anotasi/model (ML) |

> **Catatan:** Konsolidasi Redis dan MinIO menjadi instance bersama tidak melanggar prinsip Database-per-Service, karena keduanya bersifat cache/ephemeral — bukan sumber kebenaran domain.

### 3.3.4 Rancangan Kontrak API dan Event

**Standar Respons REST:**
Semua layanan menggunakan format respons JSON yang seragam:
- Sukses: `{ "success": true, "data": <payload> }`
- Error: `{ "success": false, "error": { "code": "<KODE>", "message": "<pesan>" } }`

**Kontrak NATS Subject (Event Bus):**

| Subject | Publisher | Subscriber | Jenis |
|---------|-----------|------------|-------|
| telemetry.ingest | Module | Alert, WS-Gateway | Core NATS |
| telemetry.batch | Module | Analytics | JetStream |
| alert.triggered / alert.resolved | Alert | Notification, WS-Gateway | Core NATS |
| audit.log | Semua layanan | Audit | Core NATS |
| detection.result | ML Service | model-control | Core NATS |

**Kontrak MQTT Topic (Edge):**

| Topic | Arah | Penjelasan |
|-------|------|------------|
| smartfarm/<node_id>/telemetry | ESP32 → Mosquitto → Module | Data sensor periodik |
| smartfarm/actuator/<node_id> | Control → Mosquitto → ESP32 | Perintah aktuator |
| smartfarm/<node_id>/confirm | ESP32 → Mosquitto → Module/Control | Konfirmasi eksekusi perintah |

---

## 3.4 Perancangan Komponen Perangkat Keras

Arsitektur perangkat lunak hanya bermakna jika ada perangkat keras yang mengirimkan data nyata. Bagian ini menjelaskan sisi fisik sistem.

### 3.4.1 Topologi Jaringan Node Sensor

Node sensor aeroponik berbasis **ESP32** terhubung ke jaringan WiFi lokal dan berkomunikasi dengan broker MQTT (Mosquitto) di server. Setiap node secara periodik mempublikasikan data sensor dan berlangganan topik perintah aktuator.

**Sensor yang digunakan:**
- Sensor suhu dan kelembapan udara (dalam & luar): SHT31 (SensorTemp & Humidity, I2C, presisi ±0.2°C / ±2% RH)
- Sensor EC (Electrical Conductivity) larutan nutrisi
- Sensor pH larutan nutrisi
- Sensor suhu larutan nutrisi

Desain modular perangkat keras memungkinkan penambahan kategori sensor baru tanpa perlu menulis ulang firmware. Setiap jenis sensor memetakan nilai telemetrinya ke kolom MQTT yang terpisah, dan firmware ESP32 menggunakan registry sensor modular yang mendaftarkan driver sensor secara dinamis. Akibatnya, integrasi sensor baru hanya memerlukan penambahan driver dan skema MQTT, bukan perubahan arsitektur keseluruhan sistem.

**Aktuator yang dikendalikan:**
- Pompa misting (load1/pump) — dikontrol via sinyal on/off dengan jadwal interval
- Valve nutrisi (load2/valve) — dikontrol via perintah langsung on/off dari TD3 controller

### 3.4.2 Firmware ESP32

Firmware ESP32 dirancang dengan arsitektur modular yang memisahkan empat komponen menjadi modul mandiri:

1. **Modul driver sensor** — membaca nilai mentah dari setiap sensor (SHT31, EC, pH, dsb.) dan menerapkan kalibrasi per-perangkat
2. **Modul klien MQTT** — menangani koneksi WiFi, publish telemetri ke `smartfarm/<node_id>/telemetry`, dan subscribe perintah
3. **Modul pengendali aktuator** — menerjemahkan perintah ON/OFF menjadi sinyal GPIO untuk pompa dan valve
4. **Modul pembaruan OTA** — mengunduh dan menerapkan firmware baru tanpa kabel serial

Alur operasi firmware:
1. Inisialisasi WiFi dan koneksi ke broker MQTT
2. Pembacaan sensor secara periodik setiap **5 detik**
3. Publikasi data telemetri ke topik `smartfarm/<node_id>/telemetry`
4. Langganan (subscribe) pada topik perintah `smartfarm/actuator/<node_id>`
5. Pada penerimaan perintah, eksekusi aktuator dan kirim konfirmasi ke `smartfarm/<node_id>/confirm`

Pemisahan modul ini memastikan bahwa penambahan sensor atau aktuator baru tidak memerlukan penulisan ulang seluruh firmware, melainkan hanya perlu menambahkan driver di registry sensor dan memperluas skema payload MQTT.

---

## 3.5 Perancangan Layanan Backend (Microservices)

Setelah arsitektur dan hardware terdefinisi, bagian ini menjelaskan rancangan masing-masing layanan yang membentuk sistem backend. Setiap layanan dirancang dengan prinsip single responsibility — satu layanan, satu domain bisnis.

Sistem backend terdiri dari **15 layanan** yang dikembangkan menggunakan bahasa Go dan Python. Masing-masing layanan mengikuti struktur direktori standar:

```
services/<nama-service>/
├── internal/
│   ├── config/      # Konfigurasi & environment variables
│   ├── model/       # Struct & DTO
│   ├── repository/  # Interaksi database
│   ├── service/     # Business logic
│   └── handler/     # HTTP handlers
├── main.go
├── Dockerfile
└── go.mod
```

Struktur direktori standar ini adalah manifestasi langsung dari prinsip *separation of concerns* pada tingkat kode. Karena setiap lapisan — konfigurasi, model, repository, service logic, dan handler — dipisahkan ke direktori masing-masing, pengembang dapat mengganti seluruh lapisan database (misal: mengganti MariaDB dengan PostgreSQL) hanya dengan memodifikasi layer repository, tanpa menyentuh logika bisnis di layer service. Demikian pula, pengujian unit dapat dilakukan secara terisolasi pada layer service dengan mock repository, dan deployment dapat diatur secara independen karena setiap service memiliki Dockerfile dan go.mod-nya sendiri. Pemisahan ini juga memudahkan penambahan layanan baru: cukup menyalakan *skeleton* direktori standar, mendefinisikan model dan repository, lalu menghubungkannya ke Kong dan NATS tanpa mengganggu layanan yang sudah berjalan.

### 3.5.1 Auth Service

**Domain:** Autentikasi, otorisasi, dan manajemen akun pengguna.

**Fungsi utama:**
- Registrasi akun, login dengan validasi kredensial, dan logout
- Penerbitan access token (JWT HS256, masa berlaku 15 menit) dan refresh token (rotasi + revokasi)
- Pengelolaan pengguna berbasis RBAC (Admin / Operator / Viewer)

**Poin desain kritis:**
- Semua protected route di layanan lain memvalidasi JWT menggunakan shared secret
- Refresh token disimpan dalam bentuk hash (SHA-256) di database, bukan teks biasa

Auth Service adalah fondasi keamanan seluruh ekosistem sistem. Tanpa layanan ini, tidak ada mekanisme yang mencegah akses tidak autorisasi ke data sensitif atau perintah kontrol fisik. Auth Service tidak hanya mengeluarkan token — ia juga menegakkan kebijakan akses berbasis peran (RBAC) yang memastikan pengguna dengan hak Viewer hanya dapat memantau data, sedangkan Admin memiliki kendali penuh atas konfigurasi sistem.

### 3.5.2 Module Service

**Domain:** Registrasi perangkat, onboarding node MQTT, dan ingest telemetri.

**Fungsi utama:**
- Menerima data telemetri dari Mosquitto dan menyimpan ke MariaDB (metadata) + TimescaleDB (time-series)
- Mekanisme discovery perangkat baru melalui MQTT
- Mempublikasikan event `telemetry.ingest` dan `telemetry.batch` ke NATS

Module Service adalah pintu masuk data dari dunia fisik ke sistem digital. Setiap bit telemetri yang dikirim ESP32 harus melewati tangan Module Service sebelum dapat diproses, dianalisis, atau ditampilkan. Posisi strategis ini menjadikannya sebagai *gateway* antara lapisan perangkat (Device Layer) dan lapisan pemrosesan (Processing Layer). Keandalan Module Service langsung memengaruhi kualitas data yang tersedia untuk seluruh sistem downstream.

### 3.5.3 Analytics Service

**Domain:** Agregasi dan kueri data time-series telemetri.

**Fungsi utama:**
- Berlangganan `telemetry.batch` dari NATS dan menyimpan ke TimescaleDB Analytics
- Menyediakan endpoint kueri agregat dengan berbagai resolusi (per jam, per hari, per bulan)
- Menggunakan fitur continuous aggregate TimescaleDB untuk performa kueri tinggi

Analytics Service mengubah lautan data mentah menjadi informasi yang dapat dimengerti. Tanpa layanan ini, pengguna hanya melihat deretan angka sensor tanpa konteks tren atau pola. Dengan continuous aggregate TimescaleDB, Analytics Service dapat menjawab pertanyaan kompleks — seperti "apakah kelembapan zona akar stabil selama 7 hari terakhir?" — dalam hitungan milidetik, bahkan atas data jutaan titik.

### 3.5.4 Control Service

**Domain:** Pengelolaan perintah aktuator dan penjadwalan.

**Fungsi utama:**
- Menerima perintah dari Dashboard atau TD3 Controller dan mempublikasikan ke Mosquitto
- Mengelola tiga mode operasi: Manual, Otomatis (berbasis jadwal), dan Emergency
- Melacak siklus request-acknowledge-confirm perintah aktuator
- Menyimpan jadwal interval (on_sec/off_sec) untuk pompa yang dapat diperbarui oleh AI

Control Service adalah otak eksekusi fisik sistem. Setiap perintah yang keluar dari sistem — baik dari pengguna manusia maupun dari model TD3 — harus melewati Control Service untuk memastikan validasi, pencatatan, dan pelacakan siklus. Mekanisme request-acknowledge-confirm menjamin bahwa tidak ada perintah yang "dilupakan" atau dieksekusi tanpa konfirmasi dari perangkat.

### 3.5.5 Alert Service

**Domain:** Evaluasi ambang batas sensor dan pembangkitan peringatan.

**Fungsi utama:**
- Berlangganan `telemetry.ingest` dan mengevaluasi kondisi sensor terhadap threshold
- Mempublikasikan `alert.triggered` / `alert.resolved` / `system.status` ke NATS
- Menyimpan riwayat alert di database

Alert Service berperan sebagai sistem saraf sensorik — mendeteksi kondisi abnormal dan memicu respons. Dengan mengevaluasi setiap data telemetri yang masuk, layanan ini mampu membedakan antara variasi normal dan kondisi yang memerlukan intervensi segera. Output alert dikirimkan ke Notification Service untuk disebarkan ke pengguna, sekaligus ke WS-Gateway untuk ditampilkan secara real-time di dashboard.

### 3.5.6 Notification Service

**Domain:** Pengiriman notifikasi multi-saluran.

**Fungsi utama:**
- Berlangganan `alert.triggered` / `alert.resolved` dari NATS
- Mengirimkan notifikasi melalui Telegram, Email, dan Push Notification
- Menggunakan Redis (DB2) sebagai antrian pengiriman dan retry logic

Notification Service menjamin bahwa informasi kritis tidak hanya terdeteksi, tetapi juga sampai ke tangan pengguna yang tepat. Dengan mendukung berbagai saluran (Telebot, Email, Push), layanan ini mengurangi risiko single point of failure dalam komunikasi darurat. Antrian Redis memastikan bahwa pesan tidak hilang meskipun layanan pengiriman eksternal sementara tidak tersedia.

### 3.5.7 WS-Gateway

**Domain:** Jembatan NATS <-> WebSocket untuk data real-time.

**Fungsi utama:**
- Berlangganan subject NATS (`mqtt.>`, `system.status`, `alert.triggered`) dan push ke semua klien WebSocket
- Memvalidasi JWT pada fase handshake koneksi WebSocket
- Menerima pesan dari klien Dashboard dan mempublikasikannya ke NATS (arah outbound)

WS-Gateway adalah satu-satunya titik di mana dua dunia bertemu: dunia event asinkron (NATS) dan dunia koneksi persisten browser (WebSocket). Tanpa komponen ini, dashboard hanya bisa "melihat ke masa lalu" — data historis — tanpa pernah merasakan detak waktu nyata sistem. WS-Gateway menerjemahkan aliran event yang tak terbatas dari NATS menjadi frame WebSocket yang ringan dan terstruktur untuk konsumsi frontend.

### 3.5.8 Stream Service dan MediaMTX

**Domain:** Pengelolaan stream video kamera dan snapshot.

**Fungsi utama:**
- Mendaftarkan dan mengelola jalur RTSP di MediaMTX
- Menyimpan snapshot dan rekaman video ke MinIO (bucket `stream`)
- Memicu proses deteksi AI pada snapshot yang diambil

Stream Service menghubungkan sensor visual dengan pipeline AI. Dengan mengelola stream video melalui MediaMTX dan menyimpan snapshot ke MinIO, layanan ini memastikan bahwa setiap momen penting dapat direkam dan dianalisis. Integrasi dengan ML Service memungkinkan deteksi objek (YOLOv8) secara otomatis pada setiap snapshot, menciptakan loop penutup antara visualisasi dan kecerdasan buatan.

### 3.5.9 ML Service (Vision API)

**Domain:** Registri model deteksi objek dan inferensi YOLOv8.

**Fungsi utama:**
- Mengelola daftar model YOLO yang tersedia
- Melakukan inferensi pada gambar dari MinIO (bucket `stream`)
- Mempublikasikan hasil deteksi (`detection.result`) ke NATS dan menyimpan metadata ke MinIO

ML Service memisahkan beban komputasi inferensi dari layanan-stream agar tidak menghambat aliran data video. Dengan menerbitkan hasil deteksi ke NATS, layanan ini memungkinkan kontrol berbasis visual — misalnya, mendeteksi ukuran akar untuk memperbarui estimasi pertumbuhan yang digunakan oleh TD3 Controller.

### 3.5.10 Layanan Pendukung

| Layanan | Fungsi Singkat |
|---------|----------------|
| Audit Service | Berlangganan `audit.log` dan menyimpan audit trail ke database |
| Export Service | Melayani ekspor data telemetri dalam format CSV dari TimescaleDB |
| DLQ Worker | Menangani pesan yang melewati batas retry NATS JetStream |
| Webhook Service | Dispatcher webhook ke endpoint eksternal dengan retry AES-GCM |
| Monitor Service | Menyediakan data sumber daya kontainer untuk halaman status di dashboard |

Layanan pendukung ini menutupi kebutuhan operasional yang tidak termasuk dalam alur inti, namun krusial untuk keandalan dan kepatuhan sistem:

- **Audit Service** berjalan sebagai subscriber independen di NATS, merekam setiap event kritis ke database terpisah tanpa memengaruhi jalur data utama.
- **Export Service** mengonsumsi data dari TimescaleDB dan menyajikannya sebagai file CSV, memisahkan beban analisis eksternal dari layer presentasi.
- **DLQ Worker** memantau antrian *dead-letter* NATS JetStream dan menangani retry otomatis, menjamin bahwa kegagalan sementara tidak menghilangkan pesan penting.
- **Webhook Service** bertindak sebagai dispatcher terpisah dengan enkripsi AES-GCM, memastikan integrasi eksternal tetap aman dan tidak mengganggu inti sistem.
- **Monitor Service** mengumpulkan metrik kontainer dan menyajikannya ke dashboard, memberikan visibilitas operasional tanpa menambahkan logika bisnis ke layanan lain.

---

## 3.6 Perancangan Sistem Kontrol Berbasis AI (TD3)

Pembeda utama sistem ini adalah kemampuan adaptasi kontrol berbasis AI. Bagian ini menjelaskan bagaimana model TD3 dirancang, dilatih, dan diintegrasikan ke loop kontrol fisik.

### 3.6.1 Motivasi Penggunaan TD3

Sistem aeroponik memerlukan penyesuaian parameter misting yang responsif terhadap perubahan kondisi lingkungan. Pendekatan aturan statis (threshold-based) tidak mampu beradaptasi secara optimal terhadap variasi kondisi yang bersifat kontinu dan saling bergantung. Algoritma **Twin Delayed Deep Deterministic Policy Gradient (TD3)** dipilih karena:

- Dirancang untuk ruang aksi kontinu — sesuai dengan kontrol durasi dan interval misting
- Lebih stabil dibanding DDPG (overestimation bias diminimalkan lewat delayed actor update dan double critic)
- Telah terbukti efektif untuk masalah kontrol lingkungan dalam literatur

Sebelum memilih TD3, dua algoritma lain dievaluasi untuk konteks aeroponik khusus. **PPO** diuji terlebih dahulu karena kemudahannya dalam hyperparameter tuning, namun menunjukkan gejala *stuck local optimum*: clip_fraction mendekati nol dan panjang episode membeku di 90–94 langkah. Hal ini disebabkan oleh reward yang sangat jarang (sparse) setiap 720 langkah dalam episode 1.440 langkah, sehingga gradient policy tidak mendapatkan sinyal pembelajaran yang cukup sering. Sementara itu, **DDPG** memiliki bias overestimasi nilai Q yang masif pada critic tunggal, berisiko menginstruksikan aksi yang terlalu agresif pada lingkungan yang sudah memiliki feedback lingkungan yang tidak pasti. TD3 mengatasi kedua masalah tersebut secara bersamaan: twin critics mengurangi overestimasi, delayed policy update menstabilkan pembelajaran, dan target policy smoothing memperhalus eksplorasi di ruang aksi kontinu. Kombinasi ini membuat TD3 lebih sesuai untuk kontrol aeroponik yang membutuhkan stabilitas jangka panjang terhadap feedback lingkungan yang jarang dan tidak pasti.

### 3.6.2 Pemodelan Lingkungan (Gymnasium Simulator)

Agent TD3 dilatih menggunakan **simulator aeroponik** berbasis Gymnasium yang memodelkan:
- Dinamika kelembapan zona akar sebagai fungsi durasi dan interval misting
- Drift suhu, EC, dan pH seiring waktu dan siklus misting
- Variasi intensitas cahaya (solar index berdasarkan jam)
- **Domain Randomization** — variasi parameter fisik tiap episode untuk meningkatkan generalisasi

**Ruang Keadaan (State Space) — 10 Dimensi:**

| Dimensi | Variabel | Sumber Data (Deployment) |
|---------|----------|--------------------------|
| 1 | L_root — panjang akar (cm) | MinIO metadata deteksi ML |
| 2 | U_status — skor kondisi tanaman [0,1] | MinIO metadata deteksi ML |
| 3 | T_in — suhu dalam ruang | Telemetri Module Service |
| 4 | H_in — kelembapan dalam ruang | Telemetri Module Service |
| 5 | T_out — suhu luar ruang | Telemetri Module Service |
| 6 | H_out — kelembapan luar ruang | Telemetri Module Service |
| 7 | EC — electrical conductivity | Telemetri Module Service |
| 8 | pH — keasaman larutan nutrisi | Telemetri Module Service |
| 9 | T_nut — suhu larutan nutrisi | Telemetri Module Service |
| 10 | I_day — indeks intensitas matahari | Kalkulasi berdasarkan jam lokal |

**Ruang Aksi (Action Space) — 3 Dimensi:**

| Dimensi | Aksi Ternormalisasi [-1,1] | Rentang Fisik |
|---------|----------------------------|---------------|
| a_mist | Durasi misting | D_mist dalam [120, 600] detik |
| a_interval | Jeda antar misting | interval_sec dalam [120, 600] detik |
| a_valve | Buka/tutup valve | A_valve: 0=OFF, 1=ON (threshold: nilai >= 0 → ON) |

**Fungsi Reward:**

Fungsi reward dirancang untuk memprioritaskan pertumbuhan tanaman, stabilitas lingkungan, efisiensi sumber daya, dan eksplorasi aksi yang beragam. Total reward dihitung sebagai:

$$
R_{total} = R_{growth} + R_{growth\_proxy} + R_{state} + R_{joint\_tin\_o2} + P_{diversity} + R_{efficiency} - C_{resource} - P_{env} - P_{hypoxia} - P_{extreme} - P_{shrink} - P_{death}
$$

**Komponen Reward:**

1. **$R_{growth}$ — Reward Pertumbuhan Langsung:**
   $$R_{growth} = w_{growth} \times captured\_growth \times f_{Hin} \times f_T$$
   dengan $w_{growth} = 100.0$. Komponen ini memberikan reward besar ketika tanaman berhasil menangkap nutrisi (captured_growth) pada kondisi kelembapan dan suhu yang optimal. Faktor $f_{Hin}$ dan $f_T$ menormalkan reward berdasarkan kesesuaian lingkungan.

2. **$R_{growth\_proxy}$ — Reward Proksi Pertumbuhan (Dense Signal):**
   $$R_{growth\_proxy} = 0.3 \times limiting\_factor$$
   memberikan sinyal reward padat setiap langkah berdasarkan kondisi lingkungan yang mendukung pertumbuhan, tanpa harus menunggu penangkapan nutrisi aktual.

3. **$R_{state}$ — Reward Stabilitas Lingkungan:**
   $$R_{state} = R_{state}^{pH} + R_{state}^{EC} + R_{state}^{H_{in}} + R_{state}^{T_{in}} + R_{state}^{T_{root}} + R_{state}^{O2} + R_{state}^{joint} + R_{state}^{action}$$
   
   - pH: $+0.4$ jika pH $\in$ [5.5, 6.5]; $-0.4 \times \min(1.0, |pH - 6.0| / 1.0)$ jika di luar rentang
   - EC: $+0.4$ jika EC $\in$ [1.2, 2.0]; $-0.4 \times \min(1.0, |EC - 1.6| / 0.8)$ jika di luar rentang
   - H_in: $+0.4$ jika H_in $\geq$ 85%; $+0.2 \times (H_{in} - 80) / 5$ jika $80 \leq H_{in} < 85$; $-0.8 \times (85 - H_{in}) / 10$ jika H_in < 80%
   - T_in: $+0.6$ jika $T_{in}$ dalam rentang kurikulum (bergantung pada fase episode); $-0.6 \times \min(1.0, deviasi / lebar\_rentang)$ jika di luar
   - T_root: $+0.2$ jika $T_{root} \in$ [15, 22]; $-0.2 \times \min(1.0, deviasi / 10)$ jika di luar
   - O2 (fase $\geq$ 2): $+0.4$ jika O2_status $\geq$ 0.6; $-0.4 \times \min(1.0, (0.6 - O2\_status) / 0.4)$ jika di bawah
   - Action shaping: $+0.3 \times \min(1.0, (D_{mist} - 120) / 180)$ jika $D_{mist} \geq 120$; $+0.2 \times \min(1.0, (interval - 180) / 420)$ jika $interval \geq 180$; $-0.5$ jika $interval < 180$

4. **$R_{joint\_tin\_o2}$ — Bonus Bersama T_in dan O2 (Fase 3):**
   $$R_{joint\_tin\_o2} = \begin{cases} 0.8 & \text{jika } T_{in} \text{ OK dan } O2 \text{ OK} \\ 0.2 & \text{jika salah satu OK} \\ 0 & \text{jika keduanya buruk} \end{cases}$$

5. **$P_{diversity}$ — Penalti Mode Collapse:**
   $$P_{diversity} = P_{diversity}^{mist} + P_{diversity}^{interval} + P_{diversity}^{valve}$$
   
   - $P_{diversity}^{mist} = 0.4 + 0.8 \times \min(1.0, (\sigma_{mist} - 10) / 40)$ jika $\sigma_{mist} > 10$
   - $P_{diversity}^{interval} = 0.2 + 0.4 \times \min(1.0, (\sigma_{interval} - 15) / 30)$ jika $\sigma_{interval} > 15$
   - $P_{diversity}^{valve} = 0.2$ jika valve beralih minimal 1 kali dalam 10 aksi terakhir

6. **$R_{efficiency}$ — Reward Efisiensi (kondisional pada stabilitas):**
   $$R_{efficiency} = \begin{cases} 0.3 \times (300 - D_{mist}) / 180 & \text{jika } D_{mist} \leq 300 \\ 0.3 \times (interval_{sec} - 300) / 300 & \text{jika } interval \geq 300 \\ +0.6 & \text{jika } A_{valve} < 0.5 \text{ dan } D_{mist} < 300 \text{ dan } interval > 300 \end{cases}$$
   Hanya aktif jika semua kondisi stabilitas terpenuhi (EC, pH, H_in, T_in, dan O2 sesuai rentang).

7. **$C_{resource}$ — Biaya Sumber Daya:**
   $$C_{resource} = 0.01 + 0.15 \times (1 \text{ jika } A_{valve} \geq 0.5 \text{ else } 0)$$

8. **$P_{env}$ — Penalti Deviasi Lingkungan:**
   $$P_{env} = 0.05 \times (dev_{pH} + dev_{EC} + dev_{Hin})$$
   
   - $dev_{pH} = |pH - 6.0|$ jika $pH < 5.5$ atau $pH > 6.5$, else 0
   - $dev_{EC} = |EC - 1.6|$ jika $EC < 1.2$ atau $EC > 2.0$, else 0
   - $dev_{Hin} = \max(0, 85 - H_{in})$ jika $H_{in} < 85$, else 0

9. **$P_{hypoxia}$ — Penalti Hipoksia (Fase 3):**
   $$P_{hypoxia} = 5.0 \times \max(0, 1 - O2_{status}) \quad \text{( fase } \geq 3 \text{ saja; fase 1-2 = 0)}$$

10. **$P_{extreme}$ — Penalti Aksi Ekstrem:**
    $$P_{extreme} = 0.5 \quad \text{jika } A_{valve} \geq 0.5 \text{ dan } (D_{mist} \leq 120 \text{ atau } interval_{sec} \leq 120)$$

11. **$P_{shrink}$ — Penalti Penyusutan Akar:**
    $$P_{shrink} = w_{growth} \times (L_{root}^{prev} - L_{root}) \times 2.0 \quad \text{jika } L_{root} \text{ menyusut}$$

12. **$P_{death}$ — Penalti Kematian / Kondisi Kritis:**
    $$P_{death} = \begin{cases} w_{status} \times 5.0 & \text{jika tanaman mati} \\ w_{status} \times (0.3 - U_{status}) \times 3.0 & \text{jika } U_{status} < 0.3 \\ w_{status} \times (0.6 - U_{status}) \times 1.5 & \text{jika } U_{status} < 0.6 \\ 0 & \text{lainnya} \end{cases}$$

**Survival Bonuses:**

Selain reward komponen di atas, agent mendapatkan bonus kelangsungan hidup yang semakin besar seiring waktu:

- **+0.5** per langkah simulasi
- **+5.0** setiap 30 menit waktu simulasi
- **+20.0** pada milestone 3 jam
- **+50.0** pada milestone 6 jam
- **+100.0** pada milestone 12 jam
- **+200.0** pada milestone 18 jam
- **+10.0** jika berhasil menyelesaikan episode penuh tanpa terminated

**Early Termination Penalties:**

Jika episode dihentikan prematur (kondisi tanaman kritis sebelum batas waktu episode):
- **$-0.5 \times remaining\_ratio$** — kehilangan bonus kelangsungan hidup yang tersisa (dinormalisasi)
- **$-w_{growth} \times (1.0 + L_{root}/100.0)$** — penalti tumbuh yang lebih berat untuk tanaman yang sudah lebih berkembang

### 3.6.3 Proses Pelatihan

Model dilatih menggunakan **Stable-Baselines3** pada environment Gymnasium kustom dengan total **2,000,000 timestep**. Konfigurasi hyperparameter ditentukan secara eksperimental untuk menyeimbangkan stabilitas pembelajaran dan eksplorasi:

| Hyperparameter | Nilai |
|----------------|-------|
| Total timesteps | 2,000,000 |
| Learning rate | $10^{-4}$ (linear schedule) |
| Buffer size | 2,000,000 |
| Learning starts | 100,000 |
| Batch size | 256 |
| Tau ($\tau$) | 0.005 |
| Gamma ($\gamma$) | 0.995 |
| Policy delay | 2 |
| Target policy noise ($\sigma$) | 0.2 |
| Target noise clip | 0.3 |
| Action noise sigma | [0.1, 0.18, 0.2] |
| Device | CPU |
| Hardware | CPU training (Intel/AMD x86_64) |

Model disimpan dalam format `aeroponic_td3.zip` bersama statistik normalisasi `vec_normalize_td3.pkl`. Curriculum weather scaling diterapkan secara bertahap dari 0.0 hingga 1.0 seiring progresi pelatihan untuk meningkatkan generalisasi terhadap variasi iklim.

Hasil pelatihan yang dicapai:

| Metrik | Nilai |
|--------|-------|
| Mean Episode Reward | 6.671 |
| Episode Length | 150 siklus |
| D_mist Coefficient of Variation | 0.33 |
| Interval CV | 0.20 |
| Penggunaan A_valve | 50.1% |

### 3.6.4 Arsitektur Deployment Model TD3

Model TD3 di-deploy sebagai dua layanan terpisah (prinsip Single Responsibility):

**1. model-controller (Pure Inference Service):**
- FastAPI + Stable-Baselines3 + PyTorch
- Menerima vektor state 10D via `POST /predict`
- Mengembalikan aksi: D_mist, interval_sec, A_valve
- Stateless — tidak menyimpan state antar prediksi

**2. model-control (Scheduler/Orchestrator):**
- FastAPI + threading + NATS subscriber
- Mengumpulkan telemetri dari cache (subscribe `telemetry.ingest`)
- Mengambil metadata kondisi tanaman dari MinIO (bucket `mlbucket`)
- Memanggil model-controller/predict secara periodik
- Memperbarui jadwal pompa via Control Service API
- Mengirim perintah langsung ke valve via Control Service

**Mekanisme Cycle-Boundary Update:**

Untuk mencegah reset siklus misting yang terus-menerus:
1. Model TD3 melakukan evaluasi setiap 5 detik
2. Hasil prediksi disimpan sebagai pending_action
3. Pembaruan ke Control Service hanya dikirim ketika satu siklus ON/OFF sudah selesai (elapsed >= D_mist + interval_sec)

---

## 3.7 Perancangan Dashboard (Frontend)

Seluruh informasi dari sistem backend hanya bernilai jika dapat diakses dan dioperasikan dengan mudah oleh pengguna.

### 3.7.1 Teknologi Frontend

Dashboard dikembangkan menggunakan:
- React 18 dengan Vite sebagai build tool
- Tailwind CSS untuk gaya antarmuka
- WebSocket untuk data telemetri real-time
- REST API melalui Kong untuk operasi CRUD

### 3.7.2 Halaman Utama dan Fungsionalitas

| Halaman | Fungsionalitas |
|---------|----------------|
| Login / Auth | Autentikasi pengguna, manajemen sesi JWT |
| Dashboard Utama | Ringkasan status semua node, alert aktif |
| Node Detail | Telemetri real-time via WebSocket, grafik historis, status aktuator |
| Control Panel | Pemilihan mode (Manual/Otomatis/Emergency), perintah aktuator, manajemen jadwal |
| Analytics | Kueri data historis, visualisasi grafik agregat |
| Live View | Player streaming video HLS/WebRTC, galeri snapshot, hasil deteksi AI |
| Alerts | Riwayat peringatan, konfigurasi threshold, notifikasi |
| Audit Log | Riwayat tindakan sistem (Admin only) |
| Pengaturan Akun | Manajemen profil dan akun pengguna |

---

## 3.8 Perancangan Infrastruktur dan Keamanan

### 3.8.1 Orkestrasi dengan Docker Compose

Seluruh komponen sistem dikelola melalui satu file `docker-compose.yml` yang mendefinisikan:
- 15 layanan aplikasi
- 12 instance database (8x MariaDB, 2x TimescaleDB, 1x Redis, 1x MinIO)
- Infrastruktur pendukung (NATS, Mosquitto, MediaMTX, Prometheus, Grafana, Kong, dll.)
- Jaringan internal private `iot-net` yang mengisolasi seluruh kontainer

### 3.8.2 Strategi Keamanan Berlapis

| Lapisan | Mekanisme | Detail |
|---------|-----------|--------|
| Jaringan | Isolasi Docker Network | Hanya Kong yang terekspos ke host; semua layanan di jaringan private |
| API Gateway | Rate Limiting + CORS | 20 req/menit untuk auth publik; whitelist origin CORS |
| Autentikasi | JWT HS256 | Access token 15 menit, refresh token dengan rotasi |
| Otorisasi | RBAC | Tiga level: Admin, Operator, Viewer — divalidasi per endpoint |
| Database | Isolasi Kredensial | Setiap layanan hanya mengetahui kredensial database miliknya |
| Storage | Scoped Access Key | MinIO: access key ter-scoping per bucket per layanan |
| MQTT | ACL Mosquitto | Kontrol akses per topik per perangkat |
| Event Bus | NATS ACL | Kontrol akses per subject per pengguna |
| WebSocket | JWT pada Handshake | Token divalidasi sebelum koneksi WebSocket diterima |

---

## 3.9 Perancangan Pengujian

Perancangan pengujian ditetapkan sejak fase desain agar hasil yang diperoleh di Bab IV dapat dievaluasi secara objektif dan terukur.

### 3.9.1 Strategi Pengujian

| Jenis Pengujian | Cakupan | Alat |
|-----------------|---------|------|
| Unit Test | Logika bisnis tiap layanan (layer service/repository) | Go testing, pytest |
| Integrasi API | Endpoint HTTP via Kong (/v1/...), validasi format respons | Python requests, script otomatis |
| Stress Test | Throughput dan latensi di bawah beban | Skrip Python + NATS bench |
| Resilience Test | Kegagalan layanan, chaos terkontrol | Skrip Python |
| Pengujian Model AI | Evaluasi kinerja TD3: reward, keragaman aksi, 5 skenario cuaca | evaluate_td3.py, stress_test.py |
| Pengujian Visual/UI | Tata letak, UX, interaksi dashboard | Manual oleh pengguna |

### 3.9.2 Kriteria Keberhasilan

| Kriteria | Target |
|----------|--------|
| Unit test pass rate | ≥ 95% dengan known failures yang didokumentasikan |
| API response format | Seluruh respons mengikuti standar wrapper { success, data/error } |
| Latensi telemetri end-to-end | <= 2 detik (p95) |
| Latensi REST API | <= 300 ms (p95) |
| Model TD3 — Mean Episode Reward | > 5.000 |
| Pipeline alert end-to-end | Alert triggered → Notifikasi terkirim dalam <= 30 detik |

Target ini diset karena sistem yang melibatkan I/O, jaringan, dan integrasi database secara alami menghasilkan flaky test yang sulit dihilangkan sepenuhnya. Known failures yang telah didokumentasikan dengan jelas dianggap dapat diterima selama tidak menimbulkan *breaking change* pada alur bisnis inti.

---

## Ringkasan Bab III

Bab ini telah menjelaskan secara sistematis seluruh aspek perancangan sistem:

1. **Metode penelitian** berbasis Design Science Research dengan enam tahap iteratif
2. **Kebutuhan sistem** terdiri dari 13 kebutuhan fungsional dan 8 kebutuhan non-fungsional
3. **Arsitektur microservice** dengan 7 lapisan topologi, 3 jalur komunikasi, dan prinsip Database-per-Service
4. **Perancangan hardware** — node ESP32 dengan sensor lingkungan dan aktuator
5. **Perancangan 15 layanan backend** dengan domain dan tanggung jawab yang terisolasi
6. **Sistem kontrol AI berbasis TD3** — dari simulator Gymnasium hingga arsitektur deployment dua layanan
7. **Dashboard React** sebagai antarmuka tunggal pemantauan dan kontrol
8. **Infrastruktur dan keamanan** berlapis via Docker Compose + Kong + NATS ACL + MQTT ACL

Rancangan ini menjadi dasar implementasi yang diuraikan hasilnya pada **Bab IV**.
