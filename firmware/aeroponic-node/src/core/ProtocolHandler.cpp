#include "ProtocolHandler.h"

std::map<String, ProtocolHandlerCreator>& ProtocolRegistry::getRegistry() {
    static std::map<String, ProtocolHandlerCreator> registry;
    return registry;
}

void ProtocolRegistry::registerProtocol(const String& name, ProtocolHandlerCreator creator) {
    getRegistry()[name] = creator;
}

ProtocolHandler* ProtocolRegistry::createHandler(const String& name, const JsonObject& config) {
    auto& reg = getRegistry();
    auto it = reg.find(name);
    if (it != reg.end()) {
        ProtocolHandler* handler = it->second();
        if (handler->init(config)) {
            return handler;
        } else {
            delete handler;
            return nullptr;
        }
    }
    return nullptr;
}

std::vector<String> ProtocolRegistry::getRegisteredProtocols() {
    std::vector<String> protocols;
    for (const auto& pair : getRegistry()) {
        protocols.push_back(pair.first);
    }
    return protocols;
}
