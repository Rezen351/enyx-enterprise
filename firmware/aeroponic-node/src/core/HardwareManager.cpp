#include "HardwareManager.h"
#include "TaskWatchdog.h"
#include "../../include/Config.h"
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
    
    SemaphoreHandle_t modbusMutex;
    SemaphoreHandle_t handlersMutex = NULL;
    TaskHandle_t telemetryTaskHandle = NULL;
    
    std::map<String, float> latestSensorValues;
    String latestTelemetryJson = "{}";
    std::vector<ProtocolHandler*> activeHandlers;
    
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

    // ==================== LOCAL CONTROL EVALUATION ====================
    // GAP #7: Edge control & histeresis
    float getSensorValueByName(const String& name) {
        auto it = latestSensorValues.find(name);
        if (it != latestSensorValues.end()) {
            return it->second;
        }
        return NAN;
    }

    void evaluateLocalControl() {
        for (const auto& rule : Config::LocalControlRules) {
            if (!rule.enabled) continue;
            
            float sensorValue = getSensorValueByName(rule.inputSensor);
            if (isnan(sensorValue)) continue;
            
            int currentOutput = outputStates[rule.outputTarget];
            
            if (currentOutput == 0 && sensorValue > rule.thresholdHigh) {
                setOutput(rule.outputTarget, 1);
                Serial.printf("LOCAL CONTROL: %s -> %s ON (%.1f > %.1f)\n",
                    rule.name.c_str(), rule.outputTarget.c_str(),
                    sensorValue, rule.thresholdHigh);
            }
            else if (currentOutput == 1 && sensorValue < rule.thresholdLow) {
                setOutput(rule.outputTarget, 0);
                Serial.printf("LOCAL CONTROL: %s -> %s OFF (%.1f < %.1f)\n",
                    rule.name.c_str(), rule.outputTarget.c_str(),
                    sensorValue, rule.thresholdLow);
            }
        }
    }

    // ==================== RELOAD CONFIGURATION ====================
    void reloadConfiguration() {
        if (!handlersMutex) return;
        if (xSemaphoreTake(handlersMutex, portMAX_DELAY) == pdTRUE) {
            Serial.println("Reloading Hardware Handlers (Hot-Swap)...");

            // Delete old handlers
            for (auto h : activeHandlers) {
                delete h;
            }
            activeHandlers.clear();
            
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

            for (const auto& hw : Config::HardwareOutputs) {
                pinMode(hw.pin, OUTPUT);
                if (hw.type == "PWM") {
                    int oldVal = outputStates.count(hw.name) ? outputStates[hw.name] : 0;
                    analogWrite(hw.pin, oldVal);
                } else {
                    int oldVal = outputStates.count(hw.name) ? outputStates[hw.name] : 0;
                    digitalWrite(hw.pin, oldVal ? HIGH : LOW);
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
                    Serial.printf("Registered Sensor: %s (Protocol: %s)\n", s.name.c_str(), s.protocol.c_str());
                } else {
                    Serial.printf("Failed to create handler for Sensor: %s (Protocol: %s)\n", s.name.c_str(), s.protocol.c_str());
                }
            }

            xSemaphoreGive(handlersMutex);
            Serial.println("Hardware Handlers Reloaded Successfully.");
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
        Serial.println("Initializing Universal Hardware Pins...");
        
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
            Serial.println("Emergency stop interrupt attached");
        }

        // Create Handlers Mutex
        handlersMutex = xSemaphoreCreateMutex();

        // Register protocol creators in ProtocolRegistry
        ProtocolRegistry::registerProtocol("GPIO", []() -> ProtocolHandler* { return new GPIOInputHandler(); });
        ProtocolRegistry::registerProtocol("MODBUS", []() -> ProtocolHandler* { return new ModbusHandler(); });
        ProtocolRegistry::registerProtocol("I2C", []() -> ProtocolHandler* { return new I2CHandler(); });
        ProtocolRegistry::registerProtocol("1-WIRE", []() -> ProtocolHandler* { return new OneWireHandler(); });
        ProtocolRegistry::registerProtocol("SPI", []() -> ProtocolHandler* { return new SPIHandler(); });

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
                Serial.println("EMERGENCY: Shutdown triggered by interrupt!");
                
                for (const auto& hw : Config::HardwareOutputs) {
                    if (hw.type == "PWM") {
                        analogWrite(hw.pin, 0);
                    } else {
                        digitalWrite(hw.pin, LOW);
                    }
                    outputStates[hw.name] = 0;
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
            
            // GAP #7: Evaluate local control rules
            evaluateLocalControl();
            
            // Publish via MQTT
            memset(jsonBuffer, 0, sizeof(jsonBuffer));
            serializeJson(doc, jsonBuffer, sizeof(jsonBuffer) - 1);
            latestTelemetryJson = String(jsonBuffer); // Save copy for local API / REST fallback
            
            if (MqttManager::isConnected()) {
                MqttManager::publish(Config::TOPIC_TELEMETRY, latestTelemetryJson);
                stats.lastMqttConnected = millis();
                stats.publishCount++;
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
        for (const auto& hw : Config::HardwareOutputs) {
            if (hw.name == targetName) {
                if (hw.type == "PWM") {
                    value = constrain(value, 0, 255);
                    analogWrite(hw.pin, value);
                    Serial.printf("Actuator: Setting PWM %s (GPIO %d) to %d\n", targetName.c_str(), hw.pin, value);
                } else {
                    value = value > 0 ? 1 : 0;
                    digitalWrite(hw.pin, value > 0 ? HIGH : LOW);
                    Serial.printf("Actuator: Setting DIGITAL %s (GPIO %d) to %d\n", targetName.c_str(), hw.pin, value);
                }
                outputStates[targetName] = value;
                if (telemetryTaskHandle != NULL) {
                    xTaskNotifyGive(telemetryTaskHandle);
                }
                return true;
            }
        }
        Serial.printf("Actuator: Target '%s' not found in Output Configuration.\n", targetName.c_str());
        return false;
    }

    // ==================== MODBUS SCAN (GAP #6: dengan watchdog feed) ====================
    String runFullScanSync(uint32_t baud) {
        String scanResultsJson = "[";
        bool firstFound = true;
        
        if (xSemaphoreTake(modbusMutex, portMAX_DELAY) == pdTRUE) {
            Serial2.end();
            vTaskDelay(100 / portTICK_PERIOD_MS);
            Serial2.begin(baud, SERIAL_8N1, Config::PIN_RS485_RX, Config::PIN_RS485_TX);
            vTaskDelay(300 / portTICK_PERIOD_MS);
            currentBaud = baud;
            
            Serial.println("\n================================");
            Serial.printf("STARTING MODBUS SCAN ON %d BAUD\n", baud);
            Serial.println("================================");
            
            for (uint16_t id = 1; id <= 247; id++) {
                // GAP #6: Feed watchdog setiap iterasi
                esp_task_wdt_reset();
                TaskWatchdog::heartbeat("TelemetryTask");
                
                Serial.printf("Checking Slave ID %d ... ", id);
                node.begin(id, Serial2);
                uint8_t result = node.readHoldingRegisters(0, 1);
                
                if (result == node.ku8MBSuccess) {
                    Serial.println("FOUND");
                    Serial.printf("Register0 = %d\n", node.getResponseBuffer(0));
                    if (!firstFound) scanResultsJson += ",";
                    scanResultsJson += String(id);
                    firstFound = false;
                } else if (result >= node.ku8MBIllegalFunction && result <= node.ku8MBSlaveDeviceFailure) {
                    Serial.println("FOUND (Exception)");
                    if (!firstFound) scanResultsJson += ",";
                    scanResultsJson += String(id);
                    firstFound = false;
                } else {
                    Serial.printf("No Response (%d)\n", result);
                }
                vTaskDelay(50 / portTICK_PERIOD_MS);
            }
            Serial.println("================================");
            Serial.println("SCAN COMPLETE");
            Serial.println("================================");
            xSemaphoreGive(modbusMutex);
        }
        
        scanResultsJson += "]";
        return scanResultsJson;
    }
    
    uint16_t scanModbusReg(uint8_t id, uint32_t baud, uint16_t reg, String type, bool& success) {
        if (xSemaphoreTake(modbusMutex, pdMS_TO_TICKS(5000)) == pdTRUE) {
            if (currentBaud != baud) {
                Serial2.end();
                vTaskDelay(100 / portTICK_PERIOD_MS);
                Serial2.begin(baud, SERIAL_8N1, Config::PIN_RS485_RX, Config::PIN_RS485_TX);
                vTaskDelay(300 / portTICK_PERIOD_MS);
                currentBaud = baud;
            }
            Serial.printf("Scanning %s Register %d on ID %d (Baud: %d)... ", type.c_str(), reg, id, baud);
            node.begin(id, Serial2);
            uint8_t result;
            if (type == "INPUT") {
                result = node.readInputRegisters(reg, 1);
            } else {
                result = node.readHoldingRegisters(reg, 1);
            }
            uint16_t val = 0;
            if (result == node.ku8MBSuccess) {
                success = true;
                val = node.getResponseBuffer(0);
                Serial.printf("SUCCESS! Value = %d\n", val);
            } else {
                success = false;
                Serial.printf("FAILED (Error Code: %d)\n", result);
            }
            xSemaphoreGive(modbusMutex);
            return val;
        }
        Serial.println("FAILED (Could not take Modbus Mutex)");
        success = false;
        return 0;
    }
}