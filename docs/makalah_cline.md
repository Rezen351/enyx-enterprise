# PENGEMBANGAN ARSITEKTUR IOT TERDISTRIBUSI BERBASIS MICROSERVICES DAN FIRMWARE MODULAR PADA SISTEM OTOMASI BUDIDAYA AEROPONIK

*Alif Muhammad Rizky, [Nama Pembimbing I], [Nama Pembimbing II]*

Program Studi Teknik Fisika – Institut Teknologi Bandung

September – 2026

---

**ABSTRAK**

*Pertanian presisi pada budidaya aeroponik menuntut pemantauan dan kontrol mikroklimat secara kontinu, namun arsitektur monolitik konvensional memiliki keterikatan erat antarkomponen, rentan terhadap single point of failure, dan sulit diskalakan. Makalah ini merancang, mengimplementasikan, dan mengevaluasi sistem otomasi aeroponik terdistribusi berbasis dual-layer modularity: arsitektur microservice modular pada sisi server dan firmware modular pada edge node ESP32. Pada sisi edge, ESP32 berbasis FreeRTOS dual-core menggunakan pola factory pattern dan protocol registry yang memungkinkan penambahan dan konfigurasi sensor/aktuator baru tanpa proses kompilasi ulang melalui Captive Web Portal. Pada sisi server, sistem menerapkan prinsip database-per-service pada layanan inti (Auth, Module, Control, Analytics) dengan komunikasi event-driven melalui NATS JetStream dan API Gateway Kong. Layanan kontrol adaptif berbasis Reinforcement Learning (TD3) diintegrasikan secara loose coupling dengan ekstraksi fitur visual YOLOv8 untuk menghasilkan penjadwalan misting yang adaptif. Evaluasi empiris melalui unit test, stress test, dan chaos engineering membuktikan isolasi kegagalan penuh antar-layanan (zero cascade failure) serta latensi end-to-end di bawah 2 detik pada persentil ke-95.*

*Kata kunci: microservice, firmware modular, aeroponik, kontrol adaptif*

---

## 1 PENDAHULUAN

### 1.1 Latar Belakang

Pada budidaya aeroponik, akar tanaman tumbuh di udara dan disemprot nutrisi secara berkala, sehingga parameter mikroklimat seperti suhu udara, kelembapan, *electrical conductivity* (EC), dan pH larutan nutrisi bersifat kritis dan wajib dipantau secara kontinu [1]. Mayoritas sistem IoT konvensional masih berbasis arsitektur monolitik yang memiliki keterikatan erat antarkomponen (*tight coupling*), sehingga sulit diskalakan dan tidak fleksibel ketika terjadi penambahan sensor atau aktuator baru karena menuntut modifikasi logika utama serta kompilasi ulang firmware.

Penelitian ini mengadopsi pendekatan modularitas dua lapis (*dual-layer modularity*) untuk mengatasi keterbatasan tersebut. Pada sisi edge, firmware ESP32 dirancang menggunakan *factory pattern* dan *protocol registry* sehingga konfigurasi perangkat dapat dilakukan secara dinamis. Pada sisi server, sistem menerapkan arsitektur microservice dengan pola *database-per-service* agar setiap layanan dapat dikembangkan, diperbarui, dan dikelola secara independen tanpa menimbulkan kegagalan beruntun (*cascading failure*). Sistem juga dilengkapi layanan kontrol adaptif berbasis *Reinforcement Learning* (TD3) yang dikombinasikan dengan deteksi visual YOLOv8 secara *loose coupling* untuk menyesuaikan jadwal penyemprotan secara presisi [1].



### 1.2 Rumusan Masalah

Rumusan masalah dalam penelitian ini adalah: (1) bagaimana merancang arsitektur pemantauan dan kontrol aeroponik terdistribusi yang mampu memisahkan dependensi komputasi antara sisi server dan sisi edge; (2) bagaimana menerapkan *factory pattern* dan *protocol registry* pada firmware ESP32 agar penambahan protokol sensor/aktuator baru dapat dilakukan secara dinamis tanpa kompilasi ulang; (3) bagaimana menerapkan *database-per-service*, komunikasi event MQTT dan NATS JetStream, serta API Gateway Kong; (4) bagaimana mengintegrasikan TD3 dan YOLOv8 secara *loose coupling*; dan (5) sejauh mana keandalan isolasi kegagalan dan kinerja sistem diuji melalui *stress test* dan *chaos engineering* [1].

### 1.3 Tujuan Penelitian

Penelitian ini bertujuan merancang, mengimplementasikan, dan mengevaluasi sistem otomasi aeroponik terdistribusi dengan modularitas dua lapis, membuktikan modularitas firmware secara empiris melalui penambahan handler protokol I2C (sensor daya INA219) tanpa rekompilasi, membangun mekanisme ingest telemetri real-time dan alur kontrol terdistribusi berbasis microservice, mengintegrasikan model TD3 dan YOLOv8 sebagai layanan independen, serta mengevaluasi kinerja kuantitatif sistem melalui unit test, stress test, dan chaos engineering [1].

## 2 KONSEP / TEORI DASAR

Teori dasar yang menopang penelitian ini mencakup arsitektur komputasi terdistribusi dan microservice, komunikasi event-driven, firmware modular serta pemrograman berorientasi objek, dan inteligensi buatan untuk kontrol adaptif.

Pola *factory pattern* dan *protocol registry* merupakan perwujudan prinsip enkapsulasi dan *open/closed principle*, di mana penambahan tipe sensor atau aktuator baru tidak mengubah logika inti program. Prinsip *database-per-service* menjamin isolasi penyimpanan setiap layanan sehingga kegagalan basis data satu layanan tidak memengaruhi layanan lain. Komunikasi asinkron melalui NATS JetStream menjaga pesan tetap tersimpan saat subscriber gagal dan dilanjutkan setelah recovery, sedangkan API Gateway Kong memfilter permintaan hanya ke layanan yang sehat sehingga mencegah *thundering herd*. Untuk kendali adaptif, algoritma *Twin Delayed Deep Deterministic Policy Gradient* (TD3) mempelajari kebijakan penjadwalan misting pada sistem fisik kontinu berdasarkan state yang terdiri atas telemetri iklim mikro dan fitur visual tanaman [1].


## 3 RANCANGAN / PERCOBAAN / SIMULASI

### 3.1 Arsitektur Dual-Layer Modularity

Sistem dibangun sebagai arsitektur dua lapis. Lapisan *edge* berupa node ESP32 berbasis FreeRTOS dual-core yang menjalankan firmware modular, sedangkan lapisan *server* berupa 13 microservice mandiri yang diorkestrasi melalui Docker Compose dengan komunikasi antara edge dan server menggunakan protokol MQTT melalui Mosquitto.

### 3.2 Firmware Modular ESP32

Firmware pada sisi edge menerapkan *factory pattern* dan *protocol registry* (modular I/O, vector registry, map registry) sehingga penambahan handler protokol baru dapat dilakukan melalui antarmuka Captive Web Portal atau berkas `config.json` tanpa proses kompilasi ulang. Modularitas ini dibuktikan secara empiris dengan mengintegrasikan handler protokol I2C untuk sensor daya INA219 [1].

### 3.3 Arsitektur Microservice Server

Arsitektur server menerapkan *database-per-service* pada layanan inti: Auth Service (autentikasi terpusat, RBAC, penerbitan JWT), Module Service (registrasi perangkat dan ingest telemetri), Control Service (arbitrase mode kendali dan eksekusi aktuator), serta Analytics Service (agregasi deret waktu pada TimescaleDB). Layanan pendukung meliputi Stream, Alert, Notification, Export, Audit, DLQ, dan WS-Gateway, sedangkan komunikasi antar-layanan memanfaatkan NATS JetStream dan semua akses REST melalui Kong API Gateway `/v1` [1].

### 3.4 Kontrol Adaptif TD3 dan YOLOv8

Layanan *model-control* mengkombinasikan state telemetri real-time dengan metadata hasil deteksi visual dari *model-controller* (YOLOv8) untuk menghasilkan keputusan penjadwalan misting melalui algoritma TD3. Keputusan dikirimkan ke Control Service secara non-blocking sehingga pembaruan model AI tidak mengganggu layanan core operasional [1].

### 3.5 Skenario Pengujian

Pengujian dilakukan dalam dua tahap: Tahap I (konfigurasi minimal, 4–10 node) dan Tahap II (konfigurasi penuh dengan layanan AI/ML). Pengujian mencakup unit test fitur layanan melalui Kong Gateway, stress test untuk mengukur throughput dan latensi P95, serta chaos engineering untuk membuktikan isolasi kegagalan penuh (zero cascade failure) [2].



## 4 HASIL DAN ANALISIS

Hasil pengujian menunjukkan seluruh skenario chaos engineering berhasil dengan kelulusan 100% (Tahap I = 43 PASS dan Tahap II = 50 PASS, tanpa kegagalan), membuktikan tidak terjadi cascade failure ketika satu layanan, basis data, broker, maupun gateway dihentikan paksa. Seluruh layanan yang dihentikan pulih secara otomatis tanpa intervensi manual [1].

Pada sistem terdistribusi, pertumbuhan akar tanaman dapat dimodelkan dengan persamaan pertumbuhan logistik sebagai berikut:

$$\Delta L_{\text{root}} = r_{\text{step}} \cdot 180 \cdot L_{\text{root}} \cdot \left(1 - \frac{L_{\text{root}}}{K}\right) \cdot f_{\text{lim}} \cdot d_{\text{day}}$$

(1)

dengan $r_{\text{step}}$ adalah laju pertumbuhan akar spesifik (cm/menit), $L_{\text{root}}$ panjang akar (cm), $K$ kapasitas pembawa (cm), $f_{\text{lim}}$ faktor pembatas lingkungan, dan $d_{\text{day}}$ multiplier periode siang/malam [2].

Hasil kuantitatif kinerja sistem dirangkum pada Tabel 1 berikut.

| Parameter Pengujian | Tahap I | Tahap II |
|---|---|---|
| Throughput puncak (RPS) | 51,3 | 68 |
| Latensi P95 API (ms) | 1482 | 1275 |
| Error rate (%) | 2,1 | 4,5 |
| Latensi MQTT (ms) | 1,75 | 2,1 |
| Throughput MQTT (msg/s) | 4,26 | 11,5 |
| Total RAM (MB) | 800 | 1700 |
| Peak CPU (%) | 9,69 | 27,5 |

**Tabel 1. Ringkasan kinerja throughput, latensi, dan sumber daya** [1]

Berdasarkan Tabel 1, performa REST API Gateway meningkat dari 51,3 RPS menjadi 68 RPS dengan latensi P95 menurun dari 1482 ms menjadi 1275 ms. Pelipatgandaan node dari 4 menjadi 10 meningkatkan throughput MQTT sebesar 170% tanpa menimbulkan bottleneck, dengan utilisasi sumber daya tetap efisien (peak CPU 27,5% dan rata-rata RAM per layanan 54,6 MB) [1]. Perbandingan ini disajikan secara visual pada Gambar 1.

**Gambar 1: Grafik perbandingan kinerja Tahap I dan Tahap II**

## 5 KESIMPULAN

Arsitektur *dual-layer modularity* berhasil memisahkan dependensi perangkat keras di edge dan komputasi di server sehingga kedua lapisan dapat dikembangkan secara independen. Penerapan *factory pattern* dan *protocol registry* memungkinkan integrasi sensor baru (I2C INA219) secara dinamis tanpa kompilasi ulang. Alur telemetri dan kontrol berjalan aman melalui MQTT, NATS JetStream, Kong API Gateway, dan prinsip *database-per-service* yang terbukti mencegah kegagalan beruntun (zero cascade failure). Model YOLOv8 dan TD3 beroperasi sebagai microservice independen, dan hasil chaos engineering serta stress test membuktikan keandalan serta kinerja sistem dengan latensi end-to-end di bawah 2 detik pada persentil ke-95 [1].

## 6 DAFTAR PUSTAKA

1. Rizky, A. M., *Pengembangan Arsitektur IoT Terdistribusi Berbasis Microservices dan Firmware Modular pada Sistem Otomasi Budidaya Aeroponik*, Tugas Akhir, Program Studi Teknik Fisika, Institut Teknologi Bandung, 2026.
2. Rizky, A. M., *enyx-enterprise: Enterprise IoT Modular Microservices* (kode sumber program, repository GitHub: enterprise-iot-modular-microservices), 2026.