# 📓 Development Logs — enyx-enterprise

> **Format:** `[YYYY-MM-DD] [STATUS] Deskripsi`

### WPA2 Enterprise Stabilization & WiFi Mode Audit (2026-09-23)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menyelesaikan fitur WPA2 Enterprise (eduroam) di firmware node: UI captive portal, API backend, NVS credential storage, dan runtime connection mode. |
| 2 | ✅ | Memperbaiki bug flag `WIFI_ENT_ENABLED` ditimpa `false` saat NVS kosong, sehingga mode enterprise dari `config.json` tetap aktif. |
| 3 | ✅ | Memperbaiki `KEY_TOO_LONG` pada NVS dengan mengganti nama kunci enterprise menjadi pendek (`ent_enabled`, `ent_user`, `ent_pass`, `ent_ca`, `ent_cert`, `ent_key`). |
| 4 | ✅ | Menambahkan validasi backend: jika `ent_enabled=true`, maka `ent_username` dan `ent_password` wajib diisi. |
| 5 | ✅ | Memastikan password enterprise tidak disimpan ke `config.json`, hanya ke NVS; export/import API juga tidak membocorkan password. |
| 6 | ✅ | Menambahkan field `wifi_type` pada `/api/fullconfig` agar UI bisa menampilkan mode Open/WPA Personal/WPA Enterprise dengan benar setelah reload. |
| 7 | ✅ | Memperbaiki logout mode WiFi: saat user pilih Open atau Personal, flag `ent_enabled` otomatis `false` dan tidak menempel ke sesi berikutnya. |
| 8 | ✅ | Meningkatkan timeout khusus WPA2 Enterprise menjadi 60 detik, sementara mode Personal/Open tetap 30 detik. |
| 9 | ✅ | Build `esp32dev` dan `esp32s3` berhasil; WiFi modes saling toggle dengan benar. |

**Keputusan Teknis:**
- WPA2 Enterprise menggunakan header native `esp_wpa2.h` karena `WiFi.h` Arduino core tidak mengekspos API 802.1X yang dibutuhkan.
- Password enterprise hanya disimpan di NVS namespace `creds` dengan kunci pendek untuk menghindari `KEY_TOO_LONG`.
- Frontend mengirim `ent_enabled`, `ent_username`, dan `ent_password` hanya saat mode enterprise dipilih; untuk mode lain `ent_enabled=false` dikirim eksplisit.

**Catatan:**
- Setelah perubahan ini, mode WiFi (Open / WPA2 Personal / WPA2 Enterprise) sudah berjalan stabil.
- **Jangan merubah ulang implementasi WiFi di firmware kecuali ada bug kritis atau permintaan fitur baru.**

---

### Frontend XSS Hardening — `firmware/node/data/script.js` & `index.html` (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan helper `escapeHtml(str)` di `script.js` yang mengonversi `& < > " '` ke HTML entity dan mengembalikan string yang aman. |
| 2 | ✅ | Memperbaiki XSS di `loadStatus()` — log MQTT yang dirender ke `innerHTML` kini di-wrap dengan `escapeHtml(log)` agar string berbahaya dari backend tidak dieksekksi. |
| 3 | ✅ | Memperbaiki XSS di `startScanId()` — `item.id` dan `item.baud` dari hasil scan Modbus kini di-escape sebelum di-append ke `innerHTML`. |
| 4 | ✅ | Memperbaiki XSS di `startScanReg()` — `item.reg` dan `item.val` dari hasil batch scan register kini di-escape sebelum di-append ke `innerHTML`. |
| 5 | ✅ | Memperbaiki XSS di `drawInputs()` dan `drawOutputs()` — field `p.name`, `p.i2c_addr` di value attribute dan visible text kini di-escape. |
| 6 | ✅ | Memperbaiki XSS di `drawModbus()` — field `m.name`, `m.ip_address`, `r.name` di value attribute dan visible text kini di-escape. |
| 7 | ✅ | Memperbaiki XSS di `drawI2C()` — field `s.name`, `s.address`, `s.type` di value attribute dan visible text kini di-escape. |
| 8 | ✅ | Memperbaiki deprecated global `event` di `switchView()` — signature diubah ke `switchView(event, id)` dan semua inline `onclick="switchView('...')"` di `index.html` diubah ke `onclick="switchView(event, '...')"`. |
| 9 | ✅ | Mock API bypass (`localhost`/`127.0.0.1`/`file:`), `localStorage` token storage, dan `pwDirty` password-tracking logic dibiarkan tidak diubah sesuai permintaan. |

**Keputusan Teknis:**
- `escapeHtml()` digunakan untuk semua user-controlled/backend-controlled string yang di-inject ke `innerHTML` atau `value="..."` attribute.
- Escape diterapkan sebelum string interpolation untuk mencegah quote-breaking dan attribute escape.
- Inline event handlers tetap dipakai (bukan diganti `addEventListener`) agar konsisten dengan arsitektur firmware yang ada; hanya `switchView` yang diubah untuk menerima `event` eksplisit.

---

### Auto-Deteksi Pin I2C/RS485 Berdasarkan Board (2026-09-23)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan `applyBoardDefaultPins()` di `ConfigManager::init()` yang mendeteksi chip via `ESP.getChipModel()` dan menerapkan default pin sesuai board sebelum `loadConfig()`. |
| 2 | ✅ | ESP32-S3 default: I2C=8/9, RS485 RX=16/TX=15/DE=17; ESP32 default tetap I2C=21/22 dan RS485=16/17/DE=255. |
| 3 | ✅ | Memperbarui validasi I2C di `loadConfig()` agar batas maksimal GPIO menyesuaikan chip (`47` untuk S3, `39` untuk ESP32) dan fallback default ikut board. |
| 4 | ✅ | Build ESP32-S3 berhasil; commit `6842627` untuk update default pin ESP32-S3. |

### Backward Compatibility NVS Keys WPA2-Enterprise (2026-09-23)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan fallback NVS keys legacy `wifi_eap_id` dan `wifi_eap_pw` di `CredentialManager::loadCredentials()` untuk perangkat yang pernah flashed dengan versi sebelumnya. |
| 2 | ✅ | Memperbarui `hasCredentials()` dan `clearCredentials()` agar juga memeriksa/menghapus key legacy. |
| 3 | ✅ | Build ESP32-S3 berhasil; commit dua perubahan: `5821b1a` untuk backward compatibility NVS dan `0dbc6a7` untuk menonaktifkan default OTA di `platformio.ini`. |

### Perbaikan Persistence Konfigurasi Firmware (2026-09-21)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Analisis alur konfigurasi:** firmware `firmware/node` menggunakan `/config.json` di LittleFS; tidak ditemukan file `config.js`. Alur boot memuat file melalui `ConfigManager::init()` sebelum handler sensor/aktuator dibuat oleh `HardwareManager::init()`. |
| 2 | ✅ | **Perbaikan reload field:** parsing boolean dan pin kini memeriksa keberadaan key, sehingga nilai `false` dan GPIO `0` tetap dimuat; `rs485_parity` yang sebelumnya hanya ditulis kini juga dibaca saat boot. |
| 3 | ✅ | **Perbaikan penyimpanan:** `ConfigManager::saveConfig()` memvalidasi JSON, menulis ke file sementara, memeriksa jumlah byte, flush, lalu mengganti `/config.json` agar reboot tidak membaca file kosong/rusak akibat write parsial. |
| 4 | ✅ | **Perbaikan kontrak UI/API:** field interval MQTT di `script.js` disamakan menjadi `telemetry_interval_ms`, sesuai handler backend. |
| 5 | 🟡 | **Verifikasi perangkat:** PlatformIO 6.2.0 sudah tersedia melalui `python -m platformio`; target `upload` mencapai kompilasi/linking awal, sedangkan `uploadfs` masih menyiapkan toolchain ESP32 tambahan. Belum ada konfirmasi flashing serial atau uji Save/Reboot pada ESP32. |

### Perbaikan Default Identity Hotspot ESP32-S3 (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Root cause:** fallback MAC sebelumnya dijalankan setelah WiFi berhasil tersambung, sedangkan captive portal dimulai lebih dahulu sehingga SSID dan MQTT topics menggunakan `node_id` kosong. |
| 2 | ✅ | **Perbaikan:** generate `NODE_ID` dari MAC sebelum portal dan topic initialization; custom `node_id` dari config tetap dipertahankan. |
| 3 | 🟡 | **Verifikasi:** kompilasi target `esp32s3` mencapai `ConfigManager.cpp` dan `NetworkManager.cpp`; upload serta uji hardware masih menunggu koneksi serial board. |

### Perbaikan WPA2-Enterprise Inner Username (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan field `eap_username` terpisah dari outer `eap_identity`; konfigurasi lama tetap memakai identity lama sebagai fallback username. |
| 2 | ✅ | Menyimpan dan memuat inner username melalui NVS, serta memasukkannya ke save/import/export config. |
| 3 | ✅ | Memperbaiki pemanggilan `WiFi.begin()` agar outer identity, inner username, dan password tidak lagi memakai field yang sama. |
| 4 | 🟡 | Pemeriksaan editor tidak menemukan error pada file yang diubah; upload dan uji autentikasi nyata ke jaringan WPA2-Enterprise masih diperlukan. |

### Implementasi E2E Portal dan Persistence WiFi (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Memperbaiki frontend agar response `/api/fullconfig` tanpa object sensitif `security` tidak menghentikan rendering GPIO, Modbus, dan I2C. |
| 2 | ✅ | Menyamakan mock response dengan struktur device (`protocols.wifi`, `protocols.mqtt`) dan menyegarkan portal setelah hardware hot-swap tanpa menunggu reboot palsu. |
| 3 | ✅ | Memuat SSID dan identity WiFi non-sensitif dari LittleFS walaupun NVS berisi credential lain; password tetap dikelola NVS. |
| 4 | ✅ | Menghapus field Enterprise yang stale saat beralih ke Open/WPA Personal dan memperbaiki URL encoding account credentials. |
| 5 | 🟡 | Build ESP32-S3 menghasilkan artefak linker; upload board dan verifikasi WiFi/hardware fisik masih diperlukan. |

### Implementasi Control Priority dan MQTT Serialization (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan `ControlTask` priority 3 dengan bounded actuator command queue; MQTT callback tidak lagi menulis GPIO/relay secara langsung. |
| 2 | ✅ | Memisahkan `outputMutex` dari `handlersMutex` sensor sehingga pembacaan Modbus/I2C tidak menahan jalur actuator sampai 4 detik. |
| 3 | ✅ | Memindahkan ACK actuator dan telemetry ke publish queue; hanya `MqttTask` yang memanggil `PubSubClient`. |
| 4 | ✅ | Emergency stop MQTT disconnect sekarang masuk ke ControlTask dan mencoba mematikan seluruh output dengan batas lock 50 ms. |
| 5 | ✅ | ACK command membedakan `executed`, `output_not_found`, `output_busy`, dan `handler_failed`. |
| 6 | 🟡 | Editor diagnostics bersih dan ESP32-S3 berhasil mengompilasi file control/MQTT; stress test latency dan upload hardware masih diperlukan. |

### Diagnosis WiFi ITB Hotspot Status 4 (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | `WL_CONNECT_FAILED` pada `ITB Hotspot` ditelusuri sebagai kegagalan autentikasi/association, bukan SSID tidak ditemukan. Runtime SSID berasal dari NVS, sehingga dapat berbeda dari template `config.json`. |
| 2 | ✅ | Menambahkan pembersihan password Enterprise stale ketika portal mengirim identity/username kosong untuk mode personal atau open. |
| 3 | ✅ | Menambahkan log mode WiFi yang aman tanpa password: Enterprise, Personal, atau Open; ESP32-S3 compile untuk `NetworkManager.cpp` dan `WebConfigPortal.cpp` bersih. |
| 4 | 🟡 | Flash firmware + filesystem dan uji ulang diperlukan untuk memastikan `ITB Hotspot` memakai mode personal serta password NVS terbaru. |

### Perbaikan MqttTask Stack Canary (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Panic `Stack canary watchpoint triggered (MqttTask)` ditelusuri ke `PublishMessage` dengan payload 8192 byte yang dibuat sebagai local variable pada task stack 6144 byte. |
| 2 | ✅ | Publish queue diubah menjadi bounded queue berisi pointer heap; message dibebaskan setelah diproses oleh `MqttTask`, sehingga payload besar tidak memakai stack task. |
| 3 | 🟡 | `MqttManager.cpp` berhasil dikompilasi dan linking ESP32-S3 menghasilkan `firmware.elf`; perlu upload dan uji koneksi MQTT/telemetry pada board. |

### Perbaikan Export/Import Config Portal (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Import sebelumnya mengirim JSON besar sebagai `application/x-www-form-urlencoded` (`payload=...`), sehingga parsing body rentan gagal pada ukuran/encoding tertentu. |
| 2 | ✅ | Frontend kini mengirim raw `application/json`; backend menerima raw body melalui `plain` dan tetap menyediakan fallback field `payload` untuk bundle lama. |
| 3 | ✅ | Export menampilkan status HTTP/401 dengan jelas, membersihkan object URL download, dan memaksa login ulang jika token kedaluwarsa. |
| 4 | ✅ | Import melakukan persist LittleFS + NVS lalu reboot agar seluruh credential dan konfigurasi benar-benar aktif, bukan mengembalikan `reboot:false` setelah hanya hot-swap sebagian. |
| 5 | 🟡 | Editor diagnostics bersih dan ESP32-S3 mengompilasi handler portal; upload firmware/filesystem serta uji portal nyata masih diperlukan. |

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

---

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

### Implementasi ArduinoOTA untuk Upload Firmware Jarak Jauh (2026-09-22)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | Menambahkan library ArduinoOTA ke `platformio.ini` dan menginisialisasi OTA di `NetworkManager.cpp`. |
| 2 | ✅ | Mengonfigurasi `platformio.ini` dengan `upload_protocol = espota` dan `upload_port` default ke IP device. |
| 3 | ✅ | Build firmware ESP32 berhasil: Flash 91.7%, RAM 26.2%. |

**Keputusan Teknis:**
- ArduinoOTA dijalankan setelah WiFi terhubung (`wifiConnected` berubah true) agar hostname dan OTA siap tanpa blocking loop utama.
- Password OTA default: `enyx-ota` diinisialisasi di `NetworkManager::initArduinoOTA()`.
- Upload jarak jauh via PlatformIO: `python -m platformio run -e esp32dev --upload-port <IP_DEVICE>`.

---

### Migrasi Kredensial ke NVS Namespace `creds` — Firmware Node (2026-09-21)

| # | Status | Aktivitas |
|---|---|---|
| 1 | ✅ | **Membuat `CredentialManager`** — module baru [`src/core/CredentialManager.h`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/CredentialManager.h) & [`src/core/CredentialManager.cpp`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/CredentialManager.cpp) yang membungkus semua operasi NVS namespace `creds` untuk 9 field kredensial: `admin_user`, `admin_pass`, `auth_token`, `wifi_ssid`, `wifi_pass`, `wifi_eap_identity`, `wifi_eap_password`, `mqtt_user`, `mqtt_pass`. |
| 2 | ✅ | **Integrasi `CredentialManager` ke boot flow** — [`ConfigManager::init()`](file:///home/almuzky/TA/Microservices/firmware/node/src/core/ConfigManager.cpp:~9) kini memanggil `CredentialManager::init()` lalu `CredentialManager::loadCredentials()` jika NVS berisi kredensial. Jika NVS kosong, fallback ke `loadConfig()` dari `config.json` lalu otomatis memigrasikan ke NVS. |
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
