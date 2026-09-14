#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <Arduino.h>

class NetworkManager {
public:
    static void init();
    static bool isConnected();

private:
    static void wifiTask(void* parameter);
    
    static TaskHandle_t wifiTaskHandle;
    static volatile bool wifiConnected;
    static volatile bool wifiConnecting;
    static volatile bool portalActive;
    static unsigned long connectStart;
    static bool wasConnected;
    static unsigned long lastReconnectAttempt;
};

#endif // NETWORK_MANAGER_H
