#include "CredentialManager.h"
#include "../include/Config.h"
#include "../include/Logger.h"
#include <Preferences.h>

bool CredentialManager::nvsAvailable = false;

void CredentialManager::init() {
    Preferences prefs;
    if (prefs.begin("creds", false)) {
        nvsAvailable = true;
        Logger::config("NVS credential namespace 'creds' initialized.");
    } else {
        Logger::error("NVS credential namespace 'creds' initialization failed.");
    }
}

bool CredentialManager::loadCredentials() {
    if (!nvsAvailable) {
        return false;
    }

    Config::ADMIN_USER = readString("admin_user", "");
    Config::ADMIN_PASS = readString("admin_pass", "");
    Config::AUTH_TOKEN = readString("auth_token", "");
    Config::WIFI_SSID = readString("wifi_ssid", "");
    Config::WIFI_PASS = readString("wifi_pass", "");
    Config::WIFI_EAP_IDENTITY = readString("wifi_eap_identity", "");
    Config::WIFI_EAP_PASSWORD = readString("wifi_eap_password", "");
    Config::MQTT_USER = readString("mqtt_user", "");
    Config::MQTT_PASS = readString("mqtt_pass", "");

    Logger::config("Credentials loaded from NVS.");
    return true;
}

bool CredentialManager::saveCredentials() {
    if (!nvsAvailable) {
        return false;
    }

    writeString("admin_user", Config::ADMIN_USER);
    writeString("admin_pass", Config::ADMIN_PASS);
    writeString("auth_token", Config::AUTH_TOKEN);
    writeString("wifi_ssid", Config::WIFI_SSID);
    writeString("wifi_pass", Config::WIFI_PASS);
    writeString("wifi_eap_identity", Config::WIFI_EAP_IDENTITY);
    writeString("wifi_eap_password", Config::WIFI_EAP_PASSWORD);
    writeString("mqtt_user", Config::MQTT_USER);
    writeString("mqtt_pass", Config::MQTT_PASS);

    Logger::config("Credentials saved to NVS.");
    return true;
}

bool CredentialManager::hasCredentials() {
    if (!nvsAvailable) {
        return false;
    }

    Preferences prefs;
    if (!prefs.begin("creds", false)) {
        return false;
    }

    return prefs.getBool("has_creds", false);
}

void CredentialManager::clearCredentials() {
    if (!nvsAvailable) {
        return;
    }

    Preferences prefs;
    if (!prefs.begin("creds", false)) {
        return;
    }

    removeKey("admin_user");
    removeKey("admin_pass");
    removeKey("auth_token");
    removeKey("wifi_ssid");
    removeKey("wifi_pass");
    removeKey("wifi_eap_identity");
    removeKey("wifi_eap_password");
    removeKey("mqtt_user");
    removeKey("mqtt_pass");
    prefs.remove("has_creds");

    Logger::config("Credentials cleared from NVS.");
}

String CredentialManager::getAdminUser() {
    return readString("admin_user", "");
}

String CredentialManager::getAdminPass() {
    return readString("admin_pass", "");
}

String CredentialManager::getAuthToken() {
    return readString("auth_token", "");
}

String CredentialManager::getWifiSsid() {
    return readString("wifi_ssid", "");
}

String CredentialManager::getWifiPass() {
    return readString("wifi_pass", "");
}

String CredentialManager::getWifiEapIdentity() {
    return readString("wifi_eap_identity", "");
}

String CredentialManager::getWifiEapPassword() {
    return readString("wifi_eap_password", "");
}

String CredentialManager::getMqttUser() {
    return readString("mqtt_user", "");
}

String CredentialManager::getMqttPass() {
    return readString("mqtt_pass", "");
}

void CredentialManager::setAdminUser(const String& value) {
    writeString("admin_user", value);
}

void CredentialManager::setAdminPass(const String& value) {
    writeString("admin_pass", value);
}

void CredentialManager::setAuthToken(const String& value) {
    writeString("auth_token", value);
}

void CredentialManager::setWifiSsid(const String& value) {
    writeString("wifi_ssid", value);
}

void CredentialManager::setWifiPass(const String& value) {
    writeString("wifi_pass", value);
}

void CredentialManager::setWifiEapIdentity(const String& value) {
    writeString("wifi_eap_identity", value);
}

void CredentialManager::setWifiEapPassword(const String& value) {
    writeString("wifi_eap_password", value);
}

void CredentialManager::setMqttUser(const String& value) {
    writeString("mqtt_user", value);
}

void CredentialManager::setMqttPass(const String& value) {
    writeString("mqtt_pass", value);
}

String CredentialManager::readString(const char* key, const char* defaultValue) {
    Preferences prefs;
    if (!prefs.begin("creds", false)) {
        return defaultValue ? String(defaultValue) : String();
    }

    String value = prefs.getString(key, defaultValue ? String(defaultValue) : String(""));
    return value;
}

void CredentialManager::writeString(const char* key, const String& value) {
    Preferences prefs;
    if (!prefs.begin("creds", false)) {
        return;
    }

    prefs.putString(key, value);
    prefs.putBool("has_creds", true);
}

void CredentialManager::removeKey(const char* key) {
    Preferences prefs;
    if (!prefs.begin("creds", false)) {
        return;
    }

    prefs.remove(key);
}
