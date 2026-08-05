#include "ProtocolHandlers.h"
#include "HardwareManager.h"
#include "../../include/Config.h"

// I2C bus tracking variables
static bool wireInitialized = false;
static uint8_t activeSda = 21;
static uint8_t activeScl = 22;

void initI2C(uint8_t sda, uint8_t scl) {
    if (!wireInitialized || activeSda != sda || activeScl != scl) {
        Wire.begin(sda, scl);
        wireInitialized = true;
        activeSda = sda;
        activeScl = scl;
        Serial.printf("I2C Bus Initialized on SDA: %d, SCL: %d\n", sda, scl);
    }
}

// ==================== LightBME280 Driver Implementation ====================
#define BME280_REG_CALIB00 0x88
#define BME280_REG_CALIB26 0xE1
#define BME280_REG_CONTROL_HUM 0xF2
#define BME280_REG_CONTROL 0xF4
#define BME280_REG_DATA 0xF7

LightBME280::LightBME280(uint8_t address) : addr(address), t_fine(0) {}

bool LightBME280::begin() {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() != 0) return false;

    readCalibration();
    writeRegister(BME280_REG_CONTROL_HUM, 0x01); // humidity oversampling x1
    writeRegister(BME280_REG_CONTROL, 0x27);     // normal mode, temp x1, press x1
    return true;
}

void LightBME280::writeRegister(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

void LightBME280::readRegisters(uint8_t reg, uint8_t* buf, uint8_t len) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom(addr, len);
    for (uint8_t i = 0; i < len && Wire.available(); i++) {
        buf[i] = Wire.read();
    }
}

void LightBME280::readCalibration() {
    uint8_t calib[26];
    readRegisters(BME280_REG_CALIB00, calib, 26);
    dig_T1 = (calib[1] << 8) | calib[0];
    dig_T2 = (calib[3] << 8) | calib[2];
    dig_T3 = (calib[5] << 8) | calib[4];
    dig_P1 = (calib[7] << 8) | calib[6];
    dig_P2 = (calib[9] << 8) | calib[8];
    dig_P3 = (calib[11] << 8) | calib[10];
    dig_P4 = (calib[13] << 8) | calib[12];
    dig_P5 = (calib[15] << 8) | calib[14];
    dig_P6 = (calib[17] << 8) | calib[16];
    dig_P7 = (calib[19] << 8) | calib[18];
    dig_P8 = (calib[21] << 8) | calib[20];
    dig_P9 = (calib[23] << 8) | calib[22];
    dig_H1 = calib[25];

    uint8_t calibH[7];
    readRegisters(BME280_REG_CALIB26, calibH, 7);
    dig_H2 = (calibH[1] << 8) | calibH[0];
    dig_H3 = calibH[2];
    dig_H4 = (calibH[3] << 4) | (calibH[4] & 0x0F);
    dig_H5 = (calibH[5] << 4) | (calibH[4] >> 4);
    dig_H6 = calibH[6];
}

float LightBME280::readTemperature() {
    uint8_t data[3];
    readRegisters(0xFA, data, 3);
    int32_t adc_T = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4);
    
    int32_t var1 = ((((adc_T >> 3) - ((int32_t)dig_T1 << 1))) * ((int32_t)dig_T2)) >> 11;
    int32_t var2 = (((((adc_T >> 4) - ((int32_t)dig_T1)) * ((adc_T >> 4) - ((int32_t)dig_T1))) >> 12) * ((int32_t)dig_T3)) >> 14;
    t_fine = var1 + var2;
    return (t_fine * 5 + 128) >> 8;
}

float LightBME280::getTemperature() {
    return readTemperature() / 100.0f;
}

float LightBME280::getHumidity() {
    readTemperature(); // updates t_fine
    uint8_t data[2];
    readRegisters(0xFD, data, 2);
    int32_t adc_H = (data[0] << 8) | data[1];

    int32_t v_x1_u32r = (t_fine - ((int32_t)76800));
    v_x1_u32r = (((((adc_H << 14) - (((int32_t)dig_H4) << 20) - (((int32_t)dig_H5) * v_x1_u32r)) +
                       ((int32_t)16384)) >> 15) * (((((((v_x1_u32r * ((int32_t)dig_H6)) >> 10) *
                                                       (((v_x1_u32r * ((int32_t)dig_H3)) >> 11) + ((int32_t)32768))) >> 10) +
                                                     ((int32_t)2097152)) * ((int32_t)dig_H2) + 8192) >> 14));
    v_x1_u32r = (v_x1_u32r - (((((v_x1_u32r >> 15) * (v_x1_u32r >> 15)) >> 7) * ((int32_t)dig_H1)) >> 4));
    v_x1_u32r = (v_x1_u32r < 0 ? 0 : v_x1_u32r);
    v_x1_u32r = (v_x1_u32r > 419430400 ? 419430400 : v_x1_u32r);
    return (uint32_t)(v_x1_u32r >> 12) / 1024.0f;
}

// ==================== GPIOInputHandler Implementation ====================
bool GPIOInputHandler::init(const JsonObject& config) {
    if (!config.containsKey("pin") || !config.containsKey("name")) return false;
    pin = config["pin"].as<uint8_t>();
    name = config["name"].as<String>();
    type = config["type"] | "DIGITAL";
    pull = config["pull"] | "NONE";
    invert = config["invert"] | false;
    debounce_ms = config["debounce_ms"] | 0;
    interrupt = config["interrupt"] | "NONE";
    analog_min = config["analog_min"] | 0;
    analog_max = config["analog_max"] | 4095;

    uint8_t mode = INPUT;
    if (pull == "UP") mode = INPUT_PULLUP;
    else if (pull == "DOWN") mode = INPUT_PULLDOWN;
    pinMode(pin, mode);
    return true;
}

bool GPIOInputHandler::read(JsonObject& telemetry) {
    JsonObject inputs = telemetry["inputs"];
    if (inputs.isNull()) {
        inputs = telemetry.createNestedObject("inputs");
    }
    float val = 0;
    if (type == "ANALOG") {
        val = analogRead(pin);
        inputs[name] = val;
    } else {
        int dval = digitalRead(pin);
        if (invert) dval = !dval;
        inputs[name] = dval;
        val = dval;
    }
    HardwareManager::latestSensorValues[name] = val;
    return true;
}

// ==================== ModbusHandler Implementation ====================
bool ModbusHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("slave_id")) return false;
    name = config["name"].as<String>();
    slave_id = config["slave_id"].as<uint8_t>();
    baudrate = config["baudrate"] | 9600;
    
    JsonArray regs = config["registers"];
    for (JsonObject r : regs) {
        RegisterConfig rc;
        rc.address = r["address"];
        rc.name = r["name"].as<String>();
        rc.multiplier = r["multiplier"] | 1.0f;
        rc.type = r["type"] | "HOLDING";
        registers.push_back(rc);
    }
    return true;
}

bool ModbusHandler::read(JsonObject& telemetry) {
    JsonObject modbus = telemetry["modbus"];
    if (modbus.isNull()) {
        modbus = telemetry.createNestedObject("modbus");
    }
    JsonObject modbusDev = modbus.createNestedObject(name);

    if (xSemaphoreTake(HardwareManager::modbusMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
        if (HardwareManager::currentBaud != baudrate) {
            Serial2.end();
            vTaskDelay(100 / portTICK_PERIOD_MS);
            Serial2.begin(baudrate, SERIAL_8N1, Config::PIN_RS485_RX, Config::PIN_RS485_TX);
            vTaskDelay(300 / portTICK_PERIOD_MS);
            HardwareManager::currentBaud = baudrate;
        }
        HardwareManager::node.begin(slave_id, Serial2);
        
        for (const auto& reg : registers) {
            uint8_t result;
            if (reg.type == "INPUT") {
                result = HardwareManager::node.readInputRegisters(reg.address, 1);
            } else {
                result = HardwareManager::node.readHoldingRegisters(reg.address, 1);
            }
            
            if (result == HardwareManager::node.ku8MBSuccess) {
                float val = HardwareManager::node.getResponseBuffer(0) * reg.multiplier;
                modbusDev[reg.name] = val;
                HardwareManager::latestSensorValues[name + "_" + reg.name] = val;
                HardwareManager::latestSensorValues[reg.name] = val;
            }
            vTaskDelay(10 / portTICK_PERIOD_MS);
        }
        xSemaphoreGive(HardwareManager::modbusMutex);
    }
    return true;
}

// ==================== I2CHandler Implementation ====================
I2CHandler::I2CHandler() : address(0), sda_pin(21), scl_pin(22), initialized(false), bme(nullptr) {}

I2CHandler::~I2CHandler() {
    if (bme) delete bme;
}

bool I2CHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("type")) return false;
    name = config["name"].as<String>();
    type = config["type"].as<String>();
    
    sda_pin = config.containsKey("sda_pin") ? (config["sda_pin"].is<int>() ? config["sda_pin"].as<int>() : config["sda_pin"].as<String>().toInt()) : 21;
    scl_pin = config.containsKey("scl_pin") ? (config["scl_pin"].is<int>() ? config["scl_pin"].as<int>() : config["scl_pin"].as<String>().toInt()) : 22;
    
    if (config.containsKey("address")) {
        if (config["address"].is<int>()) {
            address = config["address"].as<uint8_t>();
        } else {
            String addrStr = config["address"].as<String>();
            if (addrStr.startsWith("0x") || addrStr.startsWith("0X")) {
                address = (uint8_t)strtol(addrStr.c_str(), NULL, 16);
            } else {
                address = (uint8_t)addrStr.toInt();
            }
        }
    } else {
        address = (type == "DHT12") ? 0x5C : 0x76;
    }

    initI2C(sda_pin, scl_pin);

    if (type == "BME280") {
        bme = new LightBME280(address);
        initialized = bme->begin();
        if (!initialized) {
            Serial.printf("Failed to init BME280 at 0x%02X\n", address);
        }
    } else if (type == "DHT12") {
        Wire.beginTransmission(address);
        initialized = (Wire.endTransmission() == 0);
        if (!initialized) {
            Serial.printf("Failed to find DHT12 at 0x%02X\n", address);
        }
    } else {
        initialized = true;
    }
    return true;
}

bool I2CHandler::read(JsonObject& telemetry) {
    JsonObject i2cObj = telemetry["i2c"];
    if (i2cObj.isNull()) {
        i2cObj = telemetry.createNestedObject("i2c");
    }
    JsonObject devObj = i2cObj.createNestedObject(name);

    if (!initialized) {
        if (type == "BME280" && bme) {
            initialized = bme->begin();
        } else if (type == "DHT12") {
            Wire.beginTransmission(address);
            initialized = (Wire.endTransmission() == 0);
        }
        if (!initialized) {
            devObj["status"] = "offline";
            return false;
        }
    }

    if (type == "BME280" && bme) {
        float temp = bme->getTemperature();
        float humid = bme->getHumidity();
        devObj["temperature"] = temp;
        devObj["humidity"] = humid;
        
        HardwareManager::latestSensorValues[name + "_temp"] = temp;
        HardwareManager::latestSensorValues[name + "_humidity"] = humid;
        HardwareManager::latestSensorValues[name] = temp;
    } else if (type == "DHT12") {
        Wire.beginTransmission(address);
        Wire.write(0);
        if (Wire.endTransmission() == 0) {
            Wire.requestFrom(address, (uint8_t)5);
            if (Wire.available() >= 5) {
                byte h_int = Wire.read();
                byte h_dec = Wire.read();
                byte t_int = Wire.read();
                byte t_dec = Wire.read();
                byte checksum = Wire.read();
                if (((h_int + h_dec + t_int + t_dec) & 0xFF) == checksum) {
                    float humidity = h_int + (h_dec * 0.1f);
                    float temperature = t_int + (t_dec * 0.1f);
                    devObj["temperature"] = temperature;
                    devObj["humidity"] = humidity;
                    
                    HardwareManager::latestSensorValues[name + "_temp"] = temperature;
                    HardwareManager::latestSensorValues[name + "_humidity"] = humidity;
                    HardwareManager::latestSensorValues[name] = temperature;
                } else {
                    devObj["error"] = "checksum_error";
                }
            } else {
                devObj["error"] = "read_timeout";
            }
        } else {
            devObj["error"] = "no_response";
            initialized = false;
        }
    }
    return true;
}

// ==================== OneWireHandler Implementation ====================
bool OneWireHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("pin")) return false;
    name = config["name"].as<String>();
    pin = config.containsKey("pin") ? (config["pin"].is<int>() ? config["pin"].as<int>() : config["pin"].as<String>().toInt()) : 4;
    pinMode(pin, INPUT);
    return true;
}

bool OneWireHandler::read(JsonObject& telemetry) {
    JsonObject owObj = telemetry["1wire"];
    if (owObj.isNull()) {
        owObj = telemetry.createNestedObject("1wire");
    }
    JsonObject devObj = owObj.createNestedObject(name);
    
    // Mock reading for verification
    float mockTemp = 25.0f + (esp_random() % 100) * 0.05f;
    devObj["temperature"] = mockTemp;
    
    HardwareManager::latestSensorValues[name + "_temp"] = mockTemp;
    HardwareManager::latestSensorValues[name] = mockTemp;
    return true;
}

// ==================== SPIHandler Implementation ====================
bool SPIHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("cs_pin")) return false;
    name = config["name"].as<String>();
    cs_pin = config.containsKey("cs_pin") ? (config["cs_pin"].is<int>() ? config["cs_pin"].as<int>() : config["cs_pin"].as<String>().toInt()) : 5;
    pinMode(cs_pin, OUTPUT);
    digitalWrite(cs_pin, HIGH);
    return true;
}

bool SPIHandler::read(JsonObject& telemetry) {
    JsonObject spiObj = telemetry["spi"];
    if (spiObj.isNull()) {
        spiObj = telemetry.createNestedObject("spi");
    }
    JsonObject devObj = spiObj.createNestedObject(name);
    
    // Mock reading for verification
    float mockVal = 100.0f + (esp_random() % 1000) * 0.1f;
    devObj["value"] = mockVal;
    
    HardwareManager::latestSensorValues[name] = mockVal;
    return true;
}
