#include "WebConfigPortal.h"
#include "../core/ConfigManager.h"
#include "../core/HardwareManager.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include "MqttManager.h"
#include <Update.h>

const byte DNS_PORT = 53;
IPAddress apIP(192, 133, 22, 6);
DNSServer dnsServer;
WebServer server(80);

bool portalActive = false;

// GAP #4: Rate limiter login
struct LoginAttempt {
    IPAddress ip;
    int attempts;
    unsigned long blockUntil;
};
static std::vector<LoginAttempt> loginAttempts;

// ==================== SAVE FULL CONFIG FUNCTION (GAP #15: Refactor macro) ====================
static bool saveFullConfig() {
    DynamicJsonDocument doc(8192);
    
    JsonObject device = doc.createNestedObject("device");
    device["node_id"] = Config::NODE_ID;
    device["fw_version"] = Config::FW_VERSION;
    
    JsonObject security = doc.createNestedObject("security");
    security["credentials_encrypted"] = false;
    security["auth_token"] = Config::AUTH_TOKEN;
    security["admin_user"] = Config::ADMIN_USER;
    security["admin_pass"] = Config::ADMIN_PASS;
    
    JsonObject protocols = doc.createNestedObject("protocols");
    JsonObject wifi = protocols.createNestedObject("wifi");
    wifi["ssid"]         = Config::WIFI_SSID;
    wifi["password"]     = Config::WIFI_PASS;
    wifi["eap_identity"] = Config::WIFI_EAP_IDENTITY;
    wifi["eap_password"] = Config::WIFI_EAP_PASSWORD;
    
    JsonObject mqtt = protocols.createNestedObject("mqtt");
    mqtt["server"]               = Config::MQTT_SERVER;
    mqtt["port"]                 = Config::MQTT_PORT;
    mqtt["topic_prefix"]         = Config::MQTT_TOPIC_PREFIX;
    mqtt["user"]                 = Config::MQTT_USER;
    mqtt["pass"]                 = Config::MQTT_PASS;
    mqtt["use_tls"]              = Config::MQTT_USE_TLS;
    mqtt["telemetry_interval_ms"]= Config::MQTT_PUBLISH_INTERVAL;
    mqtt["mqtt_disconnect_emergency_stop"] = Config::MQTT_DISCONNECT_EMERGENCY_STOP;
    
    JsonObject hardware = doc.createNestedObject("hardware");
    JsonArray inputs = hardware.createNestedArray("inputs");
    for (const auto& pin : Config::HardwareInputs) {
        JsonObject p = inputs.createNestedObject();
        p["pin"]         = pin.pin;
        p["type"]        = pin.type;
        p["pull"]        = pin.pull;
        p["name"]        = pin.name;
        p["invert"]      = pin.invert;
        p["debounce_ms"] = pin.debounce_ms;
        p["interrupt"]   = pin.interrupt;
        p["analog_min"]  = pin.analog_min;
        p["analog_max"]  = pin.analog_max;
        p["protocol"]    = pin.protocol != "" ? pin.protocol : "GPIO";
        char addrBuf[8];
        sprintf(addrBuf, "0x%02X", pin.i2c_addr ? pin.i2c_addr : 0x20);
        p["i2c_addr"]    = String(addrBuf);
    }
    
    JsonArray outputs = hardware.createNestedArray("outputs");
    for (const auto& pin : Config::HardwareOutputs) {
        JsonObject p = outputs.createNestedObject();
        p["pin"] = pin.pin;
        p["type"] = pin.type;
        p["name"] = pin.name;
        p["protocol"] = pin.protocol != "" ? pin.protocol : "GPIO_OUT";
        char addrBuf[8];
        sprintf(addrBuf, "0x%02X", pin.i2c_addr ? pin.i2c_addr : 0x20);
        p["i2c_addr"] = String(addrBuf);
        p["active_low"] = pin.active_low;
    }
    
    JsonArray modbus = hardware.createNestedArray("modbus");
    for (const auto& ms : Config::HardwareModbus) {
        JsonObject m = modbus.createNestedObject();
        m["name"]     = ms.name;
        m["slave_id"] = ms.slave_id;
        m["baudrate"] = ms.baudrate;
        m["transport"] = ms.transport;
        m["ip_address"] = ms.ip_address;
        m["port"] = ms.port;
        JsonArray regs = m.createNestedArray("registers");
        for (const auto& r : ms.registers) {
            JsonObject reg = regs.createNestedObject();
            reg["address"]    = r.address;
            reg["name"]       = r.name;
            reg["multiplier"] = r.multiplier;
            reg["type"]       = r.type;
            reg["length"]     = r.length;
            reg["data_type"]  = r.data_type;
        }
    }

    JsonArray sensors = hardware.createNestedArray("sensors");
    for (const auto& s : Config::HardwareSensors) {
        JsonObject sensorObj = sensors.createNestedObject();
        sensorObj["name"] = s.name;
        sensorObj["protocol"] = s.protocol;
        for (const auto& pair : s.params) {
            sensorObj[pair.first] = pair.second;
        }
    }

    // RS485 pins
    doc["hardware"]["rs485_rx"] = Config::PIN_RS485_RX;
    doc["hardware"]["rs485_tx"] = Config::PIN_RS485_TX;
    doc["hardware"]["rs485_de"] = Config::PIN_RS485_DE;
    doc["hardware"]["rs485_parity"] = Config::PARITY;

    // I2C global pins (flat, same style as RS485)
    doc["hardware"]["i2c_sda_pin"] = Config::PIN_I2C_SDA;
    doc["hardware"]["i2c_scl_pin"] = Config::PIN_I2C_SCL;
    
    String out;
    serializeJson(doc, out);
    return ConfigManager::saveConfig(out);
}

// ==================== HELPER FUNCTIONS ====================
String WebConfigPortal::generateToken() {
    String t = "";
    for(int i=0; i<32; i++) {
        t += String(esp_random() % 16, HEX);
    }
    return t;
}

bool WebConfigPortal::checkAuthToken() {
    if (!server.hasHeader("Authorization")) return false;
    String authHeader = server.header("Authorization");
    if (!authHeader.startsWith("Bearer ")) return false;
    
    String reqToken = authHeader.substring(7);
    return (reqToken == Config::AUTH_TOKEN && Config::AUTH_TOKEN.length() > 0);
}

// ==================== START PORTAL ====================
void WebConfigPortal::startAP() {
    Logger::portal("Starting Captive Portal Access Point...");
    WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0));
    String apName = "ENYX-ENTERPRISE-" + Config::NODE_ID;
    WiFi.softAP(apName.c_str());

    dnsServer.start(DNS_PORT, "*", apIP);

    const char * headerKeys[] = {"Authorization"};
    server.collectHeaders(headerKeys, 1);

    server.on("/", HTTP_GET, handleRoot);
    server.serveStatic("/style.css", LittleFS, "/style.css");
    server.serveStatic("/script.js", LittleFS, "/script.js");
    server.serveStatic("/logo.svg", LittleFS, "/logo.svg");
    server.serveStatic("/favicon.svg", LittleFS, "/favicon.svg");
    
    server.on("/api/login", HTTP_POST, handleApiLogin);
    server.on("/api/fullconfig", HTTP_GET, handleApiFullConfigGet);
    server.on("/api/wifi", HTTP_POST, handleApiWifiPost);
    server.on("/api/mqtt", HTTP_POST, handleApiMqttPost);
    server.on("/api/device", HTTP_POST, handleApiDevicePost);
    server.on("/api/hardware", HTTP_POST, handleApiHardwarePost);
    server.on("/api/hardware/discover", HTTP_GET, handleApiHardwareDiscover);
    server.on("/api/modbus/start_scan", HTTP_POST, handleApiModbusStartScan);
    server.on("/api/modbus/cancel_scan", HTTP_POST, handleApiModbusCancelScan);
    server.on("/api/modbus/scan_reg", HTTP_GET, handleApiModbusScanReg);
    server.on("/api/modbus/scan_reg_batch", HTTP_POST, handleApiModbusScanRegBatch);
    server.on("/api/account", HTTP_POST, handleApiAccountPost);
    server.on("/api/status", HTTP_GET, handleApiStatusGet);
    server.on("/api/ota", HTTP_POST, handleApiOtaUpdate, handleApiOtaUpload);
    server.on("/api/publish_discovery", HTTP_POST, handleApiPublishDiscovery);
    server.on("/api/config/export", HTTP_GET, handleApiConfigExport);
    server.on("/api/config/import", HTTP_POST, handleApiConfigImport);
    server.on("/api/telemetry/latest", HTTP_GET, handleApiTelemetryLatest); // GAP #12
    
    server.on("/api/root/health", HTTP_GET, []() {
        server.send(200, "application/json", "{\"status\":\"alive\",\"uptime_s\":" + String(millis()/1000) + "}");
    });
    
    server.onNotFound(handleNotFound);

    server.begin();
    portalActive = true;
    Logger::portal("Captive Portal Started at %s. SSID: 'ENYX-ENTERPRISE-%s'", apIP.toString().c_str(), Config::NODE_ID.c_str());
}

void WebConfigPortal::loop() {
    if (portalActive) {
        dnsServer.processNextRequest();
        server.handleClient();
    }
}

// ==================== HANDLERS ====================
void WebConfigPortal::handleRoot() {
    // GAP #14: If not logged in, serve login page instead
    if (!checkAuthToken() && Config::AUTH_TOKEN.length() > 0) {
        // For now, use the same index.html and let JS handle login
        // In production, redirect to /login.html
    }
    File file = LittleFS.open("/index.html", "r");
    if (!file) {
        server.send(500, "text/plain", "Error: index.html not found in LittleFS!");
        return;
    }
    server.streamFile(file, "text/html");
    file.close();
}

void WebConfigPortal::handleApiLogin() {
    // GAP #4: Rate limit
    IPAddress clientIP = server.client().remoteIP();
    for (auto& attempt : loginAttempts) {
        if (attempt.ip == clientIP) {
            if (millis() < attempt.blockUntil) {
                server.send(429, "application/json", 
                    "{\"error\":\"Too many attempts. Try again later.\"}");
                return;
            }
            break;
        }
    }
    
    if (!server.hasArg("user") || !server.hasArg("pass")) {
        server.send(400, "application/json", "{\"error\":\"Missing credentials\"}");
        return;
    }
    
    if (server.arg("user") == Config::ADMIN_USER && server.arg("pass") == Config::ADMIN_PASS) {
        // Reset attempts on success
        for (auto& attempt : loginAttempts) {
            if (attempt.ip == clientIP) {
                attempt.attempts = 0;
                attempt.blockUntil = 0;
            }
        }
        
        Config::AUTH_TOKEN = generateToken();
        saveFullConfig();
        
        server.send(200, "application/json", "{\"token\":\"" + Config::AUTH_TOKEN + "\"}");
    } else {
        // Track failed attempt
        bool found = false;
        for (auto& attempt : loginAttempts) {
            if (attempt.ip == clientIP) {
                attempt.attempts++;
                if (attempt.attempts >= Config::MAX_LOGIN_ATTEMPTS) {
                    attempt.blockUntil = millis() + Config::LOGIN_BLOCK_TIME_MS;
                }
                found = true;
                break;
            }
        }
        if (!found) {
            loginAttempts.push_back({clientIP, 1, 0});
        }
        
        server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    }
}

void WebConfigPortal::handleApiStatusGet() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    StaticJsonDocument<2048> doc;
    doc["status"] = WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected";
    doc["ip"] = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : "Not Connected";
    doc["rssi"] = WiFi.status() == WL_CONNECTED ? WiFi.RSSI() : 0;
    
    doc["mqtt_conn"] = MqttManager::isConnected() ? "Connected" : "Disconnected";
    doc["topic_telemetry"] = Config::TOPIC_TELEMETRY;
    doc["topic_control"] = Config::TOPIC_ACTUATOR;
    doc["fw_version"] = Config::FW_VERSION;
    
    doc["uptime_s"] = millis() / 1000;
    doc["cpu_mhz"] = ESP.getCpuFreqMHz();
    doc["heap_free"] = ESP.getFreeHeap();
    doc["heap_total"] = ESP.getHeapSize();

    JsonArray logsArray = doc.createNestedArray("mqtt_logs");
    std::vector<String> logs = MqttManager::getLogs();
    for (const auto& log : logs) {
        logsArray.add(log);
    }
    
    String out;
    serializeJson(doc, out);
    server.send(200, "application/json", out);
}

void WebConfigPortal::handleApiFullConfigGet() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    DynamicJsonDocument doc(8192);
    
    doc["device"]["node_id"]    = Config::NODE_ID;
    doc["device"]["fw_version"] = Config::FW_VERSION;
    
    // Security — kirim tanpa admin_pass untuk keamanan
    doc["security"]["admin_user"] = Config::ADMIN_USER;
    
    // WiFi — gunakan struktur sama dengan loadConfig
    doc["protocols"]["wifi"]["ssid"]         = Config::WIFI_SSID;
    doc["protocols"]["wifi"]["eap_identity"] = Config::WIFI_EAP_IDENTITY;
    // password & eap_password tidak dikirim ke browser (security)
    
    // MQTT
    doc["protocols"]["mqtt"]["server"]                = Config::MQTT_SERVER;
    doc["protocols"]["mqtt"]["port"]                  = Config::MQTT_PORT;
    doc["protocols"]["mqtt"]["topic_prefix"]          = Config::MQTT_TOPIC_PREFIX;
    doc["protocols"]["mqtt"]["user"]                  = Config::MQTT_USER;
    doc["protocols"]["mqtt"]["use_tls"]               = Config::MQTT_USE_TLS;
    doc["protocols"]["mqtt"]["telemetry_interval_ms"] = Config::MQTT_PUBLISH_INTERVAL;
    doc["protocols"]["mqtt"]["mqtt_disconnect_emergency_stop"] = Config::MQTT_DISCONNECT_EMERGENCY_STOP;
    
    // Hardware Inputs
    JsonArray inputs = doc["hardware"].createNestedArray("inputs");
    for (const auto& pin : Config::HardwareInputs) {
        JsonObject p = inputs.createNestedObject();
        p["pin"]         = pin.pin;
        p["type"]        = pin.type;
        p["pull"]        = pin.pull;
        p["name"]        = pin.name;
        p["invert"]      = pin.invert;
        p["debounce_ms"] = pin.debounce_ms;
        p["interrupt"]   = pin.interrupt;
        p["analog_min"]  = pin.analog_min;
        p["analog_max"]  = pin.analog_max;
        p["protocol"]    = pin.protocol != "" ? pin.protocol : "GPIO";
        char addrBuf[8];
        sprintf(addrBuf, "0x%02X", pin.i2c_addr ? pin.i2c_addr : 0x20);
        p["i2c_addr"]    = String(addrBuf);
    }
    
    // Hardware Outputs
    JsonArray outputs = doc["hardware"].createNestedArray("outputs");
    for (const auto& pin : Config::HardwareOutputs) {
        JsonObject p = outputs.createNestedObject();
        p["pin"] = pin.pin;
        p["type"] = pin.type;
        p["name"] = pin.name;
        p["protocol"] = pin.protocol != "" ? pin.protocol : "GPIO_OUT";
        char addrBuf[8];
        sprintf(addrBuf, "0x%02X", pin.i2c_addr ? pin.i2c_addr : 0x20);
        p["i2c_addr"] = String(addrBuf);
        p["active_low"] = pin.active_low;
    }
    
    // Modbus
    JsonArray modbus = doc["hardware"].createNestedArray("modbus");
    for (const auto& ms : Config::HardwareModbus) {
        JsonObject m = modbus.createNestedObject();
        m["name"]     = ms.name;
        m["slave_id"] = ms.slave_id;
        m["baudrate"] = ms.baudrate;
        m["transport"] = ms.transport;
        m["ip_address"] = ms.ip_address;
        m["port"] = ms.port;
        JsonArray regs = m.createNestedArray("registers");
        for (const auto& r : ms.registers) {
            JsonObject reg = regs.createNestedObject();
            reg["address"]    = r.address;
            reg["name"]       = r.name;
            reg["multiplier"] = r.multiplier;
            reg["type"]       = r.type;
            reg["length"]     = r.length;
            reg["data_type"]  = r.data_type;
        }
    }

    // RS485 pins
    doc["hardware"]["rs485_rx"] = Config::PIN_RS485_RX;
    doc["hardware"]["rs485_tx"] = Config::PIN_RS485_TX;
    doc["hardware"]["rs485_de"] = Config::PIN_RS485_DE;
    doc["hardware"]["rs485_parity"] = Config::PARITY;
    
    // I2C global pins (flat, same style as RS485)
    doc["hardware"]["i2c_sda_pin"] = Config::PIN_I2C_SDA;
    doc["hardware"]["i2c_scl_pin"] = Config::PIN_I2C_SCL;

    // Sensors (I2C / 1-Wire / SPI)
    JsonArray sensors = doc["hardware"].createNestedArray("sensors");
    for (const auto& s : Config::HardwareSensors) {
        JsonObject sensorObj = sensors.createNestedObject();
        sensorObj["name"] = s.name;
        sensorObj["protocol"] = s.protocol;
        for (const auto& pair : s.params) {
            sensorObj[pair.first] = pair.second;
        }
    }

    // I2C global pin configuration
    JsonObject i2c = doc["hardware"].createNestedObject("i2c");
    i2c["sda_pin"] = Config::PIN_I2C_SDA;
    i2c["scl_pin"] = Config::PIN_I2C_SCL;

    String out;
    serializeJson(doc, out);
    server.send(200, "application/json", out);
}

void WebConfigPortal::handleApiWifiPost() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    if (!server.hasArg("ssid") || server.arg("ssid").length() == 0) {
        server.send(400, "application/json", "{\"error\":\"SSID is required\"}");
        return;
    }
    if (server.hasArg("eap_identity") && server.arg("eap_identity").length() > 0 && (!server.hasArg("eap_password") || server.arg("eap_password").length() == 0)) {
        server.send(400, "application/json", "{\"error\":\"Enterprise password is required when identity is set\"}");
        return;
    }
    if (server.hasArg("ssid")) { Config::WIFI_SSID = server.arg("ssid"); Config::WIFI_SSID.trim(); }
    if (server.hasArg("pass")) { Config::WIFI_PASS = server.arg("pass"); Config::WIFI_PASS.trim(); }
    if (server.hasArg("eap_identity")) { Config::WIFI_EAP_IDENTITY = server.arg("eap_identity"); Config::WIFI_EAP_IDENTITY.trim(); }
    if (server.hasArg("eap_password")) { Config::WIFI_EAP_PASSWORD = server.arg("eap_password"); Config::WIFI_EAP_PASSWORD.trim(); }
    
    if (saveFullConfig()) {
        server.send(200, "application/json", "{\"status\":\"ok\",\"reboot\":true}");
        ESP.restart();
    } else {
        server.send(500, "application/json", "{\"error\":\"Failed to save config\"}");
    }
}

void WebConfigPortal::handleApiMqttPost() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    if (server.hasArg("server")) { Config::MQTT_SERVER = server.arg("server"); Config::MQTT_SERVER.trim(); }
    if (server.hasArg("port")) Config::MQTT_PORT = server.arg("port").toInt();
    if (server.hasArg("topic_prefix")) { Config::MQTT_TOPIC_PREFIX = server.arg("topic_prefix"); Config::MQTT_TOPIC_PREFIX.trim(); }
    if (server.hasArg("user")) { Config::MQTT_USER = server.arg("user"); Config::MQTT_USER.trim(); }
    if (server.hasArg("pass")) { Config::MQTT_PASS = server.arg("pass"); Config::MQTT_PASS.trim(); }
    if (server.hasArg("telemetry_interval_ms")) Config::MQTT_PUBLISH_INTERVAL = server.arg("telemetry_interval_ms").toInt();
    if (server.hasArg("use_tls")) Config::MQTT_USE_TLS = server.arg("use_tls") == "true";
    if (server.hasArg("mqtt_disconnect_emergency_stop")) Config::MQTT_DISCONNECT_EMERGENCY_STOP = server.arg("mqtt_disconnect_emergency_stop") == "true";
    
    if (saveFullConfig()) {
        server.send(200, "application/json", "{\"status\":\"ok\",\"reboot\":true,\"message\":\"Rebooting to apply\"}");
        ESP.restart();
    } else {
        server.send(500, "application/json", "{\"error\":\"Failed to save config\"}");
    }
}

void WebConfigPortal::handleApiDevicePost() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    if (server.hasArg("node_id")) { Config::NODE_ID = server.arg("node_id"); Config::NODE_ID.trim(); }
    
    if (server.hasArg("rs485_rx")) { Config::PIN_RS485_RX = server.arg("rs485_rx").toInt(); }
    if (server.hasArg("rs485_tx")) { Config::PIN_RS485_TX = server.arg("rs485_tx").toInt(); }
    if (server.hasArg("rs485_de")) { Config::PIN_RS485_DE = server.arg("rs485_de").toInt(); }
    if (server.hasArg("rs485_parity")) { Config::PARITY = server.arg("rs485_parity").toInt(); }

    if (saveFullConfig()) {
        server.send(200, "application/json", "{\"status\":\"ok\",\"reboot\":true,\"message\":\"Device config updated. Rebooting...\"}");
        ESP.restart();
    } else {
        server.send(500, "application/json", "{\"error\":\"Failed to save config\"}");
    }
}

void WebConfigPortal::handleApiHardwarePost() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    if (server.hasArg("payload")) {
        DynamicJsonDocument pdoc(4096);
        DeserializationError err = deserializeJson(pdoc, server.arg("payload"));
        if (!err && pdoc.is<JsonObject>()) {
            
            if (pdoc["inputs"].is<JsonArray>()) {
                Config::HardwareInputs.clear();
                for (JsonObject gpio : pdoc["inputs"].as<JsonArray>()) {
                    Config::InputPin pin;
                    pin.pin = gpio["pin"].as<uint8_t>();
                    pin.type = gpio["type"].as<String>(); pin.type.trim();
                    pin.pull = gpio["pull"].as<String>(); pin.pull.trim();
                    pin.name = gpio["name"].as<String>(); pin.name.trim();
                    pin.debounce_ms = gpio["debounce_ms"].as<uint16_t>();
                    pin.interrupt = gpio["interrupt"].as<String>(); pin.interrupt.trim();
                    pin.invert = gpio["invert"].as<bool>();
                    pin.protocol = gpio["protocol"].as<String>(); pin.protocol.trim();
                    if (pin.protocol == "") pin.protocol = "GPIO";
                    if (gpio.containsKey("i2c_addr")) {
                        if (gpio["i2c_addr"].is<const char*>() || gpio["i2c_addr"].is<String>()) {
                            pin.i2c_addr = (uint8_t)strtoul(gpio["i2c_addr"].as<const char*>(), NULL, 0);
                        } else {
                            pin.i2c_addr = gpio["i2c_addr"].as<uint8_t>();
                        }
                    } else {
                        pin.i2c_addr = 0x20;
                    }
                    Config::HardwareInputs.push_back(pin);
                }
            }
            
            if (pdoc["outputs"].is<JsonArray>()) {
                Config::HardwareOutputs.clear();
                for (JsonObject gpio : pdoc["outputs"].as<JsonArray>()) {
                    Config::OutputPin pin;
                    pin.pin = gpio["pin"].as<uint8_t>();
                    pin.type = gpio["type"].as<String>(); pin.type.trim();
                    pin.name = gpio["name"].as<String>(); pin.name.trim();
                    pin.protocol = gpio["protocol"].as<String>(); pin.protocol.trim();
                    if (pin.protocol == "") pin.protocol = "GPIO_OUT";
                    if (gpio.containsKey("i2c_addr")) {
                        if (gpio["i2c_addr"].is<const char*>() || gpio["i2c_addr"].is<String>()) {
                            pin.i2c_addr = (uint8_t)strtoul(gpio["i2c_addr"].as<const char*>(), NULL, 0);
                        } else {
                            pin.i2c_addr = gpio["i2c_addr"].as<uint8_t>();
                        }
                    } else {
                        pin.i2c_addr = 0x20;
                    }
                    pin.active_low = gpio.containsKey("active_low") ? gpio["active_low"].as<bool>() : true;
                    Config::HardwareOutputs.push_back(pin);
                }
            }
            
            if (pdoc["modbus"].is<JsonArray>()) {
                Config::HardwareModbus.clear();
                for (JsonObject msj : pdoc["modbus"].as<JsonArray>()) {
                    Config::ModbusSensor ms;
                    ms.name = msj["name"].as<String>(); ms.name.trim();
                    ms.slave_id = msj["slave_id"].as<uint8_t>();
                    ms.baudrate = msj["baudrate"].as<uint32_t>();
                    ms.transport = msj["transport"].as<String>(); ms.transport.trim();
                    if (ms.transport == "") ms.transport = "RTU";
                    ms.ip_address = msj["ip_address"].as<String>(); ms.ip_address.trim();
                    if (msj["port"].is<uint32_t>()) ms.port = (uint16_t)msj["port"].as<uint32_t>();
                    else if (msj["port"].is<const char*>()) ms.port = (uint16_t)atoi(msj["port"].as<const char*>());
                    else ms.port = 502;
                    if (ms.transport == "TCP" && ms.ip_address == "") ms.ip_address = "192.168.1.100";
                    if (msj["registers"].is<JsonArray>()) {
                        for (JsonObject regj : msj["registers"].as<JsonArray>()) {
                            Config::ModbusRegister reg;
                            reg.address = regj["address"].as<uint16_t>();
                            reg.name = regj["name"].as<String>(); reg.name.trim();
                            reg.multiplier = regj["multiplier"].as<float>();
                            reg.type = regj["type"].as<String>(); reg.type.trim();
                            reg.length = regj["length"].as<uint8_t>();
                            reg.data_type = regj["data_type"].as<String>(); reg.data_type.trim();
                            ms.registers.push_back(reg);
                        }
                    }
                    Config::HardwareModbus.push_back(ms);
                }
            }

             if (pdoc["sensors"].is<JsonArray>()) {
                 Config::HardwareSensors.clear();
                 for (JsonObject sj : pdoc["sensors"].as<JsonArray>()) {
                     Config::GenericSensor sensor;
                     sensor.name = sj["name"].as<String>(); sensor.name.trim();
                     sensor.protocol = sj["protocol"].as<String>(); sensor.protocol.trim();
                     for (JsonPair pair : sj) {
                         String key = pair.key().c_str();
                         if (key != "name" && key != "protocol") {
                             sensor.params[key] = pair.value().as<String>();
                         }
                     }
                     Config::HardwareSensors.push_back(sensor);
                 }
             }

             // I2C global pin configuration (flat, same style as RS485)
             if (pdoc.containsKey("i2c_sda_pin")) {
                 Config::PIN_I2C_SDA = pdoc["i2c_sda_pin"].as<uint8_t>();
             }
             if (pdoc.containsKey("i2c_scl_pin")) {
                 Config::PIN_I2C_SCL = pdoc["i2c_scl_pin"].as<uint8_t>();
             }
             if (Config::PIN_I2C_SDA > 39 || Config::PIN_I2C_SCL > 39) {
                 server.send(400, "application/json", "{\"error\":\"Invalid I2C pins. SDA and SCL must be GPIO 0-39.\"}");
                 return;
             }

            if (saveFullConfig()) {
                HardwareManager::reloadConfiguration();
                server.send(200, "application/json", "{\"status\":\"ok\",\"reboot\":false,\"message\":\"Hardware config updated dynamically (Hot-Swapped)!\"}");
            } else {
                server.send(500, "application/json", "{\"error\":\"Failed to save config\"}");
            }
        } else {
            server.send(400, "application/json", "{\"error\":\"Invalid JSON format\"}");
        }
    } else {
        server.send(400, "application/json", "{\"error\":\"Missing payload\"}");
    }
}

void WebConfigPortal::handleApiModbusStartScan() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    std::vector<uint32_t> bauds;
    if (server.hasArg("bauds")) {
        String baudsStr = server.arg("bauds");
        baudsStr.trim();
        while (baudsStr.length() > 0) {
            int comma = baudsStr.indexOf(',');
            String part;
            if (comma >= 0) {
                part = baudsStr.substring(0, comma);
                baudsStr = baudsStr.substring(comma + 1);
            } else {
                part = baudsStr;
                baudsStr = "";
            }
            part.trim();
            if (part.length() > 0) {
                bauds.push_back((uint32_t)part.toInt());
            }
        }
    }
    if (bauds.empty() && server.hasArg("baud")) {
        bauds.push_back((uint32_t)server.arg("baud").toInt());
    }
    if (bauds.empty()) {
        server.send(400, "application/json", "{\"error\":\"Missing baud/bauds\"}");
        return;
    }
    
    String jsonResult = HardwareManager::runFullScanSync(bauds);
    String response = "{\"status\":\"completed\",\"found_ids\":" + jsonResult + "}";
    return server.send(200, "application/json", response);
}

void WebConfigPortal::handleApiModbusCancelScan() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    HardwareManager::requestScanCancel();
    server.send(200, "application/json", "{\"status\":\"cancelled\"}");
}

void WebConfigPortal::handleApiModbusScanReg() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    if (server.hasArg("scan_reg") && server.hasArg("id") && server.hasArg("baud") && server.hasArg("type")) {
        uint8_t id = server.arg("id").toInt();
        uint32_t baud = server.arg("baud").toInt();
        uint16_t reg = server.arg("scan_reg").toInt();
        String type = server.arg("type");
        type.trim();
        uint8_t length = server.hasArg("length") ? (uint8_t)server.arg("length").toInt() : 1;
        if (length == 0) length = 1;
        if (length > 4) length = 4;
        bool success = false;
        uint16_t val = HardwareManager::scanModbusReg(id, baud, reg, type, length, success);
        String json = "{\"reg\":" + String(reg) + ",\"length\":" + String(length) + ",\"success\":" + (success ? "true" : "false") + ",\"val\":" + String(val) + "}";
        return server.send(200, "application/json", json);
    }
    
    server.send(400, "application/json", "{\"error\":\"Invalid parameters\"}");
}

void WebConfigPortal::handleApiModbusScanRegBatch() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    if (server.hasArg("id") && server.hasArg("baud") && server.hasArg("type") && 
        server.hasArg("start_reg") && server.hasArg("end_reg")) {
        uint8_t id = server.arg("id").toInt();
        uint32_t baud = server.arg("baud").toInt();
        uint16_t startReg = server.arg("start_reg").toInt();
        uint16_t endReg = server.arg("end_reg").toInt();
        String type = server.arg("type");
        type.trim();
        uint8_t length = server.hasArg("length") ? (uint8_t)server.arg("length").toInt() : 1;
        if (length == 0) length = 1;
        if (length > 4) length = 4;
        if (endReg < startReg) endReg = startReg;
        String result = HardwareManager::scanModbusRegBatch(id, baud, startReg, endReg, type, length);
        String json = "{\"status\":\"completed\",\"results\":" + result + "}";
        return server.send(200, "application/json", json);
    }
    
    server.send(400, "application/json", "{\"error\":\"Invalid parameters\"}");
}

void WebConfigPortal::handleApiAccountPost() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    if (server.hasArg("user")) { Config::ADMIN_USER = server.arg("user"); Config::ADMIN_USER.trim(); }
    if (server.hasArg("pass")) { Config::ADMIN_PASS = server.arg("pass"); Config::ADMIN_PASS.trim(); }
    Config::AUTH_TOKEN = ""; // Force re-login
    
    if (saveFullConfig()) {
        server.send(200, "application/json", "{\"status\":\"ok\",\"reboot\":true,\"message\":\"Account updated. Rebooting...\"}");
        ESP.restart();
    } else {
        server.send(500, "application/json", "{\"error\":\"Failed to save config\"}");
    }
}

void WebConfigPortal::handleNotFound() {
    // Captive Portal behavior: redirect to portal IP
    server.sendHeader("Location", String("http://") + apIP.toString(), true);
    server.send(302, "text/plain", "");
}

void WebConfigPortal::handleApiOtaUpdate() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    server.sendHeader("Connection", "close");
    if (Update.hasError()) {
        server.send(500, "application/json", "{\"error\":\"" + String(Update.errorString()) + "\"}");
    } else {
        server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"OTA update completed. Rebooting...\"}");
        ESP.restart();
    }
}

void WebConfigPortal::handleApiOtaUpload() {
    if (!checkAuthToken()) {
        HTTPUpload& upload = server.upload();
        (void)upload;
        return;
    }

    HTTPUpload& upload = server.upload();
    if (upload.status == UPLOAD_FILE_START) {
        Logger::portal("OTA Update Start: %s", upload.filename.c_str());
        if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
            Update.printError(Serial);
        }
    } else if (upload.status == UPLOAD_FILE_WRITE) {
        if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
            Update.printError(Serial);
        }
    } else if (upload.status == UPLOAD_FILE_END) {
        if (Update.end(true)) {
            Logger::portal("OTA Update Success: %u bytes", upload.totalSize);
        } else {
            Update.printError(Serial);
        }
    }
}

void WebConfigPortal::handleApiPublishDiscovery() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    if (MqttManager::isConnected()) {
        MqttManager::publishDiscovery();
        server.send(200, "application/json", "{\"status\":\"success\",\"message\":\"Discovery signal sent successfully\"}");
    } else {
        server.send(503, "application/json", "{\"status\":\"error\",\"message\":\"MQTT Broker not connected\"}");
    }
}

void WebConfigPortal::handleApiConfigExport() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    File file = LittleFS.open("/config.json", "r");
    if (!file) {
        server.send(500, "application/json", "{\"error\":\"Failed to open config.json\"}");
        return;
    }

    String contents = file.readString();
    file.close();

    DynamicJsonDocument doc(8192);
    DeserializationError err = deserializeJson(doc, contents);
    if (err) {
        server.send(500, "application/json", "{\"error\":\"Failed to parse config.json\"}");
        return;
    }

    doc["security"].remove("admin_pass");
    doc["security"].remove("auth_token");
    doc["protocols"]["wifi"].remove("password");
    doc["protocols"]["wifi"].remove("eap_password");
    doc["protocols"]["mqtt"].remove("pass");
    doc["protocols"]["mqtt"].remove("user");

    String out;
    serializeJson(doc, out);
    server.sendHeader("Content-Disposition", "attachment; filename=config.json");
    server.send(200, "application/json", out);
}

void WebConfigPortal::handleApiConfigImport() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    
    if (!server.hasArg("payload")) {
        server.send(400, "application/json", "{\"error\":\"Missing config payload\"}");
        return;
    }
    
    String payload = server.arg("payload");
    
    // Validasi JSON format
    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, payload);
    if (error) {
        server.send(400, "application/json", "{\"error\":\"Invalid JSON format\"}");
        return;
    }

    if (ConfigManager::saveConfig(payload)) {
        ConfigManager::loadConfig();
        HardwareManager::reloadConfiguration();
        server.send(200, "application/json", "{\"status\":\"success\",\"reboot\":false,\"message\":\"Configuration imported successfully and hot-swapped!\"}");
    } else {
        server.send(500, "application/json", "{\"error\":\"Failed to save configuration\"}");
    }
}

// GAP #12: REST fallback endpoint untuk telemetry
void WebConfigPortal::handleApiTelemetryLatest() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    server.send(200, "application/json", HardwareManager::getLatestTelemetryJson());
}

void WebConfigPortal::handleApiHardwareDiscover() {
    if (!checkAuthToken()) return server.send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    String results = HardwareManager::discoverSensors();
    server.send(200, "application/json", "{\"status\":\"ok\",\"discovered\":" + results + "}");
}