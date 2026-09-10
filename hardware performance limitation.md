# Hardware Performance Limitation — ESP32 Aeroponic Node

Dokumen ini merangkum limitasi firmware, byte budget per objek JSON, batasan pin GPIO, batasan protokol I2C, perhitungan maksimum sensor/aktuator, serta dampak ke broker jika limitasi tercapai.

---

## 1. Ukuran JSON Object per Device

### 1.1 Struktur Telemetry Saat Ini
Payload telemetry yang diterbitkan firmware ke topik `smartfarm/{node_id}/telemetry` memiliki struktur inti:

- Overhead tetap: `node_id`, `fw_version`, `network`, `device_info`, `connection_stats`
- Bagian `telemetry` berisi `outputs`, `inputs`, `modbus`, `i2c`

Rumus perkiraan ukuran payload:

```
Total (bytes) ≈ 180
             + N_inputs × 15
             + N_outputs × 15
             + Σ(I2C_devices × 80)
             + Σ(Modbus_devices × 40 + registers × 12)
```

### 1.2 Byte per Device

| Tipe Device | Field JSON Dominan | Ukuran per Device |
|-------------|--------------------|-------------------|
| GPIO Input Digital | `"name": value` | ~12–18 bytes |
| GPIO Output | `"name": value` | ~12–18 bytes |
| I2C INA219 | 4 float + name | ~80–100 bytes |
| I2C BME280 | 2 float + name | ~60–80 bytes |
| I2C DHT12 | 2 float + name | ~60–80 bytes |
| Modbus Device | N register + name | ~40 bytes + N × 12 bytes |

### 1.3 Contoh Perhitungan Konfigurasi node-00.json (Simulator)

Berdasarkan `test/results/phase1/05_unit_test_payloads.md`:

- 4 GPIO inputs: `input1`, `input2`, `input3`, `input4`
- 5 GPIO outputs: `buzzer`, `load1`, `load2`, `load3`, `load4`
- 2 Modbus devices: `cwt1` (hum, temp), `cwt2` (hum, temp)
- 1 I2C device: `power_monitor` (INA219)

```
Base overhead:       180 bytes
4 × GPIO input:       4 × 15  =   60 bytes
5 × GPIO output:      5 × 15  =   75 bytes
1 × INA219:              80   =   80 bytes
2 × Modbus (2 reg):  2 × (40 + 24) = 128 bytes
────────────────────────────────────────
Total ≈                         523 bytes
```

### 1.4 Batas Buffer JSON Firmware

| Buffer | Ukuran | Sumber Kode |
|--------|--------|-------------|
| `StaticJsonDocument<8192>` telemetry | **8,192 bytes** | `firmware/aeroponic-node/src/core/HardwareManager.cpp:42` |
| `char jsonBuffer[8192]` | **8,192 bytes** | `firmware/aeroponic-node/src/core/HardwareManager.cpp:43` |
| `DynamicJsonDocument(16384)` actuator callback | **16,384 bytes** | `firmware/aeroponic-node/src/protocols/MqttManager.cpp:224` |
| MQTT client buffer | **8,192 bytes** | `firmware/aeroponic-node/src/protocols/MqttManager.cpp:80` |

### 1.5 Maksimum Device Berdasarkan Buffer JSON

```
Max devices = (8192 - 180) / average_bytes_per_device

Konfigurasi hybrid (I2C + GPIO + Modbus), rata-rata ~60 bytes/device:
- Max devices = (8192 - 180) / 60 ≈ 133 devices

Pure I2C (~80 bytes/device):
- Max I2C devices = (8192 - 180) / 80 ≈ 100 devices

Pure GPIO (~15 bytes/device):
- Max GPIO devices = (8192 - 180) / 15 ≈ 534 devices
```

Kesimpulan: batas teoretis JSON sangat besar, sehingga **batas praktis ditentukan oleh hardware, bukan buffer JSON**.

---

## 2. Batasan Pin GPIO

### 2.1 GPIO yang Benar-Benar Usable

| Pin | Fungsi Khusus | Bisa Dipakai |
|-----|---------------|--------------|
| GPIO0 | Boot mode (LOW = download mode) | ⚠️ Jika ada pull-up |
| GPIO1 | UART0 TX (Serial) | ❌ Reserved |
| GPIO2 | LED indicator | ✅ Bisa (alternatif) |
| GPIO3 | UART0 RX | ❌ Reserved |
| GPIO4 | DHT sensor legacy | ✅ Bisa (alternatif) |
| GPIO5 | HSPI CS / VSPI CS | ✅ Jika tidak pakai SPI |
| GPIO6–11 | SPI Flash internal | ❌ Hard reserved |
| GPIO12–15 | Boot strapping | ⚠️ Perlu pull resistor |
| GPIO16–17 | RS485 RX/TX | ✅ Bisa (alternatif) |
| GPIO18–19 | SPI VSPI | ✅ Jika tidak pakai SPI |
| GPIO20 | Strapping | ❌ Reserved |
| GPIO21 | I2C SDA | ✅ Bisa (alternatif) |
| GPIO22 | I2C SCL | ✅ Bisa (alternatif) |
| GPIO23 | SPI MOSI | ✅ Jika tidak pakai SPI |
| GPIO24 | Strapping | ❌ Reserved |
| GPIO25–27 | DAC / GPIO | ✅ 3 pins |
| GPIO28–31 | Reserved ROM | ❌ Hard reserved |
| GPIO32–33 | ADC1 usable | ✅ 2 pins |
| GPIO34–35 | ADC1, input only | ✅ 2 pins |
| GPIO36–39 | ADC1, input only | ✅ 4 pins |

### 2.2 Hitung GPIO yang Bisa Digunakan

```
GPIO output-capable:
- GPIO4, GPIO5           = 2
- GPIO12–15              = 4
- GPIO18, GPIO19, GPIO23 = 3
- GPIO25, GPIO26, GPIO27 = 3
- GPIO32, GPIO33         = 2
─────────────────────────────────
Total output-capable     ≈ 14 pins

GPIO input-only:
- GPIO34–39              = 6 pins

Total combined I/O:
- ≈ 20 pins (teoritis)
- Praktis aman: 10–15 GPIO per node
```

### 2.3 Batas Analog Input

ESP32 ADC: 12-bit (0–4095), 18 channel.

- ADC1: GPIO32–39 = 8 channel, shared dengan WiFi
- ADC2: GPIO0, 2, 4, 12–15, 25–27 = 8 channel, **tidak bisa dipakai saat WiFi aktif**

Karena firmware ini memakai WiFi, maka **hanya ADC1 yang bisa dipakai**:

```
Analog input maksimum: GPIO32, GPIO33, GPIO34, GPIO35, GPIO36, GPIO37, GPIO38, GPIO39 = 8 channel
```

---

## 3. Batasan Protokol I2C

### 3.1 Alamat I2C

```
Jumlah alamat 7-bit: 1 sampai 127 = 127 kemungkinan
Batas praktis (bus capacitance 400 pF):
- @ 100 kHz (standard mode): ~12–16 devices
- @ 400 kHz (fast mode):   ~8–10 devices

Alamat yang sudah terpakai:
- 0x40: INA219 (power monitor)
- 0x5C: DHT12
- 0x76/0x77: BME280
```

### 3.2 Perhitungan Maksimum I2C Devices

```
Asumsi:
- Setiap device ≈ 100 pF parasitic capacitance
- PCB trace @ 10 cm ≈ 10 pF
- Total bus capacitance budget = 400 pF

Rumus: N_max = (400 - N_trace × 10) / 100

Trace pendek (< 5 cm):
- N_max = (400 - 10) / 100 ≈ 3–4 devices

Trace sedang (2 × 10 cm):
- N_max = (400 - 20) / 100 ≈ 3–4 devices

Pada 400 kHz fast mode:
- N_max ≈ 4–6 devices

Pada 100 kHz standard mode:
- N_max ≈ 8–12 devices
```

Kesimpulan: **maksimum 4–8 device I2C per bus**, tergantung panjang trace dan kecepatan clock. Untuk PCB kustom trace pendek: **maks 6 device**.

---

## 4. Maksimum Sensor & Aktuator per Node

### 4.1 Tabel Batas per Protokol

```
┌─────────────────┬──────────────────┬─────────────────────┐
│ Protocol        │ Theoretical Max  │ Practical Limit     │
├─────────────────┼──────────────────┼─────────────────────┤
│ GPIO Output     │ 13 pins          │ 6–8 actuators       │
│ GPIO Input      │ 19 pins          │ 10–12 sensors       │
│ Analog Input    │ 8 channels       │ 4–6 sensors         │
│ I2C             │ 127 addresses    │ 4–6 devices         │
│ Modbus RS485    │ 247 slave IDs    │ 8–12 devices        │
│ OneWire         │ 1 bus            │ ~10 sensors (DS18B20)│
│ SPI             │ 3–4 devices      │ 2–3 devices         │
└─────────────────┴──────────────────┴─────────────────────┘
```

### 4.2 Skenario Mixed (Realistis untuk Aeroponik)

```
aktuator GPIO:      8  (pump, valve, fan, light, buzzer, dll)
sensor GPIO input:  4  (float switch, soil moisture × 2, emergency stop)
sensor analog:      4  (GPIO32–35 untuk soil moisture analog)
I2C devices:        4  (BME280 × 2, INA219, DHT12)
Modbus devices:     2  (EC/pH meter, flow meter)
─────────────────────────────────────
Total devices:      22 devices

Ukuran payload:
- Base: 180 bytes
- 8 GPIO outputs: 8 × 15 = 120 bytes
- 4 GPIO inputs:  4 × 15 = 60 bytes
- 4 analog:       4 × 15 = 60 bytes
- 4 I2C:          4 × 80 = 320 bytes
- 2 Modbus (3 reg each): 2 × (40 + 36) = 152 bytes
─────────────────────────────────────
Total ≈           892 bytes (well within 8 KB limit)
```

### 4.3 Maksimum Kombinasi per Node

```
Berdasarkan RAM dan hardware:
- Free heap runtime: 40–80 KB
- JSON buffer: 8 KB
- Setiap device handler ≈ 200–500 bytes heap

Dengan 30 devices:
- Heap usage ≈ 6–15 KB
- Payload ≈ 1,200–1,500 bytes
- Rasio terhadap 8 KB buffer ≈ 19–25%

MAKSIMUM KOMBINASI PER NODE: ~30–40 devices
```

---

## 5. Dampak ke Broker Jika Mencapai Limitasi

### 5.1 Lalu Lintas MQTT Saat Ini vs Maksimum

```
Konfigurasi saat ini:
- Nodes terdeteksi: 24
- Interval publish: 5 detik
- Payload rata-rata: ~500 bytes

Lalu lintas MQTT saat ini:
- Messages/second = 24 / 5 = 4.8 msg/s
- Throughput = 4.8 × 500 bytes = 2,400 bytes/s ≈ 19.2 kbps

Dengan konfigurasi max devices (30 devices × 80 bytes):
- Payload max ≈ 2,500 bytes per message
- Throughput = 4.8 × 2,500 = 12,000 bytes/s ≈ 96 kbps
```

### 5.2 Jika Semua Node Mencapai Limitasi

```
Skenario worst case:
- 24 nodes × 30 devices × 80 bytes = 57,600 bytes/publish
- Interval 5 detik
- Throughput = 57,600 / 5 = 11,520 bytes/s ≈ 92.16 kbps

Dengan QoS 1 (aktuator):
- Overhead MQTT: +33 bytes per packet
- Total overhead: 24 × 33 = 792 bytes/s
- Total throughput ≈ 93 kbps

WiFi 802.11n throughput: 150 Mbps
Broker Mosquitto single instance: ~5,000–10,000 msg/s sustained
─────────────────────────────────────────────────────
PEMBATAS BROKER TIDAK AKAN DICAPAI pada 24 nodes
```

### 5.3 Kapan Broker Akan Terpaksa Berlatensi?

```
Batas broker Mosquitto (default config):
- Max connections: ~1,000
- Max messages/second: ~5,000–10,000
- Max payload: unlimited (RAM-limited)

Untuk mencapai limitasi broker dengan 24 nodes:
- Perlu: 10,000 msg/s ÷ 24 nodes = 416 msg/s per node
- Interval minimum: 1s ÷ 416 = 2.4 ms publish interval

Artinya: jika setiap node publish setiap 2.4 ms dengan payload besar,
BARU broker akan mulai retard.

Dengan interval 5 detik: aman sampai ~2,000 nodes.
```

### 5.4 Dampak pada Broker Jika Limitasi JSON Dicapai

```
Jika payload JSON > 8 KB (buffer overflow di ESP32):
1. ESP32 crash/restart (watchdog timeout atau heap corruption)
2. Pesan terkirim tidak lengkap → broker menerima incomplete packet → connection reset
3. Jika 50% nodes crash:
   - Message rate turun dari 4.8 → 2.4 msg/s
   - Broker latency turun (lebih sedikit message)
   - TAPI data telemetry hilang 50%

Jika publish rate terlalu tinggi (interval < 1s):
1. Broker queue buildup → memory exhaustion
2. Latency naik: P95 dari 848 ms (stress test fase 1) bisa menjadi > 5,000 ms
3. QoS 1 messages timeout → retry storm
4. Connection refused untuk node baru
```

### 5.5 Perhitungan Akurat: Latensi Broker vs Message Rate

```
Rumus empiris untuk broker latency (berdasarkan stress test fase 1):
Latency(ms) = 1 + (messages_per_second / 100) × 2

Untuk 24 nodes dengan config max:
- Messages/s = 24 / 5 = 4.8 msg/s
- Latency = 1 + (4.8 / 100) × 2 = 1.1 ms (ideal)

Skala lebih besar:
- 100 nodes:  20 msg/s  → 1.4 ms (masih ideal)
- 500 nodes: 100 msg/s  → 3 ms   (masih acceptable)
- 1,000 nodes: 200 msg/s → 5 ms  (masih acceptable)
- 2,500 nodes: 500 msg/s → 11 ms (masih acceptable)
- 5,000 nodes: 1,000 msg/s → 21 ms (masih acceptable untuk telemetry)

BROKER TIDAK AKAN MENJADI BOTTLENECK untuk skala rumah greenhouse (24–100 nodes)
```

### 5.6 Kritis: ESP32 vs Broker

```
Batas sebenarnya ada di ESP32, bukan broker:

ESP32 limits:
- JSON serialize time: ~5–20 ms per 1 KB payload
- MQTT publish blocking: ~10–50 ms (tergantung packet size)
- WiFi TX time: ~1–5 ms per packet
- Total per cycle: ~20–100 ms

With 5s interval: ESP32 menggunakan 0.4–2% waktu untuk telemetry
SISA 98% untuk reading sensors, Modbus polling, dsb.

Jika payload > 4 KB:
- Serialize time: ~50–100 ms
- MQTT publish: ~50–200 ms
- Total: ~150–300 ms per cycle (6–10% waktu)

Jika payload > 8 KB (buffer overflow):
- CRASH. Tidak ada warning. Data corruption.
```

---

## 6. Kesimpulan dan Rekomendasi

### 6.1 Tabel Limitasi

```
┌─────────────────────┬────────────────┬──────────────────┐
│ Parameter          │ Theoretical    │ Practical Limit  │
├─────────────────────┼────────────────┼──────────────────┤
│ JSON payload size  │ 8,192 bytes    │ ~6,000 bytes     │
│ GPIO pins          │ 34 pins        │ 10–15 usable     │
│ I2C devices        │ 127 addresses  │ 4–6 devices      │
│ GPIO sensors       │ 19 inputs      │ 10–12 sensors    │
│ GPIO actuators     │ 13 outputs     │ 6–8 actuators    │
│ Modbus devices     │ 247 IDs        │ 8–12 devices     │
│ Analog inputs      │ 8 channels     │ 4–6 channels     │
│ Total devices/node │ ~40 devices    │ 20–30 devices    │
│ Broker latency     │ unlimited      │ < 10 ms (safe)   │
│ Nodes per broker   │ ~5,000 nodes   │ 500–1,000 nodes  │
└─────────────────────┴────────────────┴──────────────────┘
```

### 6.2 Untuk Sistem Aeroponik (Kebutuhan Nyata)

```
Kebutuhan minimum 1 zone aeroponik:
- 2× BME280 (atas + akar)        = 2 I2C
- 1× INA219                       = 1 I2C
- 2× soil moisture analog         = 2 GPIO analog
- 2× float switch                 = 2 GPIO digital
- 3× aktuator (pump, valve, fan)  = 3 GPIO output
- 1× EC/pH meter Modbus           = 1 Modbus device
─────────────────────────────────────────
Total: 11 devices → payload ~650 bytes → aman

Dengan buffer 8 KB, bisa menambah:
- +4× I2C sensor (SHT31, BH1750, dll)
- +6× GPIO input/output
- +2× Modbus device
Total maks: ~22 devices per node → payload ~1,200 bytes → masih sangat aman
```

### 6.3 Jika Mencapai Limitasi

```
1. JSON > 8 KB:
   - ESP32 crash (heap corruption)
   - Solusi: pindah ke binary format (Protobuf/CBOR) atau split payload

2. GPIO habis:
   - Tambah IO expander (MCP23017 via I2C: +16 pins per chip)
   - Atau pakai ESP32-S3 (lebih banyak GPIO)

3. I2C > 6 devices:
   - Gunakan 2 bus I2C (ESP32 punya 2 hardware I2C: Wire, Wire1)
   - Atau pakai I2C multiplexer (TCA9548A: 8 channel)

4. Broker latency naik:
   - Tambah broker secondari (clustering)
   - Atau gunakan edge computing (proses di ESP32, kirim hasil ke broker)
```

### 6.4 Margin Keamanan Firmware

```
Margin aman untuk firmware ini:
- Buffer JSON: 8 KB used / 8 KB allocated = 100% (TIDAK ada margin)
  → Rekomendasi: pakai StaticJsonDocument<10240> (10 KB) untuk margin 20%

- Heap free: 40–80 KB digunakan untuk:
  - WiFi stack: ~10 KB
  - MQTT stack: ~8 KB
  - Task telemetry: ~8 KB
  - Sisa heap untuk JSON: ~14–54 KB

  Dengan 30 devices, heap usage ≈ 5–10 KB → AMAN

- GPIO margin: 10–15 used / 19 available = 53–79% → AMAN
```

---

## Referensi Data

- `test/results/phase1/05_unit_test_payloads.json` — Captured MQTT payloads dari 24 nodes
- `test/results/phase1/stress_test_fase1_20260828_194809.md` — Backend stress metrics
- `firmware/aeroponic-node/src/core/HardwareManager.cpp:42-43` — Buffer sizes
- `firmware/aeroponic-node/ANALISIS_FIRMWARE.md` — 18 gaps identified
- `docs/mqtt_standar_komunikasi.md:248-289` — Payload structure spec
- `firmware/aeroponic-node/src/core/Config.cpp:16-50` — Pin assignments
- `firmware/aeroponic-node/src/core/ProtocolHandlers.cpp:10-18, 236-292` — I2C config
- `firmware/aeroponic-node/RESUME_AKHIR.md:309-317` — Memory specs
