#ifndef HARDWARE_MANAGER_H
#define HARDWARE_MANAGER_H

#include <Arduino.h>
#include <map>
#include <ModbusMaster.h>

namespace HardwareManager {
    // Shared Modbus variables
    extern ModbusMaster node;
    extern uint32_t currentBaud;
    extern SemaphoreHandle_t modbusMutex;
    extern std::map<String, float> latestSensorValues;

    void init();
    void telemetryTask(void* parameter);
    bool setOutput(String targetName, int value);
    uint16_t scanModbusReg(uint8_t id, uint32_t baud, uint16_t reg, String type, bool& success);
    
    // Synchronous Scan ID
    String runFullScanSync(uint32_t baud);

    // Dynamic configuration and discovery
    void reloadConfiguration();
    String discoverSensors();
    String getLatestTelemetryJson();
}

#endif // HARDWARE_MANAGER_H
