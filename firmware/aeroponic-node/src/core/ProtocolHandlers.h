#ifndef PROTOCOL_HANDLERS_H
#define PROTOCOL_HANDLERS_H

#include "ProtocolHandler.h"
#include <Wire.h>

// Light weight Bosch BME280 driver
class LightBME280 {
public:
    uint8_t addr;
    // Calibration parameters
    uint16_t dig_T1;
    int16_t  dig_T2;
    int16_t  dig_T3;
    uint16_t dig_P1;
    int16_t  dig_P2;
    int16_t  dig_P3;
    int16_t  dig_P4;
    int16_t  dig_P5;
    int16_t  dig_P6;
    int16_t  dig_P7;
    int16_t  dig_P8;
    int16_t  dig_P9;
    uint8_t  dig_H1;
    int16_t  dig_H2;
    uint8_t  dig_H3;
    int16_t  dig_H4;
    int16_t  dig_H5;
    int8_t   dig_H6;
    int32_t  t_fine;

    LightBME280(uint8_t address = 0x76);
    bool begin();
    void writeRegister(uint8_t reg, uint8_t val);
    void readCalibration();
    void readRegisters(uint8_t reg, uint8_t* buf, uint8_t len);
    float readTemperature();
    float getTemperature();
    float getHumidity();
};

// GPIO Input Handler
class GPIOInputHandler : public ProtocolHandler {
private:
    uint8_t pin;
    String type;
    String pull;
    String name;
    bool invert;
    uint16_t debounce_ms;
    String interrupt;
    uint16_t analog_min;
    uint16_t analog_max;
public:
    bool init(const JsonObject& config) override;
    bool read(JsonObject& telemetry) override;
    String getProtocolName() override { return "GPIO"; }
    String getSensorName() override { return name; }
};

// Modbus Handler
class ModbusHandler : public ProtocolHandler {
private:
    String name;
    uint8_t slave_id;
    uint32_t baudrate;
    struct RegisterConfig {
        uint16_t address;
        String name;
        float multiplier;
        String type;
    };
    std::vector<RegisterConfig> registers;
public:
    bool init(const JsonObject& config) override;
    bool read(JsonObject& telemetry) override;
    String getProtocolName() override { return "MODBUS"; }
    String getSensorName() override { return name; }
};

// I2C Handler (DHT12, BME280)
class I2CHandler : public ProtocolHandler {
private:
    String name;
    String type;
    uint8_t address;
    uint8_t sda_pin;
    uint8_t scl_pin;
    bool initialized;
    LightBME280* bme;
public:
    I2CHandler();
    ~I2CHandler();
    bool init(const JsonObject& config) override;
    bool read(JsonObject& telemetry) override;
    String getProtocolName() override { return "I2C"; }
    String getSensorName() override { return name; }
};

// 1-Wire Handler
class OneWireHandler : public ProtocolHandler {
private:
    String name;
    uint8_t pin;
public:
    bool init(const JsonObject& config) override;
    bool read(JsonObject& telemetry) override;
    String getProtocolName() override { return "1-WIRE"; }
    String getSensorName() override { return name; }
};

// SPI Handler
class SPIHandler : public ProtocolHandler {
private:
    String name;
    uint8_t cs_pin;
public:
    bool init(const JsonObject& config) override;
    bool read(JsonObject& telemetry) override;
    String getProtocolName() override { return "SPI"; }
    String getSensorName() override { return name; }
};

// I2C bus initializer helper
void initI2C(uint8_t sda, uint8_t scl);

#endif // PROTOCOL_HANDLERS_H
