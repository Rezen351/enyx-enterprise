# ENYX Enterprise — Aeroponic Node Firmware

> **Platform:** ESP32 / ESP32-S3  
> **RTOS:** FreeRTOS  
> **Framework:** Arduino via PlatformIO  
> **Version:** 0.1.0-prototype  
> **SGAM Layer:** Component Layer (T-1)

---

## Overview

Firmware untuk node sensor dan aktuator aeroponik yang mengimplementarkan pendekatan **configuration-driven + factory pattern**. Penambahan sensor atau aktuator baru cukup dilakukan melalui `config.json` tanpa mengubah kode inti program.

---

## Features

- **Modular I/O:** Sensor dan aktuator didaftarkan via `config.json` (GPIO, I2C, Modbus RTU/TCP, PCF8575)
- **FreeRTOS Dual-Core:** Network/System di Core 0, Application di Core 1
- **MQTT Telemetry:** Publish data sensor dan current output status
- **Actuator Control:** Subscribe perintah aktuator via MQTT dengan ACK/NACK
- **Auto-Discovery:** Kirim discovery payload setiap 60 detik dan saat koneksi broker
- **Captive Portal:** AP mode + HTTP server untuk konfigurasi WiFi, MQTT, dan hardware
- **OTA Update:** Upload firmware via WiFi
- **WebSerial Configurator:** Flash firmware dan serial monitor via browser
- **NVS Storage:** Kredensial sensitif disimpan di NVS (tidak diekspor via config)
- **Emergency Stop:** Matikan semua aktuator saat MQTT disconnect

---

## Quick Start

### Prerequisites

- [PlatformIO Core](https://docs.platformio.org/en/latest/core.html) (CLI)
- Python 3.8+
- Serial adapter untuk ESP32 (USB)

### Build

```bash
# Build untuk ESP32 classic
pio run -e esp32dev

# Build untuk ESP32-S3
pio run -e esp32s3
```

### Upload

```bash
# Upload firmware + LittleFS
pio run -e esp32dev --target upload --target uploadfs

# Upload OTA (jika ESP32 sudah terhubung ke WiFi)
pio run -e esp32s3 --target upload
```

### Monitor Serial

```bash
pio device monitor -e esp32dev -b 115200
```

---

## Hardware Configuration

Semua konfigurasi hardware didefinisikan di `data/config.json`:

```json
{
  "hardware": {
    "inputs": [
      { "pin": 34, "type": "ANALOG", "name": "soil_moisture" },
      { "pin": 13, "type": "DIGITAL", "pull": "UP", "name": "float_switch" }
    ],
    "outputs": [
      { "pin": 26, "type": "DIGITAL", "name": "misting_pump" },
      { "pin": 27, "type": "PWM", "name": "cooling_fan" }
    ],
    "modbus": [
      {
        "name": "ec_ph_sensor",
        "slave_id": 1,
        "baudrate": 9600,
        "registers": [
          { "address": 0, "name": "ec_value", "multiplier": 0.01, "type": "HOLDING" }
        ]
      }
    ],
    "sensors": [
      { "name": "bme280_atas", "protocol": "I2C", "type": "BME280", "address": "0x76" }
    ]
  }
}
```

---

## Captive Portal

Untuk konfigurasi awal tanpa coding:

1. Power on ESP32 — akan membuat AP `ENYX-ENTERPRISE-<node_id>`
2. Hubungkan ke AP — seluruh DNS diarahkan ke `192.133.22.6`
3. Buka browser ke `http://192.133.22.6`
4. Login dengan akun admin
5. Konfigurasi WiFi, MQTT, dan hardware via web UI

---

## MQTT Topics

| Topic | Arah | Deskripsi |
|-------|------|-----------|
| `<prefix>/<node_id>/telemetry` | Node → Broker | Data sensor dan output status |
| `<prefix>/actuator/<node_id>` | Broker → Node | Perintah kontrol aktuator |
| `<prefix>/<node_id>/confirm` | Node → Broker | ACK/NACK perintah aktuator |
| `<prefix>/discovery` | Node → Broker | Auto-discovery signal |
| `<prefix>/status/<node_id>` | Node → Broker | LWT online/offline |

Default `prefix`: `smartgrid`

---

## Folder Structure

```
firmware/node/
├── data/
│   ├── config.json          # Konfigurasi hardware
│   └── index.html           # Captive Portal UI
├── src/
│   ├── core/
│   │   ├── HardwareManager.cpp
│   │   ├── ProtocolHandler.cpp
│   │   ├── ProtocolHandlers.cpp
│   │   └── SystemMonitor.cpp
│   └── protocols/
│       ├── MqttManager.cpp
│       └── NetworkManager.cpp
├── platformio.ini           # Build configuration
└── README.md
```

---

## Dependencies

| Library | Version | Deskripsi |
|---------|---------|-----------|
| PubSubClient | ^2.8 | MQTT client |
| ArduinoJson | ^6.21.3 | JSON serialization |
| Adafruit DHT | ^1.4.4 | Sensor suhu/kelembaban |
| Adafruit INA219 | ^1.2.1 | Power monitor |
| ModbusMaster | ^2.0.1 | Modbus RTU/TCP |

---

## Notes

- Prototype v0.1.0 — API dan schema dapat berubah
- Flash address untuk aplikasi: `0x10000`
- Kredensial disimpan di NVS dan tidak diekspor via config
