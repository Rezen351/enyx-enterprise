# Menambahkan Protokol Baru

Gunakan panduan singkat ini saat menambahkan handler protokol baru (misal I2C, Modbus, 1-Wire, SPI) ke firmware.

## Struktur yang Diperlukan

### 1. Definisi Kelas Handler

Tambahkan deklarasi kelas di [`ProtocolHandlers.h`](firmware/aeroponic-node/src/core/ProtocolHandlers.h). Kelas harus mewarisi [`ProtocolHandler`](firmware/aeroponic-node/src/core/ProtocolHandler.h) dan mengimplementasikan:

- `init(const JsonObject& config)` — parsing konfigurasi dari JSON (nama, pin/alamat, parameter khusus)
- `read(JsonObject& telemetry)` — akuisisi data sensor dan pemetaan ke JSON telemetri
- `getProtocolName()` — mengembalikan nama protokol (misal `"I2C"`)
- `getSensorName()` — mengembalikan nama perangkat dari config
- `write(int value)` — opsional, untuk aktuator

### 2. Implementasi Handler

Tambahkan implementasi di [`ProtocolHandlers.cpp`](firmware/aeroponic-node/src/core/ProtocolHandlers.cpp).

Pola yang harus diikuti:

1. **Inisialisasi bus/protokol** di `init()` jika diperlukan (misal `Wire.begin(sda, scl)` untuk I2C)
2. **Pembacaan sensor** di `read()`:
   - Buat nested object JSON di bawah key protokol (misal `telemetry["i2c"]`)
   - Buat nested object untuk nama perangkat (misal `telemetry["i2c"]["power_monitor"]`)
   - Isi parameter sensor sesuai bacaan hardware
3. **Update local cache** di `HardwareManager::latestSensorValues` agar data tersedia untuk real-time monitoring

Contoh struktur output JSON:

```json
{
  "i2c": {
    "power_monitor": {
      "bus_voltage_v": 5.02,
      "shunt_voltage_mv": 14.26,
      "current_ma": 142.6,
      "power_mw": 716.0
    }
  }
}
```

### 3. Registrasi Protokol

Pastikan handler dapat diinstansiasi melalui factory yang ada di [`ProtocolHandler.cpp`](firmware/aeroponic-node/src/core/ProtocolHandler.cpp). Jika diperlukan, tambahkan pendaftaran eksplisit di `ProtocolRegistry`.

### 4. Konfigurasi JSON

Tambahkan dukungan konfigurasi di [`Config.json`](firmware/aeroponic-node/data/script.js) atau format konfigurasi yang digunakan sistem.

### 5. Dependensi

- Tambahkan library yang diperlukan ke [`platformio.ini`](firmware/aeroponic-node/platformio.ini)
- Sertakan header library di [`ProtocolHandlers.h`](firmware/aeroponic-node/src/core/ProtocolHandlers.h)

## Aturan Penting

- Semua protokol menggunakan interface [`ProtocolHandler`](firmware/aeroponic-node/src/core/ProtocolHandler.h) yang seragam
- Format respons JSON untuk telemetri harus konsisten
- Data sensor disimpan di `HardwareManager::latestSensorValues` untuk akses real-time
- Jangan hardcode kredensial atau nilai sensitif; gunakan konfigurasi JSON
- Setiap handler bertanggung jawab penuh atas inisialisasi dan cleanup bus/protokolnya sendiri
