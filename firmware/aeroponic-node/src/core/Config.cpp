#include "../../include/Config.h"

namespace Config {
    // --- Firmware Version ---
    String FW_VERSION = "1.0.0";

    // --- Keamanan ---
    String ADMIN_USER = "";
    String ADMIN_PASS = "";
    String AUTH_TOKEN = "";
    uint8_t MAX_LOGIN_ATTEMPTS = 5;
    uint32_t LOGIN_BLOCK_TIME_MS = 30000;

    // --- Identitas Perangkat ---
    String NODE_ID = "node-01";
    uint8_t PIN_LED_INDICATOR = 2;     // Built-in LED
    uint8_t PIN_EMERGENCY_STOP = 255;  // 255 = disabled

    // --- Konfigurasi WiFi ---
    // Nilai diisi dari config.json via ConfigManager::init()
    // Jika kosong, device masuk Captive Portal untuk setup pertama
    String WIFI_SSID = "";
    String WIFI_PASS = "";
    String WIFI_EAP_IDENTITY = "";
    String WIFI_EAP_PASSWORD = "";

    // --- Konfigurasi MQTT ---
    // Nilai diisi dari config.json via ConfigManager::init()
    String MQTT_SERVER = "";
    int MQTT_PORT = 1883;
    String MQTT_TOPIC_PREFIX = "smartfarm";
    String MQTT_USER = "";
    String MQTT_PASS = "";
    bool MQTT_USE_TLS = false;
    String MQTT_CA_CERT = "";
    String MQTT_CLIENT_CERT = "";
    String MQTT_CLIENT_KEY = "";

    // --- Topik MQTT Default ---
    String TOPIC_TELEMETRY = MQTT_TOPIC_PREFIX + "/" + NODE_ID + "/telemetry";
    String TOPIC_ACTUATOR = MQTT_TOPIC_PREFIX + "/actuator/" + NODE_ID;
    String TOPIC_DIAGNOSTICS = MQTT_TOPIC_PREFIX + "/" + NODE_ID + "/diagnostics";
    String TOPIC_ALERT = MQTT_TOPIC_PREFIX + "/" + NODE_ID + "/alert";

    // --- Pin Mapping ---
    uint8_t PIN_DHT_SENSOR = 4;
    
    // --- Modbus / RS485 Pins ---
    uint8_t PIN_RS485_RX = 16;
    uint8_t PIN_RS485_TX = 17;
    uint8_t PIN_RS485_DE = 255; // 255 = Not Connected (Auto RS485 module)

    // --- Universal Hardware Pins ---
    std::vector<InputPin> HardwareInputs;
    std::vector<OutputPin> HardwareOutputs;
    std::vector<ModbusSensor> HardwareModbus;
    std::vector<GenericSensor> HardwareSensors;
    std::vector<LocalControlRule> LocalControlRules;

    // --- Interval Waktu (ms) ---
    uint32_t SENSOR_READ_INTERVAL = 5000;
    uint32_t MQTT_PUBLISH_INTERVAL = 5000;
    uint32_t DIAGNOSTICS_INTERVAL = 10000;
}