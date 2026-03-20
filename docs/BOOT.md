# Zuki Boot Protocol & Early MMU Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/boot`, `/kernel/arch/*/boot`, and any bootloader or early-userspace component that constructs `BootInfo`, initializes the MMU handoff state, or transfers control to the Zuki kernel.

This document defines:

- the boot protocol and `BootInfo` contract
- early address-space construction
- early MMU and mapping rules
- initial capability-root construction
- initial thread and scheduler entry rules
- early memory-map validation
- failure behavior
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Boot model overview

Zuki’s boot process is:

- deterministic
- capability-rooted
- architecture-neutral at the contract layer
- strictly validated
- hostile to undefined behavior
- designed for multi-architecture bring-up

The bootloader is responsible for:

- constructing a valid `BootInfo`
- providing a minimal validated physical memory map
- loading the kernel image
- transferring control to the architecture-defined kernel entry point

The kernel is responsible for:

- validating `BootInfo`
- validating the memory map and kernel handoff state
- constructing the initial translation environment
- enabling the MMU
- constructing the initial kernel address space object
- constructing the initial capability root
- constructing the initial thread
- transferring control to the scheduler

The kernel must not trust the bootloader beyond the explicit `BootInfo` and entry-state contract.

Boot is a one-way transition from firmware/bootloader state into kernel-owned state. Partial rollback is forbidden.

---

## 2. Boot phases

Zuki boot proceeds through four canonical phases:

1. **Pre-validation entry**
   - kernel has gained control
   - no bootloader-supplied structure is trusted yet

2. **Validated bootstrap**
   - `BootInfo` and memory map have been structurally validated
   - bootstrap memory regions are identified
   - early page-table construction may begin

3. **Early-MMU transition**
   - minimal required mappings are established
   - MMU is enabled
   - control transfers into the kernel’s canonical virtual execution environment

4. **Post-MMU initialization**
   - initial address-space object is constructed
   - initial capability root is constructed
   - initial thread is created
   - scheduler takes control

Each phase is monotonic. Once the kernel advances to a later phase, earlier bootstrap assumptions must not remain authoritative unless explicitly retained by contract.

---

## 3. `BootInfo` contract

## 3.1 Definition

`BootInfo` is a fixed-layout, versioned boot contract structure defined by the boot protocol, not by the object subsystem.

It contains at minimum:

- version fields
- physical memory map
- kernel image location and size
- bootstrap stack description
- optional framebuffer description
- optional ACPI or platform descriptor
- architecture-specific handoff fields

### 3.2 Invariants

- `BootInfo` must be validated before any field is used
- all addresses in `BootInfo` are physical unless explicitly defined otherwise
- all physical addresses must be aligned according to field requirements
- no field may be interpreted before version validation
- no field may be trusted before structural validation
- the kernel must treat malformed or out-of-range fields as fatal boot errors

### 3.3 Versioning

- major version mismatch: kernel must refuse to boot
- minor version mismatch: kernel may accept only if explicitly backward-compatible
- size mismatch: kernel must refuse to boot unless the version contract explicitly allows bounded extension

### 3.4 Pointer and range rules

Any pointer-like field or region descriptor in `BootInfo` must satisfy all of:

- representable in the target physical-address width
- properly aligned
- fully contained within a described valid region
- not overflow when size is added
- not overlap forbidden bootstrap regions unless explicitly permitted by contract

---

## 4. Early memory map

## 4.1 Memory map entry model

Each memory-map entry contains at minimum:

- physical base
- page count or byte size
- region type

Region types include at minimum:

- usable
- reserved
- firmware/platform
- ACPI/platform tables
- MMIO
- kernel/bootloader-owned handoff region where explicitly defined

### 4.2 Invariants

- entries must not overlap
- entries must be page-aligned
- zero-length entries are forbidden
- usable-memory accounting must be consistent with the entry set
- the kernel image must be fully covered by a region valid for kernel ownership at handoff
- the bootstrap stack must be fully covered by a region valid for bootstrap use
- required boot structures must not reside in unusable or MMIO regions unless explicitly defined by the boot contract

### 4.3 Forbidden memory-map conditions

The kernel must refuse to boot on:

- overlapping regions
- zero-length regions
- arithmetic overflow in region bounds
- kernel image outside valid handoff memory
- bootstrap stack outside valid bootstrap memory
- usable regions overlapping firmware/platform-reserved structures

### 4.4 Bootstrap-region derivation

Before any bootstrap allocation, the kernel must derive and reserve the bootstrap regions used for:

- early page tables
- temporary boot stack if relocation occurs
- copied or retained boot structures where required

No bootstrap allocator may use memory outside these validated regions.

---

## 5. Early MMU rules

## 5.1 Required pre-MMU mappings

Before enabling the MMU, the kernel must ensure that the transition path is safely mapped according to architecture requirements.

At minimum, the following must be addressable through the active translation state used during the MMU transition:

- kernel entry path
- kernel image sections required for transition
- bootstrap stack
- `BootInfo`
- early page-table structures themselves

### 5.2 Early page-table construction

The kernel must:

1. allocate early page-table memory from a reserved bootstrap region
2. construct the minimal mappings required for safe MMU enable
3. construct the canonical kernel virtual layout required after transition
4. enable the MMU with architecture-correct barriers and control-register sequencing

### 5.3 Early-MMU invariants

- no general dynamic allocator is permitted before the bootstrap allocator is valid
- no user memory may be mapped during boot
- no unnecessary device memory may be mapped
- writable and executable permissions must not overlap except where architecture bring-up strictly requires a temporary transition and that exception is explicitly documented
- partially initialized translation structures must not be published

### 5.4 Architecture-specific rules

Each supported architecture must define:

- translation-table format
- required bootstrap mappings
- MMU enable sequence
- TLB maintenance requirements
- ASID/PCID or equivalent initialization rules
- mandatory barriers

The common boot contract defines the invariants. Architecture code defines the exact sequence.

---

## 6. Initial address-space construction

## 6.1 Kernel address-space object

After MMU enable, the kernel constructs the initial `OBJ_ADDRSPACE` representing the kernel-owned initial execution address space.

Its payload must include:

- the early root page table as the canonical initial root
- a valid ASID if the architecture uses ASIDs
- a valid map-serialization primitive

### 6.2 Initial mapping properties

The initial kernel address space must satisfy:

- kernel text is executable and not writable
- kernel read-only data is not writable
- kernel writable data is not executable
- no user-accessible mappings exist
- only bootstrap-required aliasing may remain temporarily

### 6.3 Identity-map teardown rule

If identity mappings were required for bootstrap, they must be torn down once they are no longer needed.

Long-lived unintended aliasing between bootstrap identity mappings and canonical kernel mappings is forbidden.

### 6.4 Post-construction invariant

Once the initial address-space object is published:

- page-table ownership belongs to that object
- all later page-table mutation must obey `MM.md`
- early boot code must not continue mutating page tables outside the address-space ownership model

---

## 7. Initial capability root

## 7.1 Root CNode construction

The kernel constructs the initial root capability node as an `OBJ_CNODE`.

Its structure must be:

- fixed-size in slot count
- fully initialized before publication
- governed by the normal CNode and capability invariants after publication

The CNode object’s structure is immutable after publication. Slot contents remain mutable only through explicit capability authority.

### 7.2 Initial capabilities

The initial root CNode must contain at minimum the capabilities required to bootstrap the initial trusted execution graph, including:

- capability to the initial address space
- capability to the initial thread
- capability to the initial capability root where self-reference is part of the CSpace model
- capability to initial memory-management authority or frame-allocation authority as defined by the boot design
- capability to required initial service endpoints only if those services are part of the boot-trusted graph

No additional authority may appear implicitly.

### 7.3 Capability-root invariants

- no ambient authority
- no wildcard capabilities
- no capability inserted without explicit construction
- all inserted capabilities must obey generation, rights, and refcount rules from `CAPABILITIES.md`

---

## 8. Initial thread and scheduler entry

## 8.1 Initial thread construction

The kernel constructs the initial `OBJ_THREAD`:

- bound to the initial address space
- with a valid scheduler context
- with a valid trap frame or entry frame suitable for first dispatch
- with a start PC pointing to the defined first kernel-managed execution routine

### 8.2 Publication order

The minimum publication order is:

1. initial address-space object
2. initial thread object
3. initial capability root
4. scheduler-visible initial runnable state

A narrower boot implementation may construct these in memory in a different order, but no later structure may become authoritative before its dependencies are valid and published.

### 8.3 Scheduler handoff

The kernel transfers control to the scheduler only after:

- scheduler core state is initialized
- the initial thread is valid
- the initial address space is valid
- the initial thread is bound to a valid address space
- the initial runnable handoff is consistent with `SCHED.md`

### 8.4 Invariants

- no thread may run before scheduler initialization completes
- no thread may run without a valid address space
- no thread may run without a valid trap/entry frame
- no user-mode execution may begin during bootstrap unless explicitly defined by a later boot stage contract

---

## 9. Failure behavior

## 9.1 Mandatory boot refusal conditions

The kernel must refuse to boot if any of the following occurs:

- `BootInfo` validation fails
- memory map validation fails
- kernel handoff image is invalid
- required bootstrap mappings cannot be built
- MMU cannot be enabled
- initial address space cannot be constructed
- initial capability root cannot be constructed
- initial thread cannot be constructed
- scheduler bootstrap invariants cannot be satisfied

### 9.2 Failure response

On fatal boot failure, the kernel must:

- halt, or
- enter a well-defined architecture panic state

The kernel must not:

- continue partial boot
- attempt degraded execution without an explicit degraded-boot contract
- attempt to run user code
- apply silent repairs to malformed boot data

### 9.3 Forbidden fallback behavior

The following are forbidden:

- silently ignoring invalid memory-map entries
- guessing missing boot fields
- repairing malformed `BootInfo` heuristically
- continuing after partial MMU or object-construction failure

---

## 10. Concurrency and transition rules

## 10.1 Early boot concurrency model

In v1.0, early boot is single-threaded until the scheduler has taken control.

No concurrent kernel object mutation is permitted before scheduler handoff unless explicitly required by architecture bring-up and contained within non-published bootstrap state.

### 10.2 Publication rule

A bootstrap structure becomes authoritative only when published by the owning subsystem.

Examples:

- early page tables become authoritative when installed as the active root
- the initial address-space object becomes authoritative when published into the object table
- the initial thread becomes scheduler-visible only when published and enqueued according to scheduler rules

### 10.3 Raw-pointer transition rule

Raw physical or bootstrap-only pointers may exist only during bootstrap phases that require them.

After transition into canonical post-MMU ownership:

- long-lived raw physical-pointer retention is forbidden
- long-lived bootstrap-only aliases are forbidden
- subsystem-owned structures must be referenced through their canonical ownership model

---

## 11. Forbidden patterns

The following are specification violations:

- trusting bootloader-provided pointers or descriptors without validation
- enabling the MMU with incomplete required bootstrap mappings
- mapping user memory during early boot
- constructing capabilities before the capability subsystem invariants are in force
- running threads before scheduler initialization
- freeing bootstrap memory before it is no longer reachable and reclaim-safe
- retaining raw physical pointers after canonical virtual transition where canonical ownership should apply
- publishing partially initialized address spaces, CNodes, or threads
- keeping long-lived unintended identity aliases after bootstrap

Any such change is a violation, not an optimization.

---

## 12. Implementation checklist

Before merging any change touching `/kernel/boot` or `/kernel/arch/*/boot`:

- is `BootInfo` fully validated before use?
- are memory-map invariants enforced?
- is bootstrap allocation confined to validated bootstrap regions?
- is early MMU enable deterministic and architecture-correct?
- are required bootstrap mappings complete?
- is the initial address-space object constructed correctly?
- is the initial capability root constructed correctly?
- is the initial thread constructed correctly?
- is scheduler handoff ordered and safe?
- are tests present for:
  - invalid `BootInfo`
  - invalid memory map
  - bootstrap-region overflow
  - MMU enable failure
  - early mapping errors
  - initial thread bring-up
  - capability-root correctness
  - identity-map teardown
  - cross-architecture boot conformance

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 13. Ground-truth rule

This document is the ground truth for booting the Zuki kernel.

If code and this document disagree, the code is wrong.
