#include "kernel_entry.h"
#include "kernel_status.h"
#include "kernel_types.h"

_Static_assert(sizeof(kernel_u8) == 1, "kernel_u8 must be 8 bits");
_Static_assert(sizeof(kernel_u16) == 2, "kernel_u16 must be 16 bits");
_Static_assert(sizeof(kernel_u32) == 4, "kernel_u32 must be 32 bits");
_Static_assert(sizeof(kernel_u64) == 8, "kernel_u64 must be 64 bits");
_Static_assert(_Generic(&kernel_entry, kernel_status_t (*)(void): 1, default: 0), "kernel_entry signature must remain stable");
