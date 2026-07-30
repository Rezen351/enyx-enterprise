#include "MqttManager.h"
#include "../../include/Config.h"
#include "../core/HardwareManager.h"
#include "../core/TaskWatchdog.h"
#include "NetworkManager.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>

WiFiClient espClientPlain;
WiFiClientSecure espClientSecure;
PubSubClient* mqttClient = nullptr;

// GAP #16: Circular buffer with fixed char array (no heap fragmentation)
#define MAX_LOG_ENTRIES 10
#define MAX_LOG_LENGTH 80
static char logBuffer[MAX_LOG_ENTRIES][MAX_LOG_LENGTH];
static int logIndex = 0;
static int logCount = 0;

std::vector<String> MqttManager::mqttLogs;

void MqttManager::addLog(const char* logMsg) {
    // GAP #16: Truncate long messages
    snprintf(logBuffer[logIndex], MAX_LOG_LENGTH, "[%lus] %s", 
             millis() / 1000, logMsg);
    logIndex = (logIndex + 1) % MAX_LOG_ENTRIES;
    if (logCount < MAX_LOG_ENTRIES) logCount++;
    
    // Juga simpan di vector untuk backward compatibility
    // (lebih pendek)
    String shortMsg = String(logMsg);
    if (shortMsg.length() > 80) {
        shortMsg = shortMsg.substring(0, 77) + "...";
    }
    String uptimeStr = "[" + String(millis() / 1000) + "s] ";
    mqttLogs.push_back(uptimeStr + shortMsg);
    if (mqttLogs.size() > 10) {
        mqttLogs.erase(mqttLogs.begin());
    }
}

std::vector<String> MqttManager::getLogs() {
    return mqttLogs;
}

String MqttManager::getLogsJSON() {
    StaticJsonDocument<1024> doc;
    JsonArray arr = doc.createNestedArray("logs");
    for (int i = 0; i < logCount; i++) {
        int idx = (logIndex - logCount + i + MAX_LOG_ENTRIES) % MAX_LOG_ENTRIES;
        arr.add(String(logBuffer[idx]));
    }
    String out;
    serializeJson(doc, out);
    return out;
}

void MqttManager::init() {
    // GAP #1: Pilih client berdasarkan TLS
    if (Config::MQTT_USE_TLS) {
        if (Config::MQTT_CA_CERT.length() > 0) {
            espClientSecure.setCACert(Config::MQTT_CA_CERT.c_str());
        } else {
            espClientSecure.setInsecure(); // For testing only (not recommended for production)
        }
        if (Config::MQTT_CLIENT_CERT.length() > 0) {
            espClientSecure.setCertificate(Config::MQTT_CLIENT_CERT.c_str());
        }
        if (Config::MQTT_CLIENT_KEY.length() > 0) {
            espClientSecure.setPrivateKey(Config::MQTT_CLIENT_KEY.c_str());
        }
        mqttClient = new PubSubClient(espClientSecure);
        addLog("MQTT TLS mode enabled");
    } else {
        mqttClient = new PubSubClient(espClientPlain);
        addLog("MQTT Plain TCP mode");
    }
    
    mqttClient->setBufferSize(8192);
    mqttClient->setServer(Config::MQTT_SERVER.c_str(), Config::MQTT_PORT);
    mqttClient->setCallback(MqttManager::mqttCallback);

    xTaskCreatePinnedToCore(
        MqttManager::mqttTask,
        "MqttTask",
        6144, 
        NULL,
        2,
        NULL,
        0
    );
}

bool MqttManager::isConnected() {
    return mqttClient != nullptr && mqttClient->connected();
}

bool MqttManager::publish(String topic, String payload) {
    if (isConnected()) {
        if (mqttClient->publish(topic.c_str(), payload.c_str())) {
            String logMsg = "Pub to " + topic.substring(0, 30);
            addLog(logMsg.c_str());
            return true;
        } else {
            addLog("Pub FAILED");
            return false;
        }
    }
    return false;
}

bool MqttManager::publishRetained(String topic, String payload) {
    if (isConnected()) {
        return mqttClient->publish(topic.c_str(), payload.c_str(), true);
    }
    return false;
}

void MqttManager::publishDiscovery() {
    if (isConnected()) {
        String macAsli = WiFi.macAddress();
        String discoveryTopic = Config::MQTT_TOPIC_PREFIX + "/discovery";
        String discoveryPayload = "{\"node_id\": \"" + Config::NODE_ID + 
            "\", \"mac\": \"" + macAsli + 
            "\", \"ip\": \"" + WiFi.localIP().toString() + 
            "\", \"fw_version\": \"" + Config::FW_VERSION +
            "\", \"status\": \"online\"}";
        mqttClient->publish(discoveryTopic.c_str(), discoveryPayload.c_str());
        addLog("Discovery published");
    } else {
        addLog("Discovery FAILED: MQTT disconnected");
    }
}

void MqttManager::mqttTask(void* parameter) {
    while (true) {
        TaskWatchdog::heartbeat("MqttTask"); // GAP #5
        
        if (NetworkManager::isConnected()) {
            if (!mqttClient->connected()) {
                // GAP #18: Track disconnect
                addLog("Connecting to broker...");
                
                String clientId = "SmartFarmNode-" + Config::NODE_ID;
                String lwtTopic = Config::MQTT_TOPIC_PREFIX + "/status/" + Config::NODE_ID;
                String macAsli = WiFi.macAddress();
                String lwtPayload = "{\"status\":\"offline\",\"mac\":\"" + macAsli + "\"}";
                
                bool connected = false;
                
                if (Config::MQTT_USER.length() > 0) {
                    connected = mqttClient->connect(
                        clientId.c_str(), 
                        Config::MQTT_USER.c_str(), 
                        Config::MQTT_PASS.c_str(), 
                        lwtTopic.c_str(), 0, true, lwtPayload.c_str()
                    );
                } else {
                    connected = mqttClient->connect(
                        clientId.c_str(), "", "",
                        lwtTopic.c_str(), 0, true, lwtPayload.c_str()
                    );
                }
                
                if (connected) {
                    addLog("Connected to broker!");
                    
                    // Subscribe topics
                    mqttClient->subscribe(Config::TOPIC_ACTUATOR.c_str());
                    addLog(("Sub: " + Config::TOPIC_ACTUATOR).c_str());
                    
                    // Publish online status (retained)
                    String onlinePayload = "{\"status\":\"online\",\"mac\":\"" + macAsli + "\",\"ip\":\"" + WiFi.localIP().toString() + "\",\"fw\":\"" + Config::FW_VERSION + "\"}";
                    mqttClient->publish(lwtTopic.c_str(), onlinePayload.c_str(), true);
                    
                     // Publish discovery
                     publishDiscovery();

                     // Publish discovery periodically every 60 seconds
                     // so that missed discovery messages (e.g. due to
                     // startup race conditions) are eventually recovered
                     // by the module service.
                     xTaskCreatePinnedToCore(
                         [](void *param) {
                             while (true) {
                                 vTaskDelay(60000 / portTICK_PERIOD_MS);
                                 if (mqttClient != nullptr && mqttClient->connected()) {
                                     publishDiscovery();
                                 }
                             }
                         },
                         "DiscoveryPeriodic",
                         4096,
                         NULL,
                         1,
                         NULL,
                         0
                      );

                 } else {
                    int state = mqttClient->state();
                    addLog(("Conn failed, rc=" + String(state)).c_str());
                    vTaskDelay(5000 / portTICK_PERIOD_MS);
                }
            } else {
                mqttClient->loop();
            }
        }
        
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

void MqttManager::mqttCallback(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    
    addLog(("Recv: " + String(topic).substring(0, 25) + " " + msg.substring(0, 30)).c_str());
    
    if (String(topic) == Config::TOPIC_ACTUATOR) {
        DynamicJsonDocument doc(16384);
        DeserializationError err = deserializeJson(doc, msg);
        
        if (!err) {
            String action = doc["action"] | "";
            String target = doc["target"] | "";
            int value = doc["value"] | 0;
            
            if (action == "set_output" && target.length() > 0) {
                HardwareManager::setOutput(target, value);
            }
            
            // Kirim konfirmasi balik
            if (doc.containsKey("req_id")) {
                String confirmTopic = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/confirm";
                String confirmPayload = "{\"req_id\":\"" + doc["req_id"].as<String>() + 
                    "\",\"target\":\"" + target + 
                    "\",\"value\":" + String(value) + ",\"status\":\"executed\"}";
                mqttClient->publish(confirmTopic.c_str(), confirmPayload.c_str());
            }
        } else {
            addLog("Actuator: JSON parse error");
        }
    }
}