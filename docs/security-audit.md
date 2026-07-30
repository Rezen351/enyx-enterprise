# 🔧 Security Audit — Gateway & Service Hardening (2026-07-14)

> Laporan *stress test & penetration test* (toolkit di `test/`). Dipisahkan dari `planning.md` karena ini adalah laporan hasil pengujian, bukan dokumen arsitektur.

## Temuan & Perbaikan

| # | Temuan (pentest/stress) | Perbaikan | File |
|---|--------------------------|-----------|------|
| 1 | `/modules` & `/nodes` dapat diakses **tanpa token** (200) | Module Service sekarang menegakkan JWT (HS256, secret sama dengan Auth) + RBAC: read butuh user valid, write butuh `admin`/`operator`. Health `/health` tetap publik. | `services/module/internal/middleware/auth.go` (baru, stdlib-only), `services/module/main.go`, `services/module/internal/config/config.go` |
| 2 | Rate limit Kong terlalu ketat → bottleneck (Auth 20/menit, global 100/menit) | Dinaikkan: global `100→300`/menit, auth-public `20→60`/menit, route terlindungi `120→300`/menit (jam disesuaikan). Login tetap dilindungi dari brute-force. | `infra/kong/kong.yml` |
| 3 | Header keamanan tidak ada + `Server`/`X-Powered-By` bocor | Plugin global `response-transformer` menyuntikkan CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS; menghapus `Server` & `X-Powered-By`. Plus `KONG_NGINX_HTTP_SERVER_TOKENS: off`. | `infra/kong/kong.yml`, `docker-compose.yml` |
| 4 | XSS reflection pada `POST /modules` | Validasi input menolak `<` `>` & control char pada `name`/`description`; encoder JSON sudah HTML-escape sebagai lapisan kedua. | `services/module/internal/handler/handler.go` |
| 5 | Tidak ada metrik host (CPU/RAM/disk) di Prometheus → bottleneck sulit dilacak | Tambah `node-exporter` (host) & `cAdvisor` (per-container) + job scrape di Prometheus. | `docker-compose.yml`, `infra/prometheus/prometheus.yml` |

## Catatan

- Middleware JWT Module Service dibuat **tanpa dependensi baru** (verifikasi HMAC-SHA256 pakai stdlib) agar `go.mod` tidak berubah & build tetap ringan.
- Validasi RBAC di service bersifat *defense-in-depth*; Kong tetap berperan sebagai rate-limiter/entry point (plugin `jwt` Kong sengaja tidak diaktifkan — validasi claim tetap di service masing-masing, konsisten dengan pola Control Service).
- O1 (Mosquitto `allow_anonymous false` + `password_file` + `acl.conf`) sudah **closed** — konfigurasi file sudah diterapkan di repo, tinggalenergizing dengan restart container Mosquitto agar enforcement aktif di runtime.

## Verifikasi

Jalankan `python3 test/cli.py pentest` (ekspektasi: *Protected routes reject unauthenticated access* → PASS) dan `python3 test/cli.py metrics` (ekspektasi job `node-exporter` & `cadvisor` muncul).

## Remediasi Terbuka (Open Items — Belum Selesai)

Tidak ada open item keamanan yang tersisa. O1 sudah **closed** — tinggal restart container Mosquitto untuk me-load konfigurasi baru.

