# Zuki Reflector Personality Server (RPS) — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/services/personality` and any kernel or userspace code that participates in syscall reflection, trap handling, ABI translation, or RPS restart and failure isolation.

This document defines:

- the syscall reflection model
- trap descriptor format and invariants
- RPS request and response protocol
- capability and memory safety boundaries
- failure and restart semantics
- concurrency and ordering rules
- integration with IPC, scheduler, and memory subsystems
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. RPS model overview

Zuki does not implement Linux syscalls in the kernel.

Instead:

1. a Linux task executes a syscall instruction
2. hardware traps into the kernel
3. the kernel constructs a `TrapDescriptor`
4. the kernel sends the descriptor to the Reflector Personality Server (`RPS`) via IPC
5. RPS interprets the syscall, performs ABI translation and policy-constrained service logic
6. RPS returns a reply
7. the kernel validates the reply, restores user-visible state, and resumes the task

RPS is:

- isolated from the kernel
- restartable
- bounded
- protocol-constrained
- not trusted to preserve kernel correctness

RPS may be trusted for service function by deployment policy, but the kernel must remain correct even if RPS is buggy, malicious, unavailable, or crashes.

The kernel must never depend on RPS behaving correctly in order to preserve:

- kernel memory safety
- object lifetime correctness
- capability invariants
- scheduler forward progress

---

## 2. Reflection model boundary

### 2.1 Kernel role

The kernel is responsible for:

- trap capture
- transaction construction
- thread blocking and wakeup
- reply validation
- restoration of user-visible execution state
- enforcing all capability and memory-safety boundaries

### 2.2 RPS role

RPS is responsible for:

- interpreting reflected syscall intent
- implementing Linux ABI behavior in userspace
- requesting permitted operations through explicit kernel-mediated interfaces
- returning a result for the reflected transaction

### 2.3 Foreign ABI boundary

The kernel does not implement Linux syscall semantics.

However, the kernel may extract transport-relevant trap fields needed to identify and deliver a reflected request, including the syscall number as a captured user register value.

This extraction is transport metadata, not ABI implementation.

---

## 3. TrapDescriptor format

The `TrapDescriptor` contains the complete user-visible architectural state required to reflect a trapped syscall.

### 3.1 Canonical structure

```c
typedef struct TrapDescriptor {
    uint64_t regs[ARCH_REG_COUNT];
    uint64_t pc;
    uint64_t sp;
    uint64_t flags;
    uint64_t syscall_num;
    uint64_t asid;
    ObjectID thread_id;
    ObjectID addrspace_id;
    uint64_t trap_id;
} TrapDescriptor;
````

### 3.2 Invariants

* all architecturally visible user-mode state required for syscall reflection must be captured
* no kernel-only state may be exposed
* `trap_id` must uniquely identify one reflected trap transaction
* `thread_id` and `addrspace_id` must refer to objects that were live at trap capture time
* the descriptor becomes immutable once published into the IPC transaction
* the kernel must not expose raw pointers in the descriptor

### 3.3 Completeness rule

The descriptor must be sufficient for correct emulation of the reflected syscall path, including:

* general-purpose registers
* instruction pointer
* stack pointer
* flags or status register
* architecture-specific syscall selector state where applicable

If the architecture requires extended state for correct reflection, that state must be included or otherwise safely represented.

---

## 4. RPS request and reply protocol

## 4.1 Request model

Each reflected syscall becomes exactly one RPS transaction.

A transaction is identified by:

* `trap_id`
* originating `thread_id`
* originating reflection endpoint

The kernel must ensure that a thread has at most one in-flight reflected syscall transaction at a time.

### 4.2 Kernel-to-RPS request

The kernel sends an IPC request containing:

* the immutable `TrapDescriptor`
* any explicitly authorized auxiliary transport objects, such as bounded memory-window descriptors
* optional capability transfer only if explicitly required by the reflection protocol

The kernel then blocks the thread in the scheduler-visible IPC send wait state.

### 4.3 RPS reply structure

```c
typedef struct TrapFrameDelta {
    uint64_t valid_mask;
    uint64_t regs[ARCH_REG_COUNT];
    uint64_t pc;
    uint64_t sp;
    uint64_t flags;
} TrapFrameDelta;

typedef struct RPSReply {
    uint64_t       trap_id;
    uint64_t       result;
    uint64_t       errno_value;
    uint64_t       flags;
    TrapFrameDelta delta;
} RPSReply;
```

### 4.4 Reply invariants

* `trap_id` must match exactly one still-pending transaction
* reply contents must be immutable once sent
* reply must not be applied unless the originating thread is still waiting on that transaction
* malformed or mismatched replies must be rejected

### 4.5 Outcome model

A reflected syscall resolves in exactly one of:

* valid reply
* failure
* abort

Double completion is forbidden.

---

## 5. Kernel resume semantics

On valid reply:

1. validate transaction identity
2. validate reply structure and flags
3. validate `TrapFrameDelta`
4. apply permitted register updates
5. set return value and errno according to the reply contract
6. clear transaction state
7. resume the blocked thread

### 5.1 Delta validation

The kernel must validate all requested register modifications before application.

Validation must reject any attempt to:

* modify kernel-only state
* inject invalid architecture state
* violate privilege-level invariants
* produce an invalid return context

The kernel may accept only a defined subset of user-visible architectural state as modifiable through `TrapFrameDelta`.

### 5.2 Default return convention

Unless a reflected ABI path explicitly requires a different contract, the kernel resumes the thread with:

* syscall return value from `result`
* ABI-visible error state derived from `errno_value` and reply flags
* validated user-state modifications from `delta`

---

## 6. Capability and memory safety boundaries

## 6.1 RPS is not trusted for kernel safety

RPS must not:

* access kernel memory
* mutate kernel objects directly
* fabricate capabilities
* bypass capability checks
* access page tables directly
* access raw thread or address-space internals

### 6.2 Kernel enforcement obligations

The kernel must enforce:

* capability validation on every RPS-requested operation
* bounds checks on all reflected memory access
* no direct pointer exposure
* no raw page-table access
* no direct object mutation without validated authority

### 6.3 Memory windows

If RPS needs access to user memory, the kernel may provide one of:

* copy-in or copy-out buffers
* bounded temporary memory-window descriptors
* temporary lease-backed access mechanisms defined by the memory subsystem

RPS must never receive raw kernel pointers or unrestricted user pointers.

### 6.4 Memory-window invariants

Any memory window exposed to RPS must be:

* explicitly bounded
* explicitly permission-scoped
* tied to one live transaction
* revoked or destroyed at transaction completion
* unusable after reply, failure, or abort

RPS must not retain access to a memory window beyond the transaction that created it.

---

## 7. Failure and restart semantics

## 7.1 Failure modes

RPS may:

* crash
* deadlock
* become unavailable
* violate protocol
* exceed time budget
* return malformed replies

### 7.2 Kernel behavior on RPS failure

If RPS fails during syscall handling:

* the blocked thread receives deterministic failure
* default reflected failure is `-EIO` unless a narrower contract defines otherwise
* no automatic retry is performed by the kernel
* in-flight transfer state is rolled back or destroyed according to ownership rules
* the syscall is not reissued implicitly

### 7.3 Restart behavior

During RPS restart or unavailability:

* new reflection attempts must fail immediately
* no new thread may block waiting for RPS
* no stale pending `TrapDescriptor` may be delivered to a newly started RPS instance
* normal reflection resumes only after RPS is fully reinitialized and the endpoint is declared available

### 7.4 Isolation guarantee

RPS failure must not:

* corrupt kernel state
* leak capabilities
* leave threads permanently blocked
* violate scheduler invariants
* violate memory safety
* cause stale transaction reuse

---

## 8. Concurrency and ordering rules

## 8.1 Per-thread ordering

A thread may have at most one in-flight reflected syscall.

Reflected syscalls from one thread are therefore observed in program order.

### 8.2 Cross-thread ordering

No ordering is guaranteed between reflected syscalls from different threads beyond the underlying IPC and scheduler behavior.

### 8.3 RPS concurrency

RPS may process multiple requests concurrently only if:

* each request remains independently identified by `trap_id`
* reply matching is exact
* shared mutable state does not violate deterministic behavior under fixed inputs

### 8.4 Kernel ordering guarantees

The kernel must:

* publish each thread’s reflected traps in program order
* apply only replies that match the current pending transaction for that thread
* reject stale, duplicate, or mismatched replies

The kernel is not required to preserve a global reply order across unrelated threads.

---

## 9. Integration with IPC

## 9.1 RPS endpoint

RPS communicates through a defined IPC endpoint.

The endpoint must be bounded and subject to the rules in `IPC.md`.

Required service-side authority is deployment-defined, but the endpoint contract must at minimum support:

* receiving reflected trap requests
* sending replies
* optional transfer of explicitly authorized transport objects

### 9.2 IPC constraints

* RPS queues must be bounded
* the kernel must not allow unbounded accumulation of reflected requests
* blocked reflection waits must remain abortable
* endpoint retire or service unavailability must abort affected waits

### 9.3 Reply admissibility

A reply is admissible only if all of the following match:

* `trap_id`
* originating pending thread transaction
* expected reflection endpoint or service identity as defined by the transaction

Mismatched replies must be rejected and must not mutate blocked thread state.

---

## 10. Integration with scheduler

## 10.1 Blocking

A thread waiting on RPS reply is placed in:

* `THREAD_BLOCKED_IPC_SEND`

### 10.2 Wake conditions

The thread may wake only on:

* valid RPS reply
* deterministic failure
* endpoint retire
* watchdog or policy abort
* service unavailability that resolves the wait

### 10.3 Abort behavior

Abort must:

* wake the thread
* clear reflection transaction state
* return deterministic failure to the resumed execution path
* prevent stale descriptor or reply reuse

Abort must not:

* leave the thread blocked
* leave stale transaction metadata active
* allow a later reply to complete the aborted transaction

---

## 11. Integration with memory subsystem

## 11.1 Address-space safety

RPS must not:

* mutate page tables directly
* request mapping or unmapping without explicit validated authority
* access kernel memory
* hold translation-related access beyond transaction lifetime

### 11.2 User-memory access

RPS may request mediated user-memory operations such as:

* copy-in
* copy-out
* bounded temporary window access

The kernel must enforce:

* bounds
* rights
* lifetime
* architecture-safe access semantics

### 11.3 Non-aliasing and lifetime

Any temporary memory access granted to RPS must not outlive the transaction and must not create an unchecked alias into kernel memory or unrestricted user memory.

---

## 12. Forbidden patterns

The following are specification violations:

* RPS receiving raw kernel pointers
* RPS directly modifying kernel objects
* kernel automatically retrying reflected syscalls
* kernel blocking new reflections during restart instead of failing them immediately
* RPS returning replies without matching `trap_id`
* kernel exposing partial or incomplete trap descriptors
* RPS retaining memory windows beyond transaction lifetime
* unbounded RPS queues
* allowing RPS failure to leave threads stuck
* applying unchecked register deltas
* accepting stale or duplicate replies

Any such change is a violation, not an optimization.

---

## 13. Implementation checklist

Before merging any change touching RPS or syscall reflection:

* are `TrapDescriptor` instances complete, immutable, and pointer-free?
* are replies fully validated before application?
* is reply matching exact and single-resolution?
* are capability boundaries enforced on all RPS-mediated operations?
* are memory windows bounded, permission-scoped, and transaction-lifetime-limited?
* are RPS failures isolated and deterministic?
* do abort paths always wake blocked threads and clear transaction state?
* do restart semantics reject new waits until service recovery is complete?
* are tests present for:

  * RPS crash during reflected syscall
  * malformed replies
  * duplicate or stale replies
  * high-load reflection
  * concurrent reflections
  * restart during load
  * transfer ownership rollback
  * memory-window lifetime enforcement
  * invalid register delta rejection

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 14. Ground-truth rule

This document is the ground truth for syscall reflection in the Zuki kernel.

If code and this document disagree, the code is wrong.
