#ifndef KERNEL_LIFECYCLE_H
#define KERNEL_LIFECYCLE_H

enum kernel_lifecycle_state {
    KERNEL_LIFECYCLE_STATE_BOOTSTRAP = 0,
};

typedef enum kernel_lifecycle_state kernel_lifecycle_state_t;

kernel_lifecycle_state_t kernel_lifecycle_get_state(void);

#endif
