#ifndef KERNEL_FAULT_REASON_H
#define KERNEL_FAULT_REASON_H

typedef enum kernel_fault_reason {
    KERNEL_FAULT_NONE = 0,
    KERNEL_FAULT_UNKNOWN = 1,
    KERNEL_FAULT_INVALID_STATE = 2,
    KERNEL_FAULT_CONTRACT_VIOLATION = 3
} kernel_fault_reason_t;

#endif
