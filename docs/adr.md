# 📌 Architecture Decision Records (ADR)

> Kumpulan keputusan arsitektur penting beserta konteks & alasan. Dipisahkan dari `planning.md` agar dokumen utama tetap fokus pada arsitektur murni. Referensi: praktik standar ADR (merw/101-adr).

---

## ADR-001 — Konsolidasi MinIO (2026-07-12)

**Konteks:** Semula direncanakan instance MinIO terpisah per service (`minio-stream` untuk snapshot/recording, `minio-ml` untuk hasil anotasi YOLOv8). Muncul usulan alternatif: MinIO hanya milik ML, dan Stream cukup menangani API MediaMTX lalu menaruh snapshot/recording ke MinIO-nya ML.

**Keputusan:** Ambil **Opsi C — 1 instance MinIO bersama, multi-bucket, scoped access key.** Bukan Opsi A (Stream bergantung MinIO ML) dan bukan Opsi B (2+ instance MinIO di host yang sama).

**Alasan:**
1. **Urutan deploy & bounded context.** Stream Service sudah `✅` dan live; ML/Vision belum dibuat. Jika Stream menulis ke MinIO ML, Stream tidak bisa jalan sebelum ML di-deploy (regresi prinsip *Independen Deployable*). Stream memproduksi snapshot/recording → harus tetap punya storage sendiri (bucket `stream`).
2. **Performa.** Bottleneck MinIO adalah disk I/O + bandwidth network, bukan proses MinIO. Membelah jadi 2 instance di host/disk sama justru menambah kontensi (2 proses berebut resource), bukan isolasi. Satu instance dengan disk SSD/NVMe lebih dari cukup untuk beban TA ini (beberapa kamera, object level GB–ratusan GB). MinIO dirancang untuk throughput puluhan GB/s.
3. **Resilience.** Kelemahan satu instance = SPOF object storage. Mitigasinya **bukan** membelah container di 1 host, tapi menjalankan 1 MinIO dalam **mode distributed / erasure-coding multi-drive** (mis. 4 drive) di host yang sama. Itu lebih tangguh daripada 2 container di 1 disk.
4. **Isolasi tetap terjaga.** Buckets terpisah + access key ter-scoping (`stream-svc-key` → rw `stream`; `ml-svc-key` → rw `ml-vision` + ro `stream`) memenuhi prinsip *Zero-Trust Internal*, setara dengan isolasi per-instance.
5. **Efisiensi operasional.** Mengurangi jumlah container & beban backup, menjawab risiko "terlalu banyak instance" yang sudah tercatat di dokumen.

**Skema akhir:**
```
minio (1 instance, erasure-coding multi-drive bila memungkinkan)
  ├─ bucket: stream      owner: Stream Service   (rw: stream-svc-key)
  └─ bucket: ml-vision   owner: ML / Vision API  (rw: ml-svc-key, ro: stream)
```
ML membaca frame sumber dari `stream` (key read-only) untuk inferensi, tanpa Stream harus mengirim file ke ML. Retensi per bucket bisa berbeda (snapshot/recording pendek, model/annotated panjang).

---

## ADR-002 — Ekspor Agregat Telemetri via Analytics (Opsi A, 2026-07-13)

**Konteks:** Mahasiswa/peneliti butuh akses data telemetri berjangka panjang. Semula direncanakan service `export/` terpisah.

**Keputusan:** Ekspor agregat telemetri **tidak** dibuat sebagai service terpisah, melainkan diimplementasikan langsung di Analytics Service sebagai `GET /analytics/export` (CSV, kolom `bucket,node_id,metric,count,sum,min,max,avg,last`, resolusi `day`/`hour`/`raw`).

**Alasan:** Daily aggregate (retensi 10 tahun + kompresi) sudah cukup untuk penelitian jangka panjang (termasuk range 5+ tahun). Menghindari service baru yang memperbesar kompleksitas operasional. Service `export/` terpisah (alerts/commands/audit/Parquet) tetap tertunda sebagai Fase 9b.

---

## ADR-003 — Shared JWT Secret lintas Service (2026-07-16)

**Konteks:** Beberapa service (Auth, WS, ML, Stream) memvalidasi JWT dengan secret yang sama.

**Keputusan:** Diterima untuk TA (sama secret, validasi di service masing-masing). Produksi disarankan per-service key + mTLS.

**Alasan:** Mengurangi kompleksitas operasional di skala TA. Melanggar prinsip *Zero-Trust Internal* secara ketat, namun acceptable mengingat防御-in-depth via validasi di setiap service. Tercatat sebagai trade-off di Risiko Teknis `planning.md`.

---

## ADR-004 — Konsolidasi Redis (2026-07-16)

**Konteks:** Semula direncanakan 4 instance Redis terpisah per service (`redis-module`, `redis-alert`, `redis-notification`, `redis-export`), masing-masing dengan exporter sendiri (total 4 container Redis + 4 exporter Redis).

**Keputusan:** Gabung menjadi **1 instance Redis bersama (`redis-shared`)** dengan **multi-DB** (logical database terpisah per service) + **1 exporter bersama**. Sama seperti pola ADR-001 (MinIO), bukan membelah container di 1 host.

**Alasan:**
1. **Pola konsisten dengan MinIO (ADR-001).** Redis adalah cache/ephemeral store, bukan sumber kebenaran domain (DB per-service tetap MariaDB/TimescaleDB terpisah — prinsip *Database-per-Service* tidak dilanggar). Bottleneck Redis adalah RAM/disk I/O, bukan proses; membelah jadi 4 container di host sama justru menambah kontensi.
2. **Isolasi tetap terjaga via logical DB.** Setiap service diberi `REDIS_DB` berbeda (module=0, alert=1, notification=2, export=3). Untuk prod dapat ditambah user Redis ter-scoping per DB. Setara isolasi per-instance untuk kebutuhan TA.
3. **Efisiensi operasional.** Mengurangi 3 container Redis + 3 exporter (7 -> 2 container: 1 redis + 1 exporter). Sesuai tujuan mengurangi "terlalu banyak instance" di planning.

**Skema mapping DB:**
```
redis-shared (1 instance, appendonly on)
 ├─ DB 0: module-service        (owner: module; juga dipakai cctv-capture)
 ├─ DB 1: alert-service         (owner: alert)
 ├─ DB 2: notification-service  (owner: notification)
 └─ DB 3: export-service        (owner: export)
```

**Yang TIDAK diubah:** MariaDB/TimescaleDB tetap per-service (inti arsitektur TA). Hanya Redis (cache) yang dikonsolidasi.

> **Catatan implementasi:** `cctv-capture` sebelumnya menunjuk `redis-module:6379` DB0 -> dialihkan ke `redis-shared:6379` DB0 (mapping sama, tidak breaking).

---

## ADR-005 — Konsolidasi Prometheus Exporter (2026-07-16)

**Konteks:** Terdapat 11 container exporter terpisah: 8× `mysqld-exporter` (per MariaDB), 2× `postgres-exporter` (per TimescaleDB), 1× `redis-exporter` (sudah 1 sejak ADR-004). Tiap exporter hanya scrape 1 target → banyak container ringan yang menambah beban orkestrasi.

**Keputusan:** Gabung exporter per **tipe** menjadi **3 container** (`mysqld-exporter-all`, `postgres-exporter-all`, `redis-exporter`), masing-masing menjalankan beberapa proses exporter pada port berbeda (satu proses per DB target). Prometheus scrape tiap target sebagai job terpisah (instance label tetap membedakan DB). Sama seperti ADR-001/004: mengurangi jumlah container, bukan mengurangi cakupan metrik.

**Alasan:**
1. **Efisiensi orkestrasi.** 11 container → 3 container (-8). Exporter adalah side-car metrik ringan; tidak butuh isolasi per-DB.
2. **Metrik tetap terpisah.** Tiap proses exporter punya target/DSN sendiri dan Prometheus memberi `instance` label berbeda (`mariadb-auth`, `mariadb-module`, dst) → dashboard Grafana tidak berubah.
3. **Risiko rendah.** Tidak mengubah credential/ACL; sekadar menggabung proses sejenis dalam 1 container (multi-port).

**Skema mapping (port per target):**
```
mysqld-exporter-all   (1 container)
 ├─ :9104 → mariadb-auth
 ├─ :9105 → mariadb-control
 ├─ :9106 → mariadb-module
 ├─ :9107 → mariadb-stream
 ├─ :9108 → mariadb-audit
 ├─ :9109 → mariadb-alert
 ├─ :9110 → mariadb-notification
 └─ :9111 → mariadb-ml

postgres-exporter-all (1 container)
 ├─ :9187 → timescaledb-module
 └─ :9188 → timescaledb-analytics

redis-exporter        (1 container, sudah ada sejak ADR-004)
 └─ :9121 → redis-shared (DB0-3 via label)
```

**Yang TIDAK diubah:** Jumlah job & label di `prometheus.yml` tetap sama (per-DB), hanya `targets:` menunjuk port container gabungan. cAdvisor, node-exporter, mosquitto-exporter, nats-exporter, kong tetap 1 masing-masing (sudah shared).

---

## ADR-006 — DLQ Saga via NATS Advisory (2026-07-16)

**Konteks:** planning.md & testing-plan-agent.md §17a menuntut *Dead Letter Queue* yang sesungguhnya, bukan subject `saga.*.dlq` buatan. Saat ini bila sebuah JetStream consumer gagal melewati `MaxDeliver`, pesan hilang tanpa jejak (status "Resilience by Design" di planning.md masih ⬜). NATS JetStream menerbitkan advisory resmi `$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.{stream}.{consumer}` saat ini terjadi — mekanisme ini harus dimanfaatkan, bukan dibuat sendiri.

**Keputusan:** Buat **service `dlq` (DLQ Saga Worker)** yang:
1. Subscribe ke `$JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.>` (wildcard semua stream/consumer).
2. Pada advisory: ambil pesan asli dari source stream via `js.GetMsg(stream, stream_seq)` (bukan body advisory), lalu:
   - **Republish** pesan asli ke JetStream stream `DLQ` (`Subjects: dlq.msg`, `Retention: Limits`, `MaxAge: 720h` = 30 hari, `Replicas: 2`, `Duplicates: 2m` + header `Nats-Msg-Id` untuk publisher-side dedup).
   - **Insert** satu baris ke tabel `dlq_messages` di **`mariadb-audit`** (database yang sudah ada, bukan DB baru) berisi `trace_id`, `source_stream`, `source_consumer`, `stream_seq`, `subject`, `reason`, `payload`, `headers`.
3. Propagasi `trace_id`: baca header NATS `Trace-Id` pada advisory & pesan asli; bila kosong digenerate UUID. `trace_id` dicatat di log tiap span dan di-forward pada republish DLQ (`Trace-Id`) serta disimpan di DB. Helper reusable di `internal/trace` (`X-Trace-Id` HTTP / `Trace-Id` NATS).

**Alasan / Trade-off:**
1. **Mengapa service khusus, bukan di Audit Service?** DLQ worker butuh lifecycle JetStream consumer pada subject advisory sistem (`$JS.*`) dan akses `GetMsg` lintas stream mana pun. Menaruhnya di Audit mencampuradukkan concern audit-log (Core NATS `audit.log`) dengan infra DLQ. Service `dlq` ringan (hanya NATS + 1 tabel) → isolasi tanggung jawab jelas, sesuai filosofi modular.
2. **Mengapa tabel `dlq_messages` di `mariadb-audit` (bukan DB baru)?** AGENTS.md §4 mewajibkan *Database-per-Service isolation* — dilarang buat DB baru sembarangan. DLQ adalah **artefak observability/audit** (bukan domain bisnis), sehingga menempatkannya di instance `mariadb-audit` yang sudah ada memenuhi aturan tanpa melanggar isolasi: tidak ada service lain yang menulis/query DB domain milik service lain; dlq & audit adalah dua worker berbeda yang kebetulan berbagi instance MariaDB fisik yang sama (persis seperti pola konsolidasi ADR-001/004/005). Query DLQ hanya via endpoint `GET /dlq/messages` milik service `dlq` sendiri.
3. **Mengapa `Replicas: 2` padahal NATS dev single-node?** Spesifikasi §17a eksplisit menuntut `Replicas:2`. Di dev single-node, NATS menolak R>1 → worker **tidak panic**: `AddStream` akan gagal dan worker log warning lalu tetap jalan dengan R=1 efektif (lihat catatan verifikasi `[~]`). Di prod (NATS cluster 3-node per planning.md §HA) R=2 terpenuhi penuh. Ini adalah trade-off dokumentasi: spec vs keterbatasan dev single-node.
4. **Mengapa ambil pesan asli via `GetMsg`, bukan body advisory?** Body advisory hanya *metadata* (stream/consumer/seq/reason), bukan payload asli. Mengambil ulang via `stream_seq` menjamin DLQ menyimpan pesan utuh (subject + header + data) yang sebenarnya gagal diproses.

**Skema akhir:**
```
nats (JetStream)
  └─ advisory $JS.EVENT.ADVISORY.CONSUMER.MAX_DELIVERIES.>
       → dlq worker
            ├─ GetMsg(source_stream, stream_seq)        # ambil pesan asli
            ├─ Publish → stream DLQ  (dlq.msg, 30d, R:2) # durable retention
            └─ INSERT dlq_messages (mariadb-audit)       # audit trail DLQ
```

**Yang TIDAK diubah:** Tidak ada subject `saga.*.dlq` buatan; tidak ada DB baru; contract NATS lain tidak berubah. §17b/§17d/§17e ditangani agent lain.

---

## ADR-007 — Transactional Outbox untuk Event Publishing (2026-07-16)

**Konteks:** Service penulis event (Module, Control, Alert) saat ini mem-publish event NATS
(`audit.log`, `control.*`, `alert.*`, `telemetry.ingest`, `system.status`) **setelah** commit DB
bisnis. Ini adalah *dual-write problem* (lihat `planning.md` § "Data Consistency: Transactional
Outbox"): bila NATS publish gagal setelah DB commit sukses, event hilang dan subscriber (Audit/
Alert/Analytics/Notification) kehilangan data tanpa jejak.

**Keputusan:** Terapkan **Transactional Outbox Pattern** di Module, Control, dan Alert.
1. Setiap service menulis baris bisnis **dan** 1 baris `outbox` (subject + payload + `msg_id`
   UUID) dalam **satu transaksi DB** MariaDB milik service tersebut (isolasi *Database-per-Service*
   tetap terjaga — relay hanya baca DB service sendiri).
2. Sebuah **relay worker** (goroutine per service) mem-poll baris `outbox` yang `sent=false`,
   mem-publish ke NATS JetStream dengan header **`Nats-Msg-Id` = `msg_id`** (publisher-side dedup
   resmi NATS), lalu menandai `outbox.sent=true` dalam transaksi terpisah setelah publish sukses.
3. **Consumer-side idempotency:** subscriber (Audit/Notification/Analytics) mengecek `msg_id`
   (diambil dari header `Nats-Msg-Id` / payload) dan menolak duplikat — key disimpan di Redis
   (`redis-shared`, per-DB) dengan TTL > window retry. Kombinasi publisher dedup + consumer
   idempotency mencapai *exactly-once effect* (sesuai `planning.md`).
4. Relay dijalankan sebagai goroutine di `main.go` tiap service, dengan **graceful shutdown**
   (AGENTS.md §7.1.7) via `context` cancellation + `WaitGroup`.

**Alasan:**
- Menghilangkan *lost event* saat NATS down/blip: outbox row sudah ter-commit, relay kirim nanti.
- Tidak mengubah kontrak NATS existing (subject & payload identik) — subscriber tidak perlu diubah
  untuk bisa jalan; idempotensi di sisi consumer bersifat incremental & backward-compatible.
- `Nats-Msg-Id` adalah fitur JetStream resmi (bukan custom), sehingga publisher dedup otomatis
  ditangani server NATS dalam window waktu.
- Minimal & idiomatik: publish code existing **dibungkus** (wrap) dengan outbox, tidak ditulis ulang;
  migrasi `outbox` ditambah ke `migrate.go` tiap service via GORM AutoMigrate.

**Batasan / Trade-off:**
- `telemetry.ingest` & `mqtt.{node}` (PublishLive) adalah event live high-volume; baris bisnis
  telemetry disimpan di TimescaleDB (DB terpisah), sehingga outbox untuk event ini berada di
  MariaDB module sebagai *durable record* — relay memastikan tidak ada event telemetry hilang saat
  NATS blip (sebelumnya langsung `Publish` hilang).
- Relay poll interval default 2s; backoff eksponensial saat NATS disconnect.

**Verifikasi (§17b):**
- Simulasi NATS down saat business commit sukses → outbox row tetap ada (`sent=false`) → relay
  kirim setelah NATS recover (event **tidak hilang**).
- Redelivery (NATS `Nats-Msg-Id` + consumer dedup Redis) → **tidak ada duplikat** di subscriber.

**Yang TIDAK diubah:** `database/sql` raw (module/control) & `*gorm.DB` (alert) tetap dipakai;
schema bisnis existing tidak diubah; hanya tabel `outbox` baru + relay worker.

---

## ADR-008 — Ganti algoritma RL dari PPO ke TD3 (2026-07-30)

**Konteks:** Model PPO untuk AeroponicSimulatorEnv mencapai status training yang stabil, tetapi mempertahankan local optimum yang kurang optimal (clip_fraction≈0, episode length beku di 90–94 siklus, pertumbuhan akar terbatas). Reward jarang muncul setiap 720 langkah pada episode 1440 langkah, sehingga sinyal pembelajaran PPO kurang efektif.

**Keputusan:** Beralih ke **TD3 (Twin Delayed DDPG)** untuk kontinyu aeroponik.

**Alasan:**
1. **Overcoming local optimum:** TD3 deterministic policy + target policy smoothing mengurangi risiko terjebak padastrategi konservatif yang diamati pada PPO.
2. **Sparse reward handling:** Replay buffer off-policy pada TD3 memungkinkan data reuse meski reward hanya muncul setiap beberapa ratus siklus di simulator deterministik.
3. **Action noise untuk eksplorasi:** Gaussian action noise pada TD3 lebih sesuai untuk kontrol threshold valve (A_valve biner) dibanding entropy regularization PPO.
4. **Hyperparameter lebih stabil untuk continuous control:** TD3 lebih sedikit sensitif terhadap tuning dibanding SAC, dan lebih cocok untuk deployment CPU-only (tanpa CUDA).
5. **Latar belakang akademis:** TD3 diakui sebagai algoritma off-policy deterministic yang efektif untuk robot/precision agriculture continuous control.

**Skema model dan deployment:**
```
Training : control-model-training/
  ├── train_td3.py
  ├── evaluate_td3.py / evaluate_td3_3day.py
  ├── models/aeroponic_td3.zip
  └── models/vec_normalize_td3.pkl

Deployment:
  ├── model-controller:8080  (inference, FastAPI + SB3 TD3)
  └── model-control:8081     (scheduler + telemetry consumer)
```

**Yang TIDAK diubah:** Arsitektur dua-service (`model-controller` + `model-control`), kontrak NATS (`telemetry.ingest`/`telemetry.batch`), interface Control Service, atau skema database. Hanya model weight + loop training yang berganti algoritma.

**Verifikasi:**
- Training 2M timesteps berhasil (`aeroponic_td3.zip` + `vec_normalize_td3.pkl`).
- Evaluasi 5-episode + 3-day continuous menunjukkan stabil tanpa pelanggaran bounds pH/EC.
- `docker-compose.yml` sudah menunjuk `MODEL_PATH=/app/models/aeroponic_td3.zip` dan `VEC_NORM_PATH=/app/models/vec_normalize_td3.pkl`.

---

## 7. ADR-007: Transparent `/v1` API Versioning via Kong Gateway Reverse Proxy

**Tanggal:** 2026-07-21  
**Status:** Approved  
**Konteks:** Sistem membutuhkan pengenalan *API Versioning* standar (`/v1`) untuk seluruh panggilan API publik dari frontend dashboard dan klien eksternal guna mempermudah evolusi API dan evolusi kontrak di masa mendatang. Namun, memodifikasi struktur rute di 10+ microservices backend (Go & Python) secara manual berisiko merusak kompatibilitas internal dan menambah *code churn*.

**Keputusan:** Terapkan **Gateway-Level Reverse Proxy Versioning (`/v1`)** di Kong API Gateway.
1. **Konfigurasi Rute Regex Kong:** Setiap rute didaftarkan di Kong dengan pattern regex `~/v1(?<rel_uri>/<path>.*)`.
2. **Plugin Request-Transformer:** Dipasang plugin `request-transformer` pada rute `-v1` dengan aturan `replace.uri: $(uri_captures['rel_uri'])` untuk secara otomatis mengupas (strip) prefix `/v1` sebelum request diteruskan ke upstream container backend.
3. **Frontend Dashboard Integration:** `dashboard/src/api/client.js` secara otomatis menambahkan prefix `/v1` pada semua panggilan REST API.
4. **Backward Compatibility:** Endpoint lama tanpa `/v1` (mis. `/auth/login`) tetap dipertahankan di Kong sebagai rute fallback untuk klien legacy/firmware.

**Alasan:**
- **Zero Code Churn pada Backend:** Tidak ada satu pun baris kode microservice backend (Go/Python) yang perlu diubah.
- **Satu Pintu Pengaturan:** Evolusi versi API di masa mendatang (`/v2`, `/v3`) cukup dikonfigurasi di Kong Gatewaytanpa menduplikasi router internal microservice.
- **Performa Tinggi:** Overhead latency Kong untuk URL rewrite < 1ms (`X-Kong-Proxy-Latency: ~0-1ms`).

**Verifikasi:**
- `curl -i http://localhost:8000/v1/health` → `200 OK` (ter-forward ke Auth Service)
- `curl -i http://localhost:8000/v1/modules` → `401 Unauthorized` (ter-forward ke Module Service)
- `curl -i -X POST http://localhost:8000/v1/auth/login` → `401 Unauthorized` / `200 OK` (ter-forward ke Auth Service)
