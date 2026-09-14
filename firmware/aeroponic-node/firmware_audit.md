# Firmware Audit Report — Aeroponic Node

**Date:** 2026-09-14  
**Auditor:** Kilo / Multi-agent security review  
**Scope:** Complete firmware codebase (`firmware/aeroponic-node/`)  
**Mode:** Read-only static analysis  

---

## Executive Summary

The firmware contains **multiple critical vulnerabilities** across all major subsystems. The most severe issues are:

1. **PubSubClient race conditions** — used from multiple tasks without synchronization, causing crashes
2. **Thread-unsafe logging** — `MqttManager::addLog()` has no mutex protection, leading to buffer corruption
3. **Critical security gaps** — plaintext auth, no TLS, weak key derivation, missing credential decryption on load
4. **Reliability issues** — task leaks, unbounded heap allocations, dead code paths

---

## Table of Contents

1. [Web Config Portal Audit](#1-web-config-portal-audit)
2. [Sensor & Modbus Audit](#2-sensor--modbus-audit)
3. [Security & Crypto Audit](#3-security--crypto-audit)
4. [WiFi & Network Audit](#4-wifi--network-audit)
5. [Watchdog & SystemMonitor Audit](#5-watchdog--systemmonitor-audit)
6. [OTA & ConfigManager Audit](#6-ota--configmanager-audit)
7. [Boot Flow & Main Audit](#7-boot-flow--main-audit)
8. [Consolidated Severity Matrix](#8-consolidated-severity-matrix)
9. [Recommended Remediation Order](#9-recommended-remediation-order)

---

## 1. Web Config Portal Audit

**Files audited:**
- `firmware/aeroponic-node/data/index.html`
- `firmware/aeroponic-node/data/script.js`
- `firmware/aeroponic-node/src/protocols/WebConfigPortal.cpp`
- `firmware/aeroponic-node/src/protocols/WebConfigPortal.h`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | No CSP / X-Frame-Options / X-Content-Type-Options headers served | `data/index.html` | — |
| 2 | Inline `onclick` handlers everywhere — XSS hijack risk if HTML injection occurs | `data/index.html` | — |
| 3 | Reflected/Stored XSS via unsanitized log rendering in `loadStatus()` | `data/script.js` | 201-211 |
| 4 | XSS via unsanitized config values in `drawInputs`, `drawOutputs`, `drawModbus`, `drawI2C` | `data/script.js` | — |
| 5 | XSS in scan result rendering (`startScanId()`, `startScanReg()`) | `data/script.js` | 573-577, 626 |
| 6 | Plaintext password comparison in `handleApiLogin()` — passwords stored plaintext | `WebConfigPortal.cpp` | 230 |
| 7 | `handleRoot()` serves `index.html` to unauthenticated users — information disclosure | `WebConfigPortal.cpp` | 196-209 |
| 8 | `handleApiOtaUpload()` does not send response when auth fails mid-upload — client hangs | `WebConfigPortal.cpp` | 647-671 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 9 | No backend input validation on any POST handler (SSID, port, NODE_ID, pins) | `WebConfigPortal.cpp` | all POST handlers |
| 10 | No JSON schema validation — arbitrary JSON accepted and saved | `WebConfigPortal.cpp` | `handleApiHardwarePost`, `handleApiConfigImport` |
| 11 | Unbounded `loginAttempts` vector — no eviction, no TTL, heap exhaustion risk | `WebConfigPortal.cpp` | 28, 214-258 |
| 12 | `saveFullConfig()` uses fixed 8192-byte `DynamicJsonDocument` — silent truncation on large configs | `WebConfigPortal.cpp` | 32 |
| 13 | `handleApiConfigExport()` decrypts passwords to plaintext in memory — exposed during window | `WebConfigPortal.cpp` | 703-711 |
| 14 | No HTTPS — all traffic plaintext HTTP, credentials sniffable | `WebConfigPortal.cpp` | 143-145 |
| 15 | Unbounded loop in `startScanReg()` — 65536 sequential HTTP requests possible | `data/script.js` | 621-630 |
| 16 | No timeout on `fetch()` requests — UI hangs on stalled backend | `data/script.js` | all `fetch()` calls |
| 17 | Mock API leaks plaintext credentials in localhost bypass | `data/script.js` | 46-62 |
| 18 | `api()` function swallows errors and returns `null` — callers must remember to check | `data/script.js` | 76-84 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 19 | `millis()` rollover vulnerability in rate limiter — indefinite lockout after 49 days | `WebConfigPortal.cpp` | 216, 249-250 |
| 20 | `handleNotFound()` performs unconditional captive-portal redirect — breaks legitimate HTTP clients | `WebConfigPortal.cpp` | 629-633 |
| 21 | OTA upload has no file-size limit or integrity check | `WebConfigPortal.cpp` | 655-671 |
| 22 | `handleApiConfigImport()` accepts raw JSON without sanitization | `WebConfigPortal.cpp` | 725-750 |
| 23 | `cancelScanId()` is dead code — never wired to UI button | `data/script.js` | 589-607 |
| 24 | `handleApiHardwareDiscover()` registered but never called from JS — dead endpoint | `WebConfigPortal.cpp` | — |
| 25 | No client-side validation on scan range (`start <= end`) | `data/script.js` | `startScanReg` |
| 26 | `localStorage` token storage — vulnerable to XSS | `data/script.js` | line 1 |
| 27 | MQTT log polling is unbounded — `mqtt_logs` array can grow large | `data/script.js` | — |
| 28 | No visual feedback for file selection (OTA and Import) | `data/index.html` | — |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 29 | Heavy use of inline `style` attributes — reduces maintainability | `data/index.html` | — |
| 30 | No `rel="noopener noreferrer"` on external resource links | `data/index.html` | — |
| 31 | No `type="submit"` on Sign In button | `data/index.html` | — |
| 32 | Login form lacks `autocomplete` attribute | `data/index.html` | — |
| 33 | MQTT logs container uses same ID text as label — naming confusion | `data/index.html` | — |
| 34 | No `Connection: close` header on most responses | `WebConfigPortal.cpp` | — |
| 35 | String concatenation for JSON responses — brittle, risks injection | `WebConfigPortal.cpp` | 560, 584, 607 |
| 36 | No Doxygen documentation in header | `WebConfigPortal.h` | — |

---

## 2. Sensor & Modbus Audit

**Files audited:**
- `src/core/HardwareManager.cpp`
- `src/core/HardwareManager.h`
- `src/core/ProtocolHandlers.cpp`
- `src/core/ProtocolHandlers.h`
- `include/Config.h`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | Strict aliasing violation in FLOAT32 parsing — `uint32_t*` cast to `float*` causes UB | `ProtocolHandlers.cpp` | 239-241 |
| 2 | `latestSensorValues` read without mutex — `std::map` concurrent R/W = UB | `HardwareManager.cpp` | 365-383 vs 335-339 |
| 3 | `outputStates` read/write without mutex — concurrent access from multiple tasks | `HardwareManager.cpp` | 331, 395-399 |
| 4 | `activeOutputHandlers` accessed without mutex in `setOutput()` — can dereference freed memory | `HardwareManager.cpp` | 395-408 |
| 5 | `MqttManager::addLog()` thread-unsafe dual buffer — concurrent writes corrupt log entries | `MqttManager.cpp` | 24-41 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 6 | Hardcoded big-endian Modbus byte order — wrong values for little-endian devices | `ProtocolHandlers.cpp` | 239-248 |
| 7 | `reg.length > 2` silently ignored — registers 3-4 discarded without error | `ProtocolHandlers.cpp` | 227, 238-248 |
| 8 | I2C init without stabilization delay — WiFi EMI can cause bus failures | `ProtocolHandlers.cpp` | 12-19 |
| 9 | I2C scan 126 addresses back-to-back — excessive bus traffic, EMI, false negatives | `HardwareManager.cpp` | 192-211 |
| 10 | No error markers for failed Modbus registers — JSON has no key, impossible to distinguish offline vs unconfigured | `ProtocolHandlers.cpp` | 235-269 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 11 | `MqttManager::addLog()` race condition detailed — `logIndex`/`logCount` plain globals, `mqttLogs` vector can reallocate during read | `MqttManager.cpp` | 24-41 |
| 12 | BME280 pressure data not exposed — calibration parsed but never used | `ProtocolHandlers.cpp` | 384-403 |
| 13 | `LightBME280::readTemperature()` integer truncation — possible humidity accuracy degradation | `ProtocolHandlers.cpp` | 84-97 |
| 14 | No I2C bus recovery / stuck-bus handling | `ProtocolHandlers.cpp` | 12-19, 48-56 |
| 15 | `discoverSensors()` misidentifies devices by address only — no chip ID verification | `HardwareManager.cpp` | 201-209 |
| 16 | `reloadConfiguration()` holds `handlersMutex` for extended period — can block telemetry for seconds | `HardwareManager.cpp` | 69-183 |
| 17 | `latestTelemetryJson` updated without synchronization — partial reads possible | `HardwareManager.cpp` | 345-347 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 18 | `String` keys in `latestSensorValues` — heap fragmentation risk over days | `HardwareManager.cpp` | 25 |
| 19 | `node.begin()` called per register in batch scan — unnecessary overhead | `HardwareManager.cpp` | 513, 549 |
| 20 | OneWireHandler and SPIHandler return mock data — masks real sensor failures | `ProtocolHandlers.cpp` | 466, 501 |
| 21 | BME280 calibration read has no error checking — partial data produces garbage values | `ProtocolHandlers.cpp` | 58-82 |
| 22 | TelemetryTask pinned to Core 1 — may conflict with WiFi stack under heavy traffic | `HardwareManager.cpp` | 273 |
| 23 | Modbus flat key collision in `latestSensorValues` — same register name from different devices overwrites | `ProtocolHandlers.cpp` | 258-259 |
| 24 | `handlersMutex` initialized to NULL — `reloadConfiguration()` silent no-op if called before `init()` | `HardwareManager.cpp` | 22, 70 |

---

## 3. Security & Crypto Audit

**Files audited:**
- `src/core/CryptoCredential.h`
- `src/core/CryptoCredential.cpp`
- `src/protocols/WebConfigPortal.cpp`
- `include/Config.h`
- `src/core/Config.cpp`
- `src/core/ConfigManager.cpp`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | `CryptoCredential::init()` never called — AES key/IV remain all-zero, encryption is non-functional | `CryptoCredential.cpp` | 127 (never invoked) |
| 2 | Credential loading does NOT decrypt AES-GCM encrypted values — `loadConfig()` reads ciphertext as plaintext | `ConfigManager.cpp` | 74-81 |
| 3 | `credentials_encrypted` flag never set on save — exported configs contain undecryptable blobs | `WebConfigPortal.cpp` | 31-120 |
| 4 | Plaintext admin password logged to serial console on generation | `ConfigManager.cpp` | 96-97 |
| 5 | No TLS/HTTPS on captive portal — all credentials and tokens sniffable over WiFi | `WebConfigPortal.cpp` | 143-145 |
| 6 | Authentication bypass on root endpoint — `handleRoot()` serves UI without `checkAuthToken()` | `WebConfigPortal.cpp` | 196-209 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 7 | Weak key derivation — MAC address + static pepper, no salt, no iteration count | `CryptoCredential.cpp` | 10-28 |
| 8 | In-memory rate limiter resets on reboot — brute force can resume after every power cycle | `WebConfigPortal.cpp` | 22-28, 213-223 |
| 9 | AUTH_TOKEN has no expiration — stolen token valid indefinitely | `WebConfigPortal.cpp` | 131-138 |
| 10 | No persistent account lockout — 5 guesses every 30 seconds forever | `WebConfigPortal.cpp` | 243-258 |
| 11 | AUTH_TOKEN transmitted over plaintext HTTP — passive sniffing yields token | `WebConfigPortal.cpp` | 242 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 12 | Unbounded growth of rate limiter vector — no eviction or size limit | `WebConfigPortal.cpp` | 256-258 |
| 13 | No CSRF protection on config endpoints — forged requests possible | `WebConfigPortal.cpp` | all POST handlers |
| 14 | `millis()` wrap-around edge case in rate limiter — unpredictable behavior after 49 days | `WebConfigPortal.cpp` | 216 |
| 15 | Config import accepts raw JSON without schema validation | `WebConfigPortal.cpp` | 725-750 |
| 16 | OTA upload without size limit or integrity verification | `WebConfigPortal.cpp` | 647-671 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 17 | Dead code: `aes_iv` static member — derived but never used | `CryptoCredential.h`, `CryptoCredential.cpp` | 18, 25-27 |
| 18 | Per-operation key setup — `mbedtls_gcm_setkey()` on every encrypt/decrypt call | `CryptoCredential.cpp` | 63, 107 |
| 19 | Predictable default admin username (`admin`) | `ConfigManager.cpp` | 87-89 |
| 20 | Limited password entropy — 12 hex chars = ~48 bits | `ConfigManager.cpp` | 90-98 |
| 21 | `credentials_encrypted` flag not persisted — exported configs cannot be re-imported decrypted | `WebConfigPortal.cpp` | — |

**Positive observations:**
- AES-GCM uses proper random IV per encryption
- `saveFullConfig()` correctly excludes sensitive fields from GET responses
- `handleApiConfigExport()` strips sensitive fields before export
- `handleApiAccountPost()` invalidates AUTH_TOKEN after credential changes

---

## 4. WiFi & Network Audit

**Files audited:**
- `src/protocols/NetworkManager.cpp`
- `src/protocols/NetworkManager.h`
- `src/protocols/MqttManager.cpp`
- `src/protocols/MqttManager.h`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | `PubSubClient` accessed from multiple tasks without mutex — race condition crashes | `MqttManager.cpp` | 143-261 |
| 2 | `setInsecure()` in production path — TLS certificate validation completely disabled | `MqttManager.cpp` | 66 |
| 3 | `DiscoveryPeriodic` task leak on every MQTT reconnect — TCB/stack leaked per reconnection | `MqttManager.cpp` | 194-209 |
| 4 | Shared static log state without mutex — corrupted circular buffer, heap corruption | `MqttManager.cpp` | 15-42 |
| 5 | Heap fragmentation from per-message 16 KB `DynamicJsonDocument` in `mqttCallback` | `MqttManager.cpp` | 236 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 6 | `portalStarted` flag always true — AP loop never disabled after STA connect | `NetworkManager.cpp` | 30, 65-71 |
| 7 | `mqttClient` heap-allocated, never freed — minor leak per boot | `MqttManager.cpp` | 74, 78 |
| 8 | LWT published with QoS 0 — unreliable offline detection | `MqttManager.cpp` | 165, 170 |
| 9 | All tasks pinned to Core 0 — Core 0 starvation under load | `NetworkManager.cpp`, `MqttManager.cpp`, `TaskWatchdog.cpp` | 16, 94, 208, 18 |
| 10 | `DiscoveryPeriodic` has no watchdog heartbeat — hangs undetected | `MqttManager.cpp` | 194-209 |
| 11 | `WiFi.macAddress()` / `localIP()` called from multiple tasks — WiFi driver not thread-safe | `MqttManager.cpp` | 127, 155, 184 |
| 12 | `xTaskCreate` return value unchecked — silent failure if heap exhausted | `MqttManager.cpp` | 194 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 13 | Discovery payload QoS 0, no retain — module service may miss discovery | `MqttManager.cpp` | 134 |
| 14 | Client ID collision risk — duplicate NODE_ID causes broker to kick first client | `MqttManager.cpp` | 153 |
| 15 | Fixed retry/backoff in WiFi connect — no exponential backoff | `NetworkManager.cpp` | 46-62 |
| 16 | `publish()` return value ignored in `publishDiscovery()` — silent failures | `MqttManager.cpp` | 134 |
| 17 | No cert/key consistency validation — mismatched cert/key causes runtime TLS failure | `MqttManager.cpp` | 68-73 |
| 18 | `WiFi.disconnect(false)` before enterprise `begin` — stale enterprise credentials persist | `NetworkManager.cpp` | 38, 42 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 19 | Large stack sizes on constrained ESP32 — WiFiTask 8192, MqttTask 6144 | `NetworkManager.cpp`, `MqttManager.cpp` | 12, 90 |
| 20 | `Serial.print` in WiFi retry loop — timing skew | `NetworkManager.cpp` | 50 |

---

## 5. Watchdog & SystemMonitor Audit

**Files audited:**
- `src/core/TaskWatchdog.cpp`
- `src/core/TaskWatchdog.h`
- `src/core/SystemMonitor.cpp`
- `src/core/SystemMonitor.h`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | Watchdog is inactive — `TaskWatchdog::registerTask()` never called, `tasks` vector empty | `TaskWatchdog.cpp`, `main.cpp` | 82-84 |
| 2 | Mutex held during 1-second delay on timeout — all heartbeats blocked, cascading detection failure | `TaskWatchdog.cpp` | 71-80 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 3 | Task handle lost after restart — `restartFunc()` does not return new handle, watchdog loses tracking | `TaskWatchdog.cpp` | 64-70 |
| 4 | Critically low heap restart threshold — 10 KB is near minimum for FreeRTOS kernel | `SystemMonitor.cpp` | 31 |
| 5 | Heartbeat silently dropped under contention — 10 ms mutex timeout too short | `TaskWatchdog.cpp` | 39, 54 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 6 | Watchdog priority competes with network tasks — priority 2 same as WiFi/MQTT | `TaskWatchdog.cpp` | 16 |
| 7 | Unmonitored tasks — `SysMonitorTask`, `DiscoveryPeriodic` never registered | `TaskWatchdog.cpp`, `MqttManager.cpp` | — |
| 8 | `esp_task_wdt_reset()` calls are no-ops — hardware TWDT never initialized | `HardwareManager.cpp` | 13, 438, 552 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 9 | No self-monitoring of WatchdogTask — single point of failure | `TaskWatchdog.cpp` | — |
| 10 | `millis()` rollover — actually safe via unsigned subtraction, but undocumented | `TaskWatchdog.cpp` | 58 |
| 11 | Logging under critical low memory — `Logger::system()` may crash before heap check | `SystemMonitor.cpp` | 19-25 |

---

## 6. OTA & ConfigManager Audit

**Files audited:**
- `src/core/ConfigManager.cpp`
- `src/core/ConfigManager.h`
- `src/protocols/WebConfigPortal.cpp` (OTA handlers)
- `src/main.cpp` (boot sequence)

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | `CryptoCredential::init()` never called — zero-key encryption, all credentials trivially decryptable | `CryptoCredential.cpp` | 127 (never invoked) |
| 2 | `credentials_encrypted` flag never set on save — exported configs contain undecryptable blobs | `WebConfigPortal.cpp` | 31-120 |
| 3 | Boot health check logic broken — `boot_count` never exceeds 1, rollback unreachable | `main.cpp` | 15-54 |
| 4 | OTA upload has no size limit or integrity check — can brick device or install corrupted firmware | `WebConfigPortal.cpp` | 647-671 |
| 5 | No config backup before save — power loss during write = permanent config loss | `ConfigManager.cpp` | 247-258 |
| 6 | Rollback target partition unverified — can boot to corrupted partition | `main.cpp` | 38-47 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 7 | Config import has no validation — malformed config can break device | `WebConfigPortal.cpp` | 725-750 |
| 8 | OTA upload auth bypass risk — upload stream continues after auth failure | `WebConfigPortal.cpp` | 647-671 |
| 9 | Config load fails silently on large files (>4096 bytes) — falls back to defaults | `ConfigManager.cpp` | 36-49 |
| 10 | No fsync on config save — data corrupt on power loss | `ConfigManager.cpp` | 247-258 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 11 | Default credential generation uses low-entropy source — 12 hex chars = ~48 bits | `ConfigManager.cpp` | 90-98 |
| 12 | Rate limiter is RAM-only — survives reboot, brute force can resume | `WebConfigPortal.cpp` | 23-28 |
| 13 | No CSRF protection on config endpoints | `WebConfigPortal.cpp` | all POST handlers |
| 14 | Captive portal starts even when WiFi is configured — unnecessary attack surface | `WebConfigPortal.cpp` | 141-186 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 15 | No OTA version validation — can downgrade firmware | `WebConfigPortal.cpp` | 635 |
| 16 | No OTA rate limiting — authenticated attacker can trigger repeated updates | `WebConfigPortal.cpp` | 647-671 |

---

## 7. Boot Flow & Main Audit

**Files audited:**
- `src/main.cpp`
- `include/Config.h`
- `src/core/Config.cpp`
- `src/core/Logger.cpp` / `include/Logger.h`
- `src/core/HardwareManager.cpp`
- `src/core/ProtocolHandlers.cpp`

---

### CRITICAL

| # | Finding | File | Lines |
|---|---------|------|-------|
| 1 | `WiFi.macAddress()` invoked before WiFi initialization — NODE_ID becomes `00:00:00:00:00:00` | `ConfigManager.cpp` | 64; `main.cpp` | 56-86 |
| 2 | Generic GPIO interrupt handler triggers emergency shutdown unconditionally — false alarms | `HardwareManager.cpp` | 58-61 |
| 3 | No `nullptr` check after `new` in `ProtocolRegistry::createHandler()` — crash on OOM | `ProtocolHandler.cpp` | 16-18 |
| 4 | `MqttManager::init()` leaks `PubSubClient` and ignores task creation failure | `MqttManager.cpp` | 74-95 |

---

### HIGH

| # | Finding | File | Lines |
|---|---------|------|-------|
| 5 | Logger is not thread-safe — `Serial.printf` output interleaves under concurrent access | `Logger.cpp` | 3-11 |
| 6 | `TaskWatchdog::watchdogTask` calls `restartFunc()` while holding mutex — potential deadlock | `TaskWatchdog.cpp` | 54-79 |
| 7 | `TaskWatchdog` has no self-monitoring — single point of failure | `TaskWatchdog.cpp` | — |
| 8 | Heap threshold too low (10 KB) — may crash before restart executes | `SystemMonitor.cpp` | 31 |

---

### MEDIUM

| # | Finding | File | Lines |
|---|---------|------|-------|
| 9 | No failure propagation from `ConfigManager::init()` — `void` return, silent fallback to defaults | `ConfigManager.cpp` | 9-34 |
| 10 | `Config::TOPIC_*` globals depend on runtime state — fragile if init order changes | `Config.cpp` | 40-42 |
| 11 | `HardwareManager::init()` ignores `xSemaphoreCreateMutex()` failure — null dereference risk | `HardwareManager.cpp` | 228, 253 |
| 12 | `TaskWatchdog::init()` ignores task creation failure | `TaskWatchdog.cpp` | 11-19 |
| 13 | `SystemMonitor::init()` ignores task creation failure | `SystemMonitor.cpp` | 8-16 |
| 14 | `NetworkManager::init()` ignores task creation failure | `NetworkManager.cpp` | 9-17 |
| 15 | Debounce in ISR is non-atomic with flag update — conceptually unsafe on dual-core | `HardwareManager.cpp` | 49-56 |
| 16 | `lastInterruptTime` shared between two different ISRs — cross-pin debounce interference | `HardwareManager.cpp` | 34-35, 49-61 |
| 17 | Hardcoded I2C bus pins in `discoverSensors()` — ignores user configuration | `ProtocolHandlers.cpp` | 12-20; `HardwareManager.cpp` | 188 |
| 18 | `PIN_EMERGENCY_STOP` default 255 — `attachInterrupt(255)` may crash on some Arduino core versions | `Config.h` | 65; `Config.cpp` | 17 |
| 19 | `checkBootHealth` performs rollback inside `setup()` — no partition validation | `main.cpp` | 33-51 |
| 20 | `LittleFS.begin(true)` can auto-format and hang — 5-10 second boot delay | `ConfigManager.cpp` | 23 |
| 21 | `DynamicJsonDocument` in `loadConfig()` is 4096 bytes — silent failure on large configs | `ConfigManager.cpp` | 42 |
| 22 | `StaticJsonDocument` and `char` arrays in `reloadConfiguration()` use stack — overflow risk with many sensors | `HardwareManager.cpp` | 44-45, 105, 124, 142, 165 |
| 23 | `CryptoCredential::base64Encode` uses `calloc`/`free` repeatedly — heap fragmentation | `CryptoCredential.cpp` | 32-38 |

---

### LOW / INFO

| # | Finding | File | Lines |
|---|---------|------|-------|
| 24 | Fixed 256-byte log buffer may truncate important messages | `Logger.cpp` | 4-5 |
| 25 | Logger is not ISR-safe — `Serial.printf` inside ISR would crash | `Logger.cpp` | — |
| 26 | Default pin 2 for LED may conflict on some ESP32-S3 variants | `Config.cpp` | 16 |
| 27 | Blocking `delay(1000)` in `checkBootHealth()` during `setup()` — 1-second boot delay | `main.cpp` | 49 |

---

## 8. Consolidated Severity Matrix

| Domain | CRITICAL | HIGH | MEDIUM | LOW | Total |
|--------|----------|------|--------|-----|-------|
| Web Config Portal | 8 | 10 | 9 | 7 | 34 |
| Sensor & Modbus | 5 | 5 | 7 | 5 | 22 |
| Security & Crypto | 6 | 5 | 4 | 5 | 20 |
| WiFi & Network | 5 | 7 | 6 | 2 | 20 |
| Watchdog & SystemMonitor | 2 | 3 | 3 | 3 | 11 |
| OTA & ConfigManager | 6 | 4 | 4 | 2 | 16 |
| Boot Flow & Main | 4 | 5 | 14 | 4 | 27 |
| **Total** | **36** | **39** | **47** | **28** | **150** |

---

## 9. Recommended Remediation Order

### Phase 1 — Immediate (CRITICAL, Week 1)

| Priority | Action | Affected Files |
|----------|--------|----------------|
| P0-1 | Call `CryptoCredential::init()` in `setup()` before `ConfigManager::init()` | `main.cpp` |
| P0-2 | Add `CryptoCredential::decrypt()` in `ConfigManager::loadConfig()` for all encrypted fields | `ConfigManager.cpp` |
| P0-3 | Set `credentials_encrypted = true` in `saveFullConfig()` | `WebConfigPortal.cpp` |
| P0-4 | Register all tasks with `TaskWatchdog::registerTask()` | `main.cpp`, `NetworkManager.cpp`, `MqttManager.cpp`, `HardwareManager.cpp`, `SystemMonitor.cpp` |
| P0-5 | Fix GPIO ISR flag bug — split `emergencyShutdownTriggered` and `gpioInterruptFired` | `HardwareManager.cpp` |
| P0-6 | Add mutex around all `PubSubClient` calls | `MqttManager.cpp` |
| P0-7 | Remove `setInsecure()` or gate behind `#ifdef DEBUG` | `MqttManager.cpp` |
| P0-8 | Fix `DiscoveryPeriodic` task leak — create once in `init()`, not on reconnect | `MqttManager.cpp` |
| P0-9 | Fix WiFi MAC fallback — move NODE_ID derivation after WiFi connects | `ConfigManager.cpp`, `main.cpp` |
| P0-10 | Add `nullptr` checks after all `new` allocations | `ProtocolHandler.cpp`, `MqttManager.cpp` |

### Phase 2 — Short-term (HIGH, Week 2-3)

| Priority | Action | Affected Files |
|----------|--------|----------------|
| P1-1 | Escape all user-controlled data before `innerHTML` in `script.js` | `data/script.js` |
| P1-2 | Add backend input validation to all POST handlers | `WebConfigPortal.cpp` |
| P1-3 | Bound `startScanReg()` loop with hard max (e.g., 100 registers) | `data/script.js` |
| P1-4 | Replace per-message 16 KB `DynamicJsonDocument` with static buffer | `MqttManager.cpp` |
| P1-5 | Add mutex around `MqttManager::addLog()` shared state | `MqttManager.cpp` |
| P1-6 | Fix strict aliasing violation in FLOAT32 parsing — use `memcpy` | `ProtocolHandlers.cpp` |
| P1-7 | Add mutex protection for `latestSensorValues`, `outputStates`, `activeOutputHandlers` | `HardwareManager.cpp` |
| P1-8 | Change LWT QoS to 1, discovery publish to QoS 1 + retain | `MqttManager.cpp` |
| P1-9 | Raise heap threshold to 30-50 KB in `SystemMonitor` | `SystemMonitor.cpp` |
| P1-10 | Implement config backup (`config.json.bak`) and atomic write | `ConfigManager.cpp` |
| P1-11 | Add firmware size limit and SHA256 verification to OTA upload | `WebConfigPortal.cpp` |
| P1-12 | Move `portalStarted` logic to proper state machine with STA-connect timeout | `NetworkManager.cpp` |

### Phase 3 — Medium-term (MEDIUM, Week 4+)

| Priority | Action | Affected Files |
|----------|--------|----------------|
| P2-1 | Add CSRF tokens to all state-changing POST endpoints | `WebConfigPortal.cpp` |
| P2-2 | Validate imported config against schema before saving | `WebConfigPortal.cpp` |
| P2-3 | Add per-device random salt + PBKDF2/Argon2 for key derivation | `CryptoCredential.cpp` |
| P2-4 | Persist login attempts and block timers in Preferences/NVS | `WebConfigPortal.cpp` |
| P2-5 | Add AUTH_TOKEN TTL and automatic rotation | `WebConfigPortal.cpp` |
| P2-6 | Implement exponential backoff for WiFi reconnection | `NetworkManager.cpp` |
| P2-7 | Add I2C bus recovery / stuck-bus handling | `ProtocolHandlers.cpp` |
| P2-8 | Add byte-order configuration to `ModbusRegister` | `Config.h`, `ProtocolHandlers.cpp` |
| P2-9 | Validate `reg.length` matches `data_type` requirements | `ProtocolHandlers.cpp` |
| P2-10 | Add `file.flush()` / `fsync` in `saveConfig()` | `ConfigManager.cpp` |

### Phase 4 — Long-term (LOW, Ongoing)

| Priority | Action | Affected Files |
|----------|--------|----------------|
| P3-1 | Clean up dead `aes_iv` code or document intent | `CryptoCredential.h`, `CryptoCredential.cpp` |
| P3-2 | Increase generated password entropy to >= 80 bits | `ConfigManager.cpp` |
| P3-3 | Add OTA version validation — reject downgrades | `WebConfigPortal.cpp` |
| P3-4 | Add OTA rate limiting with cooldown period | `WebConfigPortal.cpp` |
| P3-5 | Remove OneWire/SPI mock handlers or make them return `offline` | `ProtocolHandlers.cpp` |
| P3-6 | Implement BME280 pressure reading or remove dead calibration | `ProtocolHandlers.cpp` |
| P3-7 | Add ISR-safe logging guard | `Logger.cpp` |
| P3-8 | Document `millis()` rollover safety in watchdog | `TaskWatchdog.cpp` |

---

## Appendix: Cross-Cutting Concerns

### Thread Safety Summary

| Shared Resource | Protected? | Location |
|-----------------|-----------|----------|
| `PubSubClient` instance | ❌ No | `MqttManager.cpp` |
| `MqttManager::addLog()` buffers | ❌ No | `MqttManager.cpp` |
| `latestSensorValues` map | ❌ No | `HardwareManager.cpp` |
| `outputStates` map | ❌ No | `HardwareManager.cpp` |
| `activeOutputHandlers` map | ❌ No | `HardwareManager.cpp` |
| `handlersMutex` | ✅ Yes | `HardwareManager.cpp` |
| `modbusMutex` | ✅ Yes | `HardwareManager.cpp` |
| `TaskWatchdog::mutex` | ✅ Yes | `TaskWatchdog.cpp` |
| `loginAttempts` vector | ❌ No | `WebConfigPortal.cpp` |
| `Config::*` globals | ❌ No | `Config.cpp` |

### Memory Safety Summary

| Issue | Severity | Impact |
|-------|----------|--------|
| `new` without `nullptr` check | CRITICAL | Hard fault on OOM |
| `DiscoveryPeriodic` task leak | CRITICAL | Crash after N reconnects |
| 16 KB `DynamicJsonDocument` per MQTT message | HIGH | Heap fragmentation |
| `std::vector<String>` growth/shrink | HIGH | Heap fragmentation |
| `String` keys in `latestSensorValues` | MEDIUM | Long-term fragmentation |
| `StaticJsonDocument` on stack in loops | MEDIUM | Stack overflow risk |
| `calloc`/`free` in `base64Encode()` | MEDIUM | Fragmentation under load |

### Authentication & Authorization Summary

| Issue | Severity | Impact |
|-------|----------|--------|
| Plaintext password storage | CRITICAL | Credential theft from binary/FS |
| No TLS on captive portal | CRITICAL | Credentials sniffable over WiFi |
| Auth bypass on root endpoint | CRITICAL | Unauthenticated UI access |
| `setInsecure()` in production | CRITICAL | MITM attacks possible |
| Weak key derivation | HIGH | Offline credential decryption |
| No token expiration | HIGH | Stolen token valid forever |
| No persistent lockout | HIGH | Unlimited brute force |
| RAM-only rate limiter | MEDIUM | Resets on reboot |

---

*End of audit report. No files were modified during this analysis.*
