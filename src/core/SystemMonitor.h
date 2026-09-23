#ifndef SYSTEM_MONITOR_H
#define SYSTEM_MONITOR_H

#include <Arduino.h>

class SystemMonitor {
public:
    static void init();
    static void printDiagnostics();

private:
    static void monitorTask(void* parameter);
};

#endif // SYSTEM_MONITOR_H
