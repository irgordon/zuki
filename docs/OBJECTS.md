# Zuki Object Model — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code that defines, creates, publishes, mutates, retires, or reclaims kernel objects.

This document defines:

- the canonical object model
- object layout and invariants
- object lifecycle (construction → publication → retire → reclaim)
- concurrency and memory ordering rules
- ownership boundaries across subsystems
- bootstrap interaction rules
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Object model overview

Zuki’s object model is:

- capability-addressed
- generation-protected
- refcounted
- type-safe
- concurrency-safe under adversarial input

All kernel-managed entities are represented as objects.

Objects are never accessed directly by user space. All access is mediated through capabilities.

---

## 2. Canonical object structure

All objects share a common header:

```c
typedef struct Object {
    ObjectID        id;
    ObjectType      type;
    _Atomic uint32_t generation;
    _Atomic uint32_t refcount;
} Object;
````

Each object embeds a type-specific payload:

```c
typedef struct ObjectX {
    Object header;
    XPayload payload;
} ObjectX;
```

---

## 3. Object invariants

The following invariants must always hold:

* `generation` uniquely identifies the current lifetime of the object slot
* `refcount` tracks all active references (capabilities + kernel references)
* object memory must remain valid while `refcount > 0`
* object type must not change after initialization
* payload must be fully initialized before publication

Violation of any invariant is a kernel correctness failure.

---

## 4. Object lifecycle

Objects follow a strict lifecycle:

1. **Construction** (not visible)
2. **Publication** (visible and usable)
3. **Retire** (logically dead)
4. **Reclaim** (memory freed)

### 4.1 Construction

During construction:

* memory is allocated
* header fields are initialized
* payload is fully initialized
* `generation` is set
* `refcount` is initialized

The object must not be visible outside the constructing context.

### 4.2 Publication

Publication makes the object globally visible.

After publication:

* object may be referenced via capabilities
* object participates in subsystem behavior
* all invariants must be fully satisfied

Publishing a partially initialized object is forbidden.

### 4.3 Retire

Retire:

* increments `generation`
* invalidates all existing capabilities
* prevents future use via `cap_use()`

Retire does not free memory.

### 4.4 Reclaim

Reclaim may occur only when:

* object is retired
* `refcount == 0`
* quiescence has been observed

Reclaim frees object memory and returns the slot for reuse.

---

## 5. Construction vs publication

Objects are created in two strictly separated phases:

### 5.1 Construction phase

During construction:

* object fields may be initialized
* object is not globally visible
* object is not reachable via capabilities
* object must not participate in scheduler, IPC, or memory subsystems

### 5.2 Publication phase

After publication:

* object becomes visible through the object table
* object may be referenced via capabilities
* object may participate in subsystem behavior
* all invariants must be satisfied

Publishing a partially initialized object is forbidden.

---

## 6. Bootstrap construction exception

During early boot (see BOOT.md), objects may be constructed before:

* scheduler initialization
* full capability graph availability
* full concurrency model activation

However:

* all object invariants must be satisfied before publication
* no partially initialized object may be published
* no object may be externally referenced before publication

Bootstrap does not weaken object correctness rules.
It only delays when publication occurs.

---

## 7. Initial object graph (boot)

The initial set of objects is constructed by the kernel during boot (see BOOT.md):

* initial `OBJ_ADDRSPACE`
* initial `OBJ_THREAD`
* initial `OBJ_CNODE`

These objects:

* are constructed in isolation
* are fully initialized
* are published in a defined order
* form the root of the system object graph

No other objects may exist before this root is established.

---

## 8. Object types

Zuki defines the following object types in v1.0:

* `OBJ_THREAD`
* `OBJ_ADDRSPACE`
* `OBJ_FRAME`
* `OBJ_ENDPOINT`
* `OBJ_CNODE`
* additional types as defined by subsystem documents

Each type must define:

* payload structure
* invariants
* lifecycle interactions

---

## 9. Ownership after publication

After publication:

* `OBJ_ADDRSPACE` is governed by the memory subsystem (MM.md)
* `OBJ_THREAD` is governed by the scheduler (SCHED.md)
* `OBJ_CNODE` is governed by the capability subsystem (CAPABILITIES.md)

The object model defines invariants.
Subsystem documents define behavior.

---

## 10. Pointer discipline

### 10.1 Post-publication rule

After publication:

* objects must not be accessed via raw physical pointers
* objects must not be accessed via bootstrap-only aliases
* all access must occur through the object model and capability system

### 10.2 Bootstrap exception

During early boot (see BOOT.md):

* raw pointers may exist temporarily
* bootstrap-only aliases may be used

These must not persist after publication.

---

## 11. CNode immutability clarification

For `OBJ_CNODE`:

* structure (slot count, layout) is immutable after publication
* slot contents are mutable only through valid capability operations

Direct mutation of CNode slots outside capability operations is forbidden.

---

## 12. Concurrency and memory ordering

### 12.1 Atomic fields

The following must be atomic:

* `generation`
* `refcount`

### 12.2 Generation semantics

* incrementing `generation` invalidates all stale capabilities
* `cap_use()` must verify generation equality

### 12.3 Refcount semantics

* increment before use
* decrement after release
* reclaim only when `refcount == 0`

### 12.4 Memory ordering

* retire must use release semantics
* `cap_use()` must use acquire semantics
* no torn reads are permitted

---

## 13. Forbidden patterns

The following are specification violations:

* publishing partially initialized objects
* accessing objects via raw pointers after publication
* mutating object type after initialization
* reclaiming without quiescence
* bypassing generation checks
* bypassing refcount rules
* constructing objects outside the object model
* exposing object memory directly to user space

Any such change is a violation, not an optimization.

---

## 14. Implementation checklist

Before merging any change touching object logic:

* are construction and publication clearly separated?
* are all invariants satisfied before publication?
* are generation and refcount handled correctly?
* is retire safe under concurrency?
* is reclaim safe under quiescence?
* are ownership boundaries respected?
* are bootstrap rules followed?
* are pointer discipline rules enforced?
* are tests present for:

  * stale capability rejection
  * concurrent retire/use
  * reclaim after quiescence
  * bootstrap object construction
  * initial object graph correctness

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 15. Ground-truth rule

This document is the ground truth for the Zuki object model.

If code and this document disagree, the code is wrong.
