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

    String storedUser = readString("admin_user", "");
    String storedPass = readString("admin_pass", "");
    String storedWifiSsid = readString("wifi_ssid", "");
    String storedWifiPass = readString("wifi_pass", "");
    String storedWifiEntEnabledRaw = readString("ent_enabled", "");
    String storedWifiEntUsername = readString("ent_user", "");
    String storedWifiEntPassword = readString("ent_pass", "");
    String storedWifiEntCaCert = readString("ent_ca", "");
    String storedWifiEntClientCert = readString("ent_cert", "");
    String storedWifiEntClientKey = readString("ent_key", "");
    String storedMqttUser = readString("mqtt_user", "");
    String storedMqttPass = readString("mqtt_pass", "");

    if (storedUser.length() > 0) {
        Config::ADMIN_USER = storedUser;
    }
    if (storedPass.length() > 0) {
        Config::ADMIN_PASS = storedPass;
    }
    if (storedWifiSsid.length() > 0) {
        Config::WIFI_SSID = storedWifiSsid;
    }
    if (storedWifiPass.length() > 0) {
        Config::WIFI_PASS = storedWifiPass;
    }
    if (storedWifiEntEnabledRaw.length() > 0) {
        Config::WIFI_ENT_ENABLED = storedWifiEntEnabledRaw == "1";
    }
    if (storedWifiEntUsername.length() > 0) {
        Config::WIFI_ENT_USERNAME = storedWifiEntUsername;
    }
    if (storedWifiEntPassword.length() > 0) {
        Config::WIFI_ENT_PASSWORD = storedWifiEntPassword;
    }
    if (storedWifiEntCaCert.length() > 0) {
        Config::WIFI_ENT_CA_CERT = storedWifiEntCaCert;
    }
    if (storedWifiEntClientCert.length() > 0) {
        Config::WIFI_ENT_CLIENT_CERT = storedWifiEntClientCert;
    }
    if (storedWifiEntClientKey.length() > 0) {
        Config::WIFI_ENT_CLIENT_KEY = storedWifiEntClientKey;
    }
    if (storedMqttUser.length() > 0) {
        Config::MQTT_USER = storedMqttUser;
    }
    if (storedMqttPass.length() > 0) {
        Config::MQTT_PASS = storedMqttPass;
    }

    Config::AUTH_TOKEN = readString("auth_token", "");

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
    writeString("ent_enabled", Config::WIFI_ENT_ENABLED ? "1" : "0");
    writeString("ent_user", Config::WIFI_ENT_USERNAME);
    writeString("ent_pass", Config::WIFI_ENT_PASSWORD);
    writeString("ent_ca", Config::WIFI_ENT_CA_CERT);
    writeString("ent_cert", Config::WIFI_ENT_CLIENT_CERT);
    writeString("ent_key", Config::WIFI_ENT_CLIENT_KEY);
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

    bool hasFlag = prefs.getBool("has_creds", false);
    if (!hasFlag) {
        return false;
    }

    return prefs.getString("admin_user", "").length() > 0 ||
           prefs.getString("admin_pass", "").length() > 0 ||
           prefs.getString("wifi_ssid", "").length() > 0 ||
           prefs.getString("wifi_pass", "").length() > 0 ||
           prefs.getString("ent_user", "").length() > 0 ||
           prefs.getString("ent_pass", "").length() > 0 ||
           prefs.getString("mqtt_user", "").length() > 0 ||
           prefs.getString("mqtt_pass", "").length() > 0;
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
    removeKey("ent_enabled");
    removeKey("ent_user");
    removeKey("ent_pass");
    removeKey("ent_ca");
    removeKey("ent_cert");
    removeKey("ent_key");
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

bool CredentialManager::getWifiEntEnabled() {
    return readString("ent_enabled", "") == "1";
}

String CredentialManager::getWifiEntUsername() {
    return readString("ent_user", "");
}

String CredentialManager::getWifiEntPassword() {
    return readString("ent_pass", "");
}

String CredentialManager::getWifiEntCaCert() {
    return readString("ent_ca", "");
}

String CredentialManager::getWifiEntClientCert() {
    return readString("ent_cert", "");
}

String CredentialManager::getWifiEntClientKey() {
    return readString("ent_key", "");
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

void CredentialManager::setWifiEntEnabled(bool value) {
    writeString("ent_enabled", value ? "1" : "0");
}

void CredentialManager::setWifiEntUsername(const String& value) {
    writeString("ent_user", value);
}

void CredentialManager::setWifiEntPassword(const String& value) {
    writeString("ent_pass", value);
}

void CredentialManager::setWifiEntCaCert(const String& value) {
    writeString("ent_ca", value);
}

void CredentialManager::setWifiEntClientCert(const String& value) {
    writeString("ent_cert", value);
}

void CredentialManager::setWifiEntClientKey(const String& value) {
    writeString("ent_key", value);
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

    if (!prefs.isKey(key)) {
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
