#ifndef KERNEL_PANIC_H
#define KERNEL_PANIC_H

#include "kernel_fault_reason.h"

__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason);

#endif
