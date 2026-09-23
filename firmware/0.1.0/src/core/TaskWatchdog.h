#ifndef TASK_WATCHDOG_H
#define TASK_WATCHDOG_H

#include <Arduino.h>
#include <vector>

struct ManagedTask {
    String name;
    TaskHandle_t handle;
    unsigned long lastHeartbeatMs;
    unsigned long timeoutMs;
    void (*restartFunc)();
};

class TaskWatchdog {
public:
    static void init();
    static void heartbeat(const char* taskName);

private:
    static std::vector<ManagedTask> tasks;
    static void watchdogTask(void* parameter);
    static SemaphoreHandle_t mutex;
};

#endif // TASK_WATCHDOG_H