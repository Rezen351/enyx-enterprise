#ifndef HARDWARE_MANAGER_H
#define HARDWARE_MANAGER_H

#include <Arduino.h>
#include <map>
#include <vector>
#include <ModbusMaster.h>

namespace HardwareManager {
    enum class OutputResult : uint8_t {
        Success,
        NotFound,
        Busy,
        HandlerFailed
    };

    // Shared Modbus variables
    extern ModbusMaster node;
    extern uint32_t currentBaud;
    extern SemaphoreHandle_t modbusMutex;
    extern SemaphoreHandle_t telemetryMutex;
    extern std::map<String, float> latestSensorValues;
    extern volatile bool scanCancelRequested;

    void init();
    void telemetryTask(void* parameter);
    void controlTask(void* parameter);
    bool setOutput(String targetName, int value);
    OutputResult setOutputResult(String targetName, int value);
    bool enqueueOutputCommand(const String& targetName, int value, const String& requestId);
    void requestEmergencyStop();
    uint16_t scanModbusReg(uint8_t id, uint32_t baud, uint16_t reg, String type, uint8_t length, bool& success);
    String scanModbusRegBatch(uint8_t id, uint32_t baud, uint16_t startReg, uint16_t endReg, String type, uint8_t length);
    
    // Synchronous Scan ID
    String runFullScanSync(const std::vector<uint32_t>& bauds);
    void requestScanCancel();

    // Dynamic configuration and discovery
    void reloadConfiguration();
    String discoverSensors();
    String getLatestTelemetryJson();

    // MQTT disconnect emergency stop
    void triggerMqttDisconnectEmergencyStop();
}

#endif // HARDWARE_MANAGER_H
