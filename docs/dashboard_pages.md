# Dokumentasi Halaman Dashboard

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

---

## Halaman Utama

### 1. Monitor

**Hak Akses:** Administrator, Operator, Viewer

**Fungsi Utama:**
- Menampilkan status kesehatan layanan (Auth, Module, Control, Stream, Analytics, WS-Gateway) dalam matriks status real-time.
- Menampilkan data telemetri lingkungan (suhu, kelembapan, tekanan, EC, pH, level air) yang diperbarui setiap beberapa detik.
- Menampilkan status aktuator (pump, valve, fan, light) beserta nilai ON/OFF atau level PWM terbaru.
- Menyediakan selektor modul (module selector) untuk memilih node/perangkat yang sedang dipantau.
- Menampilkan diagram skematik aeroponik yang memetakan nilai sensor dan status aktuator secara visual.

---

### 2. Analytics

**Hak Akses:** Administrator, Operator, Viewer

**Fungsi Utama:**
- Menampilkan grafik tren metrik telemetri (suhu, kelembapan, EC, pH, tekanan, level air) dengan dukungan zoom dan pan.
- Menyediakan rentang waktu preset: 1 Jam, 6 Jam, 24 Jam, 7 Hari, 30 Hari.
- Menghitung dan menampilkan statistik ringkasan per metrik: nilai minimum, maksimum, rata-rata, dan nilai terbaru.
- Menggabungkan data dari berbagai sumber telemetri (GPIO, Modbus, I2C) ke dalam sumbu waktu yang seragam.
- Mendukung ekspor data grafik dalam format CSV, JSON, Parquet, dan Excel melalui halaman Export.

---

### 3. Control

**Hak Akses:** Administrator, Operator

**Fungsi Utama:**
- Mengirim perintah manual ke aktuator (set_state, set_level, toggle, pulse, emergency_stop) melalui REST API Control Service.
- Mengelola jadwal otomatis dengan jenis interval, duration, schedule (time-of-day), threshold, ramp, dan window_pulse.
- Menampilkan riwayat perintah dengan status: pending, sent, acked, timeout, failed.
- Mendukung mode bypass untuk perintah yang dikirim oleh layanan AI/ML (TD3/PPO) tanpa mengubah mode node ke MANUAL.
- Menampilkan mode operasi node: MANUAL, AUTO, atau EMERGENCY.

---

### 4. Live

**Hak Akses:** Administrator, Operator

**Fungsi Utama:**
- Menampilkan live stream video dalam format HLS (HTTP Live Streaming) melalui player berbasis hls.js.
- Memulai dan menghentikan rekaman stream dengan timer durasi yang ditampilkan secara real-time.
- Mengelola daftar stream: menambah, mengedit, menghapus, dan mengaktifkan/menonaktifkan stream.
- Menampilkan status koneksi stream (online/offline) dan indikator recording aktif.
- Mendukung multiple stream secara bersamaan dalam grid layout.

---

### 5. Snapshot (Gallery)

**Hak Akses:** Administrator, Operator, Viewer

**Fungsi Utama:**
- Menampilkan grid snapshot yang diambil dari stream kamera pada titik waktu tertentu.
- Menampilkan overlay bounding box hasil deteksi objek (ML) di atas gambar snapshot.
- Memfilter snapshot berdasarkan stream sumber, rentang waktu, atau kata kunci.
- Mengunduh snapshot dalam format gambar asli.
- Menghapus snapshot yang tidak diperlukan.

---

### 6. Alerts

**Hak Akses:** Administrator, Operator

**Fungsi Utama:**
- Menampilkan daftar alert dengan filter berdasarkan status (Active, Resolved, Acked) dan tingkat keparahan (Warning, Critical).
- Mengakui alert untuk menandai bahwa alert telah ditinjau oleh operator.
- Mengelola aturan threshold: membuat, memperbarui, dan menghapus aturan yang mendefinisikan batas atas dan bawah untuk metrik telemetri.
- Menampilkan detail alert: timestamp, node, metrik, nilai yang memicu alert, dan pesan deskriptif.
- Mendukung auto-refresh untuk memantau alert baru secara periodik.

---

### 7. Export

**Hak Akses:** Administrator, Operator

**Fungsi Utama:**
- Mengekspor data telemetri dalam format CSV, JSON, Parquet, atau Excel.
- Mengekspor data node/module dalam format CSV atau JSON.
- Memfilter data berdasarkan rentang waktu (start dan end datetime).
- Menampilkan preview data sebelum ekspor dalam format tabel.
- Mengunduh file hasil ekspor melalui browser.

---

### 8. Module (Module Management)

**Hak Akses:** Administrator, Operator

**Fungsi Utama:**
- Membuat, memperbarui, dan menghapus modul (module) dalam sistem.
- Menampilkan daftar node yang terpasang (paired) dan node yang terdeteksi (discovered) tetapi belum dipasangkan.
- Melakukan pairing node ke modul untuk menghubungkan perangkat fisik ke logical module.
- Membuka halaman konfigurasi node (`NodeConfigPage`) untuk mengatur tag mapping, aktuator, dan kontrol.
- Menampilkan status koneksi node: online/offline berdasarkan last_seen_at.

---

### 9. Audit

**Hak Akses:** Administrator

**Fungsi Utama:**
- Menampilkan log audit dengan filter berdasarkan jenis event (Auth, Module, Node, Control) dan kata kunci pencarian.
- Menampilkan detail event: timestamp, user, action, target, dan metadata JSON.
- Mendukung pagination dengan ukuran halaman 25, 50, atau 100 record.
- Auto-refresh opsional untuk memantau log baru secara periodik.
- Menampilkan metadata dalam format JSON yang diformat untuk keterbacaan.

---

### 10. DLQ (Dead Letter Queue)

**Hak Akses:** Administrator

**Fungsi Utama:**
- Menampilkan daftar pesan di Dead Letter Queue dengan filter berdasarkan source stream dan trace ID.
- Menampilkan detail pesan: subject, payload JSON, alasan kegagalan (MaxDeliverExceeded, dll), dan timestamp.
- Mendukung pagination dengan ukuran halaman 25, 50, atau 100 record.
- Menyediakan filter berdasarkan alasan kegagalan.
- Menampilkan payload pesan dalam format JSON yang diformat.

---

### 11. Notifications & Webhooks

**Hak Akses:** Administrator

**Fungsi Utama:**
- Mengonfigurasi settings per kanal: Telegram (chat id + bot token), Email (recipient + SMTP password), Push (device token + server key), Webhook (callback URL + signature secret).
- Menguji pengiriman notifikasi dengan payload sampel untuk memverifikasi koneksi tiap kanal yang aktif.
- Menampilkan riwayat pengiriman (delivery logs) dengan status: queued, sent, retrying, failed.
- Endpoint inbound receiver (`/notifications/receive/*`) menerima payload eksternal dan mengantarkannya melalui kanal yang dikonfigurasi.
- Menampilkan log delivery dengan detail attempts, error message, dan created time.

---

### 12. Users / Account Management

**Hak Akses:** Administrator

**Fungsi Utama:**
- Menampilkan daftar akun pengguna dengan informasi username, email, role, status aktif/nonaktif, dan timestamp pembuatan.
- Membuat akun baru dengan username, email, password, dan role yang ditentukan.
- Mengedit akun: mengubah username, email, role, dan status aktif.
- Menonaktifkan akun tanpa menghapus data historis; akun nonaktif tidak dapat login.
- Menghapus akun secara permanen dari sistem.
- Mendukung role: admin, operator, viewer.

---

### 13. Profile

**Hak Akses:** Administrator, Operator, Viewer

**Fungsi Utama:**
- Menampilkan informasi profil: username, email, role, dan timestamp pembuatan akun.
- Memperbarui username dan email melalui form profil.
- Mengganti password dengan memasukkan password lama dan password baru.
- Menampilkan daftar sesi login aktif dengan informasi perangkat, browser, dan timestamp.
- Menghapus akun sendiri dengan konfirmasi password.
- Melakukan logout dari sesi saat ini.
