#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include <vector>
#include <map>

namespace Config {
    // ==================== INPUT / OUTPUT PIN STRUCTURES ====================
    
    struct InputPin {
        uint8_t pin;
        String type;        // "DIGITAL", "ANALOG"
        String pull;        // "UP", "DOWN", "NONE"
        String name;
        uint16_t debounce_ms;     // Debounce time in ms (0 = disabled)
        String interrupt;         // "RISING", "FALLING", "CHANGE", "NONE"
        uint16_t analog_min;      // Analog threshold min (for DIGITAL conversion)
        uint16_t analog_max;      // Analog threshold max
        bool invert;              // Invert logic (true = LOW is active)
    };

    struct OutputPin {
        uint8_t pin;
        String type;       // "DIGITAL", "PWM"
        String name;
        String protocol;   // ProtocolHandler name, default "GPIO_OUT"
    };

    struct ModbusRegister {
        uint16_t address;
        String name;
        float multiplier;
        String type; // "HOLDING", "INPUT"
        uint8_t length;      // jumlah register (1 atau 2)
        String data_type;    // "UINT16", "INT16", "FLOAT32", "INT32", "UINT32"
    };

    struct ModbusSensor {
        String name;
        uint8_t slave_id;
        uint32_t baudrate;
        std::vector<ModbusRegister> registers;
    };

    struct GenericSensor {
        String name;
        String protocol;
        std::map<String, String> params;
    };

    // ==================== FIRMWARE VERSION ====================
    extern String FW_VERSION;

    // ==================== KEAMANAN ====================
    extern String ADMIN_USER;
    extern String ADMIN_PASS;
    extern String AUTH_TOKEN;
    extern uint8_t MAX_LOGIN_ATTEMPTS;
    extern uint32_t LOGIN_BLOCK_TIME_MS;

    // ==================== IDENTITAS PERANGKAT ====================
    extern String NODE_ID;
    extern uint8_t PIN_LED_INDICATOR;
    extern uint8_t PIN_EMERGENCY_STOP;

    // ==================== KONFIGURASI WIFI ====================
    extern String WIFI_SSID;
    extern String WIFI_PASS;
    extern String WIFI_EAP_IDENTITY;
    extern String WIFI_EAP_PASSWORD;

    // ==================== KONFIGURASI MQTT + TLS ====================
    extern String MQTT_SERVER;
    extern int MQTT_PORT;
    extern String MQTT_TOPIC_PREFIX;
    extern String MQTT_USER;
    extern String MQTT_PASS;
    extern bool MQTT_USE_TLS;
    extern String MQTT_CA_CERT;
    extern String MQTT_CLIENT_CERT;
    extern String MQTT_CLIENT_KEY;
    extern bool MQTT_DISCONNECT_EMERGENCY_STOP;

    // ==================== TOPIK MQTT ====================
    extern String TOPIC_TELEMETRY;
    extern String TOPIC_ACTUATOR;
    extern String TOPIC_ALERT;

    // ==================== PIN MAPPING ====================
    extern uint8_t PIN_DHT_SENSOR;
    
    // ==================== MODBUS / RS485 PINS ====================
    extern uint8_t PIN_RS485_RX;
    extern uint8_t PIN_RS485_TX;
    extern uint8_t PIN_RS485_DE;
    extern uint8_t PARITY;

    inline SerialConfig parityToSerialConfig(uint8_t p) {
        switch (p) {
            case 1: return SERIAL_8E1;
            case 2: return SERIAL_8O1;
            default: return SERIAL_8N1;
        }
    }

    // ==================== UNIVERSAL HARDWARE PINS ====================
    extern std::vector<InputPin> HardwareInputs;
    extern std::vector<OutputPin> HardwareOutputs;
    extern std::vector<ModbusSensor> HardwareModbus;
    extern std::vector<GenericSensor> HardwareSensors;

    // ==================== INTERVAL WAKTU (ms) ====================
    extern uint32_t SENSOR_READ_INTERVAL;
    extern uint32_t MQTT_PUBLISH_INTERVAL;
}

#endif // CONFIG_H