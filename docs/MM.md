# Zuki Kernel Memory Management Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/mm` and any kernel code that performs mapping, unmapping, page-table mutation, ASID/TLB management, or interacts with `OBJ_FRAME` and `OBJ_ADDRSPACE`.

This document defines:

- the canonical memory-management model
- page-table ownership and mutation rules
- mapping and unmapping invariants
- ASID and TLB semantics
- concurrency and memory ordering rules
- integration with retire/reclaim
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Memory model overview

Zuki’s memory subsystem is:

- capability-based
- address-space-owned
- deterministic
- safe under concurrent revoke and retire
- strictly serialized for page-table mutation

In v1.0:

- each address space owns exactly one page-table root
- mapping and unmapping mutate only the target address space’s page tables
- frames are mapped only if the caller holds:
  - a valid `OBJ_FRAME` capability with `RIGHT_MAP`, and
  - a valid `OBJ_ADDRSPACE` capability with `RIGHT_MAP`
- unmapping requires a valid `OBJ_ADDRSPACE` capability with `RIGHT_UNMAP`
- TLB invalidation is scoped by ASID and address range as required by the architecture
- no page-table sharing exists between address spaces in v1.0

The memory subsystem must never:

- mutate page tables without owning the target address space mutation path
- expose partially initialized translation structures
- allow stale translations to remain architecturally visible after a completed unmap or teardown operation that requires invalidation
- free page-table memory before reclaim preconditions are satisfied

---

## 2. Address space object integration

Address spaces are represented by `OBJ_ADDRSPACE` objects.

### 2.1 Required payload fields

```c
typedef struct AddressSpacePayload {
    arch_page_table_t *root;
    asid_t             asid;
    lock_t             map_lock;
} AddressSpacePayload;
````

### 2.2 Payload invariants

* `root` identity is immutable after publication
* `asid` is immutable for the lifetime of the address space
* page-table memory reachable from `root` is owned exclusively by this address space
* all page-table mutation is serialized by `map_lock`
* no other subsystem may mutate page tables directly
* no other address space may share `root` or any writable page-table structure in v1.0

### 2.3 Publication rule

`root` and `asid` must be fully initialized before the address-space object is published.

After publication:

* `root` must not change
* `asid` must not change
* all further mutation occurs only within owned page-table memory under `map_lock`

---

## 3. Frame object integration

Frames are represented by `OBJ_FRAME` objects.

### 3.1 Required payload fields

```c
typedef struct FramePayload {
    paddr_t   phys_addr;
    size_t    size;
    uint32_t  attrs;
} FramePayload;
```

### 3.2 Payload invariants

* `phys_addr` is immutable after publication
* `size` is immutable after publication
* `size` must be page-aligned and allocator-constrained
* `attrs` is immutable unless the architecture-specific implementation defines a safe serialized update path

### 3.3 Memory-management role

Frames provide physical backing for mappings.

A frame object does not own page tables and does not serialize page-table mutation.

Existing mappings of a frame are properties of address spaces, not of the frame object itself.

---

## 4. Mapping and unmapping operations

## 4.1 Required rights

To map a frame into an address space, the caller must hold:

* a valid frame capability with `RIGHT_MAP`
* a valid address-space capability with `RIGHT_MAP`

To unmap from an address space, the caller must hold:

* a valid address-space capability with `RIGHT_UNMAP`

### 4.2 Canonical mapping operation

Mapping steps are:

1. validate frame via `cap_use(frame_cap, RIGHT_MAP)`
2. validate address space via `cap_use(as_cap, RIGHT_MAP)`
3. acquire `map_lock` on the address space
4. re-check that the address space remains live for the bounded operation
5. validate mapping constraints:

   * address alignment
   * frame size and range
   * permission compatibility
   * architecture-specific constraints
   * absence or handling of existing conflicting mapping
6. install or update page-table entries
7. perform architecture-required ordering and TLB maintenance
8. release `map_lock`

### 4.3 Canonical unmapping operation

Unmapping steps are:

1. validate address space via `cap_use(as_cap, RIGHT_UNMAP)`
2. acquire `map_lock`
3. re-check that the address space remains live for the bounded operation
4. remove or clear the relevant page-table entries
5. perform architecture-required ordering and TLB invalidation
6. release `map_lock`

### 4.4 Mapping invariants

* page-table entries must not reference reclaimed frame memory
* effective mapping permissions must not exceed the authority implied by the frame capability and architecture rules
* mapping must not occur after address-space retire is observed
* mapping must not produce architecturally invalid aliasing
* mapping must leave page tables structurally consistent

### 4.5 Unmapping invariants

* unmapping must leave page tables structurally consistent
* unmapping does not free frame memory
* unmapping does not by itself retire or reclaim frame objects
* ordinary unmapping must not proceed after retire is observed except as part of serialized address-space teardown

---

## 5. Effective permission model

### 5.1 Permission derivation

The permissions installed into page-table entries must be derived from:

* the rights granted by the validated frame capability
* the requested mapping permissions
* architecture-specific executable, writable, user, and cacheability constraints

### 5.2 Non-amplification rule

A mapping must not amplify authority.

Examples:

* a frame not authorized for writable mapping must not be mapped writable
* a frame not authorized for executable mapping under policy or architecture rules must not be mapped executable
* a narrower requested permission set may be installed, but not a broader one

### 5.3 Architecture responsibility

Architecture-specific code may refine encodings, but it must not weaken the non-amplification rule.

---

## 6. Page-table mutation rules

### 6.1 Serialization

All page-table mutation must be serialized by `map_lock`.

No other lock or ad hoc synchronization primitive may be used as a substitute for page-table mutation ownership on the same address space in v1.0.

### 6.2 Mutation scope

Under `map_lock`, the implementation may:

* allocate intermediate page-table structures
* initialize new translation structures
* install leaf mappings
* remove mappings
* perform teardown of owned translation structures when safe

It must not:

* publish partially initialized page-table structures
* expose mixed old/new state that violates architecture rules after operation completion

### 6.3 Atomicity and visibility

* page-table writes must satisfy the architecture’s atomicity requirements for translation structures
* translation structure initialization must complete before publication into a live page-table path
* required memory ordering for translation visibility must occur before TLB invalidation or context-visible completion
* required TLB invalidation must complete before releasing `map_lock`

### 6.4 Forbidden shortcuts

The following are forbidden:

* mutating page tables without holding `map_lock`
* publishing partially initialized intermediate page tables
* using non-atomic PTE writes where the architecture requires atomicity
* skipping TLB invalidation where the architecture requires it
* releasing `map_lock` before the operation’s required translation maintenance is complete

---

## 7. ASID and TLB semantics

### 7.1 ASID invariants

* each address space has one ASID for its lifetime
* ASID identity is immutable while the address space exists
* ASID reuse is forbidden until architecture-defined safety conditions are met

### 7.2 ASID reuse rule

ASID reuse may occur only after the previous translations associated with that ASID can no longer be observed by any CPU.

This requires architecture-defined completion, such as:

* global invalidation for that ASID
* epoch-based rollover with full safety guarantees
* stronger architecture-specific teardown guarantees

### 7.3 TLB invalidation rules

* mapping and unmapping must perform TLB invalidation as required for the affected address range and ASID
* address-space retire must invalidate translations for the retired address space as required by the architecture
* reclaim must not free page-table memory until required TLB invalidation and quiescence conditions are satisfied

### 7.4 Cross-CPU invalidation

If translations for an ASID may be cached on multiple CPUs:

* invalidation must reach all relevant CPUs
* architecture-required completion must occur before operation completion
* `map_lock` must not be released until the invalidation protocol required by the architecture is complete

---

## 8. Retire and reclaim interaction

## 8.1 Address-space retire

Address-space retire must:

* invalidate capabilities through generation increment
* prevent new mapping and unmapping operations from succeeding
* prevent future scheduler-visible use of the address space as a live execution context
* begin serialized teardown if teardown is implemented as part of retire

Address-space retire must not:

* free page tables directly
* free frame memory
* bypass reclaim preconditions

The phrase “non-runnable” does not apply to address spaces. The correct semantic is: the address space is no longer valid for new operations or future execution binding once retire is observed.

### 8.2 Address-space reclaim

Address-space reclaim may occur only when:

* retire has completed
* quiescence has been observed
* `refcount == 0`
* no threads retain scheduler-owned or active execution references to the address space
* no CPU can still observe reachable page-table memory through active translation state

Reclaim must:

* free page-table memory owned by the address space
* free architecture-specific translation structures
* free payload and object structure

### 8.3 Frame retire

Frame retire:

* invalidates frame capabilities
* does not automatically remove existing mappings
* prevents new capability-based mapping operations once retire is observed

### 8.4 Frame reclaim

Frame reclaim may occur only when:

* retire has completed if the frame has been retired
* quiescence has been observed
* `refcount == 0`
* no address space retains a mapping to the frame
* no CPU can still observe translations referencing the frame

This document does not require a specific reverse-mapping design in v1.0, but the implementation must have a correct way to establish that no mappings remain before reclaiming frame-backed memory.

---

## 9. Concurrency and memory ordering rules

### 9.1 Atomic object fields

The following object-header fields must be atomic as defined by the object subsystem:

* `Object.generation`
* `Object.refcount`

`AddressSpacePayload.root` and `AddressSpacePayload.asid` are immutable after publication and do not require atomic mutation in v1.0.

### 9.2 Locking rules

* `map_lock` serializes all page-table mutation for one address space
* mapping and unmapping on the same address space must not proceed concurrently without `map_lock`
* no path may retain raw page-table or address-space object pointers across blocking or scheduling boundaries unless owned by a narrower architecture-defined internal mechanism that does not violate object lifetime rules

### 9.3 Capability validation ordering

* capability validation for frame and address-space objects must use the acquire/release rules defined in `CAPABILITIES.md`
* mapping and unmapping operations must not assume object liveness beyond the bounded operation in which validation occurred

### 9.4 Translation ordering rule

The implementation must ensure:

* page-table updates become visible in the order required by the architecture
* invalidation occurs after the relevant update
* operation completion is not exposed before required invalidation completion

---

## 10. Forbidden patterns

The following are specification violations:

* modifying page tables without holding `map_lock`
* sharing page-table roots or writable page-table structures between address spaces
* reusing ASIDs without architecture-safe invalidation or rollover
* mapping a frame without validated `RIGHT_MAP`
* unmapping without validated `RIGHT_UNMAP`
* mapping after address-space retire is observed
* retaining raw page-table pointers across blocking or scheduling
* freeing page-table memory before quiescence and translation safety are satisfied
* reclaiming frame memory while any mapping may still reference it
* using page-table mutation as an implicit capability bypass

Any such change is a violation, not an optimization.

---

## 11. Implementation checklist

Before merging any change touching `/kernel/mm`:

* are all mapping and unmapping operations serialized by `map_lock`?
* are frame and address-space capabilities validated with correct rights?
* are effective permissions derived without authority amplification?
* are page-table updates published with architecture-correct ordering?
* are required TLB invalidations performed and completed before operation completion?
* are ASIDs allocated and reused safely?
* does retire prevent new mapping operations?
* does reclaim wait for quiescence, zero refcount, and translation safety?
* does frame reclaim have a correct proof that no mappings remain?
* are tests present for:

  * mapping and unmapping under load
  * concurrent mapping attempts on one address space
  * retire during mapping
  * reclaim after quiescence
  * ASID reuse or rollover safety
  * TLB invalidation correctness
  * frame reclaim with stale-mapping prevention

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 12. Ground-truth rule

This document is the ground truth for memory management in the Zuki kernel.

If code and this document disagree, the code is wrong.
