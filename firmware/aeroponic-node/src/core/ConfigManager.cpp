#include "ConfigManager.h"
#include "../../include/Config.h"
#include <ArduinoJson.h>
#include <LittleFS.h>
#include <WiFi.h>
#include "esp_partition.h"

void ConfigManager::init() {
    Serial.println("Mounting LittleFS...");

    // Verify partition table contains a 'spiffs' partition (used by LittleFS)
    const esp_partition_t* part = esp_partition_find_first(
        ESP_PARTITION_TYPE_DATA, ESP_PARTITION_SUBTYPE_DATA_SPIFFS, "spiffs");
    if (part == NULL) {
        Serial.println("[ERROR] LittleFS: Partition 'spiffs' NOT found in flash!");
        Serial.println("[ERROR] Re-flash firmware + partition table, then run 'uploadfs'.");
        Serial.println("Using default compiled configs.");
        return;
    }
    Serial.printf("[INFO] LittleFS: Partition found at 0x%06X, size %u bytes\n",
                  part->address, part->size);

    if (!LittleFS.begin(true)) {  // true = formatOnFail
        Serial.println("[ERROR] LittleFS mount failed even after format attempt.");
        Serial.println("Using default compiled configs.");
        return;
    }

    Serial.println("[OK] LittleFS mounted successfully.");

    if (!loadConfig()) {
        Serial.println("Failed to load config.json. Using default compiled configs.");
    }
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
        Serial.print("Failed to parse config.json: ");
        Serial.println(error.c_str());
        return false;
    }

    Serial.println("config.json loaded successfully. Applying core configurations...");

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
        Serial.printf("INFO: No admin password in config.json. Generated random password: %s\n",
                      Config::ADMIN_PASS.c_str());
        Serial.println("INFO: Change it via the Web Portal at your earliest convenience.");
    }

    // Protocols - WiFi
    if (doc["protocols"]["wifi"]["ssid"]) {
        Config::WIFI_SSID = doc["protocols"]["wifi"]["ssid"].as<String>();
        Config::WIFI_SSID.trim();
    }
    if (doc["protocols"]["wifi"]["password"]) {
        Config::WIFI_PASS = doc["protocols"]["wifi"]["password"].as<String>();
        Config::WIFI_PASS.trim();
    }
    if (doc["protocols"]["wifi"]["eap_identity"]) {
        Config::WIFI_EAP_IDENTITY = doc["protocols"]["wifi"]["eap_identity"].as<String>();
        Config::WIFI_EAP_IDENTITY.trim();
    }
    if (doc["protocols"]["wifi"]["eap_password"]) {
        Config::WIFI_EAP_PASSWORD = doc["protocols"]["wifi"]["eap_password"].as<String>();
        Config::WIFI_EAP_PASSWORD.trim();
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

    // Updating dynamic topics based on potentially new NODE_ID and TOPIC_PREFIX
    Config::TOPIC_TELEMETRY = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/telemetry";
    Config::TOPIC_ACTUATOR  = Config::MQTT_TOPIC_PREFIX + "/actuator/" + Config::NODE_ID;
    Config::TOPIC_DIAGNOSTICS = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/diagnostics";
    Config::TOPIC_ALERT = Config::MQTT_TOPIC_PREFIX + "/" + Config::NODE_ID + "/alert";

    Serial.printf("MQTT Topics:\n");
    Serial.printf("  Telemetry : %s\n", Config::TOPIC_TELEMETRY.c_str());
    Serial.printf("  Actuator  : %s\n", Config::TOPIC_ACTUATOR.c_str());
    Serial.printf("  Diagnos   : %s\n", Config::TOPIC_DIAGNOSTICS.c_str());
    Serial.printf("  Alert     : %s\n", Config::TOPIC_ALERT.c_str());

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
            
            if (m["registers"].is<JsonArray>()) {
                JsonArray registers = m["registers"].as<JsonArray>();
                for (JsonObject r : registers) {
                    Config::ModbusRegister reg;
                    reg.address = r["address"].as<uint16_t>();
                    reg.name = r["name"].as<String>(); reg.name.trim();
                    reg.multiplier = r["multiplier"].as<float>();
                    reg.type = r["type"].as<String>(); reg.type.trim();
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

    // Local Control Rules
    Config::LocalControlRules.clear();
    if (doc["local_control"].is<JsonArray>()) {
        for (JsonObject r : doc["local_control"].as<JsonArray>()) {
            Config::LocalControlRule rule;
            rule.name         = r["name"].as<String>(); rule.name.trim();
            rule.inputSensor  = r["input_sensor"].as<String>(); rule.inputSensor.trim();
            rule.outputTarget = r["output_target"].as<String>(); rule.outputTarget.trim();
            rule.thresholdHigh= r["threshold_high"].as<float>();
            rule.thresholdLow = r["threshold_low"].as<float>();
            rule.enabled      = r["enabled"] | true;
            Config::LocalControlRules.push_back(rule);
        }
    }

    return true;
}

bool ConfigManager::saveConfig(String jsonPayload) {
    File file = LittleFS.open("/config.json", "w");
    if (!file) {
        Serial.println("Failed to open config.json for writing");
        return false;
    }
    
    file.print(jsonPayload);
    file.close();
    Serial.println("config.json successfully saved!");
    return true;
}
