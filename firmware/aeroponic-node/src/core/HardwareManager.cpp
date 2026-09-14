#include "HardwareManager.h"
#include "TaskWatchdog.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include "../protocols/MqttManager.h"
#include "../protocols/NetworkManager.h"
#include "ProtocolHandler.h"
#include "ProtocolHandlers.h"
#include <ArduinoJson.h>
#include <WiFi.h>
#include <map>
#include <ModbusMaster.h>
#include "esp_task_wdt.h"

namespace HardwareManager {

    ModbusMaster node;
    uint32_t currentBaud = 0;
    volatile bool scanCancelRequested = false;
    
    SemaphoreHandle_t modbusMutex;
    SemaphoreHandle_t handlersMutex = NULL;
    TaskHandle_t telemetryTaskHandle = NULL;
    
    std::map<String, float> latestSensorValues;
    String latestTelemetryJson = "{}";
    std::vector<ProtocolHandler*> activeHandlers;
    std::map<String, ProtocolHandler*> activeOutputHandlers;   // name -> actuator handler
    
    // State terakhir output
    std::map<String, int> outputStates;
    
    // Flag interrupt untuk emergency shutdown
    volatile bool emergencyShutdownTriggered = false;
    volatile unsigned long lastInterruptTime = 0;
    
    // Connection stats
    struct {
        unsigned long lastMqttConnected = 0;
        int publishCount = 0;
    } stats;
    
    // Pre-allocated static buffers (GAP #9 fix)
    static StaticJsonDocument<8192> doc;
    static char jsonBuffer[8192];

    // ==================== INTERRUPT HANDLER ====================
    // GAP #11: Interrupt untuk input kritis
    void IRAM_ATTR emergencyInterruptHandler() {
        unsigned long now = millis();
        // Debounce 200ms
        if (now - lastInterruptTime > 200) {
            emergencyShutdownTriggered = true;
            lastInterruptTime = now;
        }
    }

    void IRAM_ATTR gpioInterruptHandler() {
        // Generic interrupt handler — set flag, actual processing in telemetryTask
        emergencyShutdownTriggered = true;
    }

    // ==================== SCAN CANCEL ====================
    void requestScanCancel() {
        scanCancelRequested = true;
    }

    // ==================== RELOAD CONFIGURATION ====================
    void reloadConfiguration() {
        if (!handlersMutex) return;
        if (xSemaphoreTake(handlersMutex, portMAX_DELAY) == pdTRUE) {
            Logger::hardware("Reloading Hardware Handlers (Hot-Swap)...");

            // Delete old handlers
            for (auto h : activeHandlers) {
                delete h;
            }
            activeHandlers.clear();

            // Delete old output (actuator) handlers
            for (auto& kv : activeOutputHandlers) {
                delete kv.second;
            }
            activeOutputHandlers.clear();
            
            // Re-initialize GPIO pin modes for legacy inputs/outputs
            for (const auto& hw : Config::HardwareInputs) {
                uint8_t mode = INPUT;
                if (hw.pull == "UP") mode = INPUT_PULLUP;
                else if (hw.pull == "DOWN") mode = INPUT_PULLDOWN;
                pinMode(hw.pin, mode);

                if (hw.interrupt != "NONE" && hw.interrupt.length() > 0) {
                    detachInterrupt(digitalPinToInterrupt(hw.pin));
                    int intMode = LOW;
                    if (hw.interrupt == "RISING") intMode = RISING;
                    else if (hw.interrupt == "FALLING") intMode = FALLING;
                    else if (hw.interrupt == "CHANGE") intMode = CHANGE;
                    attachInterrupt(digitalPinToInterrupt(hw.pin), gpioInterruptHandler, intMode);
                }
            }

            // Create handlers for outputs (actuator) via ProtocolRegistry
            for (const auto& hw : Config::HardwareOutputs) {
                StaticJsonDocument<256> cdoc;
                JsonObject obj = cdoc.to<JsonObject>();
                obj["pin"] = hw.pin;
                obj["type"] = hw.type;
                obj["name"] = hw.name;
                obj["protocol"] = hw.protocol;
                ProtocolHandler* h = ProtocolRegistry::createHandler(hw.protocol, obj);
                if (h) {
                    activeOutputHandlers[hw.name] = h;
                    int oldVal = outputStates.count(hw.name) ? outputStates[hw.name] : 0;
                    h->write(oldVal);
                    Logger::hardware("Registered Output: %s (Protocol: %s)", hw.name.c_str(), hw.protocol.c_str());
                } else {
                    Logger::hardware("Failed to create output handler for: %s (Protocol: %s)", hw.name.c_str(), hw.protocol.c_str());
                }
            }

            // Create handlers for legacy inputs
            for (const auto& hw : Config::HardwareInputs) {
                StaticJsonDocument<512> cdoc;
                JsonObject obj = cdoc.to<JsonObject>();
                obj["pin"] = hw.pin;
                obj["type"] = hw.type;
                obj["pull"] = hw.pull;
                obj["name"] = hw.name;
                obj["invert"] = hw.invert;
                obj["debounce_ms"] = hw.debounce_ms;
                obj["interrupt"] = hw.interrupt;
                obj["analog_min"] = hw.analog_min;
                obj["analog_max"] = hw.analog_max;
                
                ProtocolHandler* h = ProtocolRegistry::createHandler("GPIO", obj);
                if (h) activeHandlers.push_back(h);
            }

            // Create handlers for legacy modbus
            for (const auto& ms : Config::HardwareModbus) {
                StaticJsonDocument<2048> cdoc;
                JsonObject obj = cdoc.to<JsonObject>();
                obj["name"] = ms.name;
                obj["slave_id"] = ms.slave_id;
                obj["baudrate"] = ms.baudrate;
                JsonArray regs = obj.createNestedArray("registers");
                for (const auto& r : ms.registers) {
                    JsonObject reg = regs.createNestedObject();
                    reg["address"] = r.address;
                    reg["name"] = r.name;
                    reg["multiplier"] = r.multiplier;
                    reg["type"] = r.type;
                    reg["length"] = r.length;
                    reg["data_type"] = r.data_type;
                }
                
                ProtocolHandler* h = ProtocolRegistry::createHandler("MODBUS", obj);
                if (h) activeHandlers.push_back(h);
            }

            // Create handlers for new generic sensors
            for (const auto& s : Config::HardwareSensors) {
                StaticJsonDocument<1024> cdoc;
                JsonObject obj = cdoc.to<JsonObject>();
                obj["name"] = s.name;
                obj["protocol"] = s.protocol;
                for (const auto& pair : s.params) {
                    obj[pair.first] = pair.second;
                }
                
                ProtocolHandler* h = ProtocolRegistry::createHandler(s.protocol, obj);
                if (h) {
                    activeHandlers.push_back(h);
                    Logger::hardware("Registered Sensor: %s (Protocol: %s)", s.name.c_str(), s.protocol.c_str());
                } else {
                    Logger::hardware("Failed to create handler for Sensor: %s (Protocol: %s)", s.name.c_str(), s.protocol.c_str());
                }
            }

            xSemaphoreGive(handlersMutex);
            Logger::hardware("Hardware Handlers Reloaded Successfully.");
        }
    }

    // ==================== DISCOVER SENSORS ====================
    String discoverSensors() {
        initI2C(21, 22);
        StaticJsonDocument<1024> ddoc;
        JsonArray i2cDevices = ddoc.createNestedArray("i2c");
        
        for (uint8_t address = 1; address < 127; address++) {
            Wire.beginTransmission(address);
            byte error = Wire.endTransmission();
            
            if (error == 0) {
                JsonObject dev = i2cDevices.createNestedObject();
                char addrStr[6];
                sprintf(addrStr, "0x%02X", address);
                dev["address"] = String(addrStr);
                if (address == 0x5C) {
                    dev["detected_type"] = "DHT12";
                } else if (address == 0x76 || address == 0x77) {
                    dev["detected_type"] = "BME280";
                } else if (address == 0x40 || address == 0x41 || address == 0x44 || address == 0x45) {
                    dev["detected_type"] = "INA219";
                } else {
                    dev["detected_type"] = "UNKNOWN_I2C";
                }
            }
        }
        
        String result;
        serializeJson(ddoc, result);
        return result;
    }

    // ==================== GET LATEST TELEMETRY JSON ====================
    String getLatestTelemetryJson() {
        return latestTelemetryJson;
    }

    // ==================== INIT ====================
    void init() {
        Logger::hardware("Initializing Universal Hardware Pins...");
        
        // Modbus Setup
        modbusMutex = xSemaphoreCreateMutex();
        currentBaud = 0;
        
        if (Config::PIN_RS485_DE != 255) {
            pinMode(Config::PIN_RS485_DE, OUTPUT);
            digitalWrite(Config::PIN_RS485_DE, LOW);
            node.preTransmission([]() { digitalWrite(Config::PIN_RS485_DE, HIGH); });
            node.postTransmission([]() { digitalWrite(Config::PIN_RS485_DE, LOW); });
        }

        // LED indikator (GAP #18)
        if (Config::PIN_LED_INDICATOR != 255) {
            pinMode(Config::PIN_LED_INDICATOR, OUTPUT);
            digitalWrite(Config::PIN_LED_INDICATOR, LOW);
        }

        // Emergency stop pin (GAP #11)
        if (Config::PIN_EMERGENCY_STOP != 255) {
            pinMode(Config::PIN_EMERGENCY_STOP, INPUT_PULLUP);
            attachInterrupt(digitalPinToInterrupt(Config::PIN_EMERGENCY_STOP),
                            emergencyInterruptHandler, FALLING);
            Logger::hardware("Emergency stop interrupt attached");
        }

        // Create Handlers Mutex
        handlersMutex = xSemaphoreCreateMutex();

        // Register protocol creators in ProtocolRegistry
        ProtocolRegistry::registerProtocol("GPIO", []() -> ProtocolHandler* { return new GPIOInputHandler(); });
        ProtocolRegistry::registerProtocol("MODBUS", []() -> ProtocolHandler* { return new ModbusHandler(); });
        ProtocolRegistry::registerProtocol("I2C", []() -> ProtocolHandler* { return new I2CHandler(); });
        ProtocolRegistry::registerProtocol("1-WIRE", []() -> ProtocolHandler* { return new OneWireHandler(); });
        ProtocolRegistry::registerProtocol("SPI", []() -> ProtocolHandler* { return new SPIHandler(); });
        ProtocolRegistry::registerProtocol("GPIO_OUT", []() -> ProtocolHandler* { return new GpioOutputHandler(); });

        // Load handlers initially
        reloadConfiguration();

        xTaskCreatePinnedToCore(
            telemetryTask, 
            "TelemetryTask", 
            8192, 
            NULL, 
            1, 
            &telemetryTaskHandle, 
            1
        );
    }

    // ==================== TELEMETRY TASK ====================
    void telemetryTask(void* parameter) {
        uint32_t delayTime = Config::MQTT_PUBLISH_INTERVAL > 0 ? Config::MQTT_PUBLISH_INTERVAL : 5000;
        
        while (true) {
            TaskWatchdog::heartbeat("TelemetryTask"); // GAP #5
            
            // GAP #11: Cek flag interrupt untuk emergency shutdown
            if (emergencyShutdownTriggered) {
                emergencyShutdownTriggered = false;
                Logger::emergency("Shutdown triggered by interrupt!");
                
                for (const auto& hw : Config::HardwareOutputs) {
                    setOutput(hw.name, 0);
                }
                
                // Kirim alert via MQTT
                String alertPayload = "{\"alert\":\"EMERGENCY_SHUTDOWN\",\"node_id\":\"" 
                    + Config::NODE_ID + "\",\"uptime_s\":" + String(millis() / 1000) + "}";
                if (MqttManager::isConnected()) {
                    MqttManager::publish(Config::TOPIC_ALERT, alertPayload);
                }
            }
            
            doc.clear();
            
            // System Info
            doc["node_id"] = Config::NODE_ID;
            doc["fw_version"] = Config::FW_VERSION;
            
            // Network Info
            JsonObject network = doc.createNestedObject("network");
            network["ssid"] = Config::WIFI_SSID;
            network["ip_address"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "Not Connected";
            network["wifi_rssi"] = WiFi.RSSI();
            
            // Device Hardware Info
            JsonObject devInfo = doc.createNestedObject("device_info");
            devInfo["uptime_s"] = millis() / 1000;
            devInfo["cpu_freq_mhz"] = ESP.getCpuFreqMHz();
            devInfo["free_heap_kb"] = ESP.getFreeHeap() / 1024;
            devInfo["flash_size_mb"] = ESP.getFlashChipSize() / (1024 * 1024);
            
            // Connection stats (GAP #18)
            JsonObject connStats = doc.createNestedObject("connection_stats");
            connStats["mqtt_connected"] = MqttManager::isConnected();
            connStats["uptime_s"] = millis() / 1000;
            
            // Sensor Telemetry
            JsonObject telemetry = doc.createNestedObject("telemetry");
            
            // Outputs telemetry
            JsonObject outputsObj = telemetry.createNestedObject("outputs");
            for (const auto& hw : Config::HardwareOutputs) {
                outputsObj[hw.name] = outputStates[hw.name];
            }
            
            // Run all dynamic protocol handlers
            if (handlersMutex && xSemaphoreTake(handlersMutex, pdMS_TO_TICKS(4000)) == pdTRUE) {
                for (auto handler : activeHandlers) {
                    handler->read(telemetry);
                }
                xSemaphoreGive(handlersMutex);
            }
            
            // GAP #7: Edge control removed - local control rules are no longer supported
            
            // Publish via MQTT
            memset(jsonBuffer, 0, sizeof(jsonBuffer));
            serializeJson(doc, jsonBuffer, sizeof(jsonBuffer) - 1);
            latestTelemetryJson = String(jsonBuffer); // Save copy for local API / REST fallback
            
            if (MqttManager::isConnected()) {
                MqttManager::publish(Config::TOPIC_TELEMETRY, latestTelemetryJson);
                stats.lastMqttConnected = millis();
                stats.publishCount++;
            }
            
            String sysLog = "[";
            sysLog += String(millis() / 1000);
            sysLog += "s] Sys: heap=";
            sysLog += String(ESP.getFreeHeap() / 1024);
            sysLog += "KB rssi=";
            sysLog += String(WiFi.RSSI());
            sysLog += "dBm mqtt=";
            sysLog += MqttManager::isConnected() ? "ON" : "OFF";
            MqttManager::addLog(sysLog.c_str());
            
            if (!latestSensorValues.empty()) {
                String sensorLog = "[";
                sensorLog += String(millis() / 1000);
                sensorLog += "s] Sensors: ";
                int count = 0;
                for (auto& kv : latestSensorValues) {
                    if (count >= 2) break;
                    if (count > 0) sensorLog += ", ";
                    sensorLog += kv.first;
                    sensorLog += "=";
                    sensorLog += String(kv.second, 1);
                    count++;
                }
                if (latestSensorValues.size() > 2) {
                    sensorLog += " +";
                    sensorLog += String(latestSensorValues.size() - 2);
                }
                MqttManager::addLog(sensorLog.c_str());
            }
            
            // LED indikator (GAP #18)
            if (Config::PIN_LED_INDICATOR != 255) {
                digitalWrite(Config::PIN_LED_INDICATOR, MqttManager::isConnected() ? HIGH : LOW);
            }
            
            ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(delayTime));
        }
    }
    
    // ==================== SET OUTPUT ====================
    bool setOutput(String targetName, int value) {
        auto it = activeOutputHandlers.find(targetName);
        if (it != activeOutputHandlers.end()) {
            it->second->write(value);
            outputStates[targetName] = value;
            Logger::actuator("%s -> %d (via %s handler)",
                targetName.c_str(), value, it->second->getProtocolName().c_str());
            if (telemetryTaskHandle != NULL) {
                xTaskNotifyGive(telemetryTaskHandle);
            }
            return true;
        }
        Logger::actuator("Target '%s' not found in Output Configuration.", targetName.c_str());
        return false;
    }

    // ==================== MODBUS SCAN (GAP #6: dengan watchdog feed) ====================
    String runFullScanSync(const std::vector<uint32_t>& bauds) {
        String scanResultsJson = "[";
        bool firstFound = true;
        scanCancelRequested = false;
        
        if (xSemaphoreTake(modbusMutex, portMAX_DELAY) == pdTRUE) {
            for (size_t bi = 0; bi < bauds.size(); bi++) {
                uint32_t baud = bauds[bi];
                Serial2.end();
                vTaskDelay(100 / portTICK_PERIOD_MS);
                Serial2.begin(baud, Config::parityToSerialConfig(Config::PARITY), Config::PIN_RS485_RX, Config::PIN_RS485_TX);
                vTaskDelay(300 / portTICK_PERIOD_MS);
                currentBaud = baud;
                
                Logger::modbus("================================");
                Logger::modbus("STARTING MODBUS SCAN ON %d BAUD", baud);
                Logger::modbus("================================");
                
                for (uint16_t id = 1; id <= 247; id++) {
                    if (scanCancelRequested) {
                        Logger::modbus("SCAN CANCELLED BY USER");
                        xSemaphoreGive(modbusMutex);
                        scanResultsJson += "]";
                        scanCancelRequested = false;
                        return scanResultsJson;
                    }
                    esp_task_wdt_reset();
                    TaskWatchdog::heartbeat("TelemetryTask");
                    
                    bool found = false;
                    for (int attempt = 0; attempt < 2 && !found; attempt++) {
                        if (attempt > 0) {
                            Logger::modbus("Retrying ID %d ...", id);
                            vTaskDelay(100 / portTICK_PERIOD_MS);
                        }
                        for (uint16_t reg = 0; reg <= 2 && !found; reg++) {
                            node.begin(id, Serial2);
                            uint8_t result = node.readHoldingRegisters(reg, 1);
                            if (result == node.ku8MBSuccess) {
                                Logger::modbus("FOUND (HOLDING reg %d)", reg);
                                found = true;
                                break;
                            } else if (result >= node.ku8MBIllegalFunction && result <= node.ku8MBSlaveDeviceFailure) {
                                Logger::modbus("FOUND (Exception on HOLDING reg %d)", reg);
                                found = true;
                                break;
                            }
                            vTaskDelay(10 / portTICK_PERIOD_MS);
                        }
                        if (found) break;
                        for (uint16_t reg = 0; reg <= 2 && !found; reg++) {
                            node.begin(id, Serial2);
                            uint8_t result = node.readInputRegisters(reg, 1);
                            if (result == node.ku8MBSuccess) {
                                Logger::modbus("FOUND (INPUT reg %d)", reg);
                                found = true;
                                break;
                            } else if (result >= node.ku8MBIllegalFunction && result <= node.ku8MBSlaveDeviceFailure) {
                                Logger::modbus("FOUND (Exception on INPUT reg %d)", reg);
                                found = true;
                                break;
                            }
                            vTaskDelay(10 / portTICK_PERIOD_MS);
                        }
                    }
                    
                    if (found) {
                        if (!firstFound) scanResultsJson += ",";
                        scanResultsJson += "{\"id\":";
                        scanResultsJson += String(id);
                        scanResultsJson += ",\"baud\":";
                        scanResultsJson += String(baud);
                        scanResultsJson += "}";
                        firstFound = false;
                    } else {
                        Logger::modbus("No Response (ID %d)", id);
                    }
                    vTaskDelay(50 / portTICK_PERIOD_MS);
                }
                Logger::modbus("================================");
                Logger::modbus("SCAN COMPLETE FOR %d BAUD", baud);
                Logger::modbus("================================");
            }
            xSemaphoreGive(modbusMutex);
        }
        
        scanResultsJson += "]";
        scanCancelRequested = false;
        return scanResultsJson;
    }
    
    uint16_t scanModbusReg(uint8_t id, uint32_t baud, uint16_t reg, String type, uint8_t length, bool& success) {
        if (xSemaphoreTake(modbusMutex, pdMS_TO_TICKS(5000)) == pdTRUE) {
            if (currentBaud != baud) {
            Serial2.end();
            vTaskDelay(100 / portTICK_PERIOD_MS);
            Serial2.begin(baud, Config::parityToSerialConfig(Config::PARITY), Config::PIN_RS485_RX, Config::PIN_RS485_TX);
            vTaskDelay(300 / portTICK_PERIOD_MS);
            currentBaud = baud;
            }
            Logger::modbus("Scanning %s Register %d (length=%d) on ID %d (Baud: %d)...", type.c_str(), reg, length, id, baud);
            node.begin(id, Serial2);
            uint8_t result;
            if (type == "INPUT") {
                result = node.readInputRegisters(reg, length);
            } else {
                result = node.readHoldingRegisters(reg, length);
            }
            uint16_t val = 0;
            if (result == node.ku8MBSuccess) {
                success = true;
                val = node.getResponseBuffer(0);
                Logger::modbus("SUCCESS! Value = %d", val);
            } else {
                success = false;
                Logger::modbus("FAILED (Error Code: %d)", result);
            }
            xSemaphoreGive(modbusMutex);
            return val;
        }
        Logger::modbus("FAILED (Could not take Modbus Mutex)");
        success = false;
        return 0;
    }
    
    String scanModbusRegBatch(uint8_t id, uint32_t baud, uint16_t startReg, uint16_t endReg, String type, uint8_t length) {
        String resultJson = "[";
        bool first = true;
        
        if (xSemaphoreTake(modbusMutex, pdMS_TO_TICKS(5000)) == pdTRUE) {
            if (currentBaud != baud) {
                Serial2.end();
                vTaskDelay(100 / portTICK_PERIOD_MS);
                Serial2.begin(baud, Config::parityToSerialConfig(Config::PARITY), Config::PIN_RS485_RX, Config::PIN_RS485_TX);
                vTaskDelay(300 / portTICK_PERIOD_MS);
                currentBaud = baud;
            }
            node.begin(id, Serial2);
            
            for (uint16_t reg = startReg; reg <= endReg; reg++) {
                esp_task_wdt_reset();
                TaskWatchdog::heartbeat("TelemetryTask");
                
                bool success = false;
                uint16_t val = 0;
                uint8_t result;
                if (type == "INPUT") {
                    result = node.readInputRegisters(reg, length);
                } else {
                    result = node.readHoldingRegisters(reg, length);
                }
                if (result == node.ku8MBSuccess) {
                    success = true;
                    val = node.getResponseBuffer(0);
                    Logger::modbus("Batch Reg %d = %d", reg, val);
                } else {
                    Logger::modbus("Batch Reg %d FAILED (Error %d)", reg, result);
                }
                
                if (!first) resultJson += ",";
                resultJson += "{\"reg\":" + String(reg) + ",\"success\":" + (success ? "true" : "false") + ",\"val\":" + String(val) + "}";
                first = false;
                vTaskDelay(20 / portTICK_PERIOD_MS);
            }
            xSemaphoreGive(modbusMutex);
        }
        resultJson += "]";
        return resultJson;
    }
}