# 📋 Firmware Aeroponic Node — Fitur Terbaru

**Proyek**: Sistem Smart Farm Aeroponik — Budidaya Bibit Kentang Unggul  
**Target**: `firmware/aeroponic-node/` (ESP32, PlatformIO, Framework Arduino)  
**Versi Firmware**: 1.0.0  
**Tanggal**: 9 Juli 2026  

---

## 🧠 Arsitektur Sistem

Firmware berjalan di **ESP32 dual-core** dengan **6 task FreeRTOS independen**:

```
┌─────────────────────────────────────────────────────┐
│                    ESP32 DUAL CORE                    │
├──────────────────────────┬──────────────────────────┤
│       CORE 0 (Pro)       │      CORE 1 (App)        │
├──────────────────────────┼──────────────────────────┤
│ WiFiTask     (Priority 2)│ TelemetryTask (Priority 1)│
│ MqttTask     (Priority 2)│                           │
│ WatchdogTask (Priority 2)│                           │
│ SysMonitor   (Priority 1)│                           │
└──────────────────────────┴──────────────────────────┘
```

| Task | Fungsi | Core |
|------|--------|------|
| **WiFiTask** | Koneksi WiFi station + Captive Portal AP | Core 0 |
| **MqttTask** | Koneksi MQTT broker, subscribe actuator topic, callback | Core 0 |
| **WatchdogTask** | Monitor semua task, auto-restart jika crash | Core 0 |
| **SysMonitor** | Diagnostik heap, uptime, auto-restart jika memory kritis | Core 0 |
| **TelemetryTask** | Baca sensor GPIO, Modbus RS485, publish MQTT | Core 1 |

---

## 🌐 Captive Web Portal (Hotspot Konfigurasi)

### Cara Akses
1. ESP32 menyiarkan **Access Point** dengan SSID: `SmartFarm-{NODE_ID}`
2. Connect via WiFi ke SSID tersebut (tanpa password)
3. Buka browser → otomatis redirect ke portal konfigurasi
4. Login dengan credential admin

### 20 REST API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `/` | Halaman utama portal |
| POST | `/api/login` | Autentikasi admin (dengan rate limit) |
| GET | `/api/status` | Status sistem real-time |
| GET | `/api/fullconfig` | Konfigurasi lengkap perangkat |
| POST | `/api/wifi` | Ubah setting WiFi |
| POST | `/api/mqtt` | Ubah setting MQTT (server, port, TLS) |
| POST | `/api/device` | Ubah Node ID |
| POST | `/api/hardware` | Konfigurasi pin GPIO & Modbus |
| POST | `/api/modbus/start_scan` | Scan ID Modbus otomatis |
| GET | `/api/modbus/scan_reg` | Scan register Modbus manual |
| POST | `/api/account` | Ubah username & password admin |
| POST | `/api/ota` | Update firmware via upload .bin |
| POST | `/api/publish_discovery` | Kirim sinyal discovery ke MQTT |
| GET | `/api/config/export` | Download file config.json |
| POST | `/api/config/import` | Upload/restore config.json |
| GET | `/api/telemetry/latest` | Data telemetry terkini (REST fallback) |
| GET | `/api/local_control` | Lihat daftar local control rules |
| POST | `/api/local_control` | Set local control rules (histeresis, edge control) |
| GET | `/api/root/health` | Health check endpoint |
| GET | `/style.css`, `/script.js`, dll | Static files dari LittleFS |

### Keamanan Portal
- **Rate limit login**: 5 attempts gagal → block 30 detik
- **Bearer token authentication**: Semua endpoint API wajib token
- **First-time setup**: Generate random password 12 karakter otomatis
- **Session management**: Token baru setiap login

---

## 📡 MQTT Communication

### Topik MQTT (Final, Konsisten)

| Topik | Arah | Fungsi |
|-------|------|--------|
| `smartfarm/{node_id}/telemetry` | Publish | Data sensor & sistem |
| `smartfarm/actuator/{node_id}` | Subscribe | Perintah aktuator |
| `smartfarm/{node_id}/alert` | Publish | Alert darurat |
| `smartfarm/{node_id}/confirm` | Publish | Konfirmasi eksekusi perintah |
| `smartfarm/discovery` | Publish | Discovery node |
| `smartfarm/status/{node_id}` | Publish (retained) | Online/Offline (LWT) |

### Keamanan MQTT
- **TLS/SSL**: Dukungan `WiFiClientSecure` dengan CA certificate
- **Port**: 8883 (MQTTS) / 1883 (plain TCP)
- **Username/Password authentication**
- **Last Will & Testament (LWT)**: Status offline otomatis saat disconnect

### Format Payload Telemetry
```json
{
  "node_id": "node-01",
  "fw_version": "1.0.0",
  "network": {
    "ssid": "Aeroponik 1",
    "ip_address": "192.168.1.104",
    "wifi_rssi": -65
  },
  "device_info": {
    "uptime_s": 3600,
    "cpu_freq_mhz": 240,
    "free_heap_kb": 128,
    "flash_size_mb": 4
  },
  "connection_stats": {
    "mqtt_connected": true,
    "uptime_s": 3600
  },
  "telemetry": {
    "inputs": {
      "suhu_atas": 28.5,
      "kelembaban": 75,
      "wl1": 1,
      "wl2": 0
    },
    "outputs": {
      "pompa_mist": 1,
      "pompa_inlet": 0,
      "cooling_fan": 1
    },
    "modbus": {
      "sensor_npk": {
        "nitrogen": 45.2,
        "phosphorus": 30.1,
        "kalium": 55.0
      }
    }
  }
}
```

### Format Perintah Aktuator
```json
{
  "action": "set_output",
  "target": "pompa_mist",
  "value": 1,
  "req_id": "abc123"
}
```
Response konfirmasi: `smartfarm/{node_id}/confirm`

---

## ⚙️ Hardware Abstraction

### GPIO Input
| Tipe | Dukungan |
|------|----------|
| **Digital** | HIGH/LOW dengan opsi invert |
| **Analog** | 0-4095 (ADC ESP32) |
| **Interrupt** | RISING, FALLING, CHANGE per pin |
| **Pull** | UP, DOWN, NONE |
| **Debounce** | Configurable per pin (ms) |

### GPIO Output
| Tipe | Dukungan |
|------|----------|
| **Digital** | ON/OFF (HIGH/LOW) |
| **PWM** | 0-255 (brightness, motor speed) |

### Modbus RS485
- **Multi-sensor**: NPK, CWT, suhu, pH, EC, dll
- **Auto baudrate switching**: Setiap sensor bisa beda baudrate
- **Mutex-protected**: Aman dari race condition
- **Register scanning**: Input & Holding registers
- **247 slave addresses**: Full range Modbus

### Local Control Rules (Edge Computing)
Aturan otomatis yang berjalan di ESP32 tanpa perlu MQTT:

```json
{
  "name": "overheat_protection",
  "input_sensor": "suhu_atas",
  "output_target": "cooling_fan",
  "threshold_high": 30.0,
  "threshold_low": 25.0,
  "enabled": true
}
```

Logika histeresis:
- **ON** jika suhu > 30.0°C
- **OFF** jika suhu < 25.0°C (beda 5°C mencegah oscillasi)

Contoh lain: dry-run protection (mati otomatis jika level air kosong)

---

## 📶 Multi-Mode WiFi

| Mode | Deskripsi |
|------|-----------|
| **WPA2-Personal** | SSID + Password standar |
| **WPA2-Enterprise (EAP-PEAP)** | Untuk jaringan kampus/kantor (802.1X) |
| **Captive Portal AP** | Always-on access point untuk konfigurasi |
| **Auto-reconnect** | Retry otomatis dengan interval 5 detik |

---

## 🔄 OTA Firmware Update

### Mekanisme
1. Upload file `.bin` via Web Portal (`POST /api/ota`)
2. Firmware ditulis ke partisi OTA
3. **Boot health check**: Setelah restart, ESP32 mencatat boot count
4. Jika boot gagal >3 kali → **auto rollback** ke versi sebelumnya
5. Version tracking via field `fw_version` di config.json

### Keamanan OTA
- Wajib autentikasi token
- Dual partition support (OTA_0 + OTA_1)
- Boot counter di Preferences NVS

---

## 🛡️ Task Watchdog

Monitor semua task secara real-time:

| Task | Timeout | Aksi Jika Timeout |
|------|---------|-------------------|
| WiFiTask | 30 detik | Restart task |
| MqttTask | 30 detik | Restart task |
| TelemetryTask | 30 detik | Restart task |
| SysMonitor | 60 detik | Restart ESP32 |

Setiap task mengirim **heartbeat** periodik. Jika heartbeat berhenti, watchdog akan:
1. Log error ke serial
2. Delete task yang crash
3. Buat task baru (restart)
4. Jika tidak ada restart function → reset ESP32

---

## 🚨 Emergency Shutdown

### Interrupt-Based
- Pin emergency stop (configurable) menggunakan **hardware interrupt**
- Respons dalam **mikrodetik** (bukan polling 5 detik)
- Saat triggered:
  1. Semua output langsung dimatikan (PWM → 0, Digital → LOW)
  2. Alert dikirim via MQTT ke topic `smartfarm/{node_id}/alert`
  3. Status dicatat di telemetry berikutnya

### Proteksi Tambahan
- **Invert logic**: Support sensor Normally Open (NO) / Normally Closed (NC)
- **Debounce**: 200ms hardware debounce untuk mencegah false trigger

---

## 💾 Manajemen Memori

### Heap Optimization
- **StaticJsonDocument**: Alokasi statis 4KB, zero heap fragmentation
- **Circular buffer log**: Fixed char array `[10][80]` = 800 bytes total
- **Pre-allocated buffer**: `char jsonBuffer[4096]` untuk serialisasi
- **No DynamicJsonDocument**: Tidak ada alokasi/dealokasi berulang

### LittleFS
- Persistent storage untuk config.json
- SPIFFS replacement (lebih reliable)
- Auto-mount dengan format jika corrupt

---

## 🔐 Keamanan Sistem

| Aspek | Implementasi |
|-------|-------------|
| **MQTT** | TLS/SSL dengan CA certificate |
| **Web Portal** | Bearer token authentication |
| **Login** | Rate limit (5 attempts, 30s block) |
| **Credential** | Random password 12 char di first boot |
| **OTA** | Wajib token, boot health check, auto rollback |
| **Config** | Export/Import dengan validasi JSON |

---

## 📊 Spesifikasi Teknis

### Hardware
| Parameter | Value |
|-----------|-------|
| **Board** | ESP32 Dev Module (Dual Core @240MHz) |
| **Framework** | Arduino (ESP32 Arduino Core) |
| **RTOS** | FreeRTOS (built-in) |
| **Filesystem** | LittleFS |
| **Partition** | default_ffat.csv (dual OTA slot) |

### Dependencies
| Library | Versi | Fungsi |
|---------|-------|--------|
| PubSubClient | ^2.8 | MQTT client |
| ArduinoJson | ^6.21.3 | JSON serialization |
| DHT sensor library | ^1.4.4 | DHT11/22 sensor |
| Adafruit Unified Sensor | ^1.1.9 | Sensor abstraction |
| ModbusMaster | ^2.0.1 | Modbus RTU RS485 |

### Memory
| Komponen | Ukuran |
|----------|--------|
| Flash (firmware) | ~1.2 MB |
| Heap (runtime) | ~40-80 KB free |
| Stack per task | 4-8 KB |
| JSON buffer | 4 KB (static) |
| Log buffer | 800 bytes (fixed) |

---

## 🚀 Cara Penggunaan

### 1. First Boot
```bash
# ESP32 akan membuat hotspot:
SSID: SmartFarm-node-01
# Connect via WiFi, buka browser, akses portal
# Login dengan password yang tercetak di Serial Monitor
```

### 2. Konfigurasi WiFi
```bash
# Via Web Portal:
POST /api/wifi
Body: ssid=MyNetwork&pass=MyPassword
```

### 3. Konfigurasi MQTT
```bash
POST /api/mqtt
Body: server=192.168.1.100&port=1883&topic_prefix=smartfarm
```

### 4. Monitoring
```bash
# Data telemetry otomatis terkirim setiap 5 detik ke:
smartfarm/node-01/telemetry

# Cek status via REST:
GET /api/status
```

---

*Firmware Aeroponic Node v1.0.0 — Smart Farm IoT Gateway*