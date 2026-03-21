#ifndef KERNEL_ASSERT_H
#define KERNEL_ASSERT_H

#include "kernel_fault_reason.h"

__attribute__((noreturn)) void kernel_assert(kernel_fault_reason_t reason);

#endif
