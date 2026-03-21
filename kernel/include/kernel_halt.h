#ifndef KERNEL_HALT_H
#define KERNEL_HALT_H

#include "kernel_status.h"

__attribute__((noreturn)) void kernel_halt(kernel_status_t reason);

#endif
