#include "ProtocolHandlers.h"
#include "HardwareManager.h"
#include "../protocols/MqttManager.h"
#include "../../include/Config.h"
#include "../../include/Logger.h"

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
        Logger::hardware("I2C Bus Initialized on SDA: %d, SCL: %d", sda, scl);
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
    String logMsg = "[";
    logMsg += String(millis() / 1000);
    logMsg += "s] GPIO ";
    logMsg += name;
    logMsg += "=";
    logMsg += String(val, 1);
    MqttManager::addLog(logMsg.c_str());
    return true;
}

// ==================== GpioOutputHandler Implementation (Actuator) ====================
bool GpioOutputHandler::init(const JsonObject& config) {
    if (!config.containsKey("pin") || !config.containsKey("name")) return false;
    pin = config["pin"].as<uint8_t>();
    type = config["type"] | "DIGITAL";
    name = config["name"].as<String>();
    pinMode(pin, OUTPUT);
    write(0);   // safe default; reloadConfiguration() restores last known state
    return true;
}

bool GpioOutputHandler::read(JsonObject& telemetry) {
    // Output handler does not read sensor values
    return true;
}

bool GpioOutputHandler::write(int value) {
    if (type == "PWM") {
        analogWrite(pin, constrain(value, 0, 255));
    } else {
        digitalWrite(pin, value > 0 ? HIGH : LOW);
    }
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
        rc.length = r["length"] | 1;
        rc.data_type = r["data_type"] | "UINT16";
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
            Serial2.begin(baudrate, Config::parityToSerialConfig(Config::PARITY), Config::PIN_RS485_RX, Config::PIN_RS485_TX);
            vTaskDelay(300 / portTICK_PERIOD_MS);
            HardwareManager::currentBaud = baudrate;
        }
        HardwareManager::node.begin(slave_id, Serial2);
        
        for (const auto& reg : registers) {
            uint8_t result;
            uint8_t regCount = (reg.length > 0 && reg.length <= 2) ? reg.length : 1;
            
            if (reg.type == "INPUT") {
                result = HardwareManager::node.readInputRegisters(reg.address, regCount);
            } else {
                result = HardwareManager::node.readHoldingRegisters(reg.address, regCount);
            }
            
            if (result == HardwareManager::node.ku8MBSuccess) {
                float val = 0.0f;
                
                if (reg.data_type == "FLOAT32" && regCount >= 2) {
                    uint32_t combined = ((uint32_t)HardwareManager::node.getResponseBuffer(0) << 16) |
                                        HardwareManager::node.getResponseBuffer(1);
                    val = *((float*)&combined);
                } else if (reg.data_type == "INT32" && regCount >= 2) {
                    int32_t combined = ((int32_t)HardwareManager::node.getResponseBuffer(0) << 16) |
                                       HardwareManager::node.getResponseBuffer(1);
                    val = (float)combined;
                } else if (reg.data_type == "UINT32" && regCount >= 2) {
                    uint32_t combined = ((uint32_t)HardwareManager::node.getResponseBuffer(0) << 16) |
                                        HardwareManager::node.getResponseBuffer(1);
                    val = (float)combined;
                } else if (reg.data_type == "INT16") {
                    val = (float)((int16_t)HardwareManager::node.getResponseBuffer(0));
                } else {
                    val = (float)HardwareManager::node.getResponseBuffer(0);
                }
                
                val = val * reg.multiplier;
                modbusDev[reg.name] = val;
                HardwareManager::latestSensorValues[name + "_" + reg.name] = val;
                HardwareManager::latestSensorValues[reg.name] = val;
                String logMsg = "[";
                logMsg += String(millis() / 1000);
                logMsg += "s] MODBUS ";
                logMsg += name;
                logMsg += ".";
                logMsg += reg.name;
                logMsg += "=";
                logMsg += String(val, 1);
                MqttManager::addLog(logMsg.c_str());
            }
            vTaskDelay(10 / portTICK_PERIOD_MS);
        }
        xSemaphoreGive(HardwareManager::modbusMutex);
    }
    return true;
}

// ==================== Modbus TCP Handler Implementation ====================

bool ModbusTCPHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("slave_id") ||
        !config.containsKey("ip_address")) return false;
    name = config["name"].as<String>();
    slave_id = config["slave_id"].as<uint8_t>();
    ip_address = config["ip_address"].as<String>();
    port = config.containsKey("port") ? (uint16_t)config["port"].as<uint32_t>() : 502;

    JsonArray regs = config["registers"];
    for (JsonObject r : regs) {
        RegisterConfig rc;
        rc.address = r["address"];
        rc.name = r["name"].as<String>();
        rc.multiplier = r["multiplier"] | 1.0f;
        rc.type = r["type"] | "HOLDING";
        rc.length = r["length"] | 1;
        rc.data_type = r["data_type"] | "UINT16";
        registers.push_back(rc);
    }
    return true;
}

bool ModbusTCPHandler::read(JsonObject& telemetry) {
    JsonObject modbus = telemetry["modbus"];
    if (modbus.isNull()) {
        modbus = telemetry.createNestedObject("modbus");
    }
    JsonObject modbusDev = modbus.createNestedObject(name);

    if (!client.connected()) {
        client.stop();
        if (!client.connect(ip_address.c_str(), port)) {
            modbusDev["error"] = "tcp_connect_failed";
            return false;
        }
    }

    for (const auto& reg : registers) {
        uint8_t regCount = (reg.length > 0 && reg.length <= 2) ? reg.length : 1;

        uint8_t pdu[5];
        pdu[0] = (reg.type == "INPUT") ? 0x04 : 0x03;
        pdu[1] = (uint8_t)((reg.address >> 8) & 0xFF);
        pdu[2] = (uint8_t)(reg.address & 0xFF);
        pdu[3] = (uint8_t)((regCount >> 8) & 0xFF);
        pdu[4] = (uint8_t)(regCount & 0xFF);

        uint8_t mbap[7];
        uint16_t pduLen = (uint16_t)(sizeof(pdu) + 1);
        mbap[0] = 0x00;
        mbap[1] = 0x01;
        mbap[2] = 0x00;
        mbap[3] = 0x00;
        mbap[4] = (uint8_t)((pduLen >> 8) & 0xFF);
        mbap[5] = (uint8_t)(pduLen & 0xFF);
        mbap[6] = (uint8_t)(slave_id & 0xFF);

        client.write(mbap, sizeof(mbap));
        client.write(pdu, sizeof(pdu));

        uint32_t startWait = millis();
        while (client.available() < 1 && (millis() - startWait) < 1000) {
            vTaskDelay(2 / portTICK_PERIOD_MS);
        }

        if (client.available() < 7) {
            client.stop();
            modbusDev[reg.name + "_error"] = "tcp_timeout";
            continue;
        }

        uint8_t hdr[7];
        client.read(hdr, sizeof(hdr));
        uint16_t respLen = ((uint16_t)hdr[4] << 8) | hdr[5];
        respLen -= 1;
        if (respLen > 260) respLen = 260;

        uint32_t pduWaitStart = millis();
        while (client.available() < respLen && (millis() - pduWaitStart) < 1000) {
            vTaskDelay(2 / portTICK_PERIOD_MS);
        }

        uint8_t pduResp[260];
        int readLen = client.read(pduResp, respLen);
        if (readLen < 1) {
            client.stop();
            modbusDev[reg.name + "_error"] = "tcp_pdu_timeout";
            continue;
        }

        uint8_t fc = pduResp[0];
        uint8_t byteCount = pduResp[1];
        if (fc != pdu[0] || byteCount != (uint8_t)(regCount * 2)) {
            modbusDev[reg.name + "_error"] = "tcp_invalid_response";
            continue;
        }

        float val = 0.0f;
        if (reg.data_type == "FLOAT32" && regCount >= 2) {
            uint32_t combined = ((uint32_t)pduResp[2] << 24) |
                                ((uint32_t)pduResp[3] << 16) |
                                ((uint32_t)pduResp[4] << 8) |
                                pduResp[5];
            val = *((float*)&combined);
        } else if (reg.data_type == "INT32" && regCount >= 2) {
            int32_t combined = ((int32_t)((uint32_t)pduResp[2] << 24)) |
                               ((int32_t)((uint32_t)pduResp[3] << 16)) |
                               ((int32_t)((uint32_t)pduResp[4] << 8)) |
                               pduResp[5];
            val = (float)combined;
        } else if (reg.data_type == "UINT32" && regCount >= 2) {
            uint32_t combined = ((uint32_t)pduResp[2] << 24) |
                                ((uint32_t)pduResp[3] << 16) |
                                ((uint32_t)pduResp[4] << 8) |
                                pduResp[5];
            val = (float)combined;
        } else if (reg.data_type == "INT16") {
            val = (float)((int16_t)((pduResp[2] << 8) | pduResp[3]));
        } else {
            val = (float)((pduResp[2] << 8) | pduResp[3]);
        }

        val = val * reg.multiplier;
        modbusDev[reg.name] = val;
        HardwareManager::latestSensorValues[name + "_" + reg.name] = val;
        HardwareManager::latestSensorValues[reg.name] = val;
        String logMsg = "[";
        logMsg += String(millis() / 1000);
        logMsg += "s] MODBUS_TCP ";
        logMsg += name;
        logMsg += ".";
        logMsg += reg.name;
        logMsg += "=";
        logMsg += String(val, 1);
        MqttManager::addLog(logMsg.c_str());
    }
    return true;
}

I2CHandler::I2CHandler() : address(0), initialized(false), bme(nullptr), ina219(nullptr) {}

I2CHandler::~I2CHandler() {
    if (bme) delete bme;
    if (ina219) delete ina219;
}

bool I2CHandler::init(const JsonObject& config) {
    if (!config.containsKey("name") || !config.containsKey("type")) return false;
    name = config["name"].as<String>();
    type = config["type"].as<String>();

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
        if (type == "DHT12") address = 0x5C;
        else if (type == "INA219") address = 0x40;
        else address = 0x76;
    }

    // Use global I2C pin configuration (set once at startup)
    initI2C(Config::PIN_I2C_SDA, Config::PIN_I2C_SCL);

    if (type == "BME280") {
        bme = new LightBME280(address);
        initialized = bme->begin();
        if (!initialized) {
            Logger::hardware("Failed to init BME280 at 0x%02X", address);
        }
    } else if (type == "INA219") {
        ina219 = new Adafruit_INA219(address);
        initialized = ina219->begin();
        if (!initialized) {
            Logger::hardware("Failed to init INA219 at 0x%02X", address);
        }
    } else if (type == "DHT12") {
        Wire.beginTransmission(address);
        initialized = (Wire.endTransmission() == 0);
        if (!initialized) {
            Logger::hardware("Failed to find DHT12 at 0x%02X", address);
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
        } else if (type == "INA219" && ina219) {
            initialized = ina219->begin();
        } else if (type == "DHT12") {
            Wire.beginTransmission(address);
            initialized = (Wire.endTransmission() == 0);
        }
        if (!initialized) {
            devObj["status"] = "offline";
            return false;
        }
    }

    if (type == "INA219" && ina219) {
        float busVoltage = ina219->getBusVoltage_V();
        float shuntVoltage = ina219->getShuntVoltage_mV();
        float current = ina219->getCurrent_mA();
        float power = ina219->getPower_mW();

        devObj["bus_voltage_v"] = busVoltage;
        devObj["shunt_voltage_mv"] = shuntVoltage;
        devObj["current_ma"] = current;
        devObj["power_mw"] = power;

        HardwareManager::latestSensorValues[name + "_bus_voltage"] = busVoltage;
        HardwareManager::latestSensorValues[name + "_current"] = current;
        HardwareManager::latestSensorValues[name + "_power"] = power;
        HardwareManager::latestSensorValues[name] = current;
        
        String logMsg = "[";
        logMsg += String(millis() / 1000);
        logMsg += "s] I2C ";
        logMsg += name;
        logMsg += " ";
        logMsg += String(current, 0);
        logMsg += "mA ";
        logMsg += String(busVoltage, 1);
        logMsg += "V";
        MqttManager::addLog(logMsg.c_str());
    } else if (type == "BME280" && bme) {
        float temp = bme->getTemperature();
        float humid = bme->getHumidity();
        devObj["temperature"] = temp;
        devObj["humidity"] = humid;
        
        HardwareManager::latestSensorValues[name + "_temp"] = temp;
        HardwareManager::latestSensorValues[name + "_humidity"] = humid;
        HardwareManager::latestSensorValues[name] = temp;
        
        String logMsg = "[";
        logMsg += String(millis() / 1000);
        logMsg += "s] I2C ";
        logMsg += name;
        logMsg += " ";
        logMsg += String(temp, 1);
        logMsg += "C ";
        logMsg += String(humid, 0);
        logMsg += "%";
        MqttManager::addLog(logMsg.c_str());
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
                    
                    String logMsg = "[";
                    logMsg += String(millis() / 1000);
                    logMsg += "s] I2C ";
                    logMsg += name;
                    logMsg += " ";
                    logMsg += String(temperature, 1);
                    logMsg += "C ";
                    logMsg += String(humidity, 0);
                    logMsg += "%";
                    MqttManager::addLog(logMsg.c_str());
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

// ==================== PCF8575 I2C Expander Driver ====================
namespace Pcf8575Bus {
    static std::map<uint8_t, uint16_t> pcfStates;      // Shadow state per I2C address (default 0xFFFF)
    static std::map<uint8_t, uint16_t> inputMasks;    // Bits designated as input (must stay 1)
    static SemaphoreHandle_t pcfMutex = NULL;

    static void ensureMutex() {
        if (!pcfMutex) {
            pcfMutex = xSemaphoreCreateMutex();
        }
    }

    uint16_t getState(uint8_t addr) {
        ensureMutex();
        if (pcfStates.find(addr) == pcfStates.end()) {
            pcfStates[addr] = 0xFFFF; // Default all HIGH (relay OFF for Active-LOW, and inputs ready)
        }
        return pcfStates[addr];
    }

    bool writePort(uint8_t addr, uint16_t state) {
        ensureMutex();
        initI2C(Config::PIN_I2C_SDA, Config::PIN_I2C_SCL);
        
        // Ensure any pins designated as inputs remain HIGH (1)
        uint16_t inMask = inputMasks.count(addr) ? inputMasks[addr] : 0;
        state |= inMask;

        Wire.beginTransmission(addr);
        Wire.write(lowByte(state));   // P0 .. P7
        Wire.write(highByte(state));  // P8 .. P15
        byte err = Wire.endTransmission();
        if (err == 0) {
            pcfStates[addr] = state;
            return true;
        } else {
            Logger::hardware("PCF8575 (0x%02X) I2C write error code: %d", addr, err);
            return false;
        }
    }

    uint16_t readPort(uint8_t addr, bool& success) {
        ensureMutex();
        initI2C(Config::PIN_I2C_SDA, Config::PIN_I2C_SCL);

        // Request 2 bytes from PCF8575
        uint8_t count = Wire.requestFrom(addr, (uint8_t)2);
        if (count == 2) {
            uint8_t low = Wire.read();
            uint8_t high = Wire.read();
            success = true;
            return ((uint16_t)high << 8) | low;
        }
        success = false;
        return 0xFFFF;
    }

    bool setPin(uint8_t addr, uint8_t pin, bool levelHigh) {
        if (pin > 15) return false;
        ensureMutex();
        if (xSemaphoreTake(pcfMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
            uint16_t current = getState(addr);
            if (levelHigh) {
                current |= (1u << pin);
            } else {
                current &= ~(1u << pin);
            }
            bool ok = writePort(addr, current);
            xSemaphoreGive(pcfMutex);
            return ok;
        }
        return false;
    }

    bool readPin(uint8_t addr, uint8_t pin, bool& levelHigh) {
        if (pin > 15) return false;
        ensureMutex();
        if (xSemaphoreTake(pcfMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
            bool ok = false;
            uint16_t val = readPort(addr, ok);
            xSemaphoreGive(pcfMutex);
            if (ok) {
                levelHigh = (val & (1u << pin)) != 0;
                return true;
            }
        }
        return false;
    }

    void markAsInput(uint8_t addr, uint8_t pin) {
        if (pin > 15) return;
        ensureMutex();
        if (xSemaphoreTake(pcfMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
            inputMasks[addr] |= (1u << pin);
            uint16_t current = getState(addr) | (1u << pin);
            writePort(addr, current);
            xSemaphoreGive(pcfMutex);
        }
    }
}

// ==================== Pcf8575OutputHandler Implementation ====================
bool Pcf8575OutputHandler::init(const JsonObject& config) {
    if (!config.containsKey("name")) return false;
    name = config["name"].as<String>();
    pin = config["pin"] | 0;
    if (pin > 15) pin = 15;

    i2c_addr = 0x20;
    if (config.containsKey("i2c_addr")) {
        if (config["i2c_addr"].is<const char*>() || config["i2c_addr"].is<String>()) {
            i2c_addr = (uint8_t)strtoul(config["i2c_addr"].as<const char*>(), NULL, 0);
        } else {
            i2c_addr = config["i2c_addr"].as<uint8_t>();
        }
    }
    if (i2c_addr == 0) i2c_addr = 0x20;

    active_low = config.containsKey("active_low") ? config["active_low"].as<bool>() : true;

    // Safe default: set relay to OFF
    write(0);
    Logger::hardware("Init PCF8575 Relay Output: '%s' @ 0x%02X Pin P%d (Active %s)", 
        name.c_str(), i2c_addr, pin, active_low ? "LOW" : "HIGH");
    return true;
}

bool Pcf8575OutputHandler::read(JsonObject& telemetry) {
    return true;
}

bool Pcf8575OutputHandler::write(int value) {
    bool on = (value > 0);
    // Active LOW: On -> LOW, Off -> HIGH
    // Active HIGH: On -> HIGH, Off -> LOW
    bool pinLevelHigh = active_low ? !on : on;
    return Pcf8575Bus::setPin(i2c_addr, pin, pinLevelHigh);
}

// ==================== Pcf8575InputHandler Implementation ====================
bool Pcf8575InputHandler::init(const JsonObject& config) {
    if (!config.containsKey("name")) return false;
    name = config["name"].as<String>();
    pin = config["pin"] | 0;
    if (pin > 15) pin = 15;

    i2c_addr = 0x20;
    if (config.containsKey("i2c_addr")) {
        if (config["i2c_addr"].is<const char*>() || config["i2c_addr"].is<String>()) {
            i2c_addr = (uint8_t)strtoul(config["i2c_addr"].as<const char*>(), NULL, 0);
        } else {
            i2c_addr = config["i2c_addr"].as<uint8_t>();
        }
    }
    if (i2c_addr == 0) i2c_addr = 0x20;

    invert = config["invert"] | false;

    // Mark this pin as input on the bus so its bit stays 1 (weak pull-up)
    Pcf8575Bus::markAsInput(i2c_addr, pin);
    Logger::hardware("Init PCF8575 Input: '%s' @ 0x%02X Pin P%d (Invert: %d)",
        name.c_str(), i2c_addr, pin, invert);
    return true;
}

bool Pcf8575InputHandler::read(JsonObject& telemetry) {
    JsonObject inputs = telemetry["inputs"];
    if (inputs.isNull()) {
        inputs = telemetry.createNestedObject("inputs");
    }

    bool pinLevelHigh = true;
    bool ok = Pcf8575Bus::readPin(i2c_addr, pin, pinLevelHigh);
    int dval = 0;
    if (ok) {
        dval = pinLevelHigh ? 1 : 0;
        if (invert) dval = !dval;
        inputs[name] = dval;
        HardwareManager::latestSensorValues[name] = dval;

        String logMsg = "[";
        logMsg += String(millis() / 1000);
        logMsg += "s] PCF8575_IN ";
        logMsg += name;
        logMsg += "=";
        logMsg += String(dval);
        MqttManager::addLog(logMsg.c_str());
        return true;
    } else {
        inputs[name] = 0;
        return false;
    }
}

