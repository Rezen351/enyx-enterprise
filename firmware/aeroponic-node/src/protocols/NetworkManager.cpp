#include "NetworkManager.h"
#include "WebConfigPortal.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include "../core/TaskWatchdog.h"
#include <WiFi.h>

TaskHandle_t NetworkManager::wifiTaskHandle = NULL;
volatile bool NetworkManager::wifiConnected = false;
volatile bool NetworkManager::wifiConnecting = false;
volatile bool NetworkManager::portalActive = false;
unsigned long NetworkManager::connectStart = 0;
bool NetworkManager::wasConnected = false;
unsigned long NetworkManager::lastReconnectAttempt = 0;

void NetworkManager::wifiTask(void* parameter) {
    WiFi.mode(WIFI_AP_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(true);
    
    WebConfigPortal::startAP();
    portalActive = true;
    wifiConnected = false;
    wifiConnecting = false;
    connectStart = 0;
    wasConnected = false;
    lastReconnectAttempt = 0;
    
    Logger::network("NetworkManager initialized, waiting for WiFi connection...");
    
    while (true) {
        TaskWatchdog::heartbeat("WiFiTask");
        
        if (WiFi.status() == WL_CONNECTED) {
            if (!wifiConnected) {
                wifiConnected = true;
                wifiConnecting = false;
                connectStart = 0;
                Logger::network("WiFi Connected! IP: %s", WiFi.localIP().toString().c_str());
                
                if (Config::NODE_ID == "" || Config::NODE_ID == "node-01") {
                    String mac = WiFi.macAddress();
                    mac.replace(":", "");
                    Config::NODE_ID = mac;
                    Logger::network("NODE_ID updated: %s", Config::NODE_ID.c_str());
                }
            }
            wasConnected = true;
        } else {
            if (wifiConnected) {
                Logger::network("WiFi disconnected!");
                wifiConnected = false;
            }
            
            if (!wifiConnecting && (millis() - lastReconnectAttempt > 5000 || lastReconnectAttempt == 0)) {
                wifiConnecting = true;
                connectStart = millis();
                lastReconnectAttempt = millis();
                Logger::network("Reconnecting to WiFi: %s", Config::WIFI_SSID.c_str());
                
                if (Config::WIFI_EAP_IDENTITY.length() > 0) {
                    WiFi.begin(Config::WIFI_SSID, WPA2_AUTH_PEAP, Config::WIFI_EAP_IDENTITY, "", Config::WIFI_EAP_PASSWORD);
                } else {
                    WiFi.begin(Config::WIFI_SSID.c_str(), Config::WIFI_PASS.c_str());
                }
            }
            
            if (wifiConnecting && (millis() - connectStart > 10000)) {
                Logger::network("WiFi connect timeout, will retry in 5s...");
                WiFi.disconnect(false);
                wifiConnecting = false;
                lastReconnectAttempt = 0;
                vTaskDelay(5000 / portTICK_PERIOD_MS);
                continue;
            }
        }
        
        if (portalActive) {
            WebConfigPortal::loop();
        }
        
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

void NetworkManager::init() {
    xTaskCreatePinnedToCore(
        wifiTask,
        "WiFiTask",
        8192,
        NULL,
        2,
        &wifiTaskHandle,
        0
    );
}

bool NetworkManager::isConnected() {
    return wifiConnected;
}
