#ifndef MEMORY_HELPER_H
#define MEMORY_HELPER_H

#include <Arduino.h>

class MemoryHelper {
public:
    static bool hasPsram();
    static size_t getFreePsram();
    static size_t getFreeInternalHeap();
};

#endif
