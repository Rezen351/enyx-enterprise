#ifndef PROTOCOL_HANDLER_H
#define PROTOCOL_HANDLER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>
#include <map>

class ProtocolHandler {
public:
    virtual ~ProtocolHandler() {}
    virtual bool init(const JsonObject& config) = 0;
    virtual bool read(JsonObject& telemetry) = 0;
    virtual String getProtocolName() = 0;
    virtual String getSensorName() = 0;
};

typedef ProtocolHandler* (*ProtocolHandlerCreator)();

class ProtocolRegistry {
public:
    static void registerProtocol(const String& name, ProtocolHandlerCreator creator);
    static ProtocolHandler* createHandler(const String& name, const JsonObject& config);
    static std::vector<String> getRegisteredProtocols();
private:
    static std::map<String, ProtocolHandlerCreator>& getRegistry();
};

#endif // PROTOCOL_HANDLER_H
