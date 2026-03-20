# Zuki Kernel Capability Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** This document is binding for all code under `/kernel/cap` and any kernel code that manipulates capabilities, object metadata, or object lifetime.

This document defines the concrete invariants, access patterns, and lifecycle rules for Zuki’s capability subsystem.

Code in `/kernel/cap` must be written top-down, readable, and structurally obvious. Live code should remain comment-minimal. This document carries the explanatory burden.

---

## 1. Core model

Zuki’s capability subsystem enforces four non-negotiable properties:

1. A capability is valid if and only if its minted generation matches the current object generation.
2. Revocation is constant-time and performed only by generation increment.
3. No object slot may be reused until retire/reclaim conditions are satisfied.
4. All object access must pass through `cap_use()`.

No optimization may weaken these properties.

---

## 2. Core data structures

All capability and object access must go through these structures and their invariants.

### 2.1 Constants and sentinel values

```c
typedef uint32_t ObjectID;
typedef uint32_t Rights;
typedef uint64_t CapabilityID;

enum {
    OBJECT_ID_INVALID = UINT32_MAX
};
````

`OBJECT_ID_INVALID` is the only invalid object identifier. No valid object may use this value.

### 2.2 Object types

```c
typedef enum {
    OBJ_FRAME,
    OBJ_CNODE,
    OBJ_THREAD,
    OBJ_ADDRSPACE,
    OBJ_ENDPOINT,
    OBJ_NOTIFICATION,
} ObjectType;
```

v1.0 defines no user-defined object types.

### 2.3 Object metadata

```c
typedef struct Object {
    ObjectID          id;
    _Atomic uint64_t  generation;
    _Atomic uint32_t  refcount;
    ObjectType        type;
    void             *payload;
    _Atomic uint32_t  flags;
} Object;
```

#### Invariants

* `id` is stable for the lifetime of the object slot.
* `generation` is strictly monotonic and must not wrap during system lifetime.
* `generation` is incremented only on retire/revoke.
* `refcount > 0` while the object is retained by any live capability or lease.
* `type` is immutable for the lifetime of the slot.
* `payload` identity is immutable for the lifetime of the published object.
* `payload` remains valid until reclaim frees the object.
* `flags` contains lifecycle state only; capability validity does not depend on flags.

#### Flags

```c
enum {
    OBJ_FLAG_RETIRED     = 1u << 0,
    OBJ_FLAG_RECLAIMABLE = 1u << 1,
};
```

* `OBJ_FLAG_RETIRED`: object has been revoked and placed on a retire list.
* `OBJ_FLAG_RECLAIMABLE`: object is eligible for reclaim after quiescence and zero refcount.

### 2.4 Capability representation

```c
typedef struct Capability {
    ObjectID      object_id;
    uint64_t      gen_at_mint;
    Rights        rights;
    CapabilityID  cap_id;
} Capability;
```

#### Invariants

* `object_id` refers to an object table slot or `OBJECT_ID_INVALID`.
* `gen_at_mint == object.generation` at mint time.
* `rights` is a subset of the rights held by the source capability.
* `cap_id` is optional and non-authoritative. It exists for tracing and telemetry only.

Capabilities are copied by value. No code may embed or cache raw `Object *` inside a capability.

### 2.5 Object table

```c
extern _Atomic(Object *) object_table[];
extern const size_t      object_table_size;
```

#### Invariants

* object table entries are stable in address identity while published.
* v1.0 forbids table compaction.
* a slot is published by storing a valid `Object *`.
* a slot is unpublished by storing `NULL`.
* object reuse occurs only after retire/reclaim completes.

---

## 3. `cap_use()` — mandatory access path

All object access must pass through `cap_use()`. There are no exceptions.

### 3.1 Contract

```c
Object *cap_use(const Capability *cap, Rights required_rights);
```

#### Purpose

Validate a capability and return a stable pointer to the referenced object.

#### Pre

* `cap != NULL`
* `cap->object_id != OBJECT_ID_INVALID`
* `required_rights` is the full set of rights needed for the intended operation

#### Post

Returns non-`NULL` only if:

* the object table slot exists
* rights are sufficient
* `cap->gen_at_mint == obj->generation`

If non-`NULL` is returned, the object pointer is valid for the duration of the caller’s bounded kernel operation. The caller must not retain it beyond that operation.

#### Required properties

* O(1)
* lock-free on the read path
* no refcount modification
* no blocking
* no capability slot walking

### 3.2 Canonical implementation pattern

```c
Object *cap_use(const Capability *cap, Rights required_rights)
{
    if (cap == NULL) {
        return NULL;
    }

    if (cap->object_id == OBJECT_ID_INVALID || cap->object_id >= object_table_size) {
        return NULL;
    }

    if ((cap->rights & required_rights) != required_rights) {
        return NULL;
    }

    Object *obj = atomic_load_explicit(&object_table[cap->object_id],
                                       memory_order_acquire);
    if (obj == NULL) {
        return NULL;
    }

    uint64_t gen = atomic_load_explicit(&obj->generation, memory_order_acquire);
    if (cap->gen_at_mint != gen) {
        return NULL;
    }

    return obj;
}
```

### 3.3 Semantics

`cap_use()` provides validation, not ownership.

It guarantees:

* the object slot exists at the time of validation
* the generation matched at the point of validation
* reclaim cannot free the object until retire/reclaim rules are satisfied

It does not guarantee:

* immunity from later revoke after the call returns
* permission to retain the returned pointer across blocking, scheduling, or unrelated long-lived work

Callers that need extended retention must use a lease or another explicit retention mechanism.

---

## 4. Memory ordering rules

These are mandatory.

### 4.1 Publication and validation

* object table slot publication uses release semantics
* object table slot load in `cap_use()` uses acquire semantics
* generation increment on retire uses release semantics
* generation read in `cap_use()` uses acquire semantics
* refcount loads in reclaim use acquire semantics

### 4.2 Rules

* no torn reads of `generation`, `refcount`, `flags`, or object table entries
* no non-atomic access to atomic fields
* no object reuse before generation increment is globally visible and quiescence is observed

### 4.3 Prohibited shortcuts

* load/store pairs for generation increment
* non-atomic “fast reads” of generation or refcount
* object slot reuse based only on `refcount == 0`

---

## 5. Object lifecycle

This section defines the only permitted destruction and reuse pattern.

### 5.1 States

Each object slot is in exactly one lifecycle state:

* **LIVE**: `OBJ_FLAG_RETIRED` clear
* **RETIRED**: `OBJ_FLAG_RETIRED` set, generation bumped, on retire list
* **RECLAIMABLE**: retired and eligible for reclaim after quiescence
* **FREE**: slot unpublished and available for allocation

Flags are advisory state markers. Capability validity is determined only by generation.

### 5.2 Retire path

Retire invalidates all existing capabilities in O(1) time.

```c
void object_retire(Object *obj)
{
    atomic_fetch_or_explicit(&obj->flags,
                             OBJ_FLAG_RETIRED,
                             memory_order_relaxed);

    atomic_fetch_add_explicit(&obj->generation,
                              1,
                              memory_order_release);

    retire_list_enqueue(obj);
}
```

#### Required properties

* no capability slots are walked
* no payload is freed
* no object table entry is cleared
* retire may be repeated only if the wider lifecycle guarantees idempotence; otherwise callers must ensure retire happens once

#### Note

Generation increment must be atomic fetch-add. A load/store pair is forbidden because concurrent retire paths would lose increments.

### 5.3 Reclaim path

Reclaim is responsible for freeing retired objects only after quiescence and zero refcount.

```c
void reclaim_retired_objects(void)
{
    Object *obj;

    while ((obj = retire_list_dequeue()) != NULL) {
        uint32_t refs = atomic_load_explicit(&obj->refcount,
                                             memory_order_acquire);

        if (refs != 0) {
            retire_list_reenqueue(obj);
            continue;
        }

        atomic_fetch_or_explicit(&obj->flags,
                                 OBJ_FLAG_RECLAIMABLE,
                                 memory_order_relaxed);

        free_object_payload(obj);

        atomic_store_explicit(&object_table[obj->id],
                              NULL,
                              memory_order_release);

        free_object_struct(obj);
    }
}
```

### 5.4 Quiescent state requirement

Reclaim must run only after a global quiescent state.

A quiescent state means one of:

* all cores have passed through a context switch, or
* a global epoch has advanced and all participating cores have acknowledged it

No reclaim path may bypass this requirement.

---

## 6. Capability operations

These are the canonical patterns for mint, destroy, and lease.

### 6.1 Mint

Mint creates a derived capability with equal or fewer rights.

```c
int cap_mint(Capability       *child_cap,
             const Capability *parent_cap,
             Rights            rights)
{
    if (child_cap == NULL || parent_cap == NULL) {
        return ERR_INVALID;
    }

    if ((rights & parent_cap->rights) != rights) {
        return ERR_RIGHTS;
    }

    Object *obj = cap_use(parent_cap, 0);
    if (obj == NULL) {
        return ERR_REVOKED;
    }

    uint64_t gen = atomic_load_explicit(&obj->generation, memory_order_acquire);

    atomic_fetch_add_explicit(&obj->refcount, 1, memory_order_relaxed);

    child_cap->object_id   = parent_cap->object_id;
    child_cap->gen_at_mint = gen;
    child_cap->rights      = rights;
    child_cap->cap_id      = alloc_cap_id();

    return OK;
}
```

#### Required properties

* rights can only be reduced, never amplified
* minted generation must match the generation observed during the same validated operation
* child capability is valid only if the source object remained live through validation

#### Note

In v1.0, `cap_mint()` assumes the validated object cannot be reclaimed during the bounded mint operation. If the implementation later permits blocking or preemption in mint, mint must be upgraded to use an explicit retention mechanism.

### 6.2 Destroy

Destroy clears a capability slot and decrements refcount only if the capability was still live.

```c
int cap_destroy(Capability *cap)
{
    if (cap == NULL) {
        return ERR_INVALID;
    }

    if (cap->object_id != OBJECT_ID_INVALID && cap->object_id < object_table_size) {
        Object *obj = atomic_load_explicit(&object_table[cap->object_id],
                                           memory_order_acquire);

        if (obj != NULL) {
            uint64_t gen = atomic_load_explicit(&obj->generation,
                                                memory_order_acquire);

            if (cap->gen_at_mint == gen) {
                uint32_t old_refs = atomic_fetch_sub_explicit(&obj->refcount,
                                                              1,
                                                              memory_order_relaxed);
                if (old_refs == 0) {
                    kernel_panic("cap_destroy: refcount underflow");
                }
            }
        }
    }

    cap->object_id   = OBJECT_ID_INVALID;
    cap->gen_at_mint = 0;
    cap->rights      = 0;
    cap->cap_id      = 0;

    return OK;
}
```

#### Required properties

* destroying a stale capability must not decrement refcount
* capability slot clear must leave the slot unambiguously invalid
* refcount underflow is a kernel bug

### 6.3 Lease

Leases provide bounded temporary retention for operations that cannot rely on plain `cap_use()` scope.

```c
typedef struct Lease {
    ObjectID  object_id;
    uint64_t  gen_at_lease;
} Lease;
```

#### Acquire

```c
int lease_acquire(Lease *lease, const Capability *cap, Rights required)
{
    if (lease == NULL || cap == NULL) {
        return ERR_INVALID;
    }

    Object *obj = cap_use(cap, required);
    if (obj == NULL) {
        return ERR_REVOKED;
    }

    atomic_fetch_add_explicit(&obj->refcount, 1, memory_order_relaxed);

    lease->object_id    = cap->object_id;
    lease->gen_at_lease = cap->gen_at_mint;

    return OK;
}
```

#### Release

```c
int lease_release(const Lease *lease)
{
    if (lease == NULL) {
        return ERR_INVALID;
    }

    if (lease->object_id == OBJECT_ID_INVALID || lease->object_id >= object_table_size) {
        return ERR_INVALID;
    }

    Object *obj = atomic_load_explicit(&object_table[lease->object_id],
                                       memory_order_acquire);
    if (obj == NULL) {
        return ERR_OBJECT_DEAD;
    }

    uint32_t old_refs = atomic_fetch_sub_explicit(&obj->refcount,
                                                  1,
                                                  memory_order_relaxed);
    if (old_refs == 0) {
        kernel_panic("lease_release: refcount underflow");
    }

    return OK;
}
```

#### Lease semantics

* lease acquisition requires a valid live capability
* revoke prevents new leases but does not cancel existing leases
* reclaim must wait for all leases to release via refcount reaching zero

---

## 7. Race scenarios and why they are safe

These scenarios are normative examples of the intended behavior.

### 7.1 Revoke vs `cap_use`

Scenario:

* thread A calls `cap_use(cap)`
* thread B calls `object_retire(obj)`

Outcomes:

* if A reads the old generation before B’s release increment, validation succeeds
* if A reads the new generation after B’s release increment, validation fails

Why safe:

* generation comparison is atomic
* reclaim cannot free until quiescence and zero refcount
* `cap_use()` cannot observe torn object metadata

### 7.2 Destroy vs revoke vs reclaim

Scenario:

* thread A destroys a capability
* thread B retires the object
* thread C runs reclaim later

Outcomes:

* if destroy sees the live generation, it decrements refcount
* if destroy sees the retired generation, it does not decrement
* reclaim frees only after quiescence and zero refcount

Why safe:

* stale capabilities do not affect refcount
* live capabilities are accounted before reclaim proceeds
* no object is freed while still retained

### 7.3 `cap_use` vs reclaim

Scenario:

* thread A calls `cap_use`
* thread B retires and later reclaims the object

Why safe:

* reclaim is delayed until quiescence
* object table entry remains published until reclaim
* `cap_use()` sees either a matching live generation or a mismatched retired generation

### 7.4 Lease vs revoke vs reclaim

Scenario:

* thread A acquires a lease
* thread B retires the object
* thread C attempts reclaim

Outcomes:

* reclaim sees non-zero refcount and defers
* lease release eventually decrements refcount
* reclaim succeeds only after refcount becomes zero

Why safe:

* revoke blocks new access
* existing lease preserves retention
* reclaim respects retention and quiescence

---

## 8. Forbidden patterns

The following are specification violations:

* storing raw `Object *` in long-lived structures
* accessing objects without `cap_use()` or an explicit lease/retention mechanism
* mutating `Object.id`, `Object.type`, or published object identity
* reusing object slots without retire/reclaim
* non-atomic access to `generation`, `refcount`, `flags`, or object table entries
* generation increment via load/store pair
* per-capability revoke by walking CNodes
* object table compaction in v1.0
* retaining a `cap_use()` result across blocking or scheduling boundaries

Any such change is a violation, not an optimization.

---

## 9. Implementation checklist

Before merging any change touching `/kernel/cap` or object lifecycle:

* does every object access go through `cap_use()` or a defined retention path?
* are all object table, generation, refcount, and flag accesses atomic with correct memory order?
* does every destruction path follow retire/reclaim?
* can any path underflow refcount?
* can any path free or reuse an object before quiescence?
* are new races introduced between mint, destroy, lease, retire, and reclaim?
* are tests added for:

  * revoke under load
  * concurrent mint/destroy/revoke
  * lease acquire/release under revoke
  * reclaim after delayed quiescence
  * refcount underflow defense

If any answer is no, unknown, or hand-waved, the change is not ready.

---

## 10. Ground-truth rule

This document is the ground truth for capability handling in the Zuki kernel.

If code and this document disagree, the code is wrong.
