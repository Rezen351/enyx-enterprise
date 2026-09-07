#ifndef LOGGER_H
#define LOGGER_H

#include <Arduino.h>

class Logger {
public:
    static void boot(const char* fmt, ...);
    static void init(const char* fmt, ...);
    static void config(const char* fmt, ...);
    static void network(const char* fmt, ...);
    static void mqtt(const char* fmt, ...);
    static void hardware(const char* fmt, ...);
    static void control(const char* fmt, ...);
    static void actuator(const char* fmt, ...);
    static void modbus(const char* fmt, ...);
    static void emergency(const char* fmt, ...);
    static void system(const char* fmt, ...);
    static void watchdog(const char* fmt, ...);
    static void portal(const char* fmt, ...);
    static void info(const char* fmt, ...);
    static void warn(const char* fmt, ...);
    static void error(const char* fmt, ...);
};

#endif
