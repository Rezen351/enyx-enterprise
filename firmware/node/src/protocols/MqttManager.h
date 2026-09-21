#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <Arduino.h>
#include <PubSubClient.h>
#include <vector>

class MqttManager {
public:
    static void init();
    static bool isConnected();
    static bool publish(String topic, String payload);
    static void publishDiscovery();
    static std::vector<String> getLogs();
    static void addLog(const char* logMsg);
    
private:
    static void mqttTask(void* parameter);
    static void mqttCallback(char* topic, byte* payload, unsigned int length);
    static std::vector<String> mqttLogs;
    static SemaphoreHandle_t logMutex;
};

#endif // MQTT_MANAGER_H