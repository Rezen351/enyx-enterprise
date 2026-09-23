#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <Arduino.h>

class ConfigManager {
public:
    static void init();
    static bool loadConfig();
    static bool saveConfig(String jsonPayload);
};

#endif // CONFIG_MANAGER_H
