# BAB I
# PENDAHULUAN

## 1.1 Latar Belakang

Pertanian presisi mengandalkan data *real-time* sensor untuk kendali otomatis nutrisi dan aktuator [2]. Pada budidaya aeroponik, akar tumbuh di udara dan disemprot nutrisi secara berkala sehingga suhu, kelembapan, *electrical conductivity* (EC), dan pH bersifat kritis serta wajib dipantau kontinu [3]. Arsitektur monolitik konvensional memiliki kelemahan *tight coupling*, rentan *single point of failure*, dan sukar diskalakan [1], sehingga penelitian ini mengadopsi arsitektur *microservice* dengan *database-per-service* yang dapat di-*deploy* mandiri [1].

Komunikasi antar-layanan menggunakan *event-driven architecture* via NATS JetStream yang meningkatkan skalabilitas dan isolasi kegagalan dibanding *request-response* sinkron [6], dengan Kong sebagai *API Gateway* tunggal [9]. Modularitas diterapkan ganda: *firmware* ESP32 (FreeRTOS *dual-core*) mengenkapsulasi sensor dalam *handler* mandiri yang ditambahkan via `config.json` tanpa rekompilasi berkat *factory pattern* dan *protocol registry* [5], serta layanan server dalam kontainer Docker dengan kontrak NATS/MQTT eksplisit [1]. Kontrol adaptif menggunakan *Reinforcement Learning* TD3 yang mempelajari kebijakan penjadwalan *misting* stabil untuk sistem fisik kontinu [4].

Keandalan divalidasi melalui *chaos engineering* [7], dengan pengelolaan konsistensi *eventually consistent* [8] dan *monitoring* terpusat Prometheus/Grafana [10]. Penelitian ini merancang dan mengevaluasi sistem aeroponik dengan modularitas ganda (*dual-layer modularity*) yang memisahkan dependensi perangkat keras dan komputasi awan, dibuktikan empiris melalui pengujian resiliensi, beban, dan integrasi kontrol adaptif.

## 1.2 Rumusan Masalah

Berdasarkan latar belakang yang telah diuraikan, rumusan masalah dalam penelitian ini adalah:

1. Bagaimana merancang arsitektur sistem pemantauan dan kontrol aeroponik yang modular sehingga setiap komponen, baik di sisi *firmware* maupun server, dapat dikembangkan, diuji, dan di-*deploy* secara independen tanpa memengaruhi komponen lain?
2. Bagaimana menerapkan prinsip *database-per-service* dan komunikasi *event-driven* melalui NATS JetStream dan MQTT agar sistem mampu mengisolasi kegagalan antar-layanan dan menjamin konsistensi data secara terdistribusi?
3. Bagaimana mekanisme modularitas *firmware* ESP32 berbasis *factory pattern* dan *protocol registry* memungkinkan penambahan protokol baru (seperti protokol I2C untuk sensor INA219) tanpa perlu mengubah logika inti *firmware* atau melakukan kompilasi ulang?
4. Bagaimana mengintegrasikan kapabilitas kecerdasan buatan berupa model kontrol berbasis *Reinforcement Learning* (TD3) dan deteksi visual berbasis YOLOv8 ke dalam arsitektur *microservice* tanpa menimbulkan *tight coupling* dengan layanan lainnya?
5. Sejauh mana sistem yang dibangun memenuhi kriteria kinerja (latensi, *throughput*, keandalan) yang diperlukan untuk operasional pemantauan aeroponik secara *real-time*?

## 1.3 Tujuan Penelitian

Penelitian ini bertujuan untuk:

1. Merancang dan membangun sistem pemantauan dan kontrol lingkungan aeroponik berbasis arsitektur *microservice* modular yang terdiri dari layanan-layanan *backend* mandiri, masing-masing dengan *database*, kontrak komunikasi, dan *deployment* tersendiri.
2. Mengimplementasikan *firmware* modular pada mikrokontroler ESP32 menggunakan pola *factory pattern* dan *protocol registry* yang memungkinkan penambahan sensor dan protokol baru secara dinamis melalui konfigurasi tanpa kompilasi ulang.
3. Membuktikan keunggulan modularitas secara empiris melalui pengujian pada layanan-layanan inti (Auth Service, Module Service, Control Service, Analytics Service) serta pengujian penambahan *handler* protokol I2C untuk sensor INA219 pada *firmware* ESP32.
4. Mengembangkan dan mengintegrasikan model kontrol berbasis *Reinforcement Learning* (TD3) dari awal (*from scratch*) untuk kebutuhan integrasi kontrol penjadwalan penyemprotan adaptif.
5. Mengevaluasi kinerja sistem secara kuantitatif melalui pengujian *unit*, pengujian beban (*stress test*), dan pengujian resiliensi (*chaos engineering*), meliputi metrik latensi, *throughput*, dan tingkat keberhasilan pengiriman pesan.

## 1.4 Lingkup Permasalahan, Asumsi, dan Hipotesis

Agar cakupan penelitian tetap terarah dan terukur, batasan ruang lingkup masalah ditetapkan sebagai berikut:

1. Fokus penelitian berada pada perancangan, implementasi, dan pengujian modularitas arsitektur *microservice* serta integrasi kontrol adaptif aeroponik, bukan pada optimasi algoritma *Reinforcement Learning*.
2. Pembahasan arsitektur server difokuskan secara mendalam pada layanan-layanan inti, yaitu: Auth Service (manajemen autentikasi terpusat, RBAC, dan penerbitan JWT), Module Service (registrasi perangkat dan *ingestion* telemetri), Control Service (arbitrase mode kendali dan eksekusi perintah aktuasi), serta Analytics Service (agregasi deret waktu dan komputasi metrik). Layanan lainnya (Stream, Alert, Notification, Export, Audit, DLQ, WS-Gateway) berfungsi sebagai infrastruktur pendukung operasional.
3. Pengujian integrasi algoritma kontrol adaptif cerdas diteliti melalui alur terintegrasi yang melibatkan: Auth Service, Module Service, Control Service, Stream Service, ML Service, model-control, dan model-controller.
4. Algoritma kecerdasan buatan untuk visi komputer (YOLOv8) diambil langsung dari model pra-latih (*pre-trained*) untuk mengekstraksi informasi visual (panjang akar dan kondisi umbi tanaman), sedangkan algoritma *Reinforcement Learning* (TD3) dikembangkan dari awal dengan lingkungan khusus aeroponik namun dibatasi hanya untuk kebutuhan integrasi kontrol penjadwalan adaptif.
5. Domain sensor yang dipantau dibatasi pada: suhu udara, kelembapan udara, suhu larutan nutrisi, *electrical conductivity* (EC), pH larutan, dan status aktuator (pompa *misting* dan katup nutrisi).
6. *Firmware* dikembangkan khusus untuk platform ESP32 dengan *framework* Arduino via PlatformIO di atas FreeRTOS *dual-core*; modularitas *firmware* diuji secara spesifik melalui skenario penambahan *handler* protokol I2C untuk sensor daya (IN219) melalui pendaftaran konfigurasi `config.json` maupun antarmuka lokal *firmware*.
7. Protokol komunikasi antar-layanan menggunakan NATS JetStream; komunikasi API (REST/HTTP) digunakan khusus untuk komunikasi dengan layanan luar/komputasi Python (ML Service dan model-control/model-controller), sedangkan komunikasi *edge* antara *firmware* ESP32 dan server menggunakan protokol MQTT via Mosquitto.
8. Antarmuka pengguna, baik antarmuka lokal *firmware* (Captive Web Portal) maupun *dashboard* server (React Vite), dibatasi pembahasannya pada pemenuhan fungsi-fungsi operasional *monitoring*, konfigurasi, dan kontrol data, tanpa membahas perancangan detail estetika antarmuka.

Dalam pelaksanaan penelitian ini, digunakan asumsi-asumsi dasar sebagai berikut:

1. Jaringan WiFi lokal antara ESP32 dan server diasumsikan memiliki kualitas yang memadai untuk transmisi data telemetri dengan interval 5 detik secara stabil (latensi < 500 ms, *packet loss* < 1%).
2. Server *host* diasumsikan memiliki sumber daya komputasi minimal (RAM 8 GB, CPU 4 *core*, tanpa GPU) yang memadai untuk menjalankan tumpukan Docker Compose secara bersamaan dalam lingkungan pengujian.
3. Sensor-sensor yang digunakan (suhu, EC, pH) diasumsikan telah dikalibrasi dan memberikan pembacaan yang akurat sesuai spesifikasi pabrikan sebelum pengujian dimulai.
4. Model TD3 yang dikembangkan diasumsikan telah dilatih pada lingkungan simulasi aeroponik dan siap untuk inferensi serta integrasi jadwal kontrol selama periode pengujian.
5. Seluruh layanan *backend* diasumsikan dapat berkomunikasi melalui jaringan Docker internal tanpa hambatan *firewall* atau pembatasan *port* di lingkungan pengujian.

Hipotesis awal yang diajukan dalam penelitian ini adalah: (1) arsitektur *microservice* dengan *database-per-service* dan komunikasi *event-driven* mampu mengisolasi kegagalan antar-layanan secara penuh; (2) *firmware* modular memungkinkan penambahan protokol baru tanpa rekompilasi; (3) model TD3 mampu menghasilkan jadwal *misting* adaptif yang lebih stabil dibandingkan kendali berbasis aturan tetap; serta (4) sistem memenuhi metrik latensi *end-to-end* di bawah 2 detik pada persentil ke-95.
