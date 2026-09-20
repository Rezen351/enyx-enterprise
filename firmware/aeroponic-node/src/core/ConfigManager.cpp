#include "ConfigManager.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"
#include <ArduinoJson.h>
#include <LittleFS.h>
#include <WiFi.h>
#include "esp_partition.h"

void ConfigManager::init() {
    Logger::config("Mounting LittleFS...");

    const esp_partition_t* part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, "spiffs");
    if (part == NULL) {
        Logger::error("LittleFS: Partition 'spiffs' NOT found in flash!");
        Logger::error("Re-flash firmware + partition table, then run 'uploadfs'.");
        Logger::config("Using default compiled configs.");
        return;
    }
    Logger::config("LittleFS: Partition found at 0x%06X, size %u bytes",
                   part->address, part->size);

    if (!LittleFS.begin(true)) {
        Logger::error("LittleFS mount failed even after format attempt.");
        Logger::config("Using default compiled configs.");
        return;
    }

    Logger::config("LittleFS mounted successfully.");

    if (!loadConfig()) {
        Logger::config("Failed to load config.json. Using default compiled configs.");
    }
    Logger::config("Loaded admin user: %s", Config::ADMIN_USER.c_str());
    Logger::config("Loaded admin pass: %s", Config::ADMIN_PASS.c_str());
}

bool ConfigManager::loadConfig() {
    File file = LittleFS.open("/config.json", "r");
    if (!file) {
        return false;
    }

    DynamicJsonDocument doc(4096);
    DeserializationError error = deserializeJson(doc, file);
    file.close();

    if (error) {
        Logger::config("Failed to parse config.json: %s", error.c_str());
        return false;
    }

    Logger::config("config.json loaded successfully. Applying core configurations...");

    // Device Metadata
    if (doc["device"]["node_id"]) {
        Config::NODE_ID = doc["device"]["node_id"].as<String>();
        Config::NODE_ID.trim();
    }
    if (doc["device"]["fw_version"]) {
        Config::FW_VERSION = doc["device"]["fw_version"].as<String>();
        Config::FW_VERSION.trim();
    }
    
    if (Config::NODE_ID == "" || Config::NODE_ID == "node-01") {
        String mac = WiFi.macAddress();
        mac.replace(":", "");
        Config::NODE_ID = mac;
    }

    // Security
    if (doc["security"]["admin_user"]) {
        Config::ADMIN_USER = doc["security"]["admin_user"].as<String>();
        Config::ADMIN_USER.trim();
    }
    if (doc["security"]["admin_pass"]) {
        Config::ADMIN_PASS = doc["security"]["admin_pass"].as<String>();
        Config::ADMIN_PASS.trim();
    }
    if (doc["security"]["auth_token"]) {
        Config::AUTH_TOKEN = doc["security"]["auth_token"].as<String>();
        Config::AUTH_TOKEN.trim();
    }

    // Use fixed defaults if not set in config.json.
    // GAP/SEC: never ship a hardcoded weak password. When no admin password is
    // configured we generate a random one at first boot and surface it on the
    // serial console so the operator can read & change it via the Web Portal.
    if (Config::ADMIN_USER == "") {
        Config::ADMIN_USER = "admin";
    }
    if (Config::ADMIN_PASS == "") {
        String generated = "";
        for (int i = 0; i < 12; i++) {
            generated += String(esp_random() % 16, HEX);
        }
        Config::ADMIN_PASS = generated;
        Logger::config("No admin password in config.json. Generated random password.");
        Logger::config("Change it via the Web Portal at your earliest convenience.");
    }

    // Protocols - WiFi
    if (doc["protocols"]["wifi"].is<JsonObject>()) {
        JsonObject wifi = doc["protocols"]["wifi"].as<JsonObject>();
        if (wifi.containsKey("ssid")) {
            Config::WIFI_SSID = wifi["ssid"].as<String>();
            Config::WIFI_SSID.trim();
        }
        if (wifi.containsKey("password")) {
            Config::WIFI_PASS = wifi["password"].as<String>();
            Config::WIFI_PASS.trim();
        }
        if (wifi.containsKey("eap_identity")) {
            Config::WIFI_EAP_IDENTITY = wifi["eap_identity"].as<String>();
            Config::WIFI_EAP_IDENTITY.trim();
        }
        if (wifi.containsKey("eap_password")) {
            Config::WIFI_EAP_PASSWORD = wifi["eap_password"].as<String>();
            Config::WIFI_EAP_PASSWORD.trim();
        }
    }

    // Protocols - MQTT
    if (doc["protocols"]["mqtt"]["server"]) {
        Config::MQTT_SERVER = doc["protocols"]["mqtt"]["server"].as<String>();
        Config::MQTT_SERVER.trim();
    }
    if (doc["protocols"]["mqtt"]["port"]) {
        Config::MQTT_PORT = doc["protocols"]["mqtt"]["port"].as<int>();
    }
    if (doc["protocols"]["mqtt"]["topic_prefix"]) {
        Config::MQTT_TOPIC_PREFIX = doc["protocols"]["mqtt"]["topic_prefix"].as<String>();
        Config::MQTT_TOPIC_PREFIX.trim();
    }
    if (doc["protocols"]["mqtt"]["user"]) {
        Config::MQTT_USER = doc["protocols"]["mqtt"]["user"].as<String>();
        Config::MQTT_USER.trim();
    }
    if (doc["protocols"]["mqtt"]["pass"]) {
        Config::MQTT_PASS = doc["protocols"]["mqtt"]["pass"].as<String>();
        Config::MQTT_PASS.trim();
    }
    if (doc["protocols"]["mqtt"]["telemetry_interval_ms"]) {
        Config::MQTT_PUBLISH_INTERVAL = doc["protocols"]["mqtt"]["telemetry_interval_ms"].as<uint32_t>();
    }

    // MQTT TLS
    if (doc["protocols"]["mqtt"]["use_tls"]) {
        Config::MQTT_USE_TLS = doc["protocols"]["mqtt"]["use_tls"].as<bool>();
    }
    if (doc["protocols"]["mqtt"]["mqtt_disconnect_emergency_stop"]) {
        Config::MQTT_DISCONNECT_EMERGENCY_STOP = doc["protocols"]["mqtt"]["mqtt_disconnect_emergency_stop"].as<bool>();
    }

    // Updating dynamic topics based on potentially new NODE_ID and TOPIC_PREFIX
    Config::TOPIC_TELEMETRY = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/telemetry";
    Config::TOPIC_ACTUATOR  = Config::MQTT_TOPIC_PREFIX + "/actuator/" + Config::NODE_ID;

    Logger::config("MQTT Topics:");
    Logger::config("  Telemetry : %s", Config::TOPIC_TELEMETRY.c_str());
    Logger::config("  Actuator  : %s", Config::TOPIC_ACTUATOR.c_str());

    // Hardware
    Config::HardwareInputs.clear();
    if (doc["hardware"]["inputs"].is<JsonArray>()) {
        JsonArray inputs = doc["hardware"]["inputs"].as<JsonArray>();
        for (JsonObject input : inputs) {
            Config::InputPin pin;
            pin.pin = input["pin"].as<uint8_t>();
            pin.type = input["type"].as<String>(); pin.type.trim();
            pin.pull = input["pull"].as<String>(); pin.pull.trim();
            pin.name = input["name"].as<String>(); pin.name.trim();
            pin.invert = input["invert"] | false;
            pin.debounce_ms = input["debounce_ms"] | 0;
            pin.interrupt = input["interrupt"] | "NONE"; pin.interrupt.trim();
            pin.analog_min = input["analog_min"] | 0;
            pin.analog_max = input["analog_max"] | 4095;
            pin.protocol = input["protocol"].as<String>(); pin.protocol.trim();
            if (pin.protocol == "") pin.protocol = "GPIO";
            if (input.containsKey("i2c_addr")) {
                if (input["i2c_addr"].is<const char*>() || input["i2c_addr"].is<String>()) {
                    pin.i2c_addr = (uint8_t)strtoul(input["i2c_addr"].as<const char*>(), NULL, 0);
                } else {
                    pin.i2c_addr = input["i2c_addr"].as<uint8_t>();
                }
            } else {
                pin.i2c_addr = 0x20;
            }
            Config::HardwareInputs.push_back(pin);
        }
    }

    Config::HardwareOutputs.clear();
    if (doc["hardware"]["outputs"].is<JsonArray>()) {
        JsonArray outputs = doc["hardware"]["outputs"].as<JsonArray>();
        for (JsonObject output : outputs) {
            Config::OutputPin pin;
            pin.pin = output["pin"].as<uint8_t>();
            pin.type = output["type"].as<String>(); pin.type.trim();
            pin.name = output["name"].as<String>(); pin.name.trim();
            pin.protocol = output["protocol"].as<String>(); pin.protocol.trim();
            if (pin.protocol == "") pin.protocol = "GPIO_OUT";
            if (output.containsKey("i2c_addr")) {
                if (output["i2c_addr"].is<const char*>() || output["i2c_addr"].is<String>()) {
                    pin.i2c_addr = (uint8_t)strtoul(output["i2c_addr"].as<const char*>(), NULL, 0);
                } else {
                    pin.i2c_addr = output["i2c_addr"].as<uint8_t>();
                }
            } else {
                pin.i2c_addr = 0x20;
            }
            pin.active_low = output.containsKey("active_low") ? output["active_low"].as<bool>() : true;
            Config::HardwareOutputs.push_back(pin);
        }
    }

    Config::HardwareModbus.clear();
    if (doc["hardware"]["modbus"].is<JsonArray>()) {
        JsonArray modbuses = doc["hardware"]["modbus"].as<JsonArray>();
        for (JsonObject m : modbuses) {
            Config::ModbusSensor ms;
            ms.name = m["name"].as<String>(); ms.name.trim();
            ms.slave_id = m["slave_id"].as<uint8_t>();
            ms.baudrate = m["baudrate"].as<uint32_t>();
            ms.transport = m["transport"].as<String>(); ms.transport.trim();
            if (ms.transport == "") ms.transport = "RTU";
            ms.ip_address = m["ip_address"].as<String>(); ms.ip_address.trim();
            if (m["port"].is<uint32_t>()) ms.port = (uint16_t)m["port"].as<uint32_t>();
            else if (m["port"].is<const char*>()) ms.port = (uint16_t)atoi(m["port"].as<const char*>());
            else ms.port = 502;
            if (ms.transport == "TCP" && ms.ip_address == "") ms.ip_address = "192.168.1.100";
            
            if (m["registers"].is<JsonArray>()) {
                JsonArray registers = m["registers"].as<JsonArray>();
                for (JsonObject r : registers) {
                    Config::ModbusRegister reg;
                    reg.address = r["address"].as<uint16_t>();
                    reg.name = r["name"].as<String>(); reg.name.trim();
                    reg.multiplier = r["multiplier"].as<float>();
                    reg.type = r["type"].as<String>(); reg.type.trim();
                    reg.length = r["length"].as<uint8_t>();
                    reg.data_type = r["data_type"].as<String>(); reg.data_type.trim();
                    if (reg.length == 0) reg.length = 1;
                    if (reg.data_type == "") reg.data_type = "UINT16";
                    ms.registers.push_back(reg);
                }
            }
            Config::HardwareModbus.push_back(ms);
        }
    }

    Config::HardwareSensors.clear();
    if (doc["hardware"]["sensors"].is<JsonArray>()) {
        JsonArray sensors = doc["hardware"]["sensors"].as<JsonArray>();
        for (JsonObject s : sensors) {
            Config::GenericSensor sensor;
            sensor.name = s["name"].as<String>(); sensor.name.trim();
            sensor.protocol = s["protocol"].as<String>(); sensor.protocol.trim();
            
            for (JsonPair pair : s) {
                String key = pair.key().c_str();
                if (key != "name" && key != "protocol") {
                    sensor.params[key] = pair.value().as<String>();
                }
            }
            Config::HardwareSensors.push_back(sensor);
        }
    }

    // RS485 pins
    if (doc["hardware"]["rs485_rx"]) {
        Config::PIN_RS485_RX = doc["hardware"]["rs485_rx"].as<uint8_t>();
    }
    if (doc["hardware"]["rs485_tx"]) {
        Config::PIN_RS485_TX = doc["hardware"]["rs485_tx"].as<uint8_t>();
    }
    if (doc["hardware"]["rs485_de"]) {
        Config::PIN_RS485_DE = doc["hardware"]["rs485_de"].as<uint8_t>();
    }

    // I2C pins (flat properties, same style as RS485)
    if (doc["hardware"]["i2c_sda_pin"]) {
        Config::PIN_I2C_SDA = doc["hardware"]["i2c_sda_pin"].as<uint8_t>();
    }
    if (doc["hardware"]["i2c_scl_pin"]) {
        Config::PIN_I2C_SCL = doc["hardware"]["i2c_scl_pin"].as<uint8_t>();
    }

    if (Config::PIN_I2C_SDA > 39 || Config::PIN_I2C_SCL > 39) {
        Logger::config("Invalid I2C pins detected in config, resetting to defaults 21/22");
        Config::PIN_I2C_SDA = 21;
        Config::PIN_I2C_SCL = 22;
    }

    return true;
}

bool ConfigManager::saveConfig(String jsonPayload) {
    File file = LittleFS.open("/config.json", "w");
    if (!file) {
        Logger::error("Failed to open config.json for writing");
        return false;
    }
    
    file.print(jsonPayload);
    file.close();
    Logger::config("config.json successfully saved!");
    return true;
}
