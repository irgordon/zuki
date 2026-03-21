#ifndef KERNEL_STATUS_H
#define KERNEL_STATUS_H

enum kernel_status {
    KERNEL_STATUS_OK = 0,
    KERNEL_STATUS_INVALID_ARGUMENT = 1,
    KERNEL_STATUS_UNSUPPORTED = 2,
    KERNEL_STATUS_INTERNAL_ERROR = 3,
};

typedef enum kernel_status kernel_status_t;

#endif
