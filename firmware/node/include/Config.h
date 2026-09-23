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
        String protocol;          // "GPIO", "PCF8575_IN"
        uint8_t i2c_addr;         // e.g. 0x20
    };

    struct OutputPin {
        uint8_t pin;
        String type;       // "DIGITAL", "PWM"
        String name;
        String protocol;   // ProtocolHandler name, default "GPIO_OUT" or "PCF8575_OUT"
        uint8_t i2c_addr;  // e.g. 0x20
        bool active_low;   // true for relay (default)
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
        String transport;     // "RTU" or "TCP"
        String ip_address;    // for TCP: device IP
        uint16_t port;        // for TCP: device port (default 502)
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

    // ==================== KONFIGURASI WIFI ====================
    extern String WIFI_SSID;
    extern String WIFI_PASS;

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

    // ==================== I2C PINS (Global) ====================
    extern uint8_t PIN_I2C_SDA;
    extern uint8_t PIN_I2C_SCL;
    
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
extern uint32_t MQTT_PUBLISH_INTERVAL;
}

#endif // CONFIG_H