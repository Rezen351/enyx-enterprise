# Dokumentasi Halaman Dashboard

## Halaman Utama (Main Page)

### 1. Monitor

**Deskripsi Halaman:**  
Halaman Monitor berfungsi sebagai pusat pengawasan real-time sistem aeroponik. Halaman ini menampilkan status kesehatan layanan backend, data telemetri lingkungan secara langsung, dan representasi visual status aktuator melalui diagram skematik. Data diperbarui secara otomatis melalui koneksi WebSocket tanpa perlu refresh manual.

**Hak Akses (Role):**  
- Administrator  
- Operator  
- Viewer  

**Fungsi Utama:**  
- Menampilkan status kesehatan layanan (Auth, Module, Control, Stream, Analytics, WS-Gateway) dalam matriks status real-time.  
- Menampilkan data telemetri lingkungan (suhu, kelembapan, tekanan, EC, pH, level air) yang diperbarui setiap beberapa detik.  
- Menampilkan status aktuator (pump, valve, fan, light) beserta nilai ON/OFF atau level PWM terbaru.  
- Menyediakan selektor modul (module selector) untuk memilih node/perangkat yang sedang dipantau.  
- Menampilkan diagram skematik aeroponik yang memetakan nilai sensor dan status aktuator secara visual.

**Pengalaman Pengguna (UX):**  
- Navigasi bersifat direktori tunggal dengan sidebar tetap; pengguna dapat berpindah antar halaman tanpa kehilangan konteks.  
- Modul yang ditampilkan dapat diubah melalui `ModuleSelector` di header; perubahan modul memicu pembaruan data seluruh komponen Monitor secara atomic.  
- Data real-time disajikan tanpa interupsi notifikasi atau overlay yang mengganggu; update terjadi di belakang layar dan langsung tercermin pada komponen visual.  
- Header menampilkan jam实时, notifikasi bell, dan toggle tema; elemen-elemen ini diisolasi agar tidak memicu render ulang seluruh halaman setiap detik.

---

### 2. Analytics

**Deskripsi Halaman:**  
Halaman Analytics menyediakan visualisasi data historis dalam bentuk grafik garis dan batang. Pengguna dapat mengeksplorasi tren telemetri, statistik ringkasan, dan pola operasional sistem aeroponik pada rentang waktu yang dapat dikonfigurasi.

**Hak Akses (Role):**  
- Administrator  
- Operator  
- Viewer  

**Fungsi Utama:**  
- Menampilkan grafik tren metrik telemetri (suhu, kelembapan, EC, pH, tekanan, level air) dengan dukungan zoom dan pan.  
- Menyediakan rentang waktu preset: 1 Jam, 6 Jam, 24 Jam, 7 Hari, 30 Hari.  
- Menghitung dan menampilkan statistik ringkasan per metrik: nilai minimum, maksimum, rata-rata, dan nilai terbaru.  
- Menggabungkan data dari berbagai sumber telemetri (GPIO, Modbus, I2C) ke dalam sumbu waktu yang seragam.  
- Mendukung ekspor data grafik dalam format CSV, JSON, Parquet, dan Excel melalui halaman Export.

**Pengalaman Pengguna (UX):**  
- Grafik dimuat secara progresif; pengguna melihat placeholder loading sebelum data tersedia.  
- Rentang waktu dapat diubah melalui tombol preset; perubahan memicu pengambilan data baru dari backend dan pembaruan sumbu X secara otomatis.  
- Fitur zoom dan pan pada grafik diaktifkan melalui plugin Chart.js; pengguna dapat memperluas area tertentu untuk analisis detail.  
- Tata letak menggunakan grid responsif yang menyesuaikan jumlah kolom berdasarkan lebar viewport; pada layar sempit, kartu statistik ditumpuk vertikal.

---

### 3. Control

**Deskripsi Halaman:**  
Halaman Control menyediakan antarmuka untuk mengirim perintah manual ke aktuator serta mengelola penjadwalan otomatis. Halaman ini juga menampilkan riwayat perintah dan status eksekusi mereka di firmware.

**Hak Akses (Role):**  
- Administrator  
- Operator  

**Fungsi Utama:**  
- Mengirim perintah manual ke aktuator (set_state, set_level, toggle, pulse, emergency_stop) melalui REST API Control Service.  
- Mengelola jadwal otomatis dengan jenis interval, duration, schedule (time-of-day), threshold, ramp, dan window_pulse.  
- Menampilkan riwayat perintah dengan status: pending, sent, acked, timeout, failed.  
- Mendukung mode bypass untuk perintah yang dikirim oleh layanan AI/ML (TD3/PPO) tanpa mengubah mode node ke MANUAL.  
- Menampilkan mode operasi node: MANUAL, AUTO, atau EMERGENCY.

**Pengalaman Pengguna (UX):**  
- Navigasi tersusun sebagai kartu aktor (target tiles); setiap aktuator ditampilkan dalam tile terpisah dengan kontrol ON/OFF, level slider, dan pulse button.  
- Tombol BYPASS hanya muncul ketika node dalam mode AUTO; toggle ini memungkinkan perintah AI/ML diterima tanpa mode switch.  
- Form jadwal disajikan dalam modal terpisah; parameter jadwal berubah secara dinamis sesuai jenis jadwal yang dipilih.  
- Riwayat perintah ditampilkan dalam tabel dengan pewarnaan status; pengguna dapat melihat detail req_id, target, value, dan timestamp.  
- Emergency stop ditampilkan sebagai tombol merah mencolok yang menghentikan semua aktuator secara bersamaan dan memaksa mode EMERGENCY.

---

### 4. Live

**Deskripsi Halaman:**  
Halaman Live menyediakan akses ke aliran video实时 (live stream) dari kamera yang terhubung ke sistem. Pengguna dapat menonton stream, memulai/ menghentikan rekaman, dan mengelola konfigurasi stream.

**Hak Akses (Role):**  
- Administrator  
- Operator  

**Fungsi Utama:**  
- Menampilkan live stream video dalam format HLS (HTTP Live Streaming) melalui player berbasis hls.js.  
- Memulai dan menghentikan rekaman stream dengan timer durasi yang ditampilkan secara real-time.  
- Mengelola daftar stream: menambah, mengedit, menghapus, dan mengaktifkan/menonaktifkan stream.  
- Menampilkan status koneksi stream (online/offline) dan indikator recording aktif.  
- Mendukung multiple stream secara bersamaan dalam grid layout.

**Pengalaman Pengguna (UX):**  
- Stream ditampilkan dalam kartu video dengan overlay kontrol; hover menampilkan toolbar untuk record, edit, dan delete.  
- Rekaman dimulai dengan konfirmasi durasi; timer berjalan di atas stream dan berhenti otomatis saat durasi tercapai.  
- Tombol record berwarna merah saat aktif; pengguna dapat menghentikan rekaman kapan saja.  
- Jika stream mengalami error, player menampilkan pesan fallback dan tombol retry.  
- Tata letak grid menyesuaikan jumlah stream: satu stream penuh, dua stream side-by-side, atau grid 3x3 untuk banyak stream.

---

### 5. Snapshot (Gallery)

**Deskripsi Halaman:**  
Halaman Snapshot menampilkan galeri foto yang diambil dari stream kamera, termasuk deteksi objek oleh model machine learning. Pengguna dapat meninjau snapshot, melihat bounding box deteksi, dan mengunduh gambar.

**Hak Akses (Role):**  
- Administrator  
- Operator  
- Viewer  

**Fungsi Utama:**  
- Menampilkan grid snapshot yang diambil dari stream kamera pada titik waktu tertentu.  
- Menampilkan overlay bounding box hasil deteksi objek (ML) di atas gambar snapshot.  
- Memfilter snapshot berdasarkan stream sumber, rentang waktu, atau kata kunci.  
- Mengunduh snapshot dalam format gambar asli.  
- Menghapus snapshot yang tidak diperlukan.

**Pengalaman Pengguna (UX):**  
- Snapshot ditampilkan dalam grid responsif; hover menampilkan overlay dengan informasi waktu, stream, dan jumlah deteksi.  
- Klik snapshot membuka modal lightbox dengan resolusi penuh; bounding box deteksi ditampilkan dengan koordinat yang diskalakan ke ukuran gambar asli.  
- Filter dan pencarian diterapkan secara instan tanpa reload halaman; hasil filter diperbarui secara asynchronous.  
- Tombol download tersedia di lightbox; pengguna dapat menyimpan gambar dengan nama file yang sudah terformat.

---

### 6. Alerts

**Deskripsi Halaman:**  
Halaman Alerts menampilkan daftar peringatan sistem yang dihasilkan dari pelanggaran threshold sensor atau kondisi abnormal lainnya. Pengguna dapat melihat detail alert, mengakui (acknowledge) alert, dan mengelola aturan threshold.

**Hak Akses (Role):**  
- Administrator  
- Operator  

**Fungsi Utama:**  
- Menampilkan daftar alert dengan filter berdasarkan status (Active, Resolved, Acked) dan tingkat keparahan (Warning, Critical).  
- Mengakui alert untuk menandai bahwa alert telah ditinjau oleh operator.  
- Mengelola aturan threshold: membuat, memperbarui, dan menghapus aturan yang mendefinisikan batas atas dan bawah untuk metrik telemetri.  
- Menampilkan detail alert: timestamp, node, metrik, nilai yang memicu alert, dan pesan deskriptif.  
- Mendukung auto-refresh untuk memantau alert baru secara periodik.

**Pengalaman Pengguna (UX):**  
- Alert ditampilkan dalam kartu atau tabel dengan badge warna: merah untuk Critical, kuning untuk Warning.  
- Tombol ACK tersedia hanya untuk alert dengan status Active; setelah diakui, status berubah menjadi Acked dan badge warna berubah.  
- Form threshold menawarkan dropdown metrik yang tersedia; pengguna memilih sumber telemetri dan menentukan nilai batas atas/bawah.  
- Filter diterapkan secara instan; daftar alert diperbarui tanpa reload halaman.  
- Auto-refresh dapat diaktifkan/dinonaktifkan; saat aktif, daftar alert diperbarui setiap beberapa detik.

---

### 7. Export

**Deskripsi Halaman:**  
Halaman Export menyediakan antarmuka untuk mengekspor data sistem dalam berbagai format. Pengguna dapat memilih jenis data, rentang waktu, dan format file sebelum mengunduh.

**Hak Akses (Role):**  
- Administrator  
- Operator  

**Fungsi Utama:**  
- Mengekspor data telemetri dalam format CSV, JSON, Parquet, atau Excel.  
- Mengekspor data node/module dalam format CSV atau JSON.  
- Memfilter data berdasarkan rentang waktu (start dan end datetime).  
- Menampilkan preview data sebelum ekspor dalam format tabel.  
- Mengunduh file hasil ekspor melalui browser.

**Pengalaman Pengguna (UX):**  
- Pengguna memilih tab jenis data (Telemetry atau Nodes) sebelum mengatur filter.  
- Rentang waktu dimasukkan melalui input date-time; format RFC3339 digunakan secara internal.  
- Preview data ditampilkan dalam tabel scrollable; kolom dapat diurutkan dengan klik header.  
- Tombol download diaktifkan setelah data siap; progress download ditampilkan oleh browser.  
- Format file ditentukan melalui dropdown; perubahan format memuat ulang preview dengan format yang sesuai.

---

### 8. Module (Module Management)

**Deskripsi Halaman:**  
Halaman Module menyediakan antarmuka untuk mengelola modul dan node dalam sistem. Pengguna dapat menambahkan, mengedit, dan menghapus modul; serta melakukan pairing, konfigurasi, dan pembaruan node.

**Hak Akses (Role):**  
- Administrator  
- Operator  

**Fungsi Utama:**  
- Membuat, memperbarui, dan menghapus modul (module) dalam sistem.  
- Menampilkan daftar node yang terpasang (paired) dan node yang terdeteksi (discovered) tetapi belum dipasangkan.  
- Melakukan pairing node ke modul untuk menghubungkan perangkat fisik ke logical module.  
- Membuka halaman konfigurasi node (`NodeConfigPage`) untuk mengatur tag mapping, aktuator, dan kontrol.  
- Menampilkan status koneksi node: online/offline berdasarkan last_seen_at.

**Pengalaman Pengguna (UX):**  
- Modul ditampilkan dalam kartu dengan nama, deskripsi, dan jumlah node; kartu dapat diklik untuk melihat daftar node.  
- Node dalam modul ditampilkan dalam tabel dengan indikator online/offline; status diperbarui secara otomatis setiap 4 detik.  
- Tombol Pair tersedia untuk node discovered; proses pairing memuat ulang daftar node secara atomic.  
- Navigasi ke NodeConfigPage terjadi dengan klik ikon settings; halaman konfigurasi ditampilkan sebagai overlay yang menggantikan konten Module.  
- Tombol kembali dari NodeConfigPage mengembalikan pengguna ke daftar node di modul yang aktif.

---

### 9. Audit

**Deskripsi Halaman:**  
Halaman Audit menampilkan log audit sistem yang berisi catatan aktivitas penting seperti login, perubahan konfigurasi, perintah kontrol, dan events lainnya. Halaman ini digunakan untuk forensic dan compliance tracking.

**Hak Akses (Role):**  
- Administrator  

**Fungsi Utama:**  
- Menampilkan log audit dengan filter berdasarkan jenis event (Auth, Module, Node, Control) dan kata kunci pencarian.  
- Menampilkan detail event: timestamp, user, action, target, dan metadata JSON.  
- Mendukung pagination dengan ukuran halaman 25, 50, atau 100 record.  
- Auto-refresh opsional untuk memantau log baru secara periodik.  
- Menampilkan metadata dalam format JSON yang diformat untuk keterbacaan.

**Pengalaman Pengguna (UX):**  
- Log ditampilkan dalam tabel dengan badge warna berdasarkan kategori event: biru untuk Auth, ungu untuk Module, kuning untuk Node, hijau untuk Control.  
- Filter cepat disediakan sebagai tombol pill; pengguna dapat memilih kategori atau melihat semua.  
- Pencarian teks melakukan full-text match pada field event dan metadata.  
- Auto-refresh diaktifkan melalui toggle; saat aktif, log diperbarui secara otomatis tanpa intervensi pengguna.  
- Detail JSON ditampilkan dalam blok monospace dengan sintaks highlighting; nilai string berwarna amber, number berwarna cyan.

---

### 10. DLQ (Dead Letter Queue)

**Deskripsi Halaman:**  
Halaman DLQ menampilkan pesan yang gagal diproses oleh sistem event bus (NATS JetStream) setelah upaya pengiriman berulang. Halaman ini digunakan untuk inspeksi dan debugging pesan yang tidak dapat diproses.

**Hak Akses (Role):**  
- Administrator  

**Fungsi Utama:**  
- Menampilkan daftar pesan di Dead Letter Queue dengan filter berdasarkan source stream dan trace ID.  
- Menampilkan detail pesan: subject, payload JSON, alasan kegagalan (MaxDeliverExceeded, dll), dan timestamp.  
- Mendukung pagination dengan ukuran halaman 25, 50, atau 100 record.  
- Menyediakan filter berdasarkan alasan kegagalan.  
- Menampilkan payload pesan dalam format JSON yang diformat.

**Pengalaman Pengguna (UX):**  
- Pesan ditampilkan dalam kartu atau tabel dengan badge warna berdasarkan alasan kegagalan: merah untuk MaxDeliverExceeded, abu-abu untuk alasan lainnya.  
- Filter source stream memungkinkan pengguna memfilter pesan berdasarkan topik NATS asal.  
- Pencarian trace ID membantu melacak pesan spesifik dalam alur distribusi.  
- Payload JSON ditampilkan dalam blok monospace dengan syntax highlighting; struktur payload dapat diperluas/diciutkan.  
- Tidak ada aksi retry atau delete dari UI; DLQ bersifat read-only untuk inspeksi.

---

### 11. Notifications & Webhooks

**Deskripsi Halaman:**  
Halaman Notifications & Webhooks menyediakan antarmuka tunggal untuk mengelola konfigurasi kanal notifikasi (Telegram, Email, Push, Webhook) dan memantau pengiriman ke eksternal. Pengguna dapat mengatur target tiap kanal, secret, dan menguji pengiriman.

**Hak Akses (Role):**  
- Administrator  

**Fungsi Utama:**  
- Mengonfigurasi settings per kanal: Telegram (chat id + bot token), Email (recipient + SMTP password), Push (device token + server key), Webhook (callback URL + signature secret).  
- Menguji pengiriman notifikasi dengan payload sampel untuk memverifikasi koneksi tiap kanal yang aktif.  
- Menampilkan riwayat pengiriman (delivery logs) dengan status: queued, sent, retrying, failed, dapat difilter berdasarkan kanal dan status.  
- Endpoint inbound receiver (`/notifications/receive/*`) menerima payload eksternal dan mengantarkannya melalui kanal yang dikonfigurasi.  
- Menampilkan log delivery dengan detail attempts, error message, dan created time.

**Pengalaman Pengguna (UX):**  
- Konfigurasi tiap kanal disajikan dalam form dengan field yang jelas dan toggle Enabled.  
- Tombol "Save Settings" dan "Test" mengirimkan request ke backend Notification Service (`/notifications/settings`, `/notifications/test`).  
- Riwayat pengiriman ditampilkan dalam tabel dengan badge status: hijau untuk sent, biru untuk queued, kuning untuk retrying, merah untuk failed.  
- Form mengimplementasikan validasi client-side sebelum mengirimkan konfigurasi ke backend.  
- Header kosong atau field yang belum diubah menggunakan default dari environment variables sesuai prinsip konfigurasi sistem.

---

### 12. Users / Account Management

**Deskripsi Halaman:**  
Halaman Account Management menyediakan antarmuka untuk mengelola akun pengguna sistem. Administrator dapat membuat, mengedit, menonaktifkan, dan menghapus akun; serta mengatur peran (role) untuk setiap pengguna.

**Hak Akses (Role):**  
- Administrator  

**Fungsi Utama:**  
- Menampilkan daftar akun pengguna dengan informasi username, email, role, status aktif/nonaktif, dan timestamp pembuatan.  
- Membuat akun baru dengan username, email, password, dan role yang ditentukan.  
- Mengedit akun: mengubah username, email, role, dan status aktif.  
- Menonaktifkan akun tanpa menghapus data historis; akun nonaktif tidak dapat login.  
- Menghapus akun secara permanen dari sistem.  
- Mendukung role: admin, operator, viewer.

**Pengalaman Pengguna (UX):**  
- Daftar pengguna ditampilkan dalam tabel dengan aksi edit dan delete per baris.  
- Form tambah/edit pengguna muncul dalam modal; field divalidasi sebelum dikirimkan.  
- Role ditetapkan melalui dropdown dengan opsi: admin, operator, viewer.  
- Konfirmasi penghapusan ditampilkan sebagai dialog konfirmasi sebelum aksi delete dieksekusi.  
- Status aktif/nonaktif ditoggle melalui switch; perubahan diterapkan secara immediat tanpa reload halaman.

---

### 13. Profile

**Deskripsi Halaman:**  
Halaman Profile menyediakan antarmuka untuk pengguna mengelola akun mereka sendiri. Pengguna dapat melihat informasi profil, memperbarui data pribadi, mengganti password, dan melihat sesi login aktif.

**Hak Akses (Role):**  
- Administrator  
- Operator  
- Viewer  

**Fungsi Utama:**  
- Menampilkan informasi profil: username, email, role, dan timestamp pembuatan akun.  
- Memperbarui username dan email melalui form profil.  
- Mengganti password dengan memasukkan password lama dan password baru.  
- Menampilkan daftar sesi login aktif dengan informasi perangkat, browser, dan timestamp.  
- Menghapus akun sendiri dengan konfirmasi password.  
- Melakukan logout dari sesi saat ini.

**Pengalaman Pengguna (UX):**  
- Profil ditampilkan dalam layout kartu terpisah: informasi akun, form update, form ganti password, dan daftar sesi.  
- Setiap section memiliki state loading dan error yang terisolasi; kesalahan pada satu section tidak mengganggu yang lain.  
- Form ganti password memerlukan konfirmasi password baru; validasi dilakukan sebelum pengiriman.  
- Daftar sesi menampilkan informasi perangkat dan browser; pengguna dapat memantau sesi aktif dari berbagai perangkat.  
- Tombol logout berada di sidebar; aksi logout menghentikan sesi dan mengembalikan pengguna ke halaman login.

---

## Hierarki Navigasi

```
Dashboard
├── MONITOR (admin, operator, viewer)
├── ANALYTICS (admin, operator, viewer)
├── CONTROL (admin, operator)
├── LIVE (admin, operator)
├── GALLERY (admin, operator, viewer)
├── ALERTS (admin, operator)
├── EXPORT (admin, operator)
├── MODULE (admin, operator)
│   └── NodeConfigPage (admin, operator)
└── ADMINISTRATOR (admin only)
    ├── AUDIT
    ├── DLQ
    ├── WEBHOOK
    └── ACCOUNT
└── PROFILE (all authenticated users)
```
