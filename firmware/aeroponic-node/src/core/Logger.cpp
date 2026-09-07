#include "Logger.h"

static void logPrintf(const char* tag, const char* fmt, va_list args) {
    char buf[256];
    vsnprintf(buf, sizeof(buf), fmt, args);
    Serial.printf("[%s] %s\n", tag, buf);
}

static void logPrint(const char* tag, const char* msg) {
    Serial.printf("[%s] %s\n", tag, msg);
}

void Logger::boot(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("BOOT", fmt, args);
    va_end(args);
}

void Logger::init(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("INIT", fmt, args);
    va_end(args);
}

void Logger::config(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("CONFIG", fmt, args);
    va_end(args);
}

void Logger::network(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("NETWORK", fmt, args);
    va_end(args);
}

void Logger::mqtt(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("MQTT", fmt, args);
    va_end(args);
}

void Logger::hardware(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("HARDWARE", fmt, args);
    va_end(args);
}

void Logger::control(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("CONTROL", fmt, args);
    va_end(args);
}

void Logger::actuator(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("ACTUATOR", fmt, args);
    va_end(args);
}

void Logger::modbus(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("MODBUS", fmt, args);
    va_end(args);
}

void Logger::emergency(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("EMERGENCY", fmt, args);
    va_end(args);
}

void Logger::system(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("SYSTEM", fmt, args);
    va_end(args);
}

void Logger::watchdog(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("WATCHDOG", fmt, args);
    va_end(args);
}

void Logger::portal(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("PORTAL", fmt, args);
    va_end(args);
}

void Logger::info(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("INFO", fmt, args);
    va_end(args);
}

void Logger::warn(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("WARN", fmt, args);
    va_end(args);
}

void Logger::error(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    logPrintf("ERROR", fmt, args);
    va_end(args);
}
