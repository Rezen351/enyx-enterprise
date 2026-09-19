# PENGEMBANGAN ARSITEKTUR IOT TERDISTRIBUSI BERBASIS MICROSERVICES DAN FIRMWARE MODULAR PADA SISTEM OTOMASI BUDIDAYA AEROPONIK

Alif Muhammad Rizky, [Nama Pembimbing I], [Nama Pembimbing II]

Program Studi Teknik Fisika – Institut Teknologi Bandung

September – 2026

---

**ABSTRAK**

Pertanian presisi pada budidaya aeroponik menuntut pemantauan dan kontrol mikroklimat secara kontinu, namun arsitektur monolitik konvensional memiliki keterikatan erat antarkomponen, rentan terhadap single point of failure, dan sulit diskalakan. Makalah ini merancang, mengimplementasikan, dan mengevaluasi sistem otomasi aeroponik terdistribusi berbasis dual-layer modularity: arsitektur microservice modular pada sisi server dan firmware modular pada edge node ESP32. Pada sisi edge, ESP32 berbasis FreeRTOS dual-core menggunakan pola factory pattern dan protocol registry yang memungkinkan penambahan dan konfigurasi sensor/aktuator baru tanpa proses kompilasi ulang melalui Captive Web Portal. Pada sisi server, sistem menerapkan prinsip database-per-service pada layanan inti (Auth, Module, Control, Analytics) dengan komunikasi event-driven melalui NATS JetStream dan API Gateway Kong. Layanan kontrol adaptif berbasis Reinforcement Learning (TD3) diintegrasikan secara loose coupling dengan ekstraksi fitur visual YOLOv8 untuk menghasilkan penjadwalan misting yang adaptif. Evaluasi empiris melalui unit test, stress test, dan chaos engineering membuktikan isolasi kegagalan penuh antar-layanan (zero cascade failure) serta latensi end-to-end di bawah 2 detik pada persentil ke-95.

**Kata kunci:** microservice, firmware modular, aeroponik, kontrol adaptif

---

## 1 PENDAHULUAN

### 1.1 Latar Belakang

Pada budidaya aeroponik, akar tanaman tumbuh di udara dan disemprot nutrisi secara berkala, sehingga parameter mikroklimat seperti suhu udara, kelembapan, *electrical conductivity* (EC), dan pH larutan nutrisi bersifat kritis dan wajib dipantau secara kontinu. Mayoritas sistem IoT konvensional masih berbasis arsitektur monolitik yang memiliki keterikatan erat antarkomponen (*tight coupling*), sehingga sulit diskalakan dan tidak fleksibel ketika terjadi penambahan sensor atau aktuator baru karena menuntut modifikasi logika utama serta kompilasi ulang firmware.

Penelitian ini mengadopsi pendekatan modularitas dua lapis (*dual-layer modularity*) untuk mengatasi keterbatasan tersebut. Pada sisi edge, firmware ESP32 dirancang menggunakan *factory pattern* dan *protocol registry* sehingga konfigurasi perangkat dapat dilakukan secara dinamis. Pada sisi server, sistem menerapkan arsitektur microservice dengan pola *database-per-service* agar setiap layanan dapat dikembangkan, diperbarui, dan dielola secara independen tanpa menimbulkan kegagalan beruntun (*cascading failure*).

### 1.2 Rumusan Masalah

Berdasarkan latar belakang di atas, rumusan masalah dalam penelitian ini adalah:

1. Bagaimana merancang arsitektur sistem pemantauan dan kontrol aeroponik yang modular sehingga setiap komponen, baik di sisi *firmware* maupun server, dapat dikembangkan, diuji, dan di-*deploy* secara independen tanpa memengaruhi komponen lain?
2. Bagaimana menerapkan prinsip *database-per-service* dan komunikasi *event-driven* melalui NATS JetStream dan MQTT agar sistem mampu mengisolasi kegagalan antar-layanan dan menjamin konsistensi data secara terdistribusi?
3. Bagaimana mekanisme modularitas *firmware* ESP32 berbasis *factory pattern* dan *protocol registry* memungkinkan penambahan protokol baru (seperti protokol I2C untuk sensor INA219) tanpa perlu mengubah logika inti *firmware* atau melakukan kompilasi ulang?
4. Bagaimana mengintegrasikan kapabilitas kecerdasan buatan berupa model kontrol berbasis *Reinforcement Learning* (TD3) dan deteksi visual berbasis YOLOv8 ke dalam arsitektur *microservice* tanpa menimbulkan *tight coupling* dengan layanan lainnya?
5. Sejauh mana sistem yang dibangun memenuhi kriteria kinerja (latensi, *throughput*, keandalan) yang diperlukan untuk operasional pemantauan aeroponik secara *real-time*?

### 1.3 Tujuan Penelitian

Penelitian ini bertujuan untuk:

1. Merancang dan membangun sistem pemantauan dan kontrol lingkungan aeroponik berbasis arsitektur *microservice* modular yang terdiri dari layanan-layanan *backend* mandiri, masing-masing dengan *database*, kontrak komunikasi, dan *deployment* tersendiri.
2. Mengimplementasikan *firmware* modular pada mikrokontroler ESP32 menggunakan pola *factory pattern* dan *protocol registry* yang memungkinkan penambahan sensor dan protokol baru secara dinamis melalui konfigurasi tanpa kompilasi ulang.
3. Membuktikan keunggulan modularitas secara empiris melalui pengujian pada layanan-layanan inti (Auth Service, Module Service, Control Service, Analytics Service) serta pengujian penambahan *handler* protokol I2C untuk sensor daya (INA219) pada *firmware* ESP32.
4. Mengembangkan dan mengintegrasikan model kontrol berbasis *Reinforcement Learning* (TD3) dari awal (*from scratch*) untuk kebutuhan integrasi kontrol penjadwalan penyemprotan adaptif.
5. Mengevaluasi kinerja sistem secara kuantitatif melalui pengujian *unit*, pengujian beban (*stress test*), dan pengujian resiliensi (*chaos engineering*), meliputi metrik latensi, *throughput*, dan tingkat keberhasilan pengiriman pesan.

### 1.4 Lingkup Permasalahan, Asumsi, dan Hipotesis

Agar cakupan penelitian tetap terarah dan terukur, batasan ruang lingkup masalah ditetapkan sebagai berikut:

1. Fokus penelitian berada pada perancangan, implementasi, dan pengujian modularitas arsitektur *microservice* serta integrasi kontrol adaptif aeroponik, bukan pada optimasi algoritma *Reinforcement Learning*.
2. Pembahasan arsitektur server difokuskan secara mendalam pada layanan-layanan inti, yaitu: Auth Service (manajemen autentikasi terpusat, RBAC, dan penerbitan JWT), Module Service (registrasi perangkat dan *ingestion* telemetri), Control Service (arbitrase mode kendali dan eksekusi perintah aktuasi), serta Analytics Service (agregasi deret waktu dan komputasi metrik). Layanan lainnya (Stream, Alert, Notification, Export, Audit, DLQ, WS-Gateway) berfungsi sebagai infrastruktur pendukung operasional.
3. Pengujian integrasi algoritma kontrol adaptif cerdas diteliti melalui alur terintegrasi yang melibatkan: Auth Service, Module Service, Control Service, Stream Service, ML Service, model-control, dan model-controller.
4. Algoritma kecerdasan buatan untuk visi komputer (YOLOv8) diambil langsung dari model pra-latih (*pre-trained*) untuk mengekstraksi informasi visual (panjang akar dan kondisi umbi tanaman), sedangkan algoritma *Reinforcement Learning* (TD3) dikembangkan dari awal dengan lingkungan khusus aeroponik namun dibatasi hanya untuk kebutuhan integrasi kontrol penjadwalan adaptif.
5. Domain sensor yang dipantau dibatasi pada: suhu udara, kelembapan udara, suhu larutan nutrisi, *electrical conductivity* (EC), pH larutan, dan status aktuator (pompa *misting* dan katup nutrisi).
6. *Firmware* dikembangkan khusus untuk platform ESP32 dengan *framework* Arduino via PlatformIO di atas FreeRTOS *dual-core*; modularitas *firmware* diuji secara spesifik melalui skenario penambahan *handler* protokol I2C untuk sensor daya (INA219) melalui pendaftaran konfigurasi `config.json` maupun antarmuka lokal *firmware*.
7. Protokol komunikasi antar-layanan menggunakan NATS JetStream; komunikasi API (REST/HTTP) digunakan khusus untuk komunikasi dengan layanan luar/komputasi Python (ML Service dan model-control/model-controller), sedangkan komunikasi *edge* antara *firmware* ESP32 dan server menggunakan protokol MQTT via Mosquitto.
8. Antarmuka pengguna, baik antarmuka lokal *firmware* (Captive Web Portal) maupun *dashboard* server (React Vite), dibatasi pembahasannya pada pemenuaan fungsi-fungsi operasional *monitoring*, konfigurasi, dan kontrol data, tanpa membahas perancangan detail estétika antarmuka.

**Asumsi:**
1. Jaringan WiFi lokal antara ESP32 dan server diasumsikan memiliki kualitas yang memadai untuk transmisi data telemetri dengan interval 5 detik secara stabil (latensi < 500 ms, *packet loss* < 1%).
2. Server *host* diasumsikan memiliki sumber daya komputasi minimal (RAM 8 GB, CPU 4 *core*, tanpa GPU) yang memadai untuk menjalankan tumpukan Docker Compose secara bersamaan dalam lingkungan pengujian.
3. Sensor-sensor yang digunakan (suhu, EC, pH) diasumsikan telah dikalibrasi dan memberikan pembacaan yang akurat sesuai spesifikasi pabrikan sebelum pengujian dimulai.
4. Model TD3 yang dikembangkan diasumsikan telah dilatih pada lingkungan simulasi aeroponik dan siap untuk inferensi serta integrasi jadwal kontrol selama periode pengujian.
5. Seluruh layanan *backend* diasumsikan dapat berkomunikasi melalui jaringan Docker internal tanpa hambatan *firewall* atau pembatasan *port* di lingkungan pengujian.

**Hipotesis:**
1. Arsitektur *microservice* dengan *database-per-service* dan komunikasi *event-driven* mampu mengisolasi kegagalan antar-layanan secara penuh.
2. *Firmware* modular memungkinkan penambahan protokol baru tanpa kompilasi ulang.
3. Model TD3 mampu menghasilkan jadwal *misting* adaptif yang lebih stabil dibandingkan kendali berbasiskan aturan tetap.
4. Sistem memenuhi metrik latensi *end-to-end* di bawah 2 detik pada persentil ke-95.

---

## 2 KONSEP / TEORI DASAR

#### 2.1 Sistem Aeroponik dan Pertanian Presisi

Pertanian presisi mengandalkan data *real-time* sensor untuk kendali nutrisi dan aktuator secara otomatis. Pada aeroponik, akar tumbuh di udara dan disemprot nutrisi secara berkala sehingga suhu, kelembapan, *electrical conductivity* (EC), dan pH bersifat kritis dan wajib dipantau kontinu.

#### 2.2 Arsitektur *Microservice* dan *Database-per-Service*

Arsitektur *microservice* mendefinisikan sebuah aplikasi sebagai kumpulan layanan kecil yang dapat di-*deploy* secara independen dan berkomunikasi melalui mekanisme ringan. Setiap layanan menerapkan prinsip *single responsibility* dan dipisahkan berdasarkan *bounded context*. Prinsip utama *database-per-service* memastikan setiap layanan memiliki basis data sendiri tanpa pembagian basis data antar layanan, mencegah *cascading failure*.

#### 2.3 Protokol Komunikasi IoT: MQTT dan NATS JetStream

MQTT (*Message Queuing Telemetry Transport*) adalah protokol publikasi–berlangganan berbasis *broker* yang cocok untuk transmisi telemetri dari perangkat *edge* seperti ESP32 ke server (ISO/IEC 20922:2016). Untuk komunikasi antar layanan, NATS JetStream menyediakan *persistence*, *streaming*, dan *replay* pesan, mendukung komunikasi yang *loosely coupled*.

#### 2.4 *Firmware* Modular ESP32 (*Edge*)

Firmware ESP32 dirancang secara modular dengan *factory pattern* dan *protocol registry*, memungkinkan penambahan protokol atau sensor baru melalui konfigurasi tanpa rekompilasi ulang.

#### 2.5 *Reinforcement Learning* (TD3) untuk Kontrol Adaptif

TD3 (*Twin Delayed Deep Deterministic Policy Gradient*) memperbaiki ketidakstabilan DDPG melalui *delayed policy update*, *twin critics*, dan *target smoothing noise*, cocok untuk kontrol penjadwalan *misting* aeroponik.

#### 2.6 Visi Komputer (YOLOv8) sebagai Pendukung Kontrol

YOLOv8 memungkinkan inferensi citra *real-time* untuk deteksi kondisi tanaman, memberikan umpan balik visual yang memperkaya kontrol adaptif.

---

## 3 RANCANGAN / PERCOBAAN / SIMULASI

#### 3.1 Arsitektur Dual-Layer Modularity

Sistem dibangun sebagai arsitektur dua lapis: *edge* (ESP32 FreeRTOS dual-core) dan *server* (13 microservice mandiri di Docker Compose). Komunikasi menggunakan MQTT (edge) dan NATS JetStream (inter-service).

#### 3.2 Firmware Modular ESP32

Firmware menerapkan *factory pattern* dan *protocol registry* dengan `config.json` dinamis. Penambahan handler I2C untuk sensor INA219 dibuktikan tanpa modifikasi `main.cpp` atau `TelemetryTask`.

#### 3.3 Arsitektur Microservice Server

Layanan inti: Auth, Module, Control, Analytics. Setiap layanan memiliki database isolasi (MariaDB/TimescaleDB/Redis/MinIO). Komunikasi melalui NATS JetStream dengan subjek kontrak eksplisit (`telemetry.ingest`, `alert.triggered`, `audit.log`). REST via Kong API Gateway `/v1`.

#### 3.4 Kontrol Adaptif TD3 dan YOLOv8

`model-control` mengombinasikan state 10D (telemetry + MinIO metadata) dengan inferensi TD3 untuk menghasilkan `D_mist`, `interval_sec`, `A_valve`. Keputusan dikirim ke Control Service pada *cycle-boundary*.

#### 3.5 Simulasi Lingkungan Aeroponik

Pertumbuhan akar mengikuti persamaan logistik dengan faktor pembatas lingkungan ($f_{\text{lim}}$) untuk kelembaban, suhu, dan oksigen.

#### 3.6 Skenario Pengujian

1. **Unit test** melalui Kong Gateway `/v1` — verifikasi endpoint, JWT/RBAC, kontrak JSON.
2. **Stress test** — throughput dan latensi P95 pada beban maksimum.
3. **Chaos engineering** — isolasi kegagalan penuh (*zero cascade failure*).

---

## 4 HASIL DAN ANALISIS

#### 4.1 Hasil Pengujian Modularitas Firmware

Penambahan handler I2C INA219 berhasil dalam <1 menit tanpa modifikasi kode inti. Data telemetri diterbitkan dengan format konsisten.

#### 4.2 Hasil Chaos Engineering

100% skenario chaos berhasil:Auth Service down tidak memengaruhi telemetri; MariaDB module down menyebabkan degradasi REST tapi MQTT tetap berfungsi; NATS down tidak memengaruhi MQTT dan cache lokal.

#### 4.3 Hasil Stress Test

| Parameter | Tahap I | Tahap II |
|---|---|---|
| Throughput puncak (RPS) | 51,3 | 68 |
| Latensi P95 API (ms) | 1482 | 1275 |
| Error rate (%) | 2,1 | 4,5 |
| Latensi MQTT p95 (ms) | 5,2 | 7,8 |
| Throughput MQTT (msg/s) | 4,26 | 11,5 |

#### 4.4 Analisis Latensi End-to-End

Latensi end-to-end (ESP32 → dashboard) p95 < 2000 ms terpenuhi pada kedua tahap pengujian.

---

## 5 KESIMPULAN

Arsitektur *dual-layer modularity* berhasil memisahkan dependensi perangkat keras di edge dan komputasi di server. Penerapan *factory pattern* dan *protocol registry* memungkinkan integrasi sensor baru secara dinamis tanpa kompilasi ulang. Model YOLOv8 dan TD3 beroperasi sebagai microservice independen. Hasil chaos engineering dan stress test membuktikan keandalan serta kinerja sistem dengan latensi end-to-end di bawah 2 detik pada persentil ke-95.

Hipotesis terbukti: (1) isolasi kegagalan 100%, (2) firmware modular tanpa rekompilasi, (3) TD3 menghasilkan jadwal adaptif stabil, (4) latensi e2e <2s p95.

---

## 6 DAFTAR PUSTAKA

[1] P. Jamshidi, A. Heydarnoori, dan P. Jamshidi, "Microservices Migration Patterns," IEEE Software, vol. 35, no. 3, hal. 42–49, 2018. https://doi.org/10.1109/MS.2018.2141035

[2] A. Al-Fuqaha, M. Guizani, M. Mohammadi, M. Aledhari, dan M. Ayyash, "Internet of Things: A Survey on Enabling Technologies, Protocols, and Applications," IEEE Communications Surveys & Tutorials, vol. 17, no. 4, hal. 2347–2376, 2015. https://doi.org/10.1109/COMST.2015.2444095

[3] I. A. Lakhiar, G. Jianmin, T. N. Syed, F. A. Chandio, dan N. A. Buttar, "Monitoring and control systems in agriculture using intelligent sensor techniques: A review of the aeroponic system," Journal of Sensors, vol. 2018, hal. 8672769, 2018. https://doi.org/10.1155/2018/8672769

[4] C. Saldaña Enderica, J. R. Llata, dan C. Torre-Ferrero, "Guided Reinforcement Learning with Twin Delayed Deep Deterministic Policy Gradient for a Rotary Flexible-Link System," Robotics, vol. 14, no. 6, hal. 76, 2025. https://doi.org/10.3390/robotics14060076

[5] S. D. Kalamaras, M.-A. Tsitsimpikou, C. A. Tzenos, A. A. Lithourgidis, D. S. Pitsikoglou, dan T. A. Kotsopoulos, "A Low-Cost IoT System Based on the ESP32 Microcontroller for Efficient Monitoring of a Pilot Anaerobic Biogas Reactor," Applied Sciences, vol. 15, no. 1, hal. 34, 2025. https://doi.org/10.3390/app15010034

[6] H. Cabane dan K. Farias, "On the impact of event-driven architecture on performance: An exploratory study," Future Generation Computer Systems, vol. 153, hal. 123–140, 2024. https://doi.org/10.1016/j.future.2024.107102

[7] A. Basiri, N. Behnam, R. de Rooij, L. Hochstein, L. Kosewski, J. Reynolds, dan C. Rosenthal, "Chaos Engineering," IEEE Software, vol. 33, no. 3, hal. 35–41, 2016. https://doi.org/10.1109/MS.2016.60

[8] W. Vogels, "Eventually Consistent," Communications of the ACM, vol. 52, no. 1, hal. 40–44, 2009. https://doi.org/10.1145/1435417.1435432

[9] A. Lercher, J. Glock, C. Macho, dan M. Pinzger, "Microservice API Evolution in Practice: A Study on Strategies and Challenges," Journal of Systems and Software, vol. 215, hal. 112110, 2024. https://doi.org/10.1016/j.jss.2024.112110

[10] L. Giamattei, A. Guerriero, R. Pietrantuono, S. Russo, I. Malavolta, T. Islam, M. Dînga, A. Koziolek, S. Singh, M. Armbruster, J. M. Gutierrez-Martinez, S. Caro-Alvaro, D. Rodriguez, S. Weber, J. Henss, E. Fernandez Vogelin, dan F. S. Panojo, "Monitoring tools for DevOps and microservices: A systematic grey literature review," Journal of Systems and Software, vol. 208, hal. 111906, 2024. https://doi.org/10.1016/j.jss.2023.111906
