#include "kernel_lifecycle.h"

kernel_lifecycle_state_t kernel_lifecycle_get_state(void) {
    return KERNEL_LIFECYCLE_STATE_BOOTSTRAP;
}
