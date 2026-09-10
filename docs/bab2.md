# BAB II
# DASAR TEORI

## 2.1 Sistem Aeroponik dan Pertanian Presisi

Pertanian presisi mengandalkan data *real-time* sensor untuk kendali nutrisi dan aktuator secara otomatis [2]. Pada aeroponik, akar tumbuh di udara dan disemprot nutrisi secara berkala sehingga suhu, kelembapan, *electrical conductivity* (EC), dan pH bersifat kritis serta wajib dipantau kontinu [3]. Integrasi sensor cerdas dan kendali otomatis berpengaruh langsung terhadap stabilitas pertumbuhan tanaman, sehingga sistem harus mengakuisisi telemetri secara kontinu dan responsif [3].

## 2.2 Arsitektur *Microservice* dan *Database-per-Service*

Arsitektur *microservice* mendefinisikan sebuah aplikasi sebagai kumpulan layanan kecil yang dapat di-*deploy* secara independen dan berkomunikasi melalui mekanisme ringan [1]. Setiap layanan menerapkan prinsip *single responsibility* dan dipisahkan berdasarkan *bounded context*, sehingga perubahan pada satu layanan tidak memaksa penyebaran ulang layanan lain [1]. Pendekatan ini meminimalkan *coupling* antarkomponen dan menjadi landasan bagi pengembangan, pengujian, serta *deployment* yang terpisah.

Salah satu prinsip utama arsitektur *microservice* adalah *database-per-service*, yakni setiap layanan memiliki basis data sendiri tanpa pembagian basis data antar layanan [1]. Isolasi fisik dan logis antar basis data mencegah *cascading failure* serta memungkinkan evolusi skema secara independen. Dalam praktiknya, pendekatan *polyglot persistence* dipilih sesuai kebutuhan tiap layanan—basis data relasional untuk data transaksional, basis data deret waktu (*time-series*) untuk telemetri, serta *cache* dan *object storage* untuk kebutuhan pendukung.

## 2.3 Protokol Komunikasi IoT: MQTT dan NATS JetStream

Komunikasi antar perangkat dalam sistem *Internet of Things* (IoT) memerlukan protokol yang ringan, efisien, dan mampu beroperasi pada jaringan dengan keterbatasan sumber daya, yang dibahas secara komprehensif dalam survei teknologi pengenable IoT [2]. Salah satu protokol yang banyak digunakan adalah MQTT (*Message Queuing Telemetry Transport*), protokol publikasi–berlangganan (*publish-subscribe*) berbasis *broker* yang cocok untuk transmisi telemetri dari perangkat *edge* seperti ESP32 ke server [2].

Untuk komunikasi antar layanan di sisi komputasi awan, pendekatan *event-driven architecture* memberikan dampak pada peningkatan performa dan isolasi kegagalan dibandingkan pola *request-response* sinkron [6]. NATS JetStream merupakan implementasi sistem pesan berbasis peristiwa yang menyediakan ketahanan through *persistence*, *streaming*, dan *replay* pesan, sehingga menunjang komunikasi antar-layanan yang longgar (*loosely coupled*) dan tahan terhadap kehilangan pesan [6]. Kombinasi MQTT di sisi *edge* dan NATS JetStream di sisi layanan menjembatani dua domain komunikasi dengan prinsip *event-driven* yang konsisten.

## 2.4 *Firmware* Modular ESP32 (*Edge*)

Mikrokontroler ESP32 merupakan platform berbiaya rendah yang banyak digunakan untuk sistem pemantauan IoT berbasis sensor, termasuk akuisisi data lingkungan secara efisien pada skala *pilot* [5]. Dengan kemampuan konektivitas WiFi dan arsitektur *dual-core*, ESP32 berada pada lapisan *edge* yang bertugas mengakuisisi telemetri sensor dan mengendalikan aktuator secara langsung tanpa ketergantungan penuh pada server [5].

Agar perangkat *edge* mudah dikembangkan dan dipelihara, *firmware* dirancang secara modular, di mana pembacaan sensor dan eksekusi aktuator dienkapsulasi dalam *handler* mandiri yang dapat ditambahkan melalui konfigurasi tanpa rekompilasi ulang [5]. Pendekatan modular ini selaras dengan prinsip *microservice* di sisi server, memungkinkan penambahan protokol atau jenis sensor baru tanpa mengubah logika inti *firmware* [5].

## 2.5 *Reinforcement Learning* (TD3) untuk Kontrol Adaptif

*Reinforcement learning* (RL) memungkinkan agen mempelajari kebijakan kendali melalui interaksi dengan lingkungan dan sinyal *reward* tanpa pemodelan eksplisit secara penuh. Salah satu algoritma RL untuk ruang status dan aksi kontinu adalah *Twin Delayed Deep Deterministic Policy Gradient* (TD3), yang memperbaiki ketidakstabilan pelatihan DDPG melalui tiga mekanisme utama: pembaruan *policy* yang tertunda (*delayed*), estimasi nilai ganda (*twin critics*) untuk mengurangi overestimasi, dan penambahan *target smoothing noise* [4].

Pada sistem fisik kontinu seperti kendali penjadwalan *misting* aeroponik, TD3 mampu mempelajari kebijakan adaptif yang menjaga kestabilan variabel lingkungan (suhu, kelembapan, EC, pH) melalui pengaturan aktuasi secara berkelanjutan [4]. Pendekatan berbasis RL ini memberikan kendali yang lebih responsif dibandingkan aturan tetap, sekaligus dapat diintegrasikan ke dalam arsitektur *microservice* sebagai layanan inferensi yang terpisah agar tidak menciptakan *tight coupling* dengan layanan lain [1].

## 2.6 Visi Komputer (YOLOv8) sebagai Pendukung Kontrol

Visi komputer berperan sebagai pendukung kontrol dengan mengekstraksi informasi visual dari tanaman, seperti estimasi panjang akar dan kondisi umbi, yang kemudian digunakan untuk memperkaya umpan balik sistem kendali adaptif. Arsitektur deteksi objek *You Only Look Once* versi 8 (YOLOv8) memungkinkan inferensi citra secara *real-time* pada perangkat berbasis *edge* maupun layanan komputasi awan.

> **Catatan:** Dari sepuluh entri pada `docs/daftar_pustaka.md` [1]–[10], tidak terdapat referensi yang secara khusus membahas visi komputer, deteksi objek, atau YOLOv8. Sesuai batasan "hanya gunakan daftar pustaka", subbab ini tidak dapat dikutip ke sumber daftar pustaka yang tersedia. Disarankan menambahkan minimal satu referensi jurnal terkait *computer vision*/YOLO ke daftar pustaka agar subbab 2.6 memiliki landasan sitasi yang valid.
