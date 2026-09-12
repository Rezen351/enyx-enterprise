# PENGEMBANGAN ARSITEKTUR IOT TERDISTRIBUSI BERBASIS MICROSERVICES DAN FIRMWARE MODULAR PADA SISTEM OTOMASI BUDIDAYA AEROPONIK

Alif Muhammad Rizky, [Nama Pembimbing I], [Nama Pembimbing II]

Program Studi Teknik Fisika – Institut Teknologi Bandung

September – 2026

---

**ABSTRAK**

Pertanian presisi pada budidaya aeroponik menuntut pemantauan dan kontrol mikroklimat secara kontinu, namun arsitektur monolitik konvensional memiliki keterikatan erat antarkomponen, rentan terhadap single point of failure, dan sulit diskalakan. Makalah ini merancang, mengimplementasikan, dan mengevaluasi sistem otomasi aeroponik terdistribusi berbasis dual-layer modularity: arsitektur microservice modular pada sisi server dan firmware modular pada edge node ESP32. Pada sisi edge, ESP32 berbasis FreeRTOS dual-core menggunakan pola factory pattern dan protocol registry yang memungkinkan penambahan dan konfigurasi sensor/aktuator baru tanpa proses kompilasi ulang melalui Captive Web Portal. Pada sisi server, sistem menerapkan prinsip database-per-service pada layanan inti (Auth, Module, Control, Analytics) dengan komunikasi event-driven melalui NATS JetStream dan API Gateway Kong. Layanan kontrol adaptif berbasis Reinforcement Learning (TD3) diintegrasikan secara loose coupling dengan ekstraksi fitur visual YOLOv8 untuk menghasilkan penjadwalan misting yang adaptif. Evaluasi empiris melalui unit test, stress test, dan chaos engineering membuktikan isolasi kegagalan penuh antar-layanan (zero cascade failure) serta latensi end-to-end di bawah 2 detik pada persentil ke-95.

**Kata kunci:** microservice, firmware modular, aeroponik, kontrol adaptif

---

**INSTRUCTIONS FOR WORD FORMATTING — Makalah Step**

> Berikut adalah petunjuk format dokumen makalah dalam Microsoft Word. Setiap aturan formatting harus diterapkan melalui menu Font, Paragraph, Layout, dan Style di Word.

**Judul:** Arial 14pt, bold, centered

**Nama Mahasiswa, Pemb.- I dan Pemb.-II:** Arial 10pt, centered  
**Program Studi Teknik Fisika – Institut Teknologi Bandung**  
**Bulan – Tahun**

**ABSTRAK:** Arial 12pt, bold, centered, huruf kapital

Arial 10pt, italic, single line spacing, justified. Makalah dibuat tidak lebih 6 (enam) halaman dengan ukuran A4 dalam format Word.

**Kata kunci:** 4 katakunci, Arial 10pt

---

## 1 PENDAHULUAN

Untuk teks utama gunakan Arial 10pt, kolom tunggal, spasi tunggal dan full justification. Lompat satu baris antara paragraf dan antara sub-judul dan badan text. Page Setup harus di set untuk ukuran A4, top dan bottom margins di set 25mm. Gunakan mirror margins 30mm (inside) and 20mm (outside).

### 1.1 Latar Belakang

Pada budidaya aeroponik, akar tanaman tumbuh di udara dan disemprot nutrisi secara berkala, sehingga parameter mikroklimat seperti suhu udara, kelembapan, *electrical conductivity* (EC), dan pH larutan nutrisi bersifat kritis dan wajib dipantau secara kontinu. Mayoritas sistem IoT konvensional masih berbasis arsitektur monolitik yang memiliki keterikatan erat antarkomponen (*tight coupling*), sehingga sulit diskalakan dan tidak fleksibel ketika terjadi penambahan sensor atau aktuator baru karena menuntut modifikasi logika utama serta kompilasi ulang firmware.

Penelitian ini mengadopsi pendekatan modularitas dua lapis (*dual-layer modularity*) untuk mengatasi keterbatasan tersebut. Pada sisi edge, firmware ESP32 dirancang menggunakan *factory pattern* dan *protocol registry* sehingga konfigurasi perangkat dapat dilakukan secara dinamis. Pada sisi server, sistem menerapkan arsitektur microservice dengan pola *database-per-service* agar setiap layanan dapat dikembangkan, diperbarui, dan dikelola secara independen tanpa menimbulkan kegagalan beruntun (*cascading failure*).

Arsitektur microservice mendefinisikan sebuah aplikasi sebagai kumpulan layanan kecil yang dapat di-*deploy* secara independen dan berkomunikasi melalui mekanisme ringan. Setiap layanan menerapkan prinsip *single responsibility* dan dipisahkan berdasarkan *bounded context*, sehingga perubahan pada satu layanan tidak memaksa penyebaran ulang layanan lain. Salah satu prinsip utama arsitektur *microservice* adalah *database-per-service*, yakni setiap layanan memiliki basis data sendiri tanpa pembagian basis data antar layanan. Isolasi fisik dan logis antar basis data mencegah *cascading failure* serta memungkinkan evolusi skema secara independen.

Komunikasi antar-layanan menggunakan *event-driven architecture* via NATS JetStream yang meningkatkan skalabilitas dan isolasi kegagalan dibanding *request-response* sinkron, dengan Kong sebagai *API Gateway* tunggal. Modularitas diterapkan ganda: *firmware* ESP32 (FreeRTOS *dual-core*) mengenkapsulasi sensor dalam *handler* mandiri yang ditambahkan via `config.json` tanpa rekompilasi berkat *factory pattern* dan *protocol registry*, serta layanan server dalam kontainer Docker dengan kontrak NATS/MQTT eksplisit. Kontrol adaptif menggunakan *Reinforcement Learning* TD3 yang mempelajari kebijakan penjadwalan *misting* stabil untuk sistem fisik kontinu.

Keandalan divalidasi melalui *chaos engineering*, dengan pengelolaan konsistensi *eventually consistent* dan *monitoring* terpusat Prometheus/Grafana. Penelitian ini merancang dan mengevaluasi sistem aeroponik dengan modularitas ganda (*dual-layer modularity*) yang memisahkan dependensi perangkat keras dan komputasi awak, dibuktikan empiris melalui pengujian resiliensi, beban, dan integrasi kontrol adaptif.

#### 1.2 Rumusan Masalah

Berdasarkan latar belakang di atas, rumusan masalah dalam penelitian ini adalah:

1. Bagaimana merancang arsitektur sistem pemantauan dan kontrol aeroponik yang modular sehingga setiap komponen, baik di sisi *firmware* maupun server, dapat dikembangkan, diuji, dan di-*deploy* secara independen tanpa memengaruhi komponen lain?
2. Bagaimana menerapkan prinsip *database-per-service* dan komunikasi *event-driven* melalui NATS JetStream dan MQTT agar sistem mampu mengisolasi kegagalan antar-layanan dan menjamin konsistensi data secara terdistribusi?
3. Bagaimana mekanisme modularitas *firmware* ESP32 berbasis *factory pattern* dan *protocol registry* memungkinkan penambahan protokol baru (seperti protokol I2C untuk sensor INA219) tanpa perlu mengubah logika inti *firmware* atau melakukan kompilasi ulang?
4. Bagaimana mengintegrasikan kapabilitas kecerdasan buatan berupa model kontrol berbasis *Reinforcement Learning* (TD3) dan deteksi visual berbasis YOLOv8 ke dalam arsitektur *microservice* tanpa menimbulkan *tight coupling* dengan layanan lainnya?
5. Sejauh mana sistem yang dibangun memenuhi kriteria kinerja (latensi, *throughput*, keandalan) yang diperlukan untuk operasional pemantauan aeroponik secum *real-time*?

#### 1.3 Tujuan Penelitian

Penelitian ini bertujuan untuk:

1. Merancang dan membangun sistem pemantauan dan kontrol lingkungan aeroponik berbasis arsitektur *microservice* modular yang terdiri dari layanan-layanan *backend* mandiri, masing-masing dengan *database*, kontrak komunikasi, dan *deployment* tersendiri.
2. Mengimplementasikan *firmware* modular pada mikrokontroler ESP32 menggunakan pola *factory pattern* dan *protocol registry* yang memungkinkan penambahan sensor dan protokol baru secara dinamis melalui konfigurasi tanpa kompilasi ulang.
3. Membuktikan keunggulan modularitas secara empiris melalui pengujian pada layanan-layanan inti (Auth Service, Module Service, Control Service, Analytics Service) serta pengujian penambahan *handler* protokol I2C untuk sensor daya (INA219) pada *firmware* ESP32.
4. Mengembangkan dan mengintegrasikan model kontrol berbasis *Reinforcement Learning* (TD3) dari awal (*from scratch*) untuk kebutuhan integrasi kontrol penjadwalan penyemprotan adaptif.
5. Mengevaluasi kinerja sistem secara kuantitatif melalui pengujian *unit*, pengujian beban (*stress test*), dan pengujian resiliensi (*chaos engineering*), meliputi metrik latensi, *throughput*, dan tingkat keberhasilan pengiriman pesan.

#### 1.4 Lingkup Permasalahan, Asumsi, dan Hipotesis

Agar cakupan penelitian tetap terarah dan terukur, batasan ruang lingkup masalah ditetapkan sebagai berikut:

1. Fokus penelitian berada pada perancangan, implementasi, dan pengujian modularitas arsitektur *microservice* serta integrasi kontrol adaptif aeroponik, bukan pada optimasi algoritma *Reinforcement Learning*.
2. Pembahasan arsitektur server difokuskan secara mendalam pada layanan-layanan inti, yaiti: Auth Service (manajemen autentikasi terpusat, RBAC, dan penerbitan JWT), Module Service (registrasi perangkat dan *ingestion* telemetri), Control Service (arbitrase mode kendali dan eksekusi perintah aktuasi), serta Analytics Service (agregasi deret waktu dan komputasi metrik). Layanan lainnya (Stream, Alert, Notification, Export, Audit, DLQ, WS-Gateway) berfungsi sebagai infrastruktur pendukung operasional.
3. Pengujian integrasi algoritma kontrol adaptif cerdas diteliti melalui alur terintegrasi yang melibatkan: Auth Service, Module Service, Control Service, Stream Service, ML Service, model-control, dan model-controller.
4. Algoritma kecerdasan buatan untuk visi komputer (YOLOv8) diambil langsung dari model pra-latih (*pre-trained*) untuk mengekstraksi informasi visual (panjang akar dan kondisi umbi tanaman), sedangkan algoritma *Reinforcement Learning* (TD3) dikembangkan dari awal dengan lingkungan khusus aeroponik namun dibatasi hanya untuk kebutuhan integrasi kontrol penjadwalan adaptif.
5. Domain sensor yang dipantau dibatasi pada: suhu udara, kelembapan udara, suhu larutan nutrisi, *electrical conductivity* (EC), pH larutan, dan status aktuator (pompa *misting* dan katup nutrisi).
6. *Firmware* dikembangkan khusus untuk platform ESP32 dengan *framework* Arduino via PlatformIO di atas FreeRTOS *dual-core*; modularitas *firmware* diuji secara spesifik melalui skenario penambahan *handler* protokol I2C untuk sensor daya (INA219) melalui pendaftaran konfigurasi `config.json` maupun antarmuka lokal *firmware*.
7. Protokol komunikasi antar-layanan menggunakan NATS JetStream; komunikasi API (REST/HTTP) digunakan khusus untuk komunikasi dengan layanan luar/komputasi Python (ML Service dan model-control/model-controller), sedangkan komunikasi *edge* antara *firmware* ESP32 dan server menggunakan protokol MQTT via Mosquitto.
8. Antarmuka pengguna, baik antarmuka lokal *firmware* (Captive Web Portal) maupun *dashboard* server (React Vite), dibatasi pembahasannya pada pemenuaan fungsi-fungsi operasional *monitoring*, konfigurasi, dan kontrol data, tanpa membahas perancangan detail estétika antarmuka.

Dalam pelaksanaan penelitian ini, digunakan asumsi-asumsi dasar sebagai berikut:

1. Jaringan WiFi lokal antara ESP32 dan server diasumsikan memiliki kualitas yang memadai untuk transmisi data telemetri dengan interval 5 detik secara stabil (latensi < 500 ms, *packet loss* < 1%).
2. Server *host* diasumsikan memiliki sumber daya komputasi minimal (RAM 8 GB, CPU 4 *core*, tanpa GPU) yang memadai untuk menjalalankan tumpukan Docker Compose secara bersamaan dalam lingkungan pengujian.
3. Sensor-sensor yang digunakan (suhu, EC, pH) diasumsikan telah dikalibrasi dan memberikan pembacaan yang akurat sesuai spesifikasi pabrikan sebelum pengujian dimulai.
4. Model TD3 yang dikembangkan diasumsikan telah dilatih pada lingkungan simulasi aeroponik dan siap untuk inferensi serta integrasi jadwal kontrol selama periode pengujian.
5. Seluruh layanan *backend* diasumsikan dapat berkomunikasi melalui jaringan Docker internal tanpa hambatan *firewall* atau pembatasan *port* di lingkungan pengujian.

Hipotesis awal yang diajukan dalam penelitian ini adalah: (1) arsitektur *microservice* dengan *database-per-service* dan komunikasi *event-driven* mampu mengisolasi kegagalan antar-layanan secara penuh; (2) *firmware* modular memungkinkan penambahan protokol baru tanpa kompilasi ulang; (3) model TD3 mampu menghasilkan jadwal *misting* adaptif yang lebih stabil dibandingkan kendali berbasiskan aturan tetap; serta (4) sistem memenuhi metrik latensi *end-to-end* di bawah 2 detik pada persentil ke-95.

Berikut ilustrasi arsitektur sistem secara keseluruhan:

**Gambar 1: Arsitektur sistem aeroponik berbasis dual-layer modularity**

---

## 2 KONSEP / TEORI DASAR

#### 2.1 Sistem Aeroponik dan Pertanian Presisi

Pertanian presisi mengandalkan data *real-time* sensor untuk kendali nutrisi dan aktuator secara otomatis. Pada aeroponik, akar tumbuh di udara dan disemprot nutrisi secara berkala sehingga suhu, kelembapan, *electrical conductivity* (EC), dan pH bersifat kritis dan wajib dipantau kontinu. Integrasi sensor cerdas dan kendali otomatis berpengaruh langsung terhadap stabilitas pertumbuhan tanaman, sehingga sistem harus mengakuisisi telemetri secara kontinu dan responsif.

#### 2.2 Arsitektur *Microservice* dan *Database-per-Service*

Arsitektur *microservice* mendefinisikan sebuah aplikasi sebagai kumpulan layanan kecil yang dapat di-*deploy* secara independen dan berkomunikasi melalui mekanisme ringan. Setiap layanan menerapkan prinsip *single responsibility* dan dipisahkan berdasarkan *bounded context*, sehingga perubahan pada satu layanan tidak memaksa penyebaran ulang layanan lain.

Salah satu prinsip utama arsitektur *microservice* adalah *database-per-service*, yakni setiap layanan memiliki basis data sendiri tanpa pembagian basis data antar layanan. Isolasi fisik dan logis antar basis data mencegah *cascading failure* serta memungkinkan evolusi skema secara independen. Dalam praktikanya, pendekatan *polyglot persistence* dipilih sesuai kebutuhan tiap layanan—basis data relasional untuk data transaksional, basis data deret waktu (*time-series*) untuk telemetri, serta *cache* dan *object storage* untuk kebutuhan pendukung.

#### 2.3 Protokol Komunikasi IoT: MQTT dan NATS JetStream

Komunikasi antar perangkat dalam sistem *Internet of Things* (IoT) memerlukan protokol yang ringan, efisien, dan mampu beroperasi pada jaringan dengan keterbatasan sumber daya. MQTT (*Message Queuing Telemetry Transport*), protokol publikasi–berlangganan (*publish-subscribe*) berbasis *broker* yang cocok untuk transmisi telemetri dari perangkat *edge* seperti ESP32 ke server, adalah standar ISO/IEC 20922:2016.

Untuk komunikasi antar layanan di sisi komputasi awak, pendekatan *event-driven architecture* memberikan dampak pada peningkatan performa dan isolasi kegagalan dibandingkan pola *request-response* sinkron. NATS JetStream merupakan implementasi sistem pesan berbasis peristalian yang menyediakan ketahanan melalui *persistence*, *streaming*, dan *replay* pesan, sehingga mendukung komunikasi antar-layanan yang longgar (*loosely coupled*) dan tahan terhadap kehilangan pesan. Kombinasi MQTT di sisi *edge* dan NATS JetStream di sisi layanan menjembatani dua domain komunikasi dengan prinsip *event-driven* yang konsisten.

#### 2.4 *Firmware* Modular ESP32 (*Edge*)

Mikrokontroler ESP32 merupakan platform berbiaya rendah yang banyak digunakan untuk sistem pemantauan IoT berbasis sensor. Dengan kemampuan konektivitas WiFi dan arsitektur *dual-core*, ESP32 berada pada lapisan *edge* yang bertugas mengakuisisi telemetri sensor dan mengontrol aktuator secara langsung tanpa ketergantungan penuh pada server.

Agar perangkat *edge* mudah dikembangkan dan dipelihara, *firmware* dirancang secara modular, di mana pembacaan sensor dan eksekusi aktuator dienkapsulasi dalam *handler* mandiri yang dapat ditambahkan melalui konfigurasi tanpa rekompilasi ulang. Pendekatan ini selaras dengan prinsip *microservice* di sisi server, memungkinkan penambahan protokol atau jenis sensor baru tanpa mengubah logika inti *firmware*.

#### 2.5 *Reinforcement Learning* (TD3) untuk Kontrol Adaptif

*Reinforcement learning* (RL) memungkinkan agen mempelajari kebijakan kendali melalui interaksi dengan lingkungan dan sinyal *reward* tanpa pemodelan eksplisit yang penuh. Salah satu algoritma RL untuk ruang kondisi dan aksi kontinu adalah *Twin Delayed Deep Deterministic Policy Gradient* (TD3), yang memperbaiki ketidakstabilan pelatihan DDPG melalui tiga mekanisme utama: pembaruan *policy* yang tertunda (*delayed*), estimasi nilai ganda (*twin critics*) untuk mengurangi overestimasi, dan penambahan *target smoothing noise*.

Pada sistem fisik kontinu seperti kendali penjadwalan *misting* aeroponik, TD3 mampu mempelajari kebijakan adaptif yang menjaga kestabilan variabel lingkungan (suhu, kelembapan, EC, pH) melalui pengaturan aktuasi secara berkala. Pendekatan berbasiskan RL ini memberikan kendali yang lebih responsif dibandingkan aturan tetap, sekaligus dapat diintegrasikan ke dalam arsitektur *microservice* sebagai layanan inferensi yang terpisah agar tidak menciptakan *tight coupling* dengan layanan lain.

#### 2.6 Visi Komputer (YOLOv8) sebagai Pendukung Kontrol

Visi komputer berperan sebagai pendukung kontrol dengan mengekstraksi informasi visual dari tanaman, seperti estimasi panjang akar dan kondisi umbi, yang kemudian digunakan untuk memperkaya umpan balik sistem kendali adaptif. Arsitektur deteksi objek *You Only Look Once* versi 8 (YOLOv8) memungkinkan inferensi citra secara *real-time* pada perangkat berbasis *edge* maupun layanan komputasi awak.

---

## 3 RANCANGAN / PERCOBAAN / SIMULASI

#### 3.1 Arsitektur Dual-Layer Modularity

Sistem dibangun sebagai arsitektur dua lapis. Lapisan *edge* berupa node ESP32 berbasis FreeRTOS dual-core yang menjalankan firmware modular, sedangkan lapisan *server* berupa 13 microservice mandiri yang diorkestrasi melalui Docker Compose. Komunikasi antara edge dan server menggunakan protokol MQTT melalui Mosquitto broker. Arsitektur sistem dirangkum pada Gambar 2.

**Gambar 2: Diagram deployment arsitektur sistem (SGAM layer structure)**

#### 3.2 Firmware Modular ESP32

Firmware pada sisi edge menerapkan *factory pattern* dan *protocol registry* (modular I/O, vector registry, map registry) sehingga penambahan handler protokol baru dapat dilakukan melalui antarmuka Captive Web Portal atau berkas `config.json` tanpa proses kompilasi ulang. Semua sensor dan aktuator didaftarkan di `config.json` dan di-instantiate oleh `HardwareManager::reloadConfiguration()`. 

Penambahan protokol baru dilakukan dengan 3 tahap: (1) definisikan kelas abstrak `ProtocolHandler` dengan `init()` dan `read()` pure virtual, (2) implementasikan kelas konkret seperti `I2CHandler`, (3) daftarkan lambda creator ke registry map di `HardwareManager::init()`.

Modularitas ini dibuktikan secara empiris dengan mengintegrasikan handler protokol I2C untuk sensor daya INA219 (address `0x40`, tipe `INA219`) tanpa perubahan kode pada `main.cpp` maupun `TelemetryTask`.

Berikut implementasi pembuatan instance handler di `HardwareManager::init()`:

```cpp
// HardwareManager.cpp — init()
ProtocolRegistry::registerProtocol("GPIO",
    []() -> ProtocolHandler* { return new GPIOInputHandler(); });

ProtocolRegistry::registerProtocol("MODBUS",
    []() -> ProtocolHandler* { return new ModbusHandler(); });

ProtocolRegistry::registerProtocol("I2C",
    []() -> ProtocolHandler* { return new I2CHandler(); });

ProtocolRegistry::registerProtocol("GPIO_OUT",
    []() -> ProtocolHandler* { return new GpioOutputHandler(); });
```

#### 3.3 Arsitektur Microservice Server

Arsitektur server menerapkan *database-per-service* pada layanan inti: Auth Service (autentikasi terpusat, RBAC, penerbitan JWT), Module Service (registrasi perangkat dan ingest telemetri), Control Service (arbitrase mode kendali dan eksekusi aktuator), serta Analytics Service (agregasi deret waktu pada TimescaleDB). 

Komunikasi antar-layanan menggunakan NATS JetStream dengan subjek kontrak eksplisit: `telemetry.ingest` (Core NATS, fan-out real-time), `telemetry.batch` (JetStream, durable consumer `analytics-batch` dengan replay), `alert.triggered` / `alert.resolved`, `system.status`, dan `audit.log` (Core NATS, append-only ke `mariadb-audit`). Semua akses REST melalui Kong API Gateway dengan prefix `/v1`, dilengkapi JWT validation, rate limiting, dan CORS.

#### 3.4 Kontrol Adaptif TD3 dan YOLOv8

Layanan *model-control* mengombinasikan state telemetri real-time (10D state vector) dengan metadata hasil deteksi visual dari *model-controller* (YOLOv8) untuk menghasilkan keputusan penjadwalan misting melalui algoritma TD3. State vektor 10D terdiri dari: panjang akar (`L_root`), status tanaman (`U_status`), suhu/k lembapan dalam dan luar (`T_in`, `H_in`, `T_out`, `H_out`), EC, pH, suhu larutan nutrisi (`T_nut`), dan indeks matahari (`I_day`).

Action 3D yang dihasilkan TD3: `D_mist` (durasi misting [10, 240] detik), `interval_sec` (interval [60, 540] detik), dan `A_valve` (valve ON/OFF). Keputusan dikirim ke Control Service hanya pada batas siklus (cycle-boundary) untuk mencegah reset timer berulang.

Alur kontrol adaptif:

```
model_control -> NATS + MinIO : telemetry.ingest, get_latest_metadata()
model_control -> model_controller : POST /predict {state 10D}
model_controller --> model_control : action [D_mist, interval, A_valve]
alt cycle selesai
  model_control -> Control Service : PUT /control/schedules + POST command
  Control Service -> MQTT : publish set_output {node_id, target, value}
  ESP32 -> MQTT : publish confirm {req_id, target, value, status:executed}
  Control Service -> Control Service : MarkAckedByReqID, status=acked
else
  model_control : lewati eksekusi (cycle belum selesai)
end
```

#### 3.5 Simulasi Lingkungan Aeroponik

Model pertumbuhan akur (root growth) mengikuti persamaan pertumbuhan logistik yang dibatasi oleh faktor lingkungan. Model ini dipertahankan pada `control-model-training/aeroponic_simulator.py`:

$$\Delta L_{\text{root}} = r_{\text{step}} \cdot 180 \cdot L_{\text{root}} \cdot \left(1 - \frac{L_{\text{root}}}{K}\right) \cdot f_{\text{lim}} \cdot d_{\text{day}}$$

(1)

dengan $L_{\text{root, baru}} = \max(0, L_{\text{root, lama}} + \Delta L_{\text{root}})$.

**Parameter model:**

| Simbol | Nilai | Satuan | Keterangan |
|--------|-------|--------|------------|
| $r_{\text{step}}$ | $1.5 \times 10^{-5}$ | cm/min | Laju pertumbuhan akar |
| $180$ | — | menit | Interval capture (3 jam) |
| $K$ | $300$ | cm | Kapasitas pembawa |
| $f_{\text{lim}}$ | $[0, 1]$ | — | Faktor pembatas lingkungan |
| $d_{\text{day}}$ | $1,2$ (siang) / $0,6$ (malam) | — | Multiplier periode siang/malam |

#### 3.6 Skenario Pengujian

Pengujian dilakukan dalam dua tahap: Tahap I (konfigurasi minimal, 4–10 node) dan Tahap II (konfigurasi penuh dengan layanan AI/ML). Pengujian mencakup:

1. **Unit test** fitur layanan melalui Kong Gateway `/v1` — verifikasi CRUD endpoint, autentikasi JWT/RBAC, dan kontrak respons JSON.
2. **Stress test** untuk mengukur throughput dan latensi P95 pada beban maksimum (30 node telemetri paralel + 10 user REST API sekaligus).
3. **Chaos engineering** untuk membuktikan isolasi kegagalan penuh (zero cascade failure) — membunuh satu layanan, database, broker, atau gateway secara acak dan memverifikasi semua layanan lain tetap beroperasi.

---

## 4 HASIL DAN ANALISIS

#### 4.1 Hasil Chaos Engineering

Pengujian chaos engineering dilakukan dengan membunuh paksa satu komponen sistem secara acak (Auth Service, Module Service, Control Service, MariaDB, TimescaleDB, Redis, MinIO, Mosquitto, NATS, Kong, WS-Gateway) dan memverifikasi bahwa layanan lain tetap beroperasi tanpa *cascading failure*.

Hasil menunjukkan seluruh skenario chaos engineering berhasil dengan kelulusan 100%:

| Tahap | Chaos Scenario | Result |
|-------|----------------|--------|
| I | Auth Service down | ✅ All other services continue |
| I | MariaDB module down | ✅ REST degrades, MQTT ingested |
| I | NATS down | ✅ MQTT + cache survive |
| I | Kong down | ✅ Direct service access works |
| I | Total: 43 scenarios | ✅ 43 PASS, 0 FAIL |
| II | All core + AI/ML services down (staggered) | ✅ Zero cascade failure |
| II | Total: 50 scenarios | ✅ 50 PASS, 0 FAIL |

**Tabel 1. Hasil chaos engineering (zero cascade failure)**

#### 4.2 Hasil Stress Test

Berikut ringkasan kinerja throughput, latensi, dan sumber daya:

| Parameter Pengujian | Tahap I | Tahap II |
|---|---|---|
| Throughput puncak (RPS) | 51,3 | 68 |
| Latensi P95 API (ms) | 1482 | 1275 |
| Error rate (%) | 2,1 | 4,5 |
| Latensi MQTT p95 (ms) | 5,2 | 7,8 |
| Throughput MQTT (msg/s) | 4,26 | 11,5 |
| Total RAM (MB) | 800 | 1700 |
| Peak CPU (%) | 9,69 | 27,5 |

**Tabel 2. Ringkasan kinerja throughput, latensi, dan sumber daya**

Berdasarkan Tabel 2, performa REST API Gateway meningkat dari 51,3 RPS menjadi 68 RPS dengan latensi P95 turun dari 1482 ms menjadi 1275 ms. Pelipatgandaan node dari 4 menjadi 10 meningkatkan throughput MQTT sebesar 170% tanpa menimbulkan bottleneck, dengan utilizasi sumber daya tetap efisien (peak CPU 27,5% dan rata-rata RAM per layanan 54,6 MB).

**Gambar 3: Grafik perbandingan kinerja Tahap I dan Tahap II**

#### 4.3 Analisis Latensi End-to-End

Latensi end-to-end dari pengukuran sensor pada ESP32 hingga tampilan pada dashboard React diukur melalui WebSocket ke WS-Gateway:

$$L_{\text{e2e}} = L_{\text{sensor}} + L_{\text{telemetry}} + L_{\text{MQTT}} + L_{\text{ingest}} + L_{\text{NATS}} + L_{\text{WS}} + L_{\text{dashboard}}$$

(2)

Dengan $L_{\text{e2e,p95}} < 2000$ ms terpenuhi pada kedua tahap pengujian, sesuai hipotesis.

---

## 5 KESIMPULAN

Arsitektur *dual-layer modularity* berhasil memisahkan dependensi perangkat keras di edge dan komputasi di server sehingga kedua lapisan dapat dikembangkan secara independen. Penerapan *factory pattern* dan *protocol registry* memungkinkan integrasi sensor baru (I2C INA219) secara dinamis tanpa kompilasi ulang. Alur telemetri dan kontrol berjalan aman melalui MQTT, NATS JetStream, Kong API Gateway, dan prinsip *database-per-service* yang terbukti mencegah kegagalan beruntun (zero cascade failure). Model YOLOv8 dan TD3 beroperasi sebagai microservice independen, dan hasil chaos engineering serta stress test membuktikan keandalan serta kinerja sistem dengan latensi end-to-end di bawah 2 detik pada persentil ke-95.

Hipotesis penelitian terbukti secara empiris:

1. Arsitektur *microservice* dengan *database-per-service* dan komunikasi *event-driven* berhasil mengisolasi kegagalan antar-layanan secara penuh (100% chaos pass rate).
2. *Firmware* modular memungkinkan penambahan protokol I2C baru tanpa kompilasi ulang.
3. Model TD3 menghasilkan jadwal *misting* adaptif yang stabil melalui integrasi state 10D dan deteksi visual YOLOv8.
4. Sistem memenuhi metrik latensi end-to-end di bawah 2 detik pada persentil ke-95.

---

## 6 DAFTAR PUSTAKA

[1] P. Jamshidi, A. Heydarnoori, dan P. Jamshidi, "Microservices Migration Patterns," IEEE Software, vol. 35, no. 3, hal. 42–49, 2018. https://doi.org/10.1109/MS.2018.2141035

[2] A. Al-Fuqaha, M. Guizani, M. Mohammadi, M. Aledhari, dan M. Ayyash, "Internet of Things: A Survey on Enabling Technologies, Protocols, and Applications," IEEE Communications Surveys & Tutorials, vol. 17, no. 4, hal. 2347–2376, 2015. https://doi.org/10.1109/COMST.2015.2444095

[3] I. A. Lakhiar, G. Jianmin, T. N. Syed, F. A. Chandio, dan N. A. Buttar, "Monitoring and control systems in agriculture using intelligent sensor techniques: A review of the aeroponic system," Journal of Sensors, vol. 2018, hal. 8672769, 2018. https://doi.org/10.1155/2018/8672769

[4] C. Saldaña Enderica, J. R. Llata, dan C. Torre-Ferrero, "Guided Reinforcement Learning with Twin Delayed Deep Deterministic Policy Gradient for a Rotary Flexible-Link System," Robotics, vol. 14, no. 6, hal. 76, 2025. https://doi.org/10.3390/robotics14060076

[5] S. D. Kalamaras, M.-A. Tsitsimpikou, C. A. Tzenos, A. A. Lithourgidis, D. S. Pitsikoglou, dan T. A. Kotsopoulos, "A Low-Cost IoT System Based on the ESP32 Microcontroller for Efficient Monitoring of a Pilot Anaerobic Biogas Reactor," Applied Sciences, vol. 15, no. 1, hal. 34, 2025. https://doi.org/10.3390/app15010034

[6] H. Cabane dan K. Farias, "On the impact of event-driven architecture on performance: An exploratory study," Future Generation Computer systems, vol. 153, hal. 123–140, 2024. https://doi.org/10.1016/j.future.2024.107102

[7] A. Basiri, N. Behnam, R. de Rooij, L. Hochstein, L. Kosewski, J. Reynolds, dan C. Rosenthal, "Chaos Engineering," IEEE Software, vol. 33, no. 3, hal. 35–41, 2016. https://doi.org/10.1109/MS.2016.60

[8] W. Vogels, "Eventually Consistent," Communications of the ACM, vol. 52, no. 1, hal. 40–44, 2009. https://doi.org/10.1145/1435417.1435432

[9] A. Lercher, J. Glock, C. Macho, dan M. Pinzger, "Microservice API Evolution in Practice: A Study on Strategies and Challenges," Journal of Systems and Software, vol. 215, hal. 112110, 2024. https://doi.org/10.1016/j.jss.2024.112110

[10] L. Giamattei, A. Guerriero, R. Pietrantuono, S. Russo, I. Malavolta, T. Islam, M. Dînga, A. Koziolek, S. Singh, M. Armbruster, J. M. Gutierrez-Martinez, S. Caro-Alvaro, D. Rodriguez, S. Weber, J. Henss, E. Fernandez Vogelin, dan F. S. Panojo, "Monitoring tools for DevOps and microservices: A systematic grey literature review," Journal of Systems and Software, vol. 208, hal. 111906, 2024. https://doi.org/10.1016/j.jss.2023.111906

---

> **Petunjuk Format Microsoft Word:**
>
> 1. **Page Setup:** Ukuran A4, top margin 25mm, bottom margin 25mm, mirror margins (inside 30mm, outside 20mm).
>
> 2. **Judul (halaman pertama):** Arial 14pt, bold, centered.
>
> 3. **Nama + Program Studi:** Arial 10pt, centered. Lompat satu baris.
>
> 4. **ABSTRAK:** Arial 12pt, bold, centered, huruf kapital semua.
>
> 5. **Teks abstrak:** Arial 10pt, italic, single spacing, justified. Panjang maksimal 6 halaman dokumen penuh.
>
> 6. **Kata kunci:** 4 kata kunci, Arial 10pt. Format: `kata kunci: kata1, kata2, kata3, kata4`
>
> 7. **Nomor BAB:** Arial 12pt, bold, centered, huruf kapital. Contoh: `1 PENDAHULUAN`
>
> 8. **Sub-judul nomor 1.x:** Arial 10pt, bold. Contoh: `1.1 Latar Belakang`
>
> 9. **Teks utama:** Arial 10pt, single column, single line spacing, full justification. Lompat satu baris antar paragraf dan antara sub-judul dan badan teks.
>
> 10. **Gambar:** Diletakkan di tengah. Caption di bawah gambar, Arial 10pt.
>
> 11. **Persamaan:** Gunakan SI untuk satuan. Nomor persamaan dalam tanda kurung di margin kanan. Pastikan simbol didefinisikan sebelum atau setelah persamaan.
>
> 12. **Tabel:** Diletakkan di tengah. Judul tabel di atas, Arial 8pt, bold.
>
> 13. **Daftar Pustaka:** Gunakan penulisan sumber pustaka sesuai format IEEE (angka urut [1], [2], dst.).
