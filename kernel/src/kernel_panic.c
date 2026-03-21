#include "kernel_panic.h"

__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason) {
    (void)reason;
    __builtin_trap();
    __builtin_unreachable();
}
