#include "kernel_assert.h"

__attribute__((noreturn)) void kernel_assert(kernel_fault_reason_t reason) {
    for (;;) {
    }
}
