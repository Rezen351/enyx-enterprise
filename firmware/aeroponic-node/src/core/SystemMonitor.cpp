#include "SystemMonitor.h"
#include "../../include/Config.h"
#include <WiFi.h>

void SystemMonitor::init() {
    // Create a FreeRTOS task pinned to Core 0 for system diagnostics
    xTaskCreatePinnedToCore(
        SystemMonitor::monitorTask,   // Task function
        "SysMonitorTask",             // Name of task
        4096,                         // Stack size
        NULL,                         // Parameter
        1,                            // Priority
        NULL,                         // Task handle
        0                             // Pin to core 0 (Network/System core)
    );
}

void SystemMonitor::printDiagnostics() {
    Serial.println("--- System Diagnostics ---");
    Serial.print("Free Heap: ");
    Serial.print(ESP.getFreeHeap() / 1024);
    Serial.println(" KB");
    Serial.print("Uptime: ");
    Serial.print(millis() / 1000);
    Serial.println(" s");
    Serial.print("WiFi RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println("--------------------------");
}

void SystemMonitor::monitorTask(void* parameter) {
    while (true) {
        printDiagnostics();
        
        if (ESP.getFreeHeap() < 10000) {
            Serial.println("CRITICAL: Low memory! Restarting...");
            ESP.restart();
        }

        vTaskDelay(10000 / portTICK_PERIOD_MS);
    }
}
