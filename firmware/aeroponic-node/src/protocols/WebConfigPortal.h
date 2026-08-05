#ifndef WEB_CONFIG_PORTAL_H
#define WEB_CONFIG_PORTAL_H

#include <Arduino.h>

class WebConfigPortal {
public:
    static void startAP();
    static void loop();
private:
    static void handleRoot();
    static void handleApiLogin();
    static void handleApiFullConfigGet();
    static void handleApiWifiPost();
    static void handleApiMqttPost();
    static void handleApiDevicePost();
    static void handleApiHardwarePost();
    static void handleApiModbusStartScan();
    static void handleApiModbusScanReg();
    static void handleApiAccountPost();
    static void handleApiStatusGet();
    static void handleApiOtaUpdate();
    static void handleApiOtaUpload();
    static void handleApiPublishDiscovery();
    static void handleApiConfigExport();
    static void handleApiConfigImport();
    static void handleApiTelemetryLatest();
    static void handleApiHardwareDiscover();
    static void handleApiLocalControlGet();
    static void handleApiLocalControlPost();
    static void handleNotFound();
    
    static bool checkAuthToken();
    static String generateToken();
};

#endif // WEB_CONFIG_PORTAL_H
