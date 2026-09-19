# UML Arsitektur Sistem — Deployment Diagram

**Sistem:** enyx-enterprise  
**Tanggal:** 2026-08-29

---

## Diagram Deployment — Hubungan Antarperangkat Keras

```plantuml
@startuml Deployment Diagram
skinparam backgroundColor #FFFFFF
title enyx-enterprise\nDeployment Diagram — Hardware
top to bottom direction
rectangle "OPERATIONAL ZONE" as ZoneUser #DDEBF7 {
  node "PC SERVER" as PC
  node "MOBILE DEVICE" as Mobile
}
rectangle "NETWORK ZONE" as ZoneNet #E2EFDA {
  node "ROUTER" as Router
  node "SWITCH" as Switch
}
rectangle "EDGE ZONE" as ZoneEdge #FCE4D6 {
  node "ESP32" as ESP
}
rectangle "FIELD ZONE" as ZoneField #FFF2CC {
  node "CCTV" as CCTV
  node "SENSOR" as Sensor
  node "AKTUATOR" as Aktuator
}
PC --> Router : WiFi
Mobile --> Router : WiFi
Router --> Switch : LAN
CCTV --> Switch : LAN\nRTSP
Router --> ESP : WiFi\nMQTT
ESP --> Sensor : DIGITAL\nANALOG
ESP --> Aktuator : DIGITAL\nPWM
@enduml
```

> **Tata letak vertikal (atas→bawah):** Baris 4 (atas) = PC Server & Mobile Device; Baris 3 = Router & Switch; Baris 2 = ESP32; Baris 1 (bawah) = CCTV, Sensor, Aktuator.

## Koneksi

| Dari | Ke | Protokol/Interface |
|------|-----|-------------------|
| PC SERVER → ROUTER | WiFi | — |
| MOBILE DEVICE → ROUTER | WiFi | — |
| ROUTER ↔ SWITCH | LAN | — |
| CCTV → SWITCH | LAN | RTSP |
| ROUTER ↔ ESP32 | WiFi | MQTT |
| ESP32 → SENSOR | — | Digital/Analog |
| ESP32 → AKTUATOR | — | Digital/PWM |

---

## Activity Diagram — Core Runtime ESP32 FreeRTOS

```plantuml
@startuml Core Runtime ESP32 FreeRTOS
skinparam backgroundColor #FFFFFF
title enyx-enterprise\nActivity Diagram - Core Runtime ESP32 FreeRTOS
start
fork
  :[Core 0] WiFiTask: konek ke AP/berjalan APmode;
  :[Core 0] MqttTask: connect broker, subscribe topik;
fork again
  :[Core 1] TelemetryTask: baca sensor, evaluasi kontrol, publish MQTT;
end fork
:MqttTask --> WatchdogTask : heartbeat;
:TelemetryTask --> WatchdogTask : heartbeat;
partition Watchdog {
  :WatchdogTask: cek timeout heartbeat setiap 5 detik;
  if (Task macet?) then (ya)
    if (Memiliki restartFunc?) then (ya)
      :Restart task yang hang;
    else (tidak)
      :Reset ESP32;
    endif
  else (tidak)
    :Lanjutkan eksekusi;
  endif
}
stop
@enduml
```

Core 0 menangani semua komponen jaringan dan pengawasan sistem (WiFiTask, MqttTask, WatchdogTask, SysMonitorTask). Core 1 dialokasikan untuk TelemetryTask yang bertugas membaca sensor secara periodik setiap 5 detik, memproses data GPIO, Modbus RS485, dan I2C, lalu memformatnya menjadi JSON sebelum diteruskan ke MqttTask. Hanya MqttTask dan TelemetryTask yang mengirim heartbeat ke WatchdogTask.

---

## Class Diagram — Factory Pattern & Registry ProtocolHandler

```plantuml
@startuml Factory Pattern & Registry ProtocolHandler
skinparam backgroundColor #FFFFFF
title enyx-enterprise\nClass Diagram - Factory Pattern & Registry ProtocolHandler
abstract class ProtocolHandler {
  +init(config: JsonObject)
  +read(telemetry: JsonObject)
  +write(value: int)
  +getProtocolName()
  +getSensorName()
}
class ProtocolRegistry {
  +registerProtocol(name, creator)
  +createHandler(name, config)
  +getRegisteredProtocols()
  -registry: map<String, ProtocolHandlerCreator>
}
class HardwareManager {
  -activeHandlers: vector<ProtocolHandler*>
  -activeOutputHandlers: map<String, ProtocolHandler*>
  +init()
  +reloadConfiguration()
  +telemetryTask()
  +setOutput(target, value)
}
class ConfigManager {
  +init()
  +loadConfig()
  +saveConfig(jsonPayload)
}
class MqttManager {
  +init()
  +mqttCallback(topic, payload, length)
}
class GPIOInputHandler
class GpioOutputHandler
class ModbusHandler
class I2CHandler
ProtocolHandler <|-- GPIOInputHandler
ProtocolHandler <|-- GpioOutputHandler
ProtocolHandler <|-- ModbusHandler
ProtocolHandler <|-- I2CHandler
ProtocolRegistry ..> ProtocolHandler : creates
HardwareManager ..> ProtocolRegistry : register / create
HardwareManager --> ProtocolHandler : manages
HardwareManager ..> ConfigManager : uses config vectors
MqttManager --> HardwareManager : setOutput()
@enduml
```

`ConfigManager` memuat `config.json` dari LittleFS saat boot dan memetakan elemen JSON ke dalam `std::vector` in-memory di namespace `Config`. Saat `HardwareManager::init()` dijalankan, semua handler didaftarkan ke `ProtocolRegistry` sebagai peta `String → lambda creator`. `TelemetryTask` mengiterasi `activeHandlers` dan memanggil `read()` untuk setiap sensor, sedangkan `MqttCallback` menerima perintah aktuator dan memanggil `HardwareManager::setOutput()`.

---

## Sequence Diagram — Telemetry Flow

```plantuml
@startuml Sequence Diagram - Telemetry Flow
skinparam backgroundColor #FFFFFF
title enyx-enterprise\nSequence Diagram - Telemetry Flow
actor TelemetryTask
participant "HardwareManager" as HW
participant "MQTT Broker" as MQTT
participant "Module Service" as Module
loop setiap 5 detik
  TelemetryTask -> HW : read() semua sensor
  HW --> TelemetryTask : sensor values
  TelemetryTask -> TelemetryTask : build JSON
  TelemetryTask -> MQTT : publish telemetry
  MQTT -> Module : deliver telemetry
end
@enduml
```

`TelemetryTask` di Core 1 membaca semua sensor melalui `activeHandlers` (GPIO, Modbus RS485, I2C), membentuk JSON, lalu mempublikasikan ke topik `smartfarm/{node_id}/telemetry` setiap 5 detik.

---

## Sequence Diagram — Actuator Command Flow

```plantuml
@startuml Sequence Diagram - Actuator Command Flow
skinparam backgroundColor #FFFFFF
title enyx-enterprise\nSequence Diagram - Actuator Command Flow
participant "Control Service" as Control
participant "MQTT Broker" as MQTT
participant "mqttCallback" as Callback
participant "HardwareManager" as HW
Control -> MQTT : publish set_output {target, value, req_id}
MQTT -> Callback : deliver perintah
Callback -> HW : setOutput(target, value)
HW --> Callback : executed
Callback -> MQTT : publish ACK {req_id, status}
MQTT -> Control : deliver ACK
@enduml
```

Control Service mengirim perintah ke topik `smartfarm/actuator/{node_id}`. Perintah diterima oleh `mqttCallback`, diparse, kemudian diteruskan ke `HardwareManager::setOutput()` yang pada akhirnya memanggil `write()` pada handler aktuator yang sesuai. Setelah eksekusi berhasil, ESP32 mengirim ACK ke topik `smartfarm/{node_id}/confirm`.

---

## Sequence Diagram — Adaptive Control Flow

```plantuml
@startuml Sequence Diagram - Adaptive Control Flow
skinparam backgroundColor #FFFFFF
title enyx-enterprise Sequence Diagram - Adaptive Control Flow
actor model_control
participant "NATS + MinIO" as NM
participant "model_controller\nPOST /predict" as Controller
participant "Control Service" as Control
participant "MQTT Broker" as MQTT
participant "ESP32" as ESP32
loop setiap tick
  model_control -> NM : telemetry.ingest\nget_latest_metadata()
  NM --> model_control : state 10D + detection
  model_control -> Controller : POST /predict\n{state}
  Controller --> model_control : action\n[D_mist, interval, A_valve]
  alt cycle selesai
    model_control -> Control : PUT schedules\n+ POST command bypass
    Control -> MQTT : publish set_output\n{node_id, target, value}
    MQTT -> ESP32 : deliver perintah
    ESP32 -> MQTT : publish confirm\n{prefix}/{node_id}/confirm
    MQTT -> Control : deliver confirm
    Control -> Control : MarkAckedByReqID\nmatch req_id
  else
    model_control -> model_control : lewati eksekusi
  end
end
@enduml
```

---

## Sequence Diagram — Control Service Command Flow

```plantuml
@startuml Sequence Diagram - Control Service Command Flow
skinparam backgroundColor #FFFFFF
title enyx-enterprise Sequence Diagram - Control Service Command Flow
actor Dashboard
participant "Control Service" as Control
participant "MariaDB commands" as DB
participant "MQTT Broker" as MQTT
participant "ESP32" as ESP32
Dashboard -> Control : POST /control/command\n{node_id, target, value}
Control -> Control : Mode Arbitration\n(MANUAL/AUTO/EMERGENCY)
Control -> DB : create command\nstatus=pending
Control -> MQTT : publish set_output QoS1\n{req_id, target, value}
MQTT -> ESP32 : deliver perintah
Control -> DB : update status=sent
ESP32 -> MQTT : confirm\n{req_id, target, value, status}
MQTT -> Control : deliver confirm
Control -> DB : MarkAckedByReqID\nstatus=acked
Control --> Dashboard : 202 Accepted\n{commands}
@enduml
```

Dashboard mengirim perintah ke Control Service melalui `POST /control/command`. Control Service melakukan Mode Arbitration untuk memeriksa mode node (MANUAL/AUTO/EMERGENCY) dan memastikan perintah diizinkan. Perintah disimpan ke MariaDB dengan status `pending`, lalu dipublikasikan ke MQTT dengan QoS 1. ESP32 menerima dan mengeksekusi perintah, kemudian mengirim konfirmasi ke topik `{prefix}/{node_id}/confirm`. Control Service menerima konfirmasi, mencocokkan `req_id`, dan memperbarui status menjadi `acked`. Sweep worker secara periodik memeriksa perintah yang tidak mendapat konfirmasi dalam 8 detik dan mengubah statusnya menjadi `timeout`.

---

## State Machine Diagram — Command Lifecycle

```plantuml
@startuml State Machine Diagram - Command Lifecycle
skinparam backgroundColor #FFFFFF
title enyx-enterprise State Machine Diagram - Command Lifecycle
[*] --> pending : dispatch()
pending --> sent : publish QoS1 success
pending --> failed : publish error / MQTT down
sent --> acked : ESP32 confirm\n(req_id match)
sent --> timeout : sweep worker\n(8 detik)
sent --> failed : connection error
acked --> [*]
timeout --> [*]
failed --> [*]
@enduml
```

Setiap perintah kontrol melalui lima tahapan status transaksional: `pending` → `sent` → `acked`. Jika dalam 8 detik tidak ada respons, sweep worker mengubah status menjadi `timeout`. Jika terjadi gangguan koneksi/MQTT tidak tersedia, status langsung `failed`.

---

## Data Flow Diagrams

### Telemetry Pipeline

```plantuml
@startuml Data Flow Diagram - Telemetry Pipeline
skinparam backgroundColor #FFFFFF
title enyx-enterprise Data Flow Diagram - Telemetry Pipeline
start
:Operator daftarkan perangkat via Dashboard;
:ESP32 ke MQTT Broker;
fork
  :Module Service\nPublishLive ke NATS;
  :Dashboard via WS-Gateway;
fork again
  :Module Service\nIngestTelemetry;
  :Redis + TimescaleDB + Outbox;
  :Relay Worker ke NATS Core;
  :Batch Publisher ke JetStream;
  :Analytics ke TimescaleDB metrics_rollup;
end fork
stop
@enduml
```

### Analytics Pipeline

```plantuml
@startuml Data Flow Diagram - Analytics Pipeline
skinparam backgroundColor #FFFFFF
title enyx-enterprise Data Flow Diagram - Analytics Pipeline
start
:Batch Publisher ke NATS JetStream\ntelemetry.batch;
:Analytics Service\ndurable consumer analytics-batch;
:IngestBatch() UpsertRollup\nke metrics_rollup;
:Ack ke NATS;
:TimescaleDB continuous aggregate\nmetrics_hourly + metrics_daily;
if (Dashboard request metrics?) then (ya)
  :Pilih tabel sumber\nsesuai rentang waktu;
  if (<= 1 jam?) then (ya)
    :Query metrics_rollup;
  else (tidak)
    if (<= 24 jam?) then (ya)
      :Query metrics_hourly;
    else (tidak)
      :Query metrics_daily;
    endif
  endif
  if (Data kosong?) then (ya)
    :Perluas jendela waktu\nhingga 30 hari;
    if (Masih kosong?) then (ya)
      :queryLatest\nambil 120 bucket terakhir;
    endif
  endif
endif
stop
@enduml
```

Saat dashboard meminta data grafik, sistem memilih tabel sumber secara otomatis: `metrics_rollup` untuk ≤1 jam, `metrics_hourly` untuk ≤24 jam, dan `metrics_daily` untuk >24 jam. Jika tidak ada data, sistem memperluas jendela pencarian secara bertingkat hingga 30 hari.

### ML/Stream Pipeline

```plantuml
@startuml Data Flow Diagram - ML/Stream Pipeline
skinparam backgroundColor #FFFFFF
title enyx-enterprise Data Flow Diagram - ML/Stream Pipeline
start
:CCTV RTSP stream;
:Stream Service\nFFmpeg CaptureSnapshot();
:MinIO stream bucket\nsnapshots/{cam}_{timestamp}.jpg;
:ML Service\nPOST /ml/detect/from-stream;
:ModelRegistry\nload(model_id) check cache;
if (Model di cache?) then (tidak)
  :Load YOLO(.pt) dari /app/models;
  :Simpan ke _loaded cache;
else (ya)
endif
:YOLO inference\nroot_length_cm, tuber_size_cm;
:Annotated image + metrics;
:MinIO mlbucket\noriginal/ + detected/;
:MariaDB ml_db\nvision_detections;
stop
@enduml
```

### RL Training Pipeline

```plantuml
@startuml Data Flow Diagram - RL Training Pipeline
skinparam backgroundColor #FFFFFF
title enyx-enterprise Data Flow Diagram - RL Training Pipeline
start
:Data Sources:\nMinIO (L_root, U_status)\nModule Service (T_in, H_in, EC, pH, T_nut)\nKalkulasi lokal (I_day);
:State Vector 10D\n[L_root, U_status, T_in, H_in, T_out, H_out, EC, pH, T_nut, I_day];
:Gymnasium Environment\nAeroponicGymnasiumEnv;
:TD3 Agent\nTwin Delayed DDPG;
:Action 3D ternormalisasi [-1,1]\n[a_mist, a_interval, a_valve];
:Map ke物理空间\nD_mist [120,600]s\ninterval [120,600]s\nvalve ON/OFF;
:Reward Function\nR_growth + R_growth_proxy + R_state\n+ P_diversity + R_efficiency\n- C_resource - P_env - P_hypoxia\n- P_extreme - P_shrink - P_death;
:Replay Buffer 2M;
:Training Loop\n2M timesteps;
:Model Artifacts\naeroponic_td3.zip\nvec_normalize_td3.pkl;
:model-controller Service\nload TD3 + VecNormalize;
:Inference kontrol\nmisting/interval/valve;
stop
@enduml
```

---

## Activity Diagram — Mode Arbitration

```plantuml
@startuml Activity Diagram - Mode Arbitration
skinparam backgroundColor #FFFFFF
title enyx-enterprise Activity Diagram - Mode Arbitration
start
:Terima perintah kontrol;
:Ambil mode node saat ini;
if (Mode adalah EMERGENCY?) then (ya)
  :Tolak perintah\n(kecuali emergency stop);
  stop
else (tidak)
  if (Mode adalah AUTO?) then (ya)
    if (Bypass aktif?) then (ya)
      :Izinkan eksekusi;
    else (tidak)
      :Tolak perintah manual;
      stop
    endif
  else (tidak)
    if (Mode adalah MANUAL?) then (ya)
      :Izinkan eksekusi\n(hanya intervensi pengguna);
    else (tidak)
      :Tolak perintah\n(mode tidak dikenali);
      stop
    endif
  endif
endif
stop
@enduml
```

Sebelum perintah dieksekusi, Control Service melakukan Mode Arbitration untuk menghindari bentrok eksekusi: EMERGENCY tolak semua kecuali emergency stop; AUTO tolak perintah manual kecuali bypass aktif; MANUAL hanya izinkan intervensi manual.

---

## Activity Diagram — Scheduler Engine

```plantuml
@startuml Activity Diagram - Scheduler Engine
skinparam backgroundColor #FFFFFF
title enyx-enterprise Activity Diagram - Scheduler Engine
start
:Scheduler Engine\ngoroutine mandiri;
while (eval setiap tick) is (ya)
  :Ambil semua schedule aktif;
  :Cek Mode Guard\n(node mode + prevMode);
  if (Mode Guard aktif?) then (ya)
    :Lewati eksekusi;
  else (tidak)
    :Iterasi setiap schedule;
    if (Tipe interval?) then (ya)
      :Hitung ON/OFF cycle\nberbasis detik;
    else (tidak)
      if (Tipe schedule?) then (ya)
        :Cek waktu harian\non_at / off_at;
      else (tidak)
        if (Tipe threshold?) then (ya)
          :Ambil nilai sensor\ndari telemetry;
          :Bandingkan threshold\nhisteresis;
        else (tidak)
          if (Tipe duration?) then (ya)
            :Hitung sisa waktu\none-shot activation;
          else (tidak)
            if (Tipe ramp?) then (ya)
              :Hitung langkah PWM\nlinear from → to;
            else (tidak)
              if (Tipe window_pulse?) then (ya)
                :Cek jendela waktu\nharian;
                :Hitung pulsa ON/OFF\ndalam jendela;
              endif
            endif
          endif
        endif
      endif
    endif
  endif
endwhile
stop
@enduml
```

Scheduler Engine mengelola enam tipe penjadwalan: `interval` (siklus ON/OFF berbasis detik), `schedule` (waktu harian), `threshold` (histeresis sensor), `duration` (one-shot activation), `ramp` (transisi PWM linear), `window_pulse` (pulsa dalam jendela waktu harian).

---

## Class Diagram — Model Registry

```plantuml
@startuml Class Diagram - Model Registry
skinparam backgroundColor #FFFFFF
title enyx-enterprise Class Diagram - Model Registry
class ModelRegistry {
  -_loaded: dict[str, YOLO]
  -_lock: threading.Lock
  +load(model_id) YOLO
  +resolve(model_id) YOLO
  +ensure_seeded_model()
  +warmup()
  +invalidate(model_id)
}
class VisionModel {
  +id: String PK
  +name: String
  +slug: String UNIQUE
  +model_type: String
  +framework: String
  +version: String
  +file_path: String
  +class_names: JSON
  +input_size: Integer
  +confidence_threshold: Float
  +iou_threshold: Float
  +status: Enum
  +is_default: Boolean
}
class VisionDetection {
  +id: Integer PK
  +detection_uid: String UNIQUE
  +model_id: String
  +source_type: Enum
  +source_ref: String
  +original_url: String
  +annotated_url: String
  +num_detections: Integer
  +classes: JSON
  +detections: JSON
  +confidence_min: Float
  +confidence_max: Float
  +confidence_avg: Float
  +execution_time_ms: Float
  +status: String
}
class MinIOClient {
  +download_object(bucket, key) bytes
  +upload_image(bucket, key, bytes) url
  +upload_image_with_metadata(bucket, key, bytes, metadata) url
}
class YOLO {
  +predict(source)
  +__call__(source)
}
ModelRegistry --> VisionModel : metadata dari MariaDB
ModelRegistry --> YOLO : cache in-memory
VisionDetection --> VisionModel : model_id FK
MinIOClient --> ModelRegistry : download weights + frames
@enduml
```

Dashboard memicu AI detect melalui `POST /streams/{id}/snapshot?detect=true`. Stream Service menangkap frame dari MediaMTX, mengunggahnya ke MinIO bucket `stream`, lalu memanggil ML Service `POST /ml/detect/from-stream`. ML Service mengunduh frame, memuat model YOLOv8 via `ModelRegistry` (dengan cache in-memory), menjalankan inferensi untuk mendeteksi akar dan umbi, mengukur panjang akar dalam cm, lalu menyimpan gambar original dan annotated ke MinIO `mlbucket`.

---

## Sequence Diagram — AI Detect Inference Flow

```plantuml
@startuml Sequence Diagram - AI Detect Inference Flow
skinparam backgroundColor #FFFFFF
title enyx-enterprise Sequence Diagram - AI Detect Inference Flow
actor Dashboard
participant "Stream Service" as Stream
participant "ML Service" as ML
participant "MinIO" as MinIO
participant "MariaDB ml_db" as DB
Dashboard -> Stream : POST /streams/{id}/snapshot?detect=true
Stream -> Stream : CaptureSnapshot() dari MediaMTX
Stream -> MinIO : upload frame ke stream bucket
Stream -> ML : POST /ml/detect/from-stream\n{object_key}
ML -> MinIO : download frame dari stream bucket
ML -> ML : YOLO inference\nroot_length_cm, tuber_size_cm
ML -> MinIO : upload original + annotated\nke mlbucket
ML -> DB : insert vision_detections
ML --> Stream : DetectResult
Stream -> MinIO : writeToResultBucket\nframes/ + results/ + annotated/
Stream --> Dashboard : SnapshotView\n(root_length_cm, classes)
@enduml
```
