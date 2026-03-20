# Zuki Kernel Object Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/obj` and any kernel code that allocates, mutates, retires, reclaims, or frees kernel objects.

This document defines:

- the canonical layout of each kernel object type
- the invariants governing object identity and lifetime
- the rules for payload allocation, publication, mutation, retirement, and reclaim
- the rights model for each object type
- the concurrency model for object mutation
- the integration of each object type with the retire/reclaim protocol

This document is the ground truth for object handling in the Zuki kernel.

If code and this document disagree, the code is wrong.

---

## 1. Object model overview

Zuki’s kernel objects share a common metadata header (`Object`) and a type-specific payload.

All objects:

1. are referenced exclusively through capabilities
2. are validated exclusively through `cap_use()`
3. participate in the retire/reclaim lifecycle
4. obey strict concurrency and memory ordering rules

Objects are never accessed directly by raw pointer except through:

- a validated `Object *` returned by `cap_use()`, or
- an explicit retention mechanism such as a lease where defined by subsystem rules

A raw `Object *` obtained through validation is valid only for a bounded kernel operation. It must not be retained across blocking, scheduling, or unrelated long-lived work.

---

## 2. Common object metadata

All object types embed the following header:

```c
typedef struct Object {
    ObjectID          id;
    _Atomic uint64_t  generation;
    _Atomic uint32_t  refcount;
    ObjectType        type;
    void             *payload;
    _Atomic uint32_t  flags;
} Object;
````

### 2.1 Header invariants

* `id` is stable for the lifetime of the object slot.
* `generation` is strictly monotonic and is incremented only on retire.
* `generation` must not wrap during system lifetime.
* `refcount > 0` while any live capability or lease retains the object.
* `type` is immutable after publication.
* `payload` identity is immutable after publication.
* `payload` remains valid until reclaim frees the object.
* `flags` are advisory lifecycle state only. Capability validity depends only on generation.

### 2.2 Payload allocation rules

* payload must be fully allocated and initialized before publishing the object table entry
* payload must be freed only during reclaim
* payload must not be replaced after publication
* payload must not be mutated after retire unless explicitly permitted by the object-type rules in this document

### 2.3 Publication rules

An object becomes visible to the rest of the kernel only when:

1. payload is allocated and initialized
2. `Object` is allocated and initialized
3. all immutable fields are final
4. `object_table[id]` is published with `store_release`

After publication:

* object identity must not change
* payload identity must not change
* type must not change
* object table compaction is forbidden in v1.0

---

## 3. Object types

Zuki v1.0 defines six kernel object types:

1. `OBJ_FRAME`
2. `OBJ_CNODE`
3. `OBJ_THREAD`
4. `OBJ_ADDRSPACE`
5. `OBJ_ENDPOINT`
6. `OBJ_NOTIFICATION`

Each type has:

* a canonical payload layout
* a rights model
* allowed operations
* concurrency rules
* retire/reclaim behavior

No kernel object may exist outside these definitions in v1.0.

---

## 4. Frame objects (`OBJ_FRAME`)

Frames represent physical memory pages or contiguous physical memory regions.

### 4.1 Payload layout

```c
typedef struct FramePayload {
    paddr_t   phys_addr;
    size_t    size;
    uint32_t  attrs;
} FramePayload;
```

### 4.2 Payload invariants

* `phys_addr` is immutable after publication
* `size` is immutable after publication
* `size` must be page-aligned and power-of-two or otherwise constrained by the frame allocator contract
* `attrs` is immutable after publication unless an architecture-specific rule explicitly permits a safe update path

### 4.3 Rights model

| Right         | Meaning                                   |
| ------------- | ----------------------------------------- |
| `RIGHT_MAP`   | map into an address space                 |
| `RIGHT_SHARE` | mint derived frame capabilities           |
| `RIGHT_READ`  | read via kernel-mediated copy operations  |
| `RIGHT_WRITE` | write via kernel-mediated copy operations |

### 4.4 Allowed operations

* mapping into `OBJ_ADDRSPACE`
* unmapping from `OBJ_ADDRSPACE`
* minting derived capabilities with reduced rights
* lease acquisition for temporary retention where needed

### 4.5 Concurrency rules

* frame payload is immutable after publication
* frame objects do not serialize mapping operations
* mapping and unmapping synchronization is the responsibility of the target address space

### 4.6 Retire/reclaim behavior

* retire invalidates all frame capabilities by generation increment
* retire does not itself remove existing mappings
* reclaim frees only the frame payload and object structure according to allocator rules
* policy for reclaiming the underlying physical memory is external to the frame object contract and must occur only after reclaim eligibility is satisfied

---

## 5. CNode objects (`OBJ_CNODE`)

CNodes store capability slots and define the kernel capability address space.

### 5.1 Payload layout

```c
typedef struct CNodePayload {
    size_t       slot_count;
    Capability  *slots;
} CNodePayload;
```

### 5.2 Payload invariants

* `slot_count` is immutable after publication
* `slots` identity is immutable after publication
* slot array size is fixed for the lifetime of the object
* no resizing or compaction is permitted in v1.0

### 5.3 Rights model

| Right         | Meaning                                    |
| ------------- | ------------------------------------------ |
| `RIGHT_READ`  | inspect or enumerate capability slots      |
| `RIGHT_WRITE` | insert, replace, or clear capability slots |
| `RIGHT_MINT`  | mint new capabilities into this CNode      |

### 5.4 Allowed operations

* capability insert
* capability move
* capability destroy
* capability enumeration where permitted
* CSpace construction

### 5.5 Concurrency rules

* CNode size is immutable
* individual slot mutation must be externally serialized or use a well-defined atomic slot protocol
* concurrent mutation of the same slot without serialization is forbidden

### 5.6 Retire/reclaim behavior

* retire invalidates all capabilities referencing the CNode object itself
* retire does not walk slots for per-capability revocation
* reclaim must destroy or otherwise account for all contained slots according to the capability subsystem rules before freeing the slot array
* reclaim then frees the slot array and object structure

---

## 6. Thread objects (`OBJ_THREAD`)

Threads represent schedulable execution contexts.

### 6.1 Payload layout

```c
typedef struct ThreadPayload {
    ObjectID            addrspace_id;
    sched_context_t    *sched_ctx;
    TrapFrame          *trap_frame;
    _Atomic uint32_t    state;
} ThreadPayload;
```

### 6.2 Payload invariants

* `addrspace_id` identifies the bound address space object and is mutable only through a defined bind/rebind operation if such an operation exists
* `sched_ctx` identity is immutable after publication unless replaced by a scheduler-defined transition that is externally serialized
* `trap_frame` identity is immutable after publication
* `state` is atomic and reflects runnable, blocked, stopped, or equivalent scheduler-defined states

### 6.3 Rights model

| Right          | Meaning                                                                     |
| -------------- | --------------------------------------------------------------------------- |
| `RIGHT_RUN`    | permit scheduling or resume operations                                      |
| `RIGHT_SIGNAL` | permit signal or wake-style operations defined by scheduler/IPC integration |
| `RIGHT_DEBUG`  | inspect or modify architecturally permitted thread state                    |

### 6.4 Allowed operations

* scheduling
* descheduling
* trap entry and return
* IPC block and unblock transitions
* debug inspection where permitted

### 6.5 Concurrency rules

* `state` must be mutated atomically
* `trap_frame` contents may be mutated only by the scheduler, trap handler, or debugger path explicitly authorized to do so
* any mutation of non-atomic thread payload fields must be externally serialized
* no thread payload mutation is permitted after retire except transitions required to complete stop/abort handling before reclaim eligibility

### 6.6 Retire/reclaim behavior

* retire makes the thread non-runnable and prevents future scheduling
* retire must abort or resolve any outstanding waits according to scheduler and IPC rules
* reclaim frees the trap frame, scheduler context, and payload
* reclaim must not run until refcount is zero and quiescence is satisfied

---

## 7. Address space objects (`OBJ_ADDRSPACE`)

Address spaces represent virtual memory contexts.

### 7.1 Payload layout

```c
typedef struct AddressSpacePayload {
    arch_page_table_t *root;
    asid_t             asid;
    lock_t             map_lock;
} AddressSpacePayload;
```

### 7.2 Payload invariants

* `root` identity is immutable after publication
* `asid` is immutable after publication
* page-table contents are mutable only through defined mapping operations
* `map_lock` or equivalent serialization mechanism is mandatory for page-table mutation in v1.0

### 7.3 Rights model

| Right         | Meaning                                             |
| ------------- | --------------------------------------------------- |
| `RIGHT_MAP`   | map frames into the address space                   |
| `RIGHT_UNMAP` | unmap frames from the address space                 |
| `RIGHT_CLONE` | create derived or child address spaces if supported |

### 7.4 Allowed operations

* mapping frames
* unmapping frames
* TLB invalidation
* cloning where supported by architecture and subsystem rules

### 7.5 Concurrency rules

* page table mutation must be serialized
* read-only inspection paths may be lock-free only if backed by a documented safe synchronization scheme
* `asid` is immutable
* no ad hoc page-table mutation outside the address-space subsystem is permitted

### 7.6 Retire/reclaim behavior

* retire invalidates all capabilities referencing the address-space object
* retire prevents new mapping operations
* retire may trigger architecture-specific teardown, but does not relax reclaim preconditions
* reclaim frees page tables, architecture-specific translation structures, and payload

Retire does **not** mean “invalidate all mappings immediately” unless the architecture-specific implementation explicitly performs such teardown as part of serialized retirement. The minimum required semantic is: no new valid access through the address-space object after retire.

---

## 8. Endpoint objects (`OBJ_ENDPOINT`)

Endpoints are synchronous IPC channels with bounded queueing.

### 8.1 Payload layout

```c
typedef struct MessageSlot {
    ipc_message_t  message;
    Capability    *caps;
    size_t         cap_count;
} MessageSlot;

typedef struct EndpointPayload {
    _Atomic ObjectID waiter_thread_id;
    MessageSlot     *queue;
    size_t           queue_len;
    size_t           queue_cap;
    lock_t           queue_lock;
} EndpointPayload;
```

### 8.2 Payload invariants

* `queue` identity is immutable after publication
* `queue_cap` is immutable after publication
* `queue_len` is mutated only under endpoint serialization
* `waiter_thread_id` is either a valid thread object id or `OBJECT_ID_INVALID`
* endpoint queue capacity is bounded and must not grow dynamically in v1.0

### 8.3 Rights model

| Right            | Meaning                             |
| ---------------- | ----------------------------------- |
| `RIGHT_SEND`     | send messages                       |
| `RIGHT_RECV`     | receive messages                    |
| `RIGHT_TRANSFER` | transfer capabilities with messages |

### 8.4 Allowed operations

* synchronous send
* synchronous receive
* bounded queue management
* capability transfer as part of IPC

### 8.5 Concurrency rules

* queue mutation must be externally serialized or protected by the endpoint’s defined lock/protocol
* `waiter_thread_id` must be updated atomically
* send/receive paths must obey the IPC subsystem’s deadlock and abort rules
* indefinite blocking due to queue saturation is forbidden

### 8.6 Retire/reclaim behavior

* retire aborts blocked IPC operations associated with the endpoint
* retire prevents new send/receive operations from succeeding
* reclaim frees queued message storage, transferred capability storage that remains owned by the endpoint, and payload
* reclaim must not free the endpoint while blocked or queued operations still retain object references

---

## 9. Notification objects (`OBJ_NOTIFICATION`)

Notifications are lightweight event sources.

### 9.1 Payload layout

```c
typedef struct NotificationPayload {
    _Atomic uint32_t pending;
} NotificationPayload;
```

### 9.2 Payload invariants

* `pending` is atomic
* notification payload contains no mutable identity-bearing pointer fields in v1.0

### 9.3 Rights model

| Right          | Meaning               |
| -------------- | --------------------- |
| `RIGHT_SIGNAL` | send notification     |
| `RIGHT_WAIT`   | wait for notification |

### 9.4 Allowed operations

* signal
* wait
* clear or consume pending bits according to notification semantics

### 9.5 Concurrency rules

* `pending` is modified atomically
* no additional synchronization is required beyond atomic update semantics unless a wider subsystem introduces waiting queues

### 9.6 Retire/reclaim behavior

* retire invalidates all notification capabilities
* retire prevents new wait/signal operations from succeeding
* reclaim frees payload and object structure

Retire may clear pending state as part of teardown, but correctness must not depend on pending bits being preserved after retire.

---

## 10. Object allocation and publication

### 10.1 Allocation sequence

Every object allocation must follow this order:

1. allocate payload
2. initialize payload
3. allocate `Object`
4. initialize `Object` fields
5. set initial `generation`, `refcount`, `type`, `payload`, and `flags`
6. publish into `object_table[id]` with `store_release`

### 10.2 Initial state requirements

At publication time:

* `generation` must be the first live generation for the slot
* `refcount` must reflect the initial live retention owned by the creating path
* `flags` must not indicate retired or reclaimable
* payload must be fully initialized

### 10.3 Publication invariant

Once published:

* `Object *` identity must not change
* payload identity must not change
* type must not change

---

## 11. Object mutation rules

### 11.1 Immutable fields

The following fields are immutable after publication:

* `Object.id`
* `Object.type`
* `Object.payload`
* `FramePayload.phys_addr`
* `FramePayload.size`
* `AddressSpacePayload.asid`
* fixed-capacity sizing fields such as `slot_count` and `queue_cap`

### 11.2 Mutable fields

The following fields may mutate only under their defined synchronization rules:

* `Object.refcount`
* `Object.flags`
* `Object.generation` on retire only
* thread state
* endpoint queue contents and queue length
* notification pending bits
* address-space page tables

### 11.3 Forbidden mutations

The following are specification violations:

* changing object identity
* changing payload identity
* changing object type
* changing object id
* mutating immutable payload fields after publication
* mutating payload after retire unless explicitly allowed by this document

---

## 12. Integration with retire/reclaim

Every object type must obey the common retire/reclaim contract:

* retire invalidates capabilities by generation increment
* retire does not free payload
* reclaim frees payload only after:

  * generation increment is globally visible
  * a quiescent state has been observed
  * `refcount == 0`

No object may be reused or freed outside this protocol.

Object-type-specific teardown may occur during retire if required, but such teardown must not violate:

* capability revocation semantics
* quiescence requirements
* refcount-based retention guarantees

---

## 13. Forbidden patterns

The following are specification violations:

* storing raw `Object *` outside a bounded operation
* mutating payload identity after publication
* reusing object slots without retire/reclaim
* non-atomic access to `generation`, `refcount`, or `flags`
* per-capability revoke
* object table compaction
* retaining `Object *` across blocking or scheduling
* embedding cross-subsystem raw pointers in payloads where object identity should be represented by object id or a subsystem-owned stable internal allocation
* allowing dynamic resizing of fixed-capacity kernel object payloads in v1.0 unless explicitly authorized by subsystem specification

---

## 14. Implementation checklist

Before merging any change touching `/kernel/obj`:

* do all object allocations follow the required publication sequence?
* are all immutable fields finalized before publication?
* are all atomic fields accessed atomically with correct memory ordering?
* are all payload frees deferred to reclaim?
* does the object type respect its concurrency rules?
* does retire avoid freeing payload or bypassing refcount/quiescence rules?
* are object-type-specific teardown steps safe under concurrent revoke?
* are new operations correct under concurrent `cap_use`, retire, and reclaim?

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 15. Ground-truth rule

This document is the ground truth for object handling in the Zuki kernel.

If code and this document disagree, the code is wrong.
