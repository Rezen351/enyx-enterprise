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
    // Default to empty so the runtime can derive a unique identity from the ESP32
    // MAC address when no custom node_id is configured in the file or portal.
    String NODE_ID = "";
    uint8_t PIN_LED_INDICATOR = 2;     // Built-in LED

    // --- Konfigurasi WiFi ---
    // Nilai diisi dari config.json via ConfigManager::init()
    // Jika kosong, device masuk Captive Portal untuk setup pertama
    String WIFI_SSID = "";
    String WIFI_PASS = "";
    bool WIFI_ENT_ENABLED = false;
    String WIFI_ENT_USERNAME = "";
    String WIFI_ENT_PASSWORD = "";
    String WIFI_ENT_CA_CERT = "";
    String WIFI_ENT_CLIENT_CERT = "";
    String WIFI_ENT_CLIENT_KEY = "";

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
    bool MQTT_DISCONNECT_EMERGENCY_STOP = true;

    // --- Topik MQTT Default ---
    String TOPIC_TELEMETRY = MQTT_TOPIC_PREFIX + "/" + NODE_ID + "/telemetry";
    String TOPIC_ACTUATOR = MQTT_TOPIC_PREFIX + "/actuator/" + NODE_ID;

    // --- I2C Pins (Global) ---
    uint8_t PIN_I2C_SDA = 21;
    uint8_t PIN_I2C_SCL = 22;
    
    // --- Modbus / RS485 Pins ---
    uint8_t PIN_RS485_RX = 16;
    uint8_t PIN_RS485_TX = 17;
    uint8_t PIN_RS485_DE = 255; // 255 = Not Connected (Auto RS485 module)
    uint8_t PARITY = 0; // 0 = None, 1 = Even, 2 = Odd

    // --- Universal Hardware Pins ---
    std::vector<InputPin> HardwareInputs;
    std::vector<OutputPin> HardwareOutputs;
    std::vector<ModbusSensor> HardwareModbus;
    std::vector<GenericSensor> HardwareSensors;

    // --- Interval Waktu (ms) ---
    uint32_t MQTT_PUBLISH_INTERVAL = 5000;
}