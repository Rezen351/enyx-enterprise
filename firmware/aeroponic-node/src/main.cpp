#include <Arduino.h>
#include "../include/Config.h"
#include "../include/Logger.h"
#include "core/SystemMonitor.h"
#include "core/ConfigManager.h"
#include "core/HardwareManager.h"
#include "core/TaskWatchdog.h"
#include "protocols/NetworkManager.h"
#include "protocols/MqttManager.h"
#include <Preferences.h>
#include "esp_ota_ops.h"
#include "esp_partition.h"

// GAP #8: Boot health check function
void checkBootHealth() {
    Preferences prefs;
    prefs.begin("ota", false);
    
    int bootCount = prefs.getInt("boot_count", 0);
    bootCount++;
    prefs.putInt("boot_count", bootCount);
    
    Logger::boot("Boot health check: boot_count=%d", bootCount);
    
    if (bootCount <= 2) {
        // First or second boot after OTA - mark as success
        prefs.putInt("boot_count", 0);
        bool isHealthy = prefs.getBool("healthy", false);
        if (!isHealthy) {
            prefs.putBool("healthy", true);
            Logger::boot("Boot health: OK");
        }
    } else if (bootCount > 3) {
        // Boot failed 3+ times - rollback needed
        Logger::boot("CRITICAL: Boot failure detected multiple times!");
        Logger::boot("Attempting rollback to previous firmware...");
        
        const esp_partition_t* running = esp_ota_get_running_partition();
        const esp_partition_t* next = esp_ota_get_next_update_partition(NULL);
        
        if (running != NULL && next != NULL && running != next) {
            esp_ota_set_boot_partition(next);
            prefs.putInt("boot_count", 0);
            Logger::boot("Rollback initiated. Rebooting...");
        } else {
            Logger::boot("ERROR: Cannot perform rollback - no alternate partition");
        }
        
        delay(1000);
        ESP.restart();
    }
    
    prefs.end();
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Logger::init("\n--- SmartFarm Node Initializing ---");
    
    // 0. Check boot health (GAP #8)
    checkBootHealth();
    
    // 0. Initialize TaskWatchdog (GAP #5)
    TaskWatchdog::init();
    
    // 0. Initialize Configuration from LittleFS
    ConfigManager::init();
    
    // 1. Initialize System Diagnostics
    SystemMonitor::init();
    
    // 2. Initialize Network (WiFi & Captive Portal)
    NetworkManager::init();
    
    // 3. Initialize MQTT Protocol
    MqttManager::init();
    
    // 4. Initialize Universal Hardware Pins & Telemetry Loop
    HardwareManager::init();
    
    // Register tasks with watchdog (GAP #5)
    // Note: Task handles are internal, we track by name
    // heartbeat calls from each task loop keep them alive
    
    Logger::init("--- Initialization Complete ---");
}

void loop() {
    vTaskDelay(1000 / portTICK_PERIOD_MS);
}