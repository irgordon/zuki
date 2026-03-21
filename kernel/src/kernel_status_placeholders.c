#include "kernel_status.h"

_Static_assert(KERNEL_STATUS_OK == 0, "KERNEL_STATUS_OK must remain stable");
_Static_assert(KERNEL_STATUS_INVALID_ARGUMENT == 1, "KERNEL_STATUS_INVALID_ARGUMENT must remain stable");
_Static_assert(KERNEL_STATUS_UNSUPPORTED == 2, "KERNEL_STATUS_UNSUPPORTED must remain stable");
_Static_assert(KERNEL_STATUS_INTERNAL_ERROR == 3, "KERNEL_STATUS_INTERNAL_ERROR must remain stable");
