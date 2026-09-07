# Aeroponic Node Firmware (ESP32)

Folder ini berisi *source code* mikrokontroler (C++) untuk Node Hardware Aeroponik, yang berjalan di atas *board* ESP32. Pengembangan di folder ini dioptimalkan untuk menggunakan **PlatformIO** sebagai *build system* dan **Wokwi Simulator** untuk pengujian virtual tanpa *hardware* fisik.

## 🛠 Prasyarat (Prerequisites)
Pastikan VS Code kamu telah terpasang ekstensi berikut:
1. **PlatformIO IDE** (Oleh PlatformIO)
2. **Wokwi Simulator** (Oleh Wokwi)

---

## 🚀 Cara Menjalankan & Simulasi (Developer Guide)

Karena arsitektur PlatformIO bergantung pada pendeteksian direktori *root*, kamu **WAJIB** menjadikan folder `aeroponic-node` ini sebagai *root workspace* saat mengompilasi.

### Langkah 1: Membuka Folder dengan Benar
1. Di VS Code, klik **File** -> **Add Folder to Workspace...**
2. Pilih folder `firmware/aeroponic-node`.
3. *(Atau kamu bisa membuka folder ini langsung di jendela VS Code baru).*

### Langkah 2: Build / Kompilasi Program

Ada dua cara untuk mengompilasi program ini, melalui antarmuka VS Code atau melalui Terminal:

**Cara A: Melalui Antarmuka VS Code**
1. Tunggu hingga PlatformIO selesai melakukan *Initializing* di latar belakang.
2. Klik **ikon Tanda Centang (✓) [PlatformIO: Build]** di panel bawah VS Code.
3. Tunggu hingga muncul tulisan `[SUCCESS]`.

**Cara B: Melalui Terminal (Direkomendasikan jika UI bermasalah)**
Jika ikon centang tidak muncul atau *Initializing* terlalu lama, kamu bisa mem-*build* secara manual menggunakan Python Virtual Environment (*venv*) seperti yang saya lakukan sebelumnya:
1. Buka Terminal baru di VS Code (`Ctrl + \``).
2. Pindah ke folder *root* proyekmu, lalu buat dan aktifkan *venv*:
   ```bash
   python3 -m venv ~/.platformio-venv
   source ~/.platformio-venv/bin/activate
   ```
3. Instal PlatformIO Core ke dalam *venv* tersebut:
   ```bash
   pip install -U platformio
   ```
4. Jalankan perintah kompilasi langsung menunjuk ke folder *firmware*:
   ```bash
   pio run -d firmware/aeroponic-node
   ```
5. Tunggu hingga terminal menunjukkan `======================== [SUCCESS] ========================`.

### Langkah 3: Menjalankan Simulator Wokwi
1. Buka file `diagram.json`.
2. Tekan kombinasi keyboard `Ctrl + Shift + P` (atau `F1`).
3. Ketik dan pilih **`Wokwi: Start Simulator`**.
4. Wokwi akan otomatis mencari file hasil *build* (`.pio/build/esp32dev/firmware.bin`) dan menjalankannya secara virtual.

---

## 🔧 Struktur File Penting

- `src/main.cpp` : Kode utama C++ Arduino/ESP32.
- `platformio.ini` : Konfigurasi *board*, *framework*, dan daftar *library* yang digunakan.
- `diagram.json` : Diagram skematik visual untuk Wokwi Simulator (sensor, LED, kabel, dsb).
- `wokwi.toml` : File penghubung yang memberitahu Wokwi di mana letak file *binary* (`.bin` / `.elf`) hasil kompilasi PlatformIO.

---

## 📡 MQTT Topics & API Endpoints

### Default Config
- **Broker**: `broker.hivemq.com`
- **Port**: `1883`
- **Prefix**: `smartfarm` (Bisa diubah via Web Portal)

### MQTT Topics
Topik akan mengikuti format: `<prefix>/<node_id>/<kategori>`
1. **Telemetry Data**
   - Topic: `smartfarm/node-01/telemetry`
   - Berisi data sensor (Suhu, Kelembaban, Modbus, dll) dikirim setiap interval tertentu.
2. **Actuator Command**
   - Topic: `smartfarm/node-01/actuator`
   - Digunakan untuk menerima perintah (misalnya menyalakan pompa/relay).

### Web Portal API Endpoints (Local IP)
1. **`GET /api/status`**
   - Mengambil status sistem, WiFi, memori, status MQTT, dan logs live MQTT terbaru (`mqtt_logs`).
2. **`GET /api/config`** & **`POST /api/config`**
   - Mengambil & menyimpan konfigurasi perangkat di memori internal.
3. **`GET /api/config/export`**
   - Mengekspor/mengunduh file setelan konfigurasi `config.json` dari LittleFS.
4. **`POST /api/config/import`**
   - Mengunggah (restore) file konfigurasi ke LittleFS ESP32 lalu memicu reboot.
5. **`POST /api/modbus/start_scan`**
   - Memulai *scan* Modbus ID secara sinkron.
6. **`GET /api/modbus/scan_registers`**
   - Memindai *holding registers* dari sebuah Modbus Slave ID.

---

## 🐛 Troubleshooting

**1. Wokwi error "firmware.bin not found"**
Ini artinya program C++ belum dikompilasi. Jalankan langkah 2 (Build) terlebih dahulu sampai berstatus `[SUCCESS]`.

**2. PlatformIO "Initializing..." tidak selesai-selesai**
Biasanya terjadi saat baru pertama kali dipasang karena sedang mengunduh *toolchain* C++ di latar belakang. Jika dirasa terlalu lama/nyangkut:
- Restart VS Code kamu.
- Pastikan kamu sudah klik "Add Folder to Workspace..." untuk folder ini.
- Coba jalankan *compile* manual lewat terminal: `pio run`.

**3. Ingin konek MQTT dari Wokwi ke Docker lokal (127.0.0.1)?**
Wokwi *cloud engine* tidak bisa mengakses localhost komputer kamu. Kamu harus mengunduh dan menjalankan **Wokwi Private Gateway** secara lokal agar simulator bisa menjembatani koneksi ke `127.0.0.1:1883`.
