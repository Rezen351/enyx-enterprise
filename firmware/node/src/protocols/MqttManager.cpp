#include "MqttManager.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include "../core/HardwareManager.h"
#include "../core/TaskWatchdog.h"
#include "NetworkManager.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <new>

WiFiClient espClientPlain;
WiFiClientSecure espClientSecure;
PubSubClient* mqttClient = nullptr;

namespace {
    constexpr size_t MQTT_QUEUE_TOPIC_SIZE = 128;
    constexpr size_t MQTT_QUEUE_PAYLOAD_SIZE = 8192;

    struct PublishMessage {
        char topic[MQTT_QUEUE_TOPIC_SIZE];
        char payload[MQTT_QUEUE_PAYLOAD_SIZE];
    };

    QueueHandle_t publishQueue = NULL;
}

// GAP #16: Circular buffer with fixed char array (no heap fragmentation)
#define MAX_LOG_ENTRIES 10
#define MAX_LOG_LENGTH 80
static char logBuffer[MAX_LOG_ENTRIES][MAX_LOG_LENGTH];
static int logIndex = 0;
static int logCount = 0;

std::vector<String> MqttManager::mqttLogs;
SemaphoreHandle_t MqttManager::logMutex = NULL;

void MqttManager::addLog(const char* logMsg) {
    if (logMutex && xSemaphoreTake(logMutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        snprintf(logBuffer[logIndex], MAX_LOG_LENGTH, "[%lus] %s", 
                 millis() / 1000, logMsg);
        logIndex = (logIndex + 1) % MAX_LOG_ENTRIES;
        if (logCount < MAX_LOG_ENTRIES) logCount++;
        
        String shortMsg = String(logMsg);
        if (shortMsg.length() > 80) {
            shortMsg = shortMsg.substring(0, 77) + "...";
        }
        String uptimeStr = "[" + String(millis() / 1000) + "s] ";
        mqttLogs.push_back(uptimeStr + shortMsg);
        if (mqttLogs.size() > 10) {
            mqttLogs.erase(mqttLogs.begin());
        }
        xSemaphoreGive(logMutex);
    }
}

std::vector<String> MqttManager::getLogs() {
    if (logMutex && xSemaphoreTake(logMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
        std::vector<String> copy = mqttLogs;
        xSemaphoreGive(logMutex);
        return copy;
    }
    return {};
}

void MqttManager::init() {
    logMutex = xSemaphoreCreateMutex();
    publishQueue = xQueueCreate(4, sizeof(PublishMessage*));
    
    if (Config::MQTT_USE_TLS) {
        if (Config::MQTT_CA_CERT.length() > 0) {
            espClientSecure.setCACert(Config::MQTT_CA_CERT.c_str());
        } else {
            Logger::mqtt("ERROR: TLS enabled but no CA cert provided.");
        }
        if (Config::MQTT_CLIENT_CERT.length() > 0) {
            espClientSecure.setCertificate(Config::MQTT_CLIENT_CERT.c_str());
        }
        if (Config::MQTT_CLIENT_KEY.length() > 0) {
            espClientSecure.setPrivateKey(Config::MQTT_CLIENT_KEY.c_str());
        }
        mqttClient = new PubSubClient(espClientSecure);
        Logger::mqtt("MQTT TLS mode enabled");
        addLog("MQTT TLS mode enabled");
    } else {
        mqttClient = new PubSubClient(espClientPlain);
        Logger::mqtt("MQTT Plain TCP mode");
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
        1
    );
}

bool MqttManager::isConnected() {
    return mqttClient != nullptr && mqttClient->connected();
}

bool MqttManager::publish(String topic, String payload) {
    return queuePublish(topic, payload);
}

bool MqttManager::queuePublish(String topic, String payload) {
    if (!publishQueue || topic.length() >= MQTT_QUEUE_TOPIC_SIZE ||
        payload.length() >= MQTT_QUEUE_PAYLOAD_SIZE) {
        return false;
    }

    PublishMessage* message = new (std::nothrow) PublishMessage{};
    if (!message) return false;

    topic.toCharArray(message->topic, sizeof(message->topic));
    payload.toCharArray(message->payload, sizeof(message->payload));
    if (xQueueSend(publishQueue, &message, 0) != pdTRUE) {
        delete message;
        return false;
    }
    return true;
}

bool MqttManager::publishNow(const char* topic, const char* payload) {
    if (!mqttClient || !mqttClient->connected()) return false;
    if (mqttClient->publish(topic, payload)) {
        String logMsg = "Pub to " + String(topic).substring(0, 30);
        Logger::mqtt("%s", logMsg.c_str());
        addLog(logMsg.c_str());
        return true;
    }
    Logger::mqtt("Pub FAILED");
    addLog("Pub FAILED");
    return false;
}

void MqttManager::drainPublishQueue() {
    if (!isConnected()) return;

    PublishMessage* message = nullptr;
    while (xQueueReceive(publishQueue, &message, 0) == pdTRUE) {
        if (message) {
            publishNow(message->topic, message->payload);
            delete message;
        }
    }
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
        queuePublish(discoveryTopic, discoveryPayload);
    } else {
        Logger::mqtt("Discovery FAILED: MQTT disconnected");
        addLog("Discovery FAILED: MQTT disconnected");
    }
}

void MqttManager::mqttTask(void* parameter) {
    unsigned long lastDiscovery = 0;
    static bool wasConnected = false;
    
    while (true) {
        TaskWatchdog::heartbeat("MqttTask");
        
        if (NetworkManager::isConnected()) {
            if (!mqttClient->connected()) {
                if (wasConnected) {
                    if (Config::MQTT_DISCONNECT_EMERGENCY_STOP) {
                        Logger::mqtt("MQTT disconnected! Triggering actuator emergency stop.");
                        addLog("MQTT disconnected! Actuator emergency stop triggered.");
                        HardwareManager::triggerMqttDisconnectEmergencyStop();
                    } else {
                        Logger::mqtt("MQTT disconnected! Emergency stop is disabled.");
                        addLog("MQTT disconnected! Emergency stop disabled.");
                    }
                    wasConnected = false;
                }
                
                Logger::mqtt("Connecting to broker...");
                addLog("Connecting to broker...");
                
                String clientId = "enyx-" + Config::NODE_ID;
                String lwtTopic = Config::MQTT_TOPIC_PREFIX + "/status/" + Config::NODE_ID;
                String macAsli = WiFi.macAddress();
                String lwtPayload = "{\"status\":\"offline\",\"mac\":\"" + macAsli + "\"}";
                
                bool connected = false;
                
                if (Config::MQTT_USER.length() > 0) {
                    connected = mqttClient->connect(
                        clientId.c_str(), 
                        Config::MQTT_USER.c_str(), 
                        Config::MQTT_PASS.c_str(), 
                        lwtTopic.c_str(), 1, true, lwtPayload.c_str()
                    );
                } else {
                    connected = mqttClient->connect(
                        clientId.c_str(), "", "",
                        lwtTopic.c_str(), 1, true, lwtPayload.c_str()
                    );
                }
                
                if (connected) {
                    Logger::mqtt("Connected to broker!");
                    addLog("Connected to broker!");
                    wasConnected = true;
                    
                    mqttClient->subscribe(Config::TOPIC_ACTUATOR.c_str());
                    Logger::mqtt("Sub: %s", Config::TOPIC_ACTUATOR.c_str());
                    addLog(("Sub: " + Config::TOPIC_ACTUATOR).c_str());
                    
                    String onlinePayload = "{\"status\":\"online\",\"mac\":\"" + macAsli + "\",\"ip\":\"" + WiFi.localIP().toString() + "\",\"fw\":\"" + Config::FW_VERSION + "\"}";
                    mqttClient->publish(lwtTopic.c_str(), onlinePayload.c_str(), true);
                    
                    publishDiscovery();
                    lastDiscovery = millis();
                } else {
                    int state = mqttClient->state();
                    Logger::mqtt("Conn failed, rc=%d", state);
                    addLog(("Conn failed, rc=" + String(state)).c_str());
                    vTaskDelay(5000 / portTICK_PERIOD_MS);
                }
            } else {
                mqttClient->loop();
                drainPublishQueue();
                
                if (millis() - lastDiscovery >= 60000) {
                    lastDiscovery = millis();
                    publishDiscovery();
                }
            }
        } else {
            wasConnected = false;
        }
        
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

void MqttManager::mqttCallback(char* topic, byte* payload, unsigned int length) {
    if (length > 4096) {
        Logger::mqtt("Actuator command rejected: payload too large");
        addLog("Actuator command rejected: payload too large");
        return;
    }

    String msg;
    for (unsigned int i = 0; i < length; i++) {
        msg += (char)payload[i];
    }
    
    Logger::mqtt("Recv: %s %s", String(topic).substring(0, 25).c_str(), msg.substring(0, 30).c_str());
    addLog(("Recv: " + String(topic).substring(0, 25) + " " + msg.substring(0, 30)).c_str());
    
    if (String(topic) == Config::TOPIC_ACTUATOR) {
        DynamicJsonDocument doc(16384);
        DeserializationError err = deserializeJson(doc, msg);
        
        if (!err) {
            String action = doc["action"] | "";
            String target = doc["target"] | "";
            int value = doc["value"] | 0;
            
            if (action == "set_output" && target.length() > 0) {
                String requestId = doc["req_id"] | "";
                if (!HardwareManager::enqueueOutputCommand(target, value, requestId)) {
                    Logger::mqtt("Actuator command queue full");
                    addLog("Actuator command queue full");
                }
            }
        } else {
            Logger::mqtt("Actuator: JSON parse error");
            addLog("Actuator: JSON parse error");
        }
    }
}