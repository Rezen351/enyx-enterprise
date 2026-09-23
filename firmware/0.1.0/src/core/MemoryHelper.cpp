#include "MemoryHelper.h"

bool MemoryHelper::hasPsram() {
    return ESP.getPsramSize() > 0;
}

size_t MemoryHelper::getFreePsram() {
    if (hasPsram()) {
        return heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    }
    return 0;
}

size_t MemoryHelper::getFreeInternalHeap() {
    return ESP.getFreeHeap();
}
