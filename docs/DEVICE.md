# Zuki Device Model & Driver Isolation — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/dev`, `/services/dev`, and any userspace component that interacts with device capabilities, DMA, interrupts, or driver sandboxes.

This document defines:

- the device capability model
- driver isolation and sandboxing
- I/O queue semantics
- DMA and memory-safety rules
- interrupt delivery
- enumeration and hotplug
- restart and failure semantics
- integration with MM, scheduler, IPC, and policy
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Device model overview

Zuki’s device subsystem is:

- capability-rooted
- driver-isolated
- DMA-safe
- interrupt-mediated
- policy-visible
- restart-safe
- service-implemented (drivers run in userspace)

The kernel does not implement device drivers.

The kernel is responsible only for:

- capability validation
- DMA boundary enforcement
- IOMMU programming (when present)
- interrupt routing
- memory safety
- enforcing object invariants (OBJECTS.md)

Drivers run in userspace sandboxes and interact with devices via:

- device capabilities
- I/O queues
- DMA windows
- interrupt endpoints

---

## 2. Device object model

Device objects are **kernel objects** governed by OBJECTS.md.

### 2.1 Object types

- `OBJ_DEVICE` — abstract device
- `OBJ_DMA_WINDOW` — bounded DMA region
- `OBJ_IOQUEUE` — device I/O queue
- `OBJ_IRQ` — interrupt endpoint

### 2.2 Lifecycle

Device objects follow:

- construction (kernel only)
- publication (capability-visible)
- retire (device removal or failure)
- reclaim (after quiescence)

Device objects must obey:

- generation safety
- refcount rules
- no use-after-retire

---

## 3. Capability rights

Each device capability carries a rights mask:

- `RIGHT_MMIO`
- `RIGHT_DMA`
- `RIGHT_QUEUE_SEND`
- `RIGHT_QUEUE_RECV`
- `RIGHT_IRQ_BIND`
- `RIGHT_RESET`

Rules:

- rights must be validated on every operation
- rights must not be amplified
- rights must be monotonic under derivation

---

## 4. Driver isolation

### 4.1 Execution model

Drivers run in userspace sandboxes and are:

- untrusted
- restartable
- capability-scoped

### 4.2 Isolation invariants

Drivers must not:

- access kernel memory
- access MMIO without RIGHT_MMIO
- perform DMA without RIGHT_DMA
- receive interrupts without RIGHT_IRQ_BIND

Sandbox must enforce:

- no raw pointer escape
- no implicit shared memory
- no syscall bypass of capability checks
- bounded execution (policy-controlled)

### 4.3 Restart rule

On driver failure:

- all in-flight I/O must abort
- all DMA windows must be revoked
- all IRQ bindings must be removed
- all I/O queues must be reset
- device must be placed into a safe or reset state

Driver restart must not reuse stale kernel objects.

---

## 5. MMIO access

### 5.1 Mapping rules

MMIO mapping requires:

- `OBJ_DEVICE` with RIGHT_MMIO

Kernel must:

- validate region belongs to device
- enforce alignment and bounds
- map with correct permissions
- prevent aliasing with:
  - kernel memory
  - other device regions

### 5.2 Memory rules

- MMIO must not be cached unless architecture permits and is explicitly configured
- mapping must respect architecture ordering rules

### 5.3 Forbidden patterns

- arbitrary physical mapping
- overlapping MMIO mappings
- privilege escalation via writable mappings

---

## 6. DMA model

### 6.1 DMA windows

`OBJ_DMA_WINDOW` defines:

- physical pages
- size
- access direction (read/write)

### 6.2 MM integration

DMA windows must be created from memory governed by MM.md:

- frames must be validated via capability
- pages must be pinned if required
- ownership must remain consistent with frame lifecycle

### 6.3 IOMMU rule

If an IOMMU is present:

- all DMA must be mediated through it
- identity DMA is forbidden unless explicitly allowed by architecture and policy

### 6.4 Invariants

- DMA must be bounded
- DMA must not target kernel memory
- DMA must not target memory outside the window
- DMA windows must be revocable

### 6.5 Teardown

On revoke or restart:

- IOMMU mappings must be removed
- pinned pages must be released
- device access must be invalidated

---

## 7. I/O queues

### 7.1 Queue model

`OBJ_IOQUEUE` represents a shared queue between:

- driver (userspace)
- device (hardware)

Queue memory must:

- reside in DMA-safe memory
- be explicitly allocated and validated
- not overlap unrelated memory

### 7.2 Operations

- `queue_submit` (RIGHT_QUEUE_SEND)
- `queue_complete` (RIGHT_QUEUE_RECV)

### 7.3 Invariants

- bounded queue size
- no torn writes
- no stale entry reuse
- memory visibility must follow architecture rules

### 7.4 Concurrency

Queue access must be:

- atomic
- ordered (producer/consumer semantics)
- safe under concurrent device and driver execution

### 7.5 Abort rule

All queue operations must be abortable:

- driver crash → queue invalidated
- device failure → queue drained or aborted

---

## 8. Interrupt delivery

### 8.1 IRQ endpoints

Interrupts are delivered via `OBJ_IRQ`.

### 8.2 Binding

Requires:

- RIGHT_IRQ_BIND

Binding must be exclusive per interrupt source unless explicitly shared by design.

### 8.3 Delivery model

- interrupts are delivered via IPC
- delivery must be bounded
- delivery must be backpressure-aware
- delivery must be abortable

### 8.4 Ordering

- per-IRQ ordering must be preserved
- cross-IRQ ordering is not guaranteed

### 8.5 Storm handling

Interrupt storms must be mitigated via:

- rate limiting
- masking
- policy intervention

---

## 9. Enumeration and hotplug

### 9.1 Enumeration

At boot:

- kernel discovers devices
- constructs `OBJ_DEVICE` objects
- publishes capabilities to authorized components only

No ambient device visibility is permitted.

### 9.2 Hotplug

On insertion:

- device is validated
- object is constructed and published

On removal:

- object is retired
- all dependent capabilities become invalid
- all in-flight operations abort

### 9.3 Policy integration

Policy may:

- allow or deny device exposure
- restrict driver binding
- enforce sandbox constraints

---

## 10. Restart and failure semantics

### 10.1 Driver failure

- all operations abort
- queues reset
- DMA revoked
- IRQ unbound

### 10.2 Device failure

- all dependent operations abort
- device enters safe state
- capabilities are retired

### 10.3 Restart invariants

After restart:

- no stale DMA mappings exist
- no stale queue entries exist
- no stale IRQ bindings exist

---

## 11. Integration rules

### 11.1 With MM (MM.md)

- DMA windows must use frame capabilities
- page ownership must remain consistent
- reclaim must respect DMA quiescence

### 11.2 With scheduler (SCHED.md)

- driver threads must block only via IPC or explicit waits
- interrupt delivery must wake threads correctly
- abort must wake blocked threads

### 11.3 With IPC (IPC.md)

- interrupt delivery uses IPC
- queue notifications may use IPC
- all IPC must be bounded and abortable

### 11.4 With policy (POLICY.md)

All device operations are policy sites.

Policy may:

- allow/deny access
- limit rates
- control binding

Policy must not:

- fabricate device capabilities
- bypass validation

---

## 12. Forbidden patterns

The following are specification violations:

- kernel-resident drivers
- ambient device access
- unbounded DMA
- MMIO without capability validation
- interrupt delivery without capability validation
- cross-driver memory aliasing
- non-abortable queue operations
- stale state after restart
- device access outside capability authority

Any such change is a violation, not an optimization.

---

## 13. Implementation checklist

Before merging any device-related change:

- are all operations capability-validated?
- are DMA windows bounded and revocable?
- are MMIO mappings correct and isolated?
- are I/O queues safe and restartable?
- are interrupts correctly routed and bounded?
- are driver sandboxes enforced?
- are policy hooks present?

Tests must include:

- DMA boundary violations
- MMIO mapping correctness
- interrupt routing correctness
- driver crash and restart
- hotplug handling
- queue overflow and recovery
- policy enforcement

---

## 14. Ground-truth rule

This document is the ground truth for device access and driver isolation in Zuki.

If code and this document disagree, the code is wrong.
