#include "TaskWatchdog.h"
#include "../../include/Logger.h"
#include <Arduino.h>

std::vector<ManagedTask> TaskWatchdog::tasks;
SemaphoreHandle_t TaskWatchdog::mutex = NULL;

void TaskWatchdog::init() {
    mutex = xSemaphoreCreateMutex();
    
    xTaskCreatePinnedToCore(
        TaskWatchdog::watchdogTask,
        "WatchdogTask",
        4096,
        NULL,
        2,  // High priority
        NULL,
        0   // Core 0
    );
    Logger::watchdog("Initialized");
}

void TaskWatchdog::registerTask(const char* name, TaskHandle_t handle, unsigned long timeoutMs, void (*restartFunc)()) {
    if (xSemaphoreTake(mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        ManagedTask t;
        t.name = String(name);
        t.handle = handle;
        t.lastHeartbeatMs = millis();
        t.timeoutMs = timeoutMs;
        t.restartFunc = restartFunc;
        tasks.push_back(t);
        xSemaphoreGive(mutex);
        
        Logger::watchdog("Registered '%s' (timeout: %lu ms)", name, timeoutMs);
    }
}

void TaskWatchdog::heartbeat(const char* taskName) {
    if (xSemaphoreTake(mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
        for (auto& t : tasks) {
            if (t.name == taskName) {
                t.lastHeartbeatMs = millis();
                break;
            }
        }
        xSemaphoreGive(mutex);
    }
}

void TaskWatchdog::watchdogTask(void* parameter) {
    vTaskDelay(5000 / portTICK_PERIOD_MS); // Initial delay to let tasks start
    
    while (true) {
        if (xSemaphoreTake(mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            unsigned long now = millis();
            
            for (auto& t : tasks) {
                unsigned long elapsed = now - t.lastHeartbeatMs;
                
                if (elapsed > t.timeoutMs && t.timeoutMs > 0) {
                    Logger::watchdog("Task '%s' timeout! Elapsed: %lu ms, Limit: %lu ms",
                                  t.name.c_str(), elapsed, t.timeoutMs);
                    
                    if (t.restartFunc != nullptr) {
                        if (t.handle != NULL) {
                            vTaskDelete(t.handle);
                            t.handle = NULL;
                        }
                        Logger::watchdog("Restarting task '%s'...", t.name.c_str());
                        t.restartFunc();
                    } else {
                        Logger::watchdog("No restart function for '%s'. Resetting ESP32...", t.name.c_str());
                        delay(1000);
                        ESP.restart();
                    }
                    
                    t.lastHeartbeatMs = millis();
                }
            }
            xSemaphoreGive(mutex);
        }
        
        vTaskDelay(5000 / portTICK_PERIOD_MS); // Check every 5 seconds
    }
}