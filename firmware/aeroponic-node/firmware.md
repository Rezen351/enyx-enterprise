# Firmware Specification — Aeroponic Node

**Board:** ESP32  
**Framework:** Arduino / PlatformIO  
**Filesystem:** LittleFS (`config.json`)  
**Primary Transport:** MQTT over TCP/TLS  

---

## 1. Purpose

Aeroponic Node adalah firmware untuk node sensor dan aktuator di lingkungan hydroponik/aeroponik. Setiap node bertugas:

- Membaca sensor lokal sesuai konfigurasi
- Mempublikasikan data telemetry ke MQTT broker
- Menerima dan mengeksekusi perintah aktuator dari MQTT broker
- Menyediakan web UI untuk konfigurasi, monitoring, dan OTA

---

## 2. Boot Sequence

1. Inisialisasi sistem (watchdog, logging)
2. Mount LittleFS
3. Load `config.json`
4. Jika `admin_pass` kosong → generate password acak 12-digit hex dan tampilkan di serial
5. Inisialisasi WiFi, MQTT, Hardware Manager
6. Start telemetry task dan MQTT task
7. Jalankan Captive Portal AP untuk konfigurasi awal

---

## 3. Connectivity

### WiFi

- Mode: Station + SoftAP (Captive Portal)
- SSID dan password disimpan di `config.json`
- Mendukung WPA2-Enterprise (`eap_identity`, `eap_password`)
- Auto reconnect

### MQTT

- Broker, port, prefix, username, password, interval, dan TLS dikonfigurasi via web UI
- Topik default: `smartfarm/<node_id>/...`
- LWT (Last Will Testament) untuk status online/offline
- Discovery signal bisa dipicu manual dari UI

---

## 4. MQTT Topics

Semua topik mengikuti format: `<prefix>/<node_id>/<kategori>`

| Kategori | Topic | Arah | Deskripsi |
|----------|-------|------|-----------|
| Telemetry | `<prefix>/<node_id>/telemetry` | Node → Broker | Data sensor + status aktuator + info device |
| Actuator | `<prefix>/actuator/<node_id>` | Broker → Node | Perintah kontrol aktuator |
| Status | `<prefix>/status/<node_id>` | Node → Broker | LWT online/offline |

### Actuator Command Format

```json
{
  "action": "set_output",
  "target": "<nama_aktuator>",
  "value": 1
}
```

- `value` untuk digital: `0` = OFF, `1` = ON
- `value` untuk PWM: `0` - `255`

### Telemetry Payload Structure

```json
{
  "node_id": "8C94DF6BCDFC",
  "fw_version": "1.0.0",
  "network": {
    "ssid": "PAU Hotspot",
    "ip_address": "10.18.128.31",
    "wifi_rssi": -62
  },
  "device_info": {
    "uptime_s": 60,
    "cpu_freq_mhz": 240,
    "free_heap_kb": 164,
    "flash_size_mb": 4
  },
  "connection_stats": {
    "mqtt_connected": true,
    "mqtt_broker": "192.168.1.103"
  },
  "telemetry": {
    "outputs": {
      "pump": 1
    },
    "sensor_data": { ... }
  }
}
```

---

## 5. Sensors

### Supported Protocols

| Protocol | Jenis Sensor | Keterangan |
|----------|--------------|-----------|
| GPIO (Digital/Analog) | Sensor digital, analog, sensor tanah, level air | Pull-up/down, invert logic, debounce |
| I2C | BME280 (temp/hum/pressure), INA219 (voltage/current/power), DHT12 (temp/hum) | Alamat I2C konfigurasi per sensor |
| Modbus RTU (RS485) | Holding/Input registers, berbagai tipe data | Multi-baud, slave ID 1-247, multiplier scaling |
| Generic Sensor | Protocol handler berbasis konfigurasi | Didefinisikan via `params` map |

### Konfigurasi Sensor

Semua sensor didefinisikan di `config.json` bagian `hardware`:

```json
{
  "hardware": {
    "inputs": [
      {
        "pin": 4,
        "type": "DIGITAL",
        "pull": "UP",
        "name": "Water Sensor",
        "invert": false,
        "debounce_ms": 0,
        "interrupt": "NONE",
        "analog_min": 0,
        "analog_max": 4095
      }
    ],
    "outputs": [
      {
        "pin": 5,
        "type": "DIGITAL",
        "name": "Pump Relay",
        "protocol": "GPIO_OUT"
      }
    ],
    "modbus": [
      {
        "name": "Soil Sensor",
        "slave_id": 1,
        "baudrate": 9600,
        "registers": [
          {
            "address": 0,
            "name": "Moisture",
            "multiplier": 0.1,
            "type": "HOLDING",
            "length": 1,
            "data_type": "UINT16"
          }
        ]
      }
    ],
    "sensors": [
      {
        "name": "BME280 Main",
        "protocol": "I2C",
        "address": "0x76",
        "sda_pin": 21,
        "scl_pin": 22
      }
    ]
  }
}
```

#### Modbus Register Fields

| Field | Type | Deskripsi |
|-------|------|-----------|
| `address` | uint16 | Register address (0 = register 40001) |
| `name` | string | Nama register |
| `multiplier` | float | Scaling factor diterapkan setelah decoding |
| `type` | string | `"HOLDING"` atau `"INPUT"` |
| `length` | uint8 | Jumlah register (1-4). Untuk FLOAT32/INT32/UINT32 gunakan `2` |
| `data_type` | string | `"UINT16"`, `"INT16"`, `"FLOAT32"`, `"INT32"`, `"UINT32"` |

#### Float32 / Multi-register (Big-Endian)

Nilai 32-bit (FLOAT32, INT32, UINT32) dipecah ke dua register dengan urutan **big-endian (Motorola)**:

- Register pertama (alamat N) = **High Word**
- Register kedua (alamat N+1) = **Low Word

Contoh: High Word `0x47C3` + Low Word `0x5000` digabung menjadi `0x47C35000` = float32 **100000.0**.

```json
{
  "address": 0,
  "name": "FlowRate",
  "multiplier": 1.0,
  "type": "HOLDING",
  "length": 2,
  "data_type": "FLOAT32"
}
```

---

## 6. Actuator Control

### Jenis Aktuator

- **Digital Output**: ON/OFF
- **PWM Output**: 0-255 (AnalogWrite)

### Cara Kontrol

Kontrol aktuator **hanya melalui MQTT** topic `<prefix>/actuator/<node_id>`.

Tidak ada endpoint HTTP untuk kontrol aktuator di web UI.

---

## 7. Emergency Stop

Emergency stop aktif ketika koneksi MQTT ke broker terputus.

- **Default**: Aktif
- **Kontrol**: Bisa diaktifkan/nonaktifkan via checkbox di halaman MQTT Settings di web UI
- **Aksi**: Semua aktuator dimatikan (`setOutput(name, 0)`)

---

## 8. Web UI

Web UI diakses melalui Captive Portal atau IP lokal. Semua teks antarmuka dalam Bahasa Inggris.

### Halaman

| Halaman | Fungsi |
|---------|--------|
| STATUS | Dashboard: status WiFi, MQTT, IP, RSSI, uptime, heap, live MQTT logs, informasi topic, discovery signal |
| DEVICE | Node ID, backup/restore config |
| WIFI | SSID, password, WPA2-Enterprise |
| MQTT | Broker, port, prefix, auth, interval, TLS, emergency stop toggle |
| GPIO | Konfigurasi input/output pin |
| RS485 | Konfigurasi Modbus, scanner tool |
| I2C | Konfigurasi sensor I2C |
| FIRMWARE | OTA update |
| ACCOUNT | Ubah admin credentials |

---

## 9. Security

- **Admin Auth**: Token-based Bearer authentication
- **Credential Storage**: Plaintext di `config.json`
- **Config Export**: Menyertakan credential
- **Config Import**: Validasi dan import via web UI
- **MQTT Auth**: Optional username/password
- **TLS**: Optional (`use_tls` flag, field sertifikat tersedia di config)

---

## 10. Configuration File

File: `config.json` di LittleFS

```json
{
  "device": {
    "node_id": "8C94DF6BCDFC",
    "fw_version": "1.0.0"
  },
  "security": {
    "admin_user": "admin",
    "admin_pass": "password_anda"
  },
  "protocols": {
    "wifi": {
      "ssid": "Aeroponik 1",
      "password": "wifi_password",
      "eap_identity": "",
      "eap_password": ""
    },
    "mqtt": {
      "server": "192.168.1.103",
      "port": 1883,
      "topic_prefix": "smartfarm",
      "user": "",
      "pass": "",
      "use_tls": false,
      "telemetry_interval_ms": 5000,
      "mqtt_disconnect_emergency_stop": true
    }
  },
  "hardware": {
    "inputs": [],
    "outputs": [],
    "modbus": [],
    "sensors": []
  }
}
```

---

## 11. API Endpoints

| Method | Path | Auth | Deskripsi |
|--------|------|------|-----------|
| POST | `/api/login` | No | Login, return token |
| GET | `/api/status` | Yes | Status sistem + live MQTT logs |
| GET | `/api/fullconfig` | Yes | Full config tanpa credential sensitif |
| POST | `/api/account` | Yes | Ubah admin username/password |
| POST | `/api/wifi` | Yes | Simpan konfigurasi WiFi |
| POST | `/api/mqtt` | Yes | Simpan konfigurasi MQTT |
| POST | `/api/device` | Yes | Simpan konfigurasi device |
| POST | `/api/hardware` | Yes | Simpan konfigurasi hardware (hot-swap) |
| GET | `/api/telemetry/latest` | Yes | Telemetry JSON terbaru |
| GET | `/api/config/export` | Yes | Download `config.json` |
| POST | `/api/config/import` | Yes | Upload & restore `config.json` |
| POST | `/api/modbus/start_scan` | Yes | Scan Modbus IDs |
| POST | `/api/modbus/cancel_scan` | Yes | Cancel scan |
| POST | `/api/modbus/scan_reg` | Yes | Scan register tunggal |
| POST | `/api/modbus/scan_reg_batch` | Yes | Batch scan register |
| POST | `/api/publish_discovery` | Yes | Publish discovery signal |
| POST | `/api/ota` | Yes | OTA firmware update |

---

## 12. Hardware Pins Default

| Pin | Fungsi | Default |
|-----|--------|---------|
| GPIO 2 | LED Indicator | Built-in LED |
| GPIO 4 | DHT Sensor | DHT12 |
| GPIO 16 | RS485 RX | — |
| GPIO 17 | RS485 TX | — |
| GPIO 21 | I2C SDA | BME280, INA219 |
| GPIO 22 | I2C SCL | BME280, INA219 |

---

## 13. Build & Flash

```bash
# Build
pio run -d firmware/aeroponic-node

# Upload firmware
pio run -d firmware/aeroponic-node --target upload

# Upload filesystem (LittleFS)
pio run -d firmware/aeroponic-node --target uploadfs
```

---

## 14. Notes

- Web UI menggunakan Bahasa Inggris
- API responses menggunakan Bahasa Inggris
- Dokumentasi proyek menggunakan Bahasa Indonesia
- Protocol OneWire dan SPI tidak didukung
- Kontrol aktuator hanya melalui MQTT, tidak melalui web UI
