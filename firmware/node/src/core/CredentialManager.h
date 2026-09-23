#ifndef CREDENTIAL_MANAGER_H
#define CREDENTIAL_MANAGER_H

#include <Arduino.h>

class CredentialManager {
public:
    static void init();
    static bool loadCredentials();
    static bool saveCredentials();
    static bool hasCredentials();
    static void clearCredentials();
    
    static String getAdminUser();
    static String getAdminPass();
    static String getAuthToken();
    static String getWifiSsid();
    static String getWifiPass();
    static String getMqttUser();
    static String getMqttPass();
    
    static void setAdminUser(const String& value);
    static void setAdminPass(const String& value);
    static void setAuthToken(const String& value);
    static void setWifiSsid(const String& value);
    static void setWifiPass(const String& value);
    static void setMqttUser(const String& value);
    static void setMqttPass(const String& value);

private:
    static bool nvsAvailable;
    static String readString(const char* key, const char* defaultValue);
    static void writeString(const char* key, const String& value);
    static void removeKey(const char* key);
};

#endif
