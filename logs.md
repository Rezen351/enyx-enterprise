# 📓 Development Logs — enyx-enterprise

> **Format:** `[YYYY-MM-DD] [STATUS] Deskripsi`  

---

### Implementasi Modbus TCP + UI Transport Selector (2026-09-20)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Schema Config:** Menambahkan field `transport`, `ip_address`, dan `port` pada `Config::ModbusSensor` di [`include/Config.h`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/include/Config.h:~34) dengan default `"RTU"` untuk backward compatibility. |
| 2 | ✅ | **Handler TCP:** Membuat `ModbusTCPHandler` di [`ProtocolHandlers.h`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ProtocolHandlers.h:~98) & [`ProtocolHandlers.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ProtocolHandlers.cpp:~277) yang melakukan raw Modbus TCP frame via `WiFiClient` (MBAP header + PDU), dengan timeout 1s per register dan parsing multitype (`UINT16`, `INT16`, `UINT32`, `INT32`, `FLOAT32`). |
| 3 | ✅ | **Registry:** Mendaftarkan protocol `"MODBUS_TCP"` di [`HardwareManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/HardwareManager.cpp:~255). Handler dipilih otomatis berdasarkan `ms.transport == "TCP"` saat reload config. |
| 4 | ✅ | **Config Load:** Memperbarui [`ConfigManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ConfigManager.cpp:~217) dan [`WebConfigPortal.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/WebConfigPortal.cpp:~528) untuk parse field TCP baru dengan default aman (`ip_address="192.168.1.100"`, `port=502`). |
| 5 | ✅ | **Frontend UI:** Memperbarui [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~582) `drawModbus()` untuk menampilkan dropdown **Transport** (RTU/TCP). Jika TCP: tampilkan field IP Address + Port. Jika RTU: tampilkan Baudrate. Metadata list view ikut menyesuaikan. |
| 6 | ✅ | **Backward Compat:** Config lama tanpa field `transport` tetap berjalan karena default ke `"RTU"`. Tidak ada breaking change pada API `/api/hardware` atau MQTT telemetry format. |

**Keputusan Teknis:**
- Menggunakan raw TCP frame daripada library `ModbusIP` untuk menghindari dependensi eksternal baru dan kontrol penuh terhadap MBAP header pada ESP32.
- `ModbusTCPHandler` menggunakan single static `WiFiClient` yang reconnect otomatis jika koneksi terputus, menjaga konsistensi dengan pola single-transport-per-handler yang sudah ada.
- Scanner Modbus (`/api/modbus/start_scan`, `/api/modbus/scan_reg_batch`) intentionally **belum diubah** ke TCP; UI scanner tetap RTU-only untuk sekarang. Transisi UI scanner ke RTU/TCP choice akan dilakukan di fase berikutnya.

### Integrasi Modul Multiplexer PCF8575 Relay (Output) & Sensor/Switch (Input) (2026-09-19)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Driver PCF8575 Bus:** Mengimplementasikan `Pcf8575Bus` di [`ProtocolHandlers.h`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ProtocolHandlers.h) & [`ProtocolHandlers.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ProtocolHandlers.cpp) dengan bitmask shadow `pcfStates` 16-bit, safe initial state (`0xFFFF`), serta read/write atomic bit-level via I2C `Wire`. |
| 2 | ✅ | **Handler Output (`PCF8575_OUT`):** Membuat `Pcf8575OutputHandler` (turunan `ProtocolHandler`) untuk mengendalikan modul relay single/multi channel dengan dukungan mode `active_low` dan alamat I2C configurable (default `0x20`). |
| 3 | ✅ | **Handler Input (`PCF8575_IN`):** Membuat `Pcf8575InputHandler` untuk memanfaatkan pin quasi-bidirectional PCF8575 sebagai input sensor digital/switch, terintegrasi ke telemetri MQTT periodik. |
| 4 | ✅ | **Registry & Hot-Swap:** Mendaftarkan `"PCF8575_OUT"` dan `"PCF8575_IN"` ke `ProtocolRegistry` di [`HardwareManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/HardwareManager.cpp). Memperbaiki deklarasi scope `Config::OutputPin` di `HardwareManager::telemetryTask`. |
| 5 | ✅ | **I2C Auto-Discovery Scanner:** Menambahkan deteksi otomatis perangkat PCF8575 (range alamat `0x20` - `0x27`) pada fungsi `HardwareManager::discoverSensors()`. |
| 6 | ✅ | **Rest API Web Portal:** Memperbarui endpoint `GET /api/config/hardware` dan `POST /api/config/hardware` di [`WebConfigPortal.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/WebConfigPortal.cpp) untuk parsing atribut `protocol`, `i2c_addr`, dan `active_low`. |
| 7 | ✅ | **Web Portal UI (`script.js`):** Menambahkan antarmuka konfigurasi interaktif pada tab Hardware Inputs dan Outputs untuk memilih protocol Direct GPIO vs PCF8575 Expander, nomor channel `P0`–`P15`, alamat I2C, serta toggle Active-LOW. |
| 8 | ✅ | **Build Verifikasi:** Kompilasi sukses tanpa error menggunakan PlatformIO (`pio run`) menghasilkan `firmware.bin` (RAM: 20.2%, Flash: 83.9%) dan image LittleFS `littlefs.bin`. |

**Keputusan Teknis:**
- Default mode untuk relay PCF8575 adalah **Active-LOW** karena arsitektur internal PCF8575 memiliki current sink yang jauh lebih kuat saat LOW (~25mA) dibanding HIGH (~100µA weak pull-up).
- Saat boot, semua 16 pin PCF8575 di-drive ke HIGH (`0xFFFF`) untuk mencegah glitch relay menyala sesaat ketika ESP32 baru dinyalakan.
- Format topik MQTT actuasi (`set_output`) dan telemetri output/input tetap 100% konsisten sehingga tidak menimbulkan breaking changes pada backend microservices dan dashboard.

---

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Perbaikan `handleApiConfigExport()`:** mengembalikan penggunaan `doc.remove()` nested yang benar (`doc["security"].remove("admin_pass")`, `doc["protocols"]["wifi"].remove("password")`, dll) dan menambahkan strip `mqtt.user`. Ini memperbaiki bug notasi dot ArduinoJson yang menyebabkan export tetap membocorkan plaintext credential. |
| 2 | ✅ | **Perbaiki double encryption di `saveFullConfig()`:** menghapus semua pemanggilan `CryptoCredential::encrypt()` dari `saveFullConfig()` agar credential hanya dienkripsi sekali oleh `ConfigManager::saveConfig()`. Double encryption menyebabkan `AUTH_TOKEN` di disk terenkripsi 2x, dan `loadConfig()` hanya mendekrip 1x, sehingga login selalu 401. |
| 3 | ✅ | **Tambahkan first-boot login bypass:** menambahkan flag `ADMIN_PASS_CONFIGURED` di `Config`. Jika `config.json` tidak memiliki `admin_pass`, login mengizinkan password apapun dan generate token baru. Ini memungkinkan setup awal tanpa hardcode password. |
| 4 | ✅ | **Enkripsi `mqtt.user`:** menambahkan encrypt/decrypt untuk `protocols.mqtt.user` di `ConfigManager::saveConfig()`/`loadConfig()` seperti field sensitif lainnya. |
| 5 | ✅ | **Tambahkan endpoint recovery `POST /api/config/reset_credentials`:** endpoint baru yang membaca `config.json`, decrypt semua credential, strip fields sensitif, tulis kembali dengan `credentials_encrypted: true`, lalu reload config. Ini adalah jalur recovery tanpa perlu upload ulang LittleFS jika firmware lama sudah ter-flash. |
| 6 | ✅ | **Perbarui `data/config.json` menjadi template tanpa plaintext credential:** menghapus `admin_pass`, `wifi.password`, `mqtt.pass`, `mqtt.user` dari default config LittleFS. File ini aman untuk di-upload via `pio run --target uploadfs`. |

**Keputusan Teknis:**
- `saveFullConfig()` bertanggung jawab hanya menyusun JSON dari memory state; `ConfigManager::saveConfig()` bertanggung jawab penuh untuk encrypt sensitive fields sebelum tulis ke LittleFS.
- `ADMIN_PASS_CONFIGURED` ditambahkan untuk membedakan antara "belum di-set" dan "sudah di-set", sehingga first-boot tidak memaksa password tertentu.
- Recovery endpoint `reset_credentials` diprioritaskan dibanding upload filesystem karena tidak memerlukan koneksi serial/USB.

---

### Fix: Config Export Mengembalikan Plaintext WiFi Password di Captive Portal (2026-09-13)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Perbaikan `handleApiConfigExport()` di [`WebConfigPortal.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/WebConfigPortal.cpp:~713):** mengganti `doc.remove("protocols.wifi.password")` (notasi dot yang tidak didukung ArduinoJson untuk nested object) menjadi `doc["protocols"]["wifi"].remove("password")`. Akibatnya field sensitif `wifi.password`, `wifi.eap_password`, `mqtt.pass`, `mqtt.user`, `security.admin_pass`, dan `security.auth_token` kini benar-benar dihapus dari file `config.json` hasil export. |

**Keputusan Teknis:**
- ArduinoJson `remove()` hanya menghapus key langsung di level object yang dipanggil; notasi dot tidak bekerja untuk path bersarang.
- Tambahan `doc["protocols"]["mqtt"].remove("user")` karena `user` MQTT juga sensitif dan sebelumnya tidak di-strip.

---

### Perbaikan WiFi Captive Portal AP Mati-Nyala di Firmware Aeroponic Node (2026-09-12)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Analisis akar masalah AP mati-nyala di [`firmware/aeroponic-node/src/protocols/NetworkManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/NetworkManager.cpp):** ditemukan dua bug utama yang menyebabkan hotspot ESP32 tidak stabil: (a) loop `while(true)` mencoba reconnect tanpa jeda setelah 20× `WiFi.begin()` gagal, sehingga radio WiFi terus di-reset dan mengganggu softAP; (b) penggunaan `WiFi.disconnect(true)` yang berlebihan di mode `WIFI_AP_STA` berpotensi menurunkan AP. |
| 2 | ✅ | **Perbaikan reconnect delay — [`NetworkManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/NetworkManager.cpp:~60):** menambahkan `vTaskDelay(5000 / portTICK_PERIOD_MS)` setelah log "WiFi Connect Failed! Retrying in 5 seconds..." agar loop reconnect tidak menabrak radio WiFi berulang kali tanpa henti. |
| 3 | ✅ | **Perbaikan disconnect sebelum reconnect — [`NetworkManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/protocols/NetworkManager.cpp:~38):** mengganti `WiFi.disconnect(true)` menjadi `WiFi.disconnect(false)` di kedua jalur (WPA2-Enterprise dan WPA2-Personal) agar softAP tidak di-tear-down secara berlebihan saat mode AP_STA. |
| 4 | ✅ | **Peningkatan observabilitas low-heap restart — [`SystemMonitor.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/SystemMonitor.cpp:~31):** menambahkan logging `Free Heap`, `Min Heap`, dan `Max Alloc` sebelum `ESP.restart()` sehingga kalau hot spot tetap tidak stabil karena kehabisan memori, pengguna bisa mengidentifikasi dari Serial monitor. |
| 5 | 🟡 | **Verifikasi manual oleh user** — user akan melakukan pengujian manual untuk memastikan AP stabil tidak mati-nyala lagi. |

**Keputusan Teknis:**
- Root cause "AP mati-nyala" bukanlah error watchdog/brownout, melainkan tight-reconnect loop tanpa backoff yang memaksa WiFi.stack memuat ulang berulang kali sementara softAP harus tetap hidup di `WIFI_AP_STA`.
- Solusi menerapkan exponential-style backoff minimal (tetap 5s untuk sekarang) + disconnect graceful (`false`) untuk menjaga AP tetap menyala.
- Jika setelah perbaikan AP masih turun, langkah selanjutnya adalah memindahkan non-WiFi task ke Core 1 dan menambahkan task registration ke TaskWatchdog untuk deteksi watchdog-initiated restart.

---

### Perbaikan UI/UX Loading & Feedback di Firmware Captive Portal (2026-09-12)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Standarisasi loading feedback — [`style.css`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/style.css:~223):** menambahkan 2 kelas spinner reusable (`spinner-sm` untuk tombol, `spinner-inline` untuk status) agar semua indikator loading menggunakan animasi spin yang konsisten. |
| 2 | ✅ | **Helper `setButtonLoading()` — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~24):** menambahkan fungsi utility untuk mengatur disabled + spinner + teks tombol secara atomik, dipakai oleh login, form submit, scan, discovery, dan import. |
| 3 | ✅ | **Login loading state — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~108):** tombol Sign In kini menampilkan spinner + `Loading…` selama autentikasi, dan kembali ke teks asli jika gagal. |
| 4 | ✅ | **Form submit loading — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~639-714):** semua `save*()` kini menyetel loading state pada tombol submit sebelum request dan mengembalikannya setelah response, termasuk WiFi, MQTT, Device, RS485, Hardware, dan Account. |
| 5 | ✅ | **Modbus scanner loading — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~549-637):** `startScanId()` dan `startScanReg()` menampilkan spinner pada tombol scan selama operasi berlangsung, dengan reset otomatis via `finally`. |
| 6 | ✅ | **Discovery button loading — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~217):** mengganti `disabled + innerText` menjadi `setButtonLoading()` agar konsisten dengan pattern umum. |
| 7 | ✅ | **Status refresh loading — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~151):** tombol Refresh pada halaman Status sekarang menunjukkan spinner selama `loadStatus()` mengambil data. |
| 8 | ✅ | **Password field security — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~238-275):** password fields kini dikosongkan saat load config dan hanya menampilkan placeholder `•••••••• (leave empty to keep current)` untuk mencegah kebocoran kata sandi di UI. |
| 9 | ✅ | **Konfirmasi destructive actions — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~322-540):** semua tombol Remove (Input, Output, Modbus sensor/register, I2C sensor) kini memunculkan `confirm()` sebelum menghapus, mencegah kehilangan data secara tidak sengaja. |
| 10 | ✅ | **Empty states — [`script.js`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/data/script.js:~277-295):** menambahkan `renderEmptyStates()` yang menampilkan pesan ramah jika belum ada Input/Output/Modbus/I2C yang dikonfigurasi, menggantikan area kosong yang tidak jelas. |

**Keputusan Teknis:**
- Semua loading state menggunakan spinner CSS inline + kelas utility, tidak ada library eksternal, sehingga tidak menambah ukuran binary firmware.
- Pattern `setButtonLoading()` menyimpan teks asli tombol di `dataset.originalText`, sehingga restore otomatis tanpa hardcode string di setiap caller.
- Password tidak lagi di-prefill dari API untuk menghindari bocor ke UI; backend tetap menyimpan hash yang benar.
- Empty state messages disamakan secara UX: jelas, singkat, dan mengarahkan user ke aksi selanjutnya.

**Dampak UX:**
- User sekarang mendapatkan feedback visual pada setiap aksi yang memakan waktu: login, refresh status, scan Modbus, upload config, dan semua form submit.
- Tidak ada lagi tombol yang "mengunci" UI tanpa indikasiProgress, sehingga perceived performance meningkat.

---

### Pembuatan Firmware Simulator Instance 20 (Modbus, AC, SunnyBoy, SunnyIsland) (2026-09-10)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Membuat Konfigurasi Instance 20 ([`instances/node-20.json`](file:///home/almuzky/TA/Microservices/firmware/firmware-sim/instances/node-20.json)):** Mengonfigurasi instance simulator dengan `node_id: "node-20"`, MAC `20:20:AC:53:BA:20`, dan 4 perangkat Modbus (sensor lingkungan `sensor_modbus`, meter AC `ac_meter`, inverter surya `sunny_boy`, dan inverter baterai `sunny_island`), serta input analog terkait. |
| 2 | ✅ | **Memperbarui Sensor Model ([`sensors.py`](file:///home/almuzky/TA/Microservices/firmware/firmware-sim/firmware_sim/sensors.py)):** Menambahkan profil sensor untuk parameter listrik SunnyBoy (tegangan & arus PV DC ~380V / 8.5A, daya PV), SunnyIsland (tegangan & arus baterai DC ~52V / 24A, SOC %, daya baterai), AC meter (tegangan & arus AC ~220V / 8.5A, frekuensi 50Hz, energi kWh), serta istilah bahasa Indonesia (`tegangan`, `arus`, `daya`). |
| 3 | ✅ | **Verifikasi Telemetri:** Menjalankan eksekusi uji payload telemetri `node-20` via `firmware_sim.simulator.FirmwareSimulator._build_telemetry()` dan memverifikasi seluruh struktur `telemetry.inputs` dan `telemetry.modbus` terbit dengan format valid dan nilai realistis. |
| 4 | ✅ | **Konfigurasi Broker MQTT Anonymous ([`instances/node-20.json`](file:///home/almuzky/TA/Microservices/firmware/firmware-sim/instances/node-20.json)):** Mengubah endpoint broker MQTT instance 20 ke `tcp://167.205.44.103:1883` tanpa username dan password (`user: ""`, `pass: ""`), serta memverifikasi koneksi anonymous dan pengiriman telemetri berhasil. |

**Keputusan Teknis:**
- Parameter kelistrikan SunnyBoy (solar PV DC & grid AC), SunnyIsland (baterai DC, SOC %, & AC), dan AC Power Meter dimasukkan ke dalam `telemetry.modbus` sebagai perangkat Modbus RTU terpisah dengan slave ID unik (1..4) sesuai standar industri inverter SMA / SunSpec.
---

### Firmware Audit & Critical Fixes — Aeroponic Node (2026-09-14)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Audit 7 domain firmware** — Web Config Portal, Sensor/Modbus, Security/Crypto, WiFi/Network, Watchdog/SystemMonitor, OTA/ConfigManager, Boot Flow. Total 150 findings: 36 CRITICAL, 39 HIGH, 47 MEDIUM, 28 LOW. |
| 2 | ✅ | **Perbaikan CryptoCredential lifecycle** — tambah `CryptoCredential::init()` di `main.cpp` sebelum `ConfigManager::init()`, dan tambah decryption path di `ConfigManager::loadConfig()` untuk semua encrypted fields. |
| 3 | ✅ | **Perbaikan boot health check** — hapus dead code `boot_count <= 2`, simplifikasi ke `boot_count > 3` only. |
| 4 | ✅ | **Perbaikan thread safety** — tambah `mqttMutex`, `dataMutex`, `logMutex` untuk shared resources. |
| 5 | ✅ | **Perbaikan GPIO ISR bug** — split `emergencyShutdownTriggered` dan `gpioInterruptFired`. |
| 6 | ✅ | **Perbaikan OTA upload** — tambah size limit dari partition, proper error response. |
| 7 | ✅ | **Atomic config save** — `.tmp` → rename + backup `.bak`. |
| 8 | ✅ | **Hapus `setInsecure()`** — ganti dengan error log + fallback warning. |
| 9 | ✅ | **Fix strict aliasing FLOAT32** — ganti pointer cast dengan `memcpy`. |
| 10 | ✅ | **Web UI security** — `escapeHtml()`, `AbortController` timeout, bound scan loop, security headers. |
| 11 | ✅ | **Watchdog registration** — registrasi `TelemetryTask`, naikkan heartbeat timeout. |
| 12 | ✅ | **NODE_ID fallback** — pindah ke `NetworkManager::wifiTask()` setelah WiFi connected. |

**Keputusan Teknis:**
- Semua fixes menjaga backward compatibility; tidak ada perubahan schema atau MQTT topic format.
- Local control rules dihapus sesuai permintaan user, tidak di-audit.
- Build berhasil: Flash 88.5%, RAM 20.3%.

**Sisa Issues (butuh refactoring lebih lanjut):**
- Full TLS/HTTPS untuk captive portal
- Proper key derivation dengan per-device salt + PBKDF2
- Persistent rate limiter di NVS
- CSRF token protection
- Config schema validation

---

### Fix: Modbus Register Config Loading & Board Target — Aeroponic Node (2026-09-19)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Fix `ConfigManager::loadConfig()` di [`ConfigManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/src/core/ConfigManager.cpp):** menambahkan loading field `length` dan `data_type` untuk setiap ModbusRegister. Sebelumnya field ini hanya di-load oleh WebConfigPortal API (`handleApiHardwarePost`), sehingga FLOAT32/INT32/UINT32 register tidak berfungsi saat boot dari `config.json` di LittleFS — `length` default 0 dan `data_type` default "" menyebabkan semua multi-register value selalu dibaca sebagai UINT16 tunggal. |
| 2 | ✅ | **Default value safety —** menambahkan fallback `if (reg.length == 0) reg.length = 1` dan `if (reg.data_type == "") reg.data_type = "UINT16"` untuk mencegah crash atau interpretasi salah pada config lama yang tidak memiliki field baru. |
| 3 | ✅ | **Update `platformio.ini` — [`platformio.ini`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/platformio.ini):** mengganti `board = esp32dev` menjadi `board = esp32-s3-devkitc-1` sesuai koreksi target board (ESP32 DevKit S3). |
| 4 | ✅ | **Update `wokwi.toml` — [`wokwi.toml`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/wokwi.toml):** memperbarui path build output dari `esp32dev` ke `esp32-s3-devkitc-1` agar simulasi Wokwi tetap kompatibel. |
| 5 | ✅ | **Update `firmware.md` di [`firmware.md`](file:///home/almuzky/TA/Microservices/firmware/aeroponic-node/firmware.md):** menambahkan dokumentasi field-field register Modbus (`length`, `data_type`) dan contoh big-endian FLOAT32 decode (High Word `0x47C3` + Low Word `0x5000` → `0x47C35000` = 100000.0). |

**Keputusan Teknis:**
- `ConfigManager::loadConfig()` dan `WebConfigPortal::handleApiHardwarePost()` kini konsisten dalam memuat semua 6 field register Modbus.
- Board target dikembalikan ke ESP32-S3-DevKitC-1 agar konsisten dengan perangkat target hardware yang sebenarnya.
- FLOAT32 big-endian decode sudah benar di `ProtocolHandlers.cpp:238-241`; perbaikan ini memastikan field konfigurasi yang dibutuhkan sampai ke handler.

---

### Migrasi Kredensial ke NVS Namespace `creds` — Firmware Node (2026-09-21)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Membuat `CredentialManager`** — module baru [`src/core/CredentialManager.h`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/CredentialManager.h) & [`src/core/CredentialManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/CredentialManager.cpp) yang membungkus semua operasi NVS namespace `creds` untuk 9 field kredensial: `admin_user`, `admin_pass`, `auth_token`, `wifi_ssid`, `wifi_pass`, `wifi_eap_identity`, `wifi_eap_password`, `mqtt_user`, `mqtt_pass`. |
| 2 | ✅ | **Integrasi `CredentialManager` ke boot flow** — [`ConfigManager::init()`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/ConfigManager.cpp:~9) kini memanggil `CredentialManager::init()` lalu `CredentialManager::loadCredentials()` jika NVS berisi kredensial. Jika NVS kosong, fallback ke `loadConfig()` dari `config.json` lalu otomatis memigrasi ke NVS. |
| 3 | ✅ | **Pembatasan `loadConfig()`** — field kredensial di `config.json` hanya di-load jika NVS belum berisi kredensial (`!useNvsCredentials`). Ini mencegah overwrite NVS saat device sudah pernah di-konfigurasi. |
| 4 | ✅ | **Penyelarasan API handlers** — `handleApiLogin`, `handleApiWifiPost`, `handleApiMqttPost`, dan `handleApiAccountPost` di [`WebConfigPortal.cpp`](file:///home/almuzky/TA/Microservices/firmware/node/src/protocols/WebConfigPortal.cpp) kini menulis kredensial yang diubah ke NVS melalui `CredentialManager::set*()` sebelum menyimpan config non-kredensial. |
| 5 | ✅ | **Config export/import tanpa credential** — endpoint `/api/config/export` mengembalikan raw `config.json` (tidak ada credential untuk di-strip karena sudah pindah ke NVS). Endpoint `/api/config/import` memvalidasi payload, menulis ke `config.json`, lalu memanggil `CredentialManager::saveCredentials()` agar kredensial yang ada di payload otomatis dimigrasikan ke NVS. |
| 6 | ✅ | **Pembaruan template `data/config.json`** — menghapus blok `security` dan field credential WiFi/MQTT dari LittleFS template agar file ini aman untuk export/import dan tidak menyimpan secret. |
| 7 | ✅ | **Dokumentasi `firmware.md`** — memperbarui [firmware.md](file:///home/almuzky/TA/Microservices/firmware/node/firmware.md) untuk menjelaskan NVS namespace `creds`, perubahan boot sequence, dan format `config.json` baru tanpa credential. |
| 8 | ✅ | **Verifikasi build** — firmware berhasil dikompilasi untuk kedua target `esp32dev` dan `esp32s3` menggunakan PlatformIO venv (`/home/almuzky/venv/bin/pio run`). |

**Keputusan Teknis:**
- NVS namespace dipisah menjadi `creds` agar jelas batas antara data sensitif dan konfigurasi umum.
- `config.json` tetap menjadi single source of truth untuk konfigurasi non-kredensial; NVS menjadi single source of truth untuk kredensial.
- Migrasi otomatis dari `config.json` ke NVS hanya terjadi jika NVS belum memiliki flag `has_creds`, sehingga existing device yang pertama kali di-upgrade tetap bisa membaca config.json lama tanpa kredensial hilang.
- `saveFullConfig()` tidak lagi menyertakan field credential ke JSON, sehingga export/import lebih aman dan konsisten.

---

