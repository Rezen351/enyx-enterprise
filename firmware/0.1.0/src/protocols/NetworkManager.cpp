#include "NetworkManager.h"
#include "WebConfigPortal.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include "../core/TaskWatchdog.h"
#include <WiFi.h>
#include <ArduinoOTA.h>
#include <esp_wpa2.h>

TaskHandle_t NetworkManager::wifiTaskHandle = NULL;
volatile bool NetworkManager::wifiConnected = false;
volatile bool NetworkManager::wifiConnecting = false;
volatile bool NetworkManager::portalActive = false;
unsigned long NetworkManager::connectStart = 0;
bool NetworkManager::wasConnected = false;
unsigned long NetworkManager::lastReconnectAttempt = 0;

void NetworkManager::initArduinoOTA() {
    ArduinoOTA.setHostname(Config::NODE_ID.c_str());
    ArduinoOTA.setPassword("enyx-ota");
    
    ArduinoOTA.onStart([]() {
        Logger::network("ArduinoOTA: Update started");
    });
    ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
        Logger::network("ArduinoOTA: Progress %u%%", (progress / (total / 100)));
    });
    ArduinoOTA.onEnd([]() {
        Logger::network("ArduinoOTA: Update finished, rebooting...");
    });
    ArduinoOTA.onError([](ota_error_t error) {
        Logger::network("ArduinoOTA: Error[%u]", error);
    });
    
    ArduinoOTA.begin();
    Logger::network("ArduinoOTA initialized");
}

void NetworkManager::wifiTask(void* parameter) {
    WiFi.mode(WIFI_AP_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(true);

    if (Config::NODE_ID == "") {
        String mac = WiFi.macAddress();
        mac.replace(":", "");
        Config::NODE_ID = mac.length() > 0 ? mac : "unknown-node";
        Logger::network("NODE_ID auto-generated from MAC: %s", Config::NODE_ID.c_str());
    }
    Config::TOPIC_TELEMETRY = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/telemetry";
    Config::TOPIC_ACTUATOR = Config::MQTT_TOPIC_PREFIX + "/actuator/" + Config::NODE_ID;
    
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
                initArduinoOTA();
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
                
                if (Config::WIFI_ENT_ENABLED && Config::WIFI_ENT_USERNAME.length() > 0 && Config::WIFI_ENT_PASSWORD.length() > 0) {
                    WiFi.disconnect();
                    delay(100);
                    Logger::network("WiFi auth mode: WPA2 Enterprise (eduroam)");
                    esp_wifi_sta_wpa2_ent_set_username((uint8_t *)Config::WIFI_ENT_USERNAME.c_str(), Config::WIFI_ENT_USERNAME.length());
                    esp_wifi_sta_wpa2_ent_set_password((uint8_t *)Config::WIFI_ENT_PASSWORD.c_str(), Config::WIFI_ENT_PASSWORD.length());
                if (Config::WIFI_ENT_CA_CERT.length() > 0) {
                    esp_wifi_sta_wpa2_ent_set_ca_cert((uint8_t *)Config::WIFI_ENT_CA_CERT.c_str(), Config::WIFI_ENT_CA_CERT.length());
                }
                if (Config::WIFI_ENT_CLIENT_CERT.length() > 0 && Config::WIFI_ENT_CLIENT_KEY.length() > 0) {
                    esp_wifi_sta_wpa2_ent_set_cert_key(
                        (uint8_t *)Config::WIFI_ENT_CLIENT_CERT.c_str(), Config::WIFI_ENT_CLIENT_CERT.length(),
                        (uint8_t *)Config::WIFI_ENT_CLIENT_KEY.c_str(), Config::WIFI_ENT_CLIENT_KEY.length(),
                        NULL, 0
                    );
                }
                    esp_wifi_sta_wpa2_ent_enable();
                    WiFi.begin(Config::WIFI_SSID.c_str());
                } else if (Config::WIFI_PASS.length() > 0) {
                    esp_wifi_sta_wpa2_ent_disable();
                    WiFi.disconnect();
                    delay(100);
                    Logger::network("WiFi auth mode: WPA/WPA2 Personal (password_set=yes)");
                    WiFi.begin(Config::WIFI_SSID.c_str(), Config::WIFI_PASS.c_str());
                } else {
                    esp_wifi_sta_wpa2_ent_disable();
                    WiFi.disconnect();
                    delay(100);
                    Logger::network("WiFi auth mode: Open (no password)");
                    WiFi.begin(Config::WIFI_SSID.c_str());
                }
            }
            
            if (wifiConnecting) {
                unsigned long timeout = 30000;
                if (Config::WIFI_ENT_ENABLED) {
                    timeout = 60000;
                }
                if ((millis() - connectStart > timeout)) {
                    Logger::network("WiFi connect timeout (%lus). Status=%d", timeout / 1000, WiFi.status());
                    WiFi.disconnect(false);
                    wifiConnecting = false;
                    lastReconnectAttempt = 0;
                    vTaskDelay(5000 / portTICK_PERIOD_MS);
                    continue;
                }
            }
        }
        
        if (portalActive) {
            WebConfigPortal::loop();
        }
        
        ArduinoOTA.handle();
        
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
