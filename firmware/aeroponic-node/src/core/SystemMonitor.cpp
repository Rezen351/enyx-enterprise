#include "SystemMonitor.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
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
    Logger::system("--- System Diagnostics ---");
    Logger::system("Free Heap: %d KB", ESP.getFreeHeap() / 1024);
    Logger::system("Uptime: %d s", millis() / 1000);
    Logger::system("WiFi RSSI: %d dBm", WiFi.RSSI());
    Logger::system("--------------------------");
}

void SystemMonitor::monitorTask(void* parameter) {
    while (true) {
        printDiagnostics();
        
        if (ESP.getFreeHeap() < 10000) {
            Logger::system("CRITICAL: Low memory! Restarting...");
            ESP.restart();
        }

        vTaskDelay(10000 / portTICK_PERIOD_MS);
    }
}
