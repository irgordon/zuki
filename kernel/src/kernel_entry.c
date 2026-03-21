#include "kernel_entry.h"
#include "kernel_lifecycle.h"

kernel_status_t kernel_entry(void) {
    (void)kernel_lifecycle_get_state();
    return KERNEL_STATUS_OK;
}
