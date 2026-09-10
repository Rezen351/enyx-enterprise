# 🤖 AGENTS.md — Aturan Proyek & Panduan AI Agent (Project Rules & Agent Guidelines)

Dokumen ini berisi aturan yang **wajib** diikuti saat mengembangkan, mengubah, atau meninjau kode di repositori ini. Aturan ini berlaku untuk semua kontributor manusia maupun AI agent. Aturan di bawah ini dirancang untuk memastikan kode tetap konsisten, arsitektur terstruktur dengan baik, serta setiap keputusan dan perubahan terdokumentasi secara transparan dan rapi.

---

## 📚 0. Peta Dokumentasi Proyek (Documentation Map)

Dokumen di folder `docs/` adalah **single source of truth** untuk arsitektur, keputusan, pengujian, dan operasional. Agent wajib membaca dokumen yang relevan sebelum mengerjakan tugas pada domain terkait. Jangan mengubah keputusan arsitektur di luar `adr.md` tanpa mencatatnya sebagai ADR baru.

| Dokumen | Peran / Tanggung Jawab | Kapan dibaca/diperbarui |
|---------|------------------------|--------------------------|
| [planning.md](file:///home/almuzky/TA/Microservices/docs/planning.md) | Arsitektur murni, *bounded context*, risiko teknis, dan desain sistem inti. | Sebelum perubahan arsitektur/schema; perbarui saat arah berubah. |
| [roadmap.md](file:///home/almuzky/TA/Microservices/docs/roadmap.md) | Rencana fase & fitur (checklist `[ ]`/`[x]`). | Tandai `[x]` saat fase selesai. |
| [adr.md](file:///home/almuzky/TA/Microservices/docs/adr.md) | **Architecture Decision Records** — keputusan arsitektur penting + alasan (MinIO, ekspor analitik, shared JWT). | Baca sebelum menyimpang dari keputusan; tulis ADR baru untuk keputusan besar. |
| [runbook.md](file:///home/almuzky/TA/Microservices/docs/runbook.md) | **Operational Runbook** — panduan diagnosa & troubleshooting saat sistem bermasalah (studi kasus nyata). | Rujuk saat debugging isu produksi/container; tambah kasus baru yang ditemukan. |
| [security-audit.md](file:///home/almuzky/TA/Microservices/docs/security-audit.md) | Laporan *penetration test* & *hardening* (Kong, JWT/RBAC, XSS, eksporter). | Rujuk saat menyentuh gateway/keamanan; catat temuan baru di sini. |
| [grafana-service-health.md](file:///home/almuzky/TA/Microservices/docs/grafana-service-health.md) | Panduan membaca dashboard Grafana "Service Health" (Prometheus metrics). | Rujuk saat menginvestigasi metrik/health; bukan diubah kecuali dashboard berubah. |
| [testing-plan-agent.md](file:///home/almuzky/TA/Microservices/docs/testing-plan-agent.md) | Checklist pengujian **backend/API** (diperbolehkan & dijalankan Agent). | Perbarui `[ ]`→`[x]` per step saat verifikasi API. |
| [testing-implementasi-manual.md](file:///home/almuzky/TA/Microservices/docs/testing-implementasi-manual.md) | Checklist pengujian **UI/visual** (wajib manual oleh User). | Hanya User yang mengubah status; Agent boleh menulis draf skenario. |
| [logs.md](file:///home/almuzky/TA/Microservices/logs.md) | Log harian aktivitas & keputusan teknis (wajib diupdate tiap tugas). | Update setelah setiap tugas selesai. |
| [docs/integration-guides/](file:///home/almuzky/TA/Microservices/docs/integration-guides/) | **Per-service integration guides** — API contracts, NATS/MQTT topics, database schema, curl examples, dan error codes untuk setiap microservice. | Wajib diperbarui saat arsitektur service berubah (tambah/hapus endpoint, ubah schema, topic, env, atau contract). |

> **Catatan integrasi:** Keputusan arsitektur (ADR), runbook operasional, hasil audit keamanan, dan panduan monitoring Grafana di bawah ini merujuk ke dokumen di atas agar tidak terjadi duplikasi aturan.

---

## 🌐 1. Aturan Bahasa (Language Rule)

**Semua teks antarmuka (UI) pada dashboard dan seluruh respons dari API harus menggunakan Bahasa Inggris (English).**

### Ketentuan Detail:
1. **Dashboard / Frontend (React)**
   - Semua label, judul, tombol, placeholder, pesan error, tooltip, dan teks statis lainnya di UI wajib berbahasa Inggris.
   - Jangan menambahkan teks Bahasa Indonesia (atau bahasa lain) ke dalam komponen UI, kecuali itu adalah data dinamis dari pengguna (mis. nama yang diinput user).
   - Nama variabel, komponen, dan fungsi tetap mengikuti konvensi penamaan kode (bahasa Inggris), bukan teks yang ditampilkan ke pengguna.

2. **API Responses (Backend / Microservices)**
   - Semua pesan respons API — termasuk `message`, `error`, `description`, validasi field, dan status — wajib menggunakan Bahasa Inggris.
   - Jangan mengembalikan pesan error atau status dalam Bahasa Indonesia (atau bahasa lain).
   - Log internal (server logs) boleh menggunakan bahasa yang dipakai tim, namun payload/respons yang dikirim ke klien (dashboard/app) harus selalu English.

3. **Dokumentasi API (OpenAPI/Swagger, contoh request/response)**
   - Contoh dan deskripsi endpoint juga menggunakan Bahasa Inggris agar konsisten dengan respons aktual.

> **Catatan:** Dokumentasi proyek ([planning.md](file:///home/almuzky/TA/Microservices/docs/planning.md), [roadmap.md](file:///home/almuzky/TA/Microservices/docs/roadmap.md), [logs.md](file:///home/almuzky/TA/Microservices/logs.md), komentar deskriptif) boleh tetap berbahasa Indonesia karena ditujukan untuk tim internal, namun **produk yang diakses end-user (dashboard & API) selalu English**.

---

## 🛠️ 2. Alur Kerja Terstruktur (Structured Workflow)

Setiap agen atau kontributor wajib mengikuti alur kerja terstruktur agar perubahan tidak menimbulkan *breaking changes* atau merusak stabilitas sistem.

### 2.1 Fase Perencanaan (Planning Phase)
Sebelum melakukan modifikasi kode yang bersifat kompleks (misalnya: membuat service baru, mengubah database schema, atau mengintegrasikan library baru):
1. **Riset & Pahami Arsitektur**: Baca dan pahami arsitektur modular yang dijelaskan di [planning.md](file:///home/almuzky/TA/Microservices/docs/planning.md) dan target di [roadmap.md](file:///home/almuzky/TA/Microservices/docs/roadmap.md).
2. **Buat Rencana Implementasi**: Tulis rencana langkah demi langkah di file rencana perubahan jika diperlukan, atau sampaikan rencana secara jelas kepada tim/user sebelum eksekusi.

### 2.2 Fase Pelacakan Tugas (Task Tracking)
1. Gunakan format to-do list (`task.md` atau pesan status) untuk melacak progress pekerjaan:
    - `[ ]` Tugas belum dimulai
    - `[/]` Tugas sedang dalam pengerjaan (In Progress)
    - `[x]` Tugas selesai dilakukan (Completed)
2. Pecah tugas besar menjadi sub-tugas yang lebih kecil dan terukur.
3. **Troubleshooting Operasional**: Jika menemui anomali sistem (container mati, live stream putus, gateway error), rujuk [runbook.md](file:///home/almuzky/TA/Microservices/docs/runbook.md) untuk pola diagnosa end-to-end yang sudah tercatat. Tambahkan kasus baru ke runbook setelah berhasil diatasi agar tim lain bisa belajar dari solusi tersebut.

### 2.3 Fase Verifikasi & Pengujian (Verification Phase)
1. **Verifikasi Fungsional**: Selalu uji kode secara lokal (misalnya menjalankan unit test atau memvalidasi endpoint API via container Docker).
2. **Wajib Tambah / Update Test Case untuk Fitur Baru**:
   - Setiap kali menambahkan fitur baru, mengubah logika bisnis, atau menambahkan endpoint API baru pada microservices, kontributor / AI Agent **WAJIB menambahkan test case baru** pada Unit & Feature Test Suite ([`test/unit_test.py`](file:///home/almuzky/TA/Microservices/test/unit_test.py)).
   - Perbarui katalog endpoint pada [`test/config.py`](file:///home/almuzky/TA/Microservices/test/config.py) dan skenario pada [`test/resilience_test.py`](file:///home/almuzky/TA/Microservices/test/resilience_test.py) jika fitur memerlukan pengujian beban/chaos.
   - Dilarang menganggap fitur selesai tanpa adanya unit test otomatis di folder `test/` yang menguji fungsionalitasnya via Kong Gateway `/v1`.
3. **Pemeriksaan Kompilasi & Visual Graph Generator**:
   - Pastikan semua service yang dimodifikasi dapat di-build dengan sukses tanpa error (`go build` / Python check).
   - Jalankan `python3 test/unit_test.py && python3 test/stress_test.py && python3 test/resilience_test.py` untuk memverifikasi seluruh test cases PASS (100% OK) dan memastikan grafik PNG visual di [`test/results/`](file:///home/almuzky/TA/Microservices/test/results) ter-update.
4. **Dokumentasi Pengujian**: Dokumentasikan hasil pengujian atau perintah pengujian yang digunakan dalam [testing-implementasi-manual.md](file:///home/almuzky/TA/Microservices/docs/testing-implementasi-manual.md) atau logs.
5. **Investigasi Metrik & Health**: Saat menelusuri anomali performa/latensi/error rate, rujuk [grafana-service-health.md](file:///home/almuzky/TA/Microservices/docs/grafana-service-health.md) untuk memahami arti tiap panel dashboard (Prometheus metrics). Gunakan dashboard untuk mengonfirmasi status UP/DOWN, error rate, dan resource usage layanan yang sedang diubah.

---

## 📝 3. Aturan Pencatatan & Dokumentasi (Logging & Documentation)

Setiap aktivitas pengembangan **harus dicatat secara disiplin**. Ini adalah kunci utama transparansi dan ketertelusuran proyek.

### 3.1 Pembaruan Development Logs ([logs.md](file:///home/almuzky/TA/Microservices/logs.md))
Setiap kali menyelesaikan sebuah tugas, kontributor/agent **wajib** memperbarui file [logs.md](file:///home/almuzky/TA/Microservices/logs.md) dengan ketentuan:
1. **Gunakan Format Tabel**: Tulis aktivitas yang telah diselesaikan menggunakan tabel Markdown standar.
2. **Gunakan Status yang Konsisten**:
   - `✅` untuk aktivitas yang sudah selesai (Done)
   - `🟡` untuk aktivitas yang sedang berjalan (In Progress)
   - `❌` untuk aktivitas yang terhambat (Blocked)
   - `📝` untuk catatan penting/issues tambahan
3. **Keputusan Teknis**: Jika membuat keputusan arsitektural penting (seperti merubah skema DB, memilih library baru, atau mengubah logic workflow), tambahkan baris baru ke dalam tabel **Keputusan Teknis** di `logs.md`.
4. **Isu & Catatan**: Catat kendala atau konfigurasi khusus di bagian **Isu & Catatan** agar tim lain mengetahuinya.

### 3.2 Sinkronisasi Roadmap & Planning ([roadmap.md](file:///home/almuzky/TA/Microservices/docs/roadmap.md) & [planning.md](file:///home/almuzky/TA/Microservices/docs/planning.md))
1. Jika sebuah fitur atau fase dalam [roadmap.md](file:///home/almuzky/TA/Microservices/docs/roadmap.md) telah diselesaikan, ubah status dari `[ ]` menjadi `[x]`.
2. Jika ada perubahan arah pengembangan atau arsitektur sistem, perbarui detailnya di [planning.md](file:///home/almuzky/TA/Microservices/docs/planning.md).

---

## 🏗️ 4. Konsistensi Arsitektur & Pola Kode (Architectural Consistency)

Untuk menjaga kualitas codebase, kontributor wajib mengikuti pola arsitektur yang sudah disepakati:

1. **Database-per-Service Isolation**
   - Setiap service wajib menggunakan database terpisah.
   - Dilarang keras melakukan query langsung lintas database dari satu service ke service lainnya. Komunikasi data antar-service wajib melalui API HTTP atau Event Bus (NATS JetStream).
2. **Struktur Direktori Go (Services)**
   - Ikuti struktur standar yang sudah ada di folder `services/`:
     - `internal/config/` untuk konfigurasi & environment variables.
     - `internal/model/` untuk definisi struct & DTO.
     - `internal/repository/` untuk interaksi database.
     - `internal/service/` untuk business logic.
     - `internal/handler/` atau `internal/delivery/` untuk HTTP handlers.
3. **Manajemen Environment Variables**
   - Setiap variabel lingkungan (env) baru wajib dideklarasikan di `.env.example` beserta deskripsi/default value-nya.
   - Jangan pernah melakukan hardcode untuk kredensial, token, JWT secret, atau port. Gunakan konfigurasi env.
4. **Standardisasi API Response Wrapper**
   - Setiap microservice wajib menggunakan struktur respons JSON yang seragam untuk mempermudah konsumsi data di sisi frontend.
   - Respons Sukses (2xx): `{ "success": true, "data": <payload/array/object> }`.
   - Respons Eror (4xx/5xx): `{ "success": false, "error": { "code": "<KODE_ERROR>", "message": "<pesan_error_dalam_bahasa_inggris>" } }`.
    - **Prioritas Standarisasi Backend atas Kesiapan UI:** Jika ada endpoint lama yang belum mengikuti format wrapper standar di atas, Agent **wajib tetap mengimplementasikan standarisasi format tersebut di sisi backend**. Jangan menghindari perubahan kritis ini hanya karena takut akan merusak (break) tampilan UI dashboard. Kerjakan saja perubahan standar di backend tersebut, lalu sesuaikan kode UI/dashboard agar mengikuti dan mengonsumsi standar respons baru dari backend.
 5. **Sinkronisasi Integration Guide**
    - Setiap kali mengubah arsitektur service — termasuk menambah/menghapus endpoint, mengubah skema database, menambah/menghapus NATS/MQTT topic, menambah/mengubah environment variable, atau mengubah request/response contract — **wajib** memperbarui file integration guide yang sesuai di [`docs/integration-guides/`](file:///home/almuzky/TA/Microservices/docs/integration-guides/).
    - Integration guide adalah **single source of truth** untuk API contract, NATS/MQTT topics, database schema, dan curl examples. Jangan sampai kode berubah tanpa dokumentasi integrasi yang menyertainya.
 6. **Manajemen Migrasi Database**
   - Setiap perubahan skema database wajib dikelola menggunakan sistem migrasi kode resmi (misal: migrations file di Go, atau auto-migration GORM yang terkelola dengan baik).
   - Dilarang melakukan modifikasi skema database (seperti menambah kolom, mengubah tipe data, atau menghapus tabel) secara manual langsung pada DBMS di lingkungan staging/produksi.
 6. **Korelasi ID Log (Distributed Tracing / Log Correlation)**
    - Mengingat skala microservice yang besar (~30 services), setiap request HTTP wajib menyertakan ID korelasi (`X-Correlation-ID` or `X-Request-ID`) di dalam header.
    - ID korelasi ini harus dipropagasikan ke setiap downstream service tujuan, termasuk payload event yang dikirim melalui Event Bus (NATS).
    - Cantumkan ID korelasi ini di setiap baris log terkait agar memudahkan pelacakan log terdistribusi secara end-to-end.
 8. **Keputusan Arsitektur (ADR)** — Setiap keputusan arsitektur penting (pemilihan infrastruktur, pola integrasi, trade-off) **wajib** dicatat sebagai ADR di [adr.md](file:///home/almuzky/TA/Microservices/docs/adr.md) sebelum/selama implementasi. Jangan mengubah arah keputusan yang sudah ada (mis. konsolidasi MinIO, shared JWT) tanpa menambahkan ADR baru yang merujuk ke alasan perubahannya. ADR bersifat *immutable* — keputusan yang dibatalkan cukup ditandai, tidak dihapus.

 9. **Single Source of Truth & Larangan Kontainer Yatim (Orphaned Containers)**
    - Semua infrastruktur, database, cache, broker, dan microservices yang berjalan **wajib dideklarasikan secara resmi** di dalam `docker-compose.yml`.
    - **DILARANG KERAS** membiarkan kontainer/sumber daya berjalan secara mandiri (*orphaned* atau sisa dari branch/worktree lain) tanpa terdaftar di `docker-compose.yml` utama.
    - Jika suatu layanan tidak digunakan atau dinonaktifkan di branch/sesi saat ini, definisinya beserta target monitoring-nya (seperti Prometheus scrape job dan exporters) harus dihapus secara bersih, dan kontainer fisiknya dimatikan menggunakan perintah `docker compose up -d --remove-orphans`.
 10. **Optimasi Docker Build & Caching Dependensi (Docker Layer Caching)**
    - Saat membuat atau memodifikasi `Dockerfile` (terutama untuk service dengan dependensi besar seperti Service ML/Python, Node, atau Go), **wajib menggunakan metode Docker Layer Caching yang optimal** agar tidak perlu menginstal ulang seluruh dependensi dari awal setiap kali ada perubahan kecil pada program.
    - **Metode/Aturan Penulisan Dockerfile yang Benar:**
      1. **Salin Berkas Manifes Dependensi Terlebih Dahulu**: Salin berkas manifes dependensi (misal: `requirements.txt`, `package.json`, `go.mod` dan `go.sum`, atau `Gemfile`) secara terpisah sebelum menyalin kode sumber program.
      2. **Jalankan Instalasi Dependensi Terlebih Dahulu**: Jalankan perintah instalasi dependensi (misal: `pip install`, `npm install`, atau `go mod download`). Layer ini akan di-cache oleh Docker dan tidak akan dibangun ulang selama berkas manifes dependensi tidak berubah.
      3. **Salin Kode Sumber Program**: Salin sisa kode program (source code) setelah tahap instalasi dependensi selesai. Perubahan kode program kecil hanya akan membatalkan cache dari langkah penyalinan kode sumber ini ke bawah, sehingga proses build tetap sangat cepat.
      4. **Gunakan Multi-Stage Build**: Selalu gunakan multi-stage build untuk memisahkan lingkungan build (SDK penuh) dengan lingkungan runtime minimal agar ukuran akhir image seminimal mungkin.
      5. **Gunakan Cache Mounts**: Jika didukung oleh Docker builder/runner, gunakan cache mount (misal: `type=cache` untuk pip cache, npm cache, atau go build cache) untuk mempercepat instalasi dependensi.
    - **Contoh Struktur Dockerfile (Python/ML Service):**
      ```dockerfile
      FROM python:3.10-slim AS builder
      WORKDIR /app
      # 1. Salin manifes dependensi terpisah
      COPY requirements.txt .
      # 2. Install dependensi (layer ini akan dicache)
      RUN --mount=type=cache,target=/root/.cache/pip \
          pip install -r requirements.txt
      # 3. Salin sisa kode program
      COPY . .
      ```

---

## 🔒 5. Keamanan Kode (Security Guidelines)

1. **Rahasia & Kredensial**: Dilarang melakukan commit terhadap file `.env`, key file, atau file berisi kredensial sensitif ke repositori Git.
2. **Input Validation**: Lakukan validasi dan sanitasi input pada semua endpoint API untuk mencegah SQL Injection, XSS, dan serangan injeksi lainnya.
3. **Autentikasi & Otorisasi**: Gunakan middleware JWT yang sudah terstandarisasi untuk melindungi endpoint sensitif dan patuhi RBAC (Role-Based Access Control) yang sudah ditentukan di Auth Service.
4. **Rujuk Hasil Audit Keamanan**: Sebelum menyentuh gateway (Kong), validasi input, header keamanan, atau penanganan kredensial, bacalah [security-audit.md](file:///home/almuzky/TA/Microservices/docs/security-audit.md). Dokumen tersebut berisi temuan *penetration test* (akses tanpa token, rate limit, XSS, header bocor) beserta perbaikannya — jangan mengulang pola yang sudah di-*harden*. Catat temuan baru di sana.

---

## 💬 6. Gaya Komunikasi & Protokol Perilaku Agent (Agent Communication & Behavior Protocol)

Jika tugas dijalankan oleh AI Agent:

### 6.1 Gaya Komunikasi
1. **Ringkas & Informatif**: Berikan penjelasan yang padat, langsung ke tujuan, dan format dengan Markdown yang bersih.
2. **Prinsip Tautan File**: Saat menyebutkan file, direktori, kelas, atau fungsi, **selalu buat tautan aktif** menggunakan format markdown dengan skema `file://` (misal: `[logs.md](file:///home/almuzky/TA/Microservices/logs.md)`).
3. **Konfirmasi Tindakan Berisiko**: Minta konfirmasi pengguna sebelum melakukan tindakan yang merusak (seperti menghapus database, file penting, atau mereset repository).

### 6.2 Protokol Perilaku AI Agent (Actionable & Verifiable Rules)
1. **Zero-Placeholder Rule (Tanpa Placeholder)**:
   - **DILARANG KERAS** menghasilkan kode dengan komentar placeholder seperti `// TODO: implement here`, `/* sisa kode ... */`, atau `// ...`.
   - Semua perubahan kode harus lengkap, fungsional, dan siap dijalankan tanpa membutuhkan modifikasi manual tambahan dari pengguna.
2. **Prinsip Konteks Penuh (Full Context Rule)**:
   - Sebelum mengedit berkas, bacalah file target secara menyeluruh menggunakan tool pembaca file untuk memahami struktur kode yang ada.
   - **Pertahankan komentar dokumentatif dan lisensi** yang sudah ada sebelumnya. Jangan menghapus dokumentasi kode tanpa alasan jelas.
3. **Prinsip Dampak Minimal (Minimal Footprint)**:
   - Lakukan modifikasi kode dengan cara yang paling terfokus dan terlokalisasi. Hindari mengubah file atau baris kode yang tidak berhubungan dengan tugas yang diberikan.
4. **Verifikasi Mandiri Sebelum Melapor (Self-Validation)**:
   - Jalankan perintah kompilasi (`go build` atau compiler Vite React) dan pengujian lokal setelah melakukan perubahan kode, guna memastikan tidak ada sintaks rusak atau pengujian yang gagal sebelum melaporkan pekerjaan selesai.
5. **Batasan Pengujian Manual & Cakupan Uji API (Manual vs API Testing Scope)**:
   - **Cakupan Uji API (DIPERBOLEHKAN bagi Agent):** AI Agent **sangat dianjurkan** untuk melakukan pengujian backend secara riil, termasuk menjalankan container, mengeksekusi request HTTP (`curl`, `httpie`), mengetes WebSocket (`wscat`), memeriksa database, dan memverifikasi bahwa skema data/payload respons API cocok dengan ekspektasi dashboard. Agent **diperbolehkan** memperbarui status checklist (`[ ]` menjadi `[x]`) pada berkas rencana pengujian backend (**[testing-plan-agent.md](file:///home/almuzky/TA/Microservices/docs/testing-plan-agent.md)**) setelah melakukan verifikasi sukses.
     - **Pembaruan Checklist Bertahap:** Setiap kali selesai memverifikasi satu langkah pengujian (step), Agent **wajib** langsung memperbarui checklist (`[ ]` -> `[x]`) untuk langkah tersebut di **[testing-plan-agent.md](file:///home/almuzky/TA/Microservices/docs/testing-plan-agent.md)**, tidak lagi menunggu seluruh langkah pengujian di satu service selesai untuk diperbarui sekaligus.
   - **Cakupan Uji UI/Visual (DILARANG bagi Agent):** Pengujian visual, tata letak (layout), kegunaan (UX), dan interaksi antarmuka di browser pada berkas **[testing-implementasi-manual.md](file:///home/almuzky/TA/Microservices/docs/testing-implementasi-manual.md)** (seperti checklist `D1`-`D12`) **wajib** dilakukan secara manual oleh Pengguna (User). Agent **dilarang keras** mengubah status checklist UI di berkas tersebut seolah-olah Agent mengujinya secara visual.
   - **Peran Agent dalam Pengujian Manual UI:**
     - Memeriksa kesesuaian skenario pengujian UI dengan perubahan kode.
     - Menulis draf skenario pengujian baru ke berkas manual (tetap dengan status `[ ]`).
     - Membaca status untuk koordinasi kesiapan fitur.
6. **Pencegahan Perulangan Error Tanpa Ujung (Doom Loop Prevention)**:
   - Jika Agen menemui error kompilasi atau kegagalan tes yang sama setelah 3 kali percobaan perbaikan berturut-turut, Agen **harus berhenti** dan melaporkan kendala tersebut kepada Pengguna secara mendetail beserta opsi-opsi pemecahannya, alih-alih terus melakukan percobaan acak.
7. **Perlindungan Unit Test (Test Protection Rule)**:
   - **DILARANG KERAS** memodifikasi, menghapus, atau melemahkan asersi (*assertions*) pada unit test yang sudah ada hanya agar tes tersebut "lolos" secara paksa setelah adanya modifikasi kode. Jika tes gagal, cari letak kesalahan pada kode implementasi baru, bukan mengubah tesnya—kecuali jika spesifikasi fitur tersebut memang sengaja diubah oleh Pengguna.
8. **Larangan Dependensi Tanpa Izin (Unmanaged Dependencies Restriction)**:
   - **DILARANG KERAS** menginstal atau mengimpor library, package, atau dependensi eksternal baru (`go get`, `npm install`, dll.) ke dalam proyek tanpa persetujuan tertulis atau instruksi eksplisit dari Pengguna.
9. **Pembersihan Lingkungan & Manajemen Kontainer Terfokus (Focused Container Management & Cleanup)**:
   - Setelah Pengguna memberikan konfirmasi bahwa pengujian/perbaikan suatu service telah selesai, Agent **wajib mematikan/menghapus kontainer terkait** secara bersih (`docker compose stop <service>` atau `docker compose down`) dan membersihkan data uji agar lingkungan kembali steril.
   - Saat akan melakukan perbaikan kode (*bug-fixing*), Agent **dilarang menyalakan seluruh service sekaligus** via `docker compose up -d`. Agent **hanya boleh menyalakan service yang berkaitan langsung** dengan perbaikan tersebut (misalnya: `docker compose up -d <service_name> <dependent_db_name>`) agar pengujian terisolasi dan penggunaan sumber daya tetap efisien.

---

## 🛠️ 7. Aturan Penulisan Kode (Coding Guidelines)

Untuk menjaga kualitas dan keterbacaan kode, kontributor dan AI agent wajib mengikuti standar penulisan berikut:

### 7.1 Go (Backend / Microservices)
1. **Explicit Error Handling**:
   - Selalu periksa error yang dikembalikan fungsi: `if err != nil { ... }`.
   - Hindari penggunaan *blank identifier* `_` untuk menampung error, kecuali benar-benar aman dan disertai komentar penjelasan.
   - Gunakan wrapping error dengan format `fmt.Errorf("konteks error: %w", err)` untuk mempermudah debugging log.
2. **No Panic in Production**:
   - Dilarang menggunakan fungsi `panic()` di dalam kode produksi, kecuali pada inisialisasi awal aplikasi (`main.go` / `init()`) jika dependensi kritis gagal di-load.
   - Gunakan error return value untuk penanganan alur bisnis yang gagal.
3. **Structured Logging**:
   - Gunakan structured logger yang sudah ditentukan di dalam repositori dengan level yang tepat (`INFO`, `WARN`, `ERROR`, `DEBUG`).
4. **Context Propagation**:
   - Teruskan `context.Context` ke semua fungsi yang melakukan operasi I/O (database, HTTP request, NATS publish/subscribe) untuk mendukung timeout dan cancellation.
5. **Code Formatting & Linting**:
   - Pastikan semua file kode Go diformat menggunakan `go fmt` sebelum melakukan commit.
   - Jalankan pemeriksaan statis dengan `go vet` untuk mendeteksi potensi bug umum secara lokal sebelum kompilasi.
6. **Unit Testing Framework**:
   - Setiap fungsi bisnis kritis di layer `service` dan `repository` wajib memiliki unit test yang memadai.
   - Gunakan mocking framework (seperti mock generator atau manual stubbing) untuk memisahkan pengujian dari dependensi eksternal seperti database aktif atau server NATS.
7. **Graceful Shutdown**:
   - Setiap entrypoint aplikasi (`main.go`) wajib mengimplementasikan mekanisme penanganan sinyal OS (`SIGINT` dan `SIGTERM`).
   - Saat sinyal mati diterima, aplikasi harus berhenti menerima request baru, menyelesaikan proses request/worker yang sedang berjalan (in-flight), lalu menutup semua koneksi external resource (database, Redis, NATS, HTTP server) secara bersih sebelum benar-benar keluar (*exit*).

### 7.2 React / Vite (Frontend)
1. **Functional Components & Hooks**:
   - Gunakan *functional components* dengan React Hooks (bukan class components).
   - Pastikan aturan Hooks diikuti dengan ketat (jangan memanggil Hooks di dalam kondisional, perulangan, atau nested functions).
2. **Zero Memory Leaks**:
   - Bersihkan efek samping di dalam `useEffect` (misalnya: hapus event listener, bersihkan interval/timeout, dan disconnect WebSocket) menggunakan return cleanup function.
3. **Styling & CSS**:
   - Ikuti sistem styling yang ada (Vanilla CSS atau Tailwind jika digunakan). Pertahankan konsistensi desain sistem.
4. **Clean Code & Proptypes**:
   - Buat komponen sekecil dan se-modular mungkin. Pisahkan business logic kompleks ke dalam custom Hooks.
5. **Code Formatting & Linting**:
   - Wajib menggunakan `eslint` untuk mendeteksi error sintaksis dan pola kode React yang kurang tepat.
   - Gunakan `prettier` untuk memastikan format berkas konsisten sebelum melakukan commit.
6. **Frontend Unit Testing**:
   - Komponen UI yang memiliki interaksi kompleks atau custom Hooks wajib diuji menggunakan library pengujian (seperti `Vitest` / `React Testing Library`).
   - Mock semua HTTP request menggunakan tools (seperti MSW atau jest mocks) untuk memastikan unit test berjalan secara terisolasi tanpa memanggil API real.

---

## 📄 8. Standar Commit & Git Workflow

AI Agent dan kontributor wajib mengikuti standar commit berikut:

1. **Format Conventional Commits**:
   Format pesan commit harus mengikuti pola: `<type>(<scope>): <deskripsi singkat>` (semuanya dalam bahasa Inggris).
   - `feat`: Fitur baru.
   - `fix`: Perbaikan bug.
   - `docs`: Perubahan dokumentasi.
   - `style`: Perubahan formatting kode, semicolon, dll (bukan perubahan logic).
   - `refactor`: Rekonstruksi kode tanpa mengubah fungsionalitas.
   - `test`: Menambah atau memodifikasi pengujian.
   - `chore`: Tugas pemeliharaan, update dependencies, dll.
   *Contoh:* `feat(auth): implement JWT token verification`
2. **Atomic Commits**:
   - Lakukan commit dalam ukuran kecil dan fokus pada satu perubahan spesifik. Jangan menggabungkan beberapa fitur tidak terkait dalam satu commit besar.
