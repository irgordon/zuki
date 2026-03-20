# Zuki Kernel Scheduler Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/sched` and any kernel code that performs thread state transitions, dispatch, preemption, blocking, wakeup, or interacts with IPC wait states.

This document defines:

- the canonical thread state machine
- run queue semantics
- dispatch and preemption rules
- blocking and wake rules
- IPC wait integration
- scheduler context invariants
- retire/reclaim interaction
- concurrency and memory ordering rules

If code and this document disagree, the code is wrong.

---

## 1. Scheduler model overview

Zuki’s scheduler is:

- preemptive
- priority-based
- deterministic under fixed inputs
- aware of IPC wait states
- integrated with capability and object invariants

In v1.0:

- each thread has a fixed priority
- each CPU has one run queue
- FIFO order is preserved within a priority level
- cross-CPU migration, if implemented, must be explicit and serialized

The scheduler manages:

- runnable threads
- the currently running thread on each CPU
- blocked threads
- preemption and dispatch
- wakeup paths from IPC, notifications, sleep primitives, and retire/abort events

The scheduler must never:

- retain raw `Object *` across blocking or scheduling boundaries
- violate capability or object invariants
- allow uninterruptible waits
- allow a retired thread to execute again

---

## 2. Thread object integration

Threads are represented by `OBJ_THREAD` objects as defined in `OBJECTS.md`.

### 2.1 Required payload fields

```c
typedef struct ThreadPayload {
    ObjectID             addrspace_id;
    sched_context_t     *sched_ctx;
    TrapFrame           *trap_frame;
    _Atomic uint32_t     state;
    uint32_t             priority;
    _Atomic uint64_t     txn_id;
} ThreadPayload;
````

### 2.2 Field semantics

* `addrspace_id` identifies the address space bound to the thread
* `sched_ctx` is scheduler-owned execution context
* `trap_frame` holds saved architectural register state
* `state` is the canonical scheduler-visible thread state
* `priority` is fixed for the lifetime of the thread in v1.0
* `txn_id` identifies the in-flight IPC transaction only while the thread is blocked in send

### 2.3 Immutable fields

The following are immutable after publication in v1.0:

* `trap_frame` identity
* `sched_ctx` identity, unless replaced by a scheduler-defined and serialized transition
* `priority`

### 2.4 Mutable fields

The following are mutable only under scheduler-defined synchronization:

* `state`
* `txn_id`
* scheduler-internal fields inside `sched_ctx`

### 2.5 Ownership rule

Persistent scheduler state must use:

* thread-local scheduler-owned structures
* `ObjectID`
* atomic scheduler-visible fields

No scheduler path may retain a raw `Object *` to a thread across blocking, descheduling, or cross-CPU handoff.

---

## 3. Canonical thread state machine

The scheduler recognizes the following canonical states:

| State                     | Meaning                                                   |
| ------------------------- | --------------------------------------------------------- |
| `THREAD_RUNNABLE`         | eligible to run and enqueued on exactly one run queue     |
| `THREAD_RUNNING`          | currently executing on exactly one CPU                    |
| `THREAD_BLOCKED_IPC_SEND` | blocked waiting for IPC reply or abort                    |
| `THREAD_BLOCKED_IPC_RECV` | blocked waiting for IPC delivery or abort                 |
| `THREAD_BLOCKED_WAIT`     | blocked on notification or other scheduler wait primitive |
| `THREAD_STOPPED`          | no longer runnable; may be awaiting final teardown        |
| `THREAD_DEAD`             | fully quiesced and no longer scheduler-visible            |

### 3.1 State invariants

* a `THREAD_RUNNABLE` thread must appear on exactly one run queue
* a `THREAD_RUNNING` thread must not appear on any run queue
* a `THREAD_BLOCKED_*` thread must not appear on any run queue
* a `THREAD_STOPPED` thread must not appear on any run queue and must not execute
* a `THREAD_DEAD` thread must not appear in any scheduler-owned active structure

### 3.2 Legal transitions

The only legal transitions in v1.0 are:

* `THREAD_RUNNABLE -> THREAD_RUNNING`
* `THREAD_RUNNING -> THREAD_RUNNABLE`
* `THREAD_RUNNING -> THREAD_BLOCKED_IPC_SEND`
* `THREAD_RUNNING -> THREAD_BLOCKED_IPC_RECV`
* `THREAD_RUNNING -> THREAD_BLOCKED_WAIT`
* `THREAD_BLOCKED_IPC_SEND -> THREAD_RUNNABLE`
* `THREAD_BLOCKED_IPC_RECV -> THREAD_RUNNABLE`
* `THREAD_BLOCKED_WAIT -> THREAD_RUNNABLE`
* `THREAD_RUNNING -> THREAD_STOPPED`
* `THREAD_BLOCKED_* -> THREAD_STOPPED`
* `THREAD_STOPPED -> THREAD_DEAD`

No other transition is permitted.

### 3.3 Illegal transition rule

Illegal state transitions are kernel bugs and must kernel-panic.

This includes:

* waking a non-blocked thread
* enqueueing a non-runnable thread
* dispatching a blocked or stopped thread
* returning a retired thread to runnable or running state

---

## 4. Run queue model

### 4.1 Structure

Zuki v1.0 uses:

* one run queue per CPU
* fixed-priority ordering
* FIFO within each priority level

### 4.2 Run queue invariants

* a thread may appear at most once in the entire scheduler
* a thread may not appear in more than one CPU run queue
* only `THREAD_RUNNABLE` threads may be on a run queue
* `THREAD_RUNNING` and `THREAD_BLOCKED_*` threads must not be enqueued
* run queue operations must be serialized per CPU

### 4.3 Enqueue rule

A thread may be enqueued only if all of the following are true:

* `state == THREAD_RUNNABLE`
* the thread is not already enqueued
* the thread is not retired or stopped
* the target CPU run queue has accepted ownership of the enqueue

### 4.4 Dequeue rule

A thread may be dequeued only when:

* it is selected for dispatch
* it is being migrated under a serialized migration path
* a transition out of runnable is being committed

### 4.5 Queue membership consistency

State and queue membership must remain consistent.

The implementation must not expose an intermediate state in which:

* a blocked thread is still discoverable as runnable
* a running thread remains queued
* a runnable thread is absent from all scheduler-visible ownership structures without an active dispatch transition

---

## 5. Dispatch and preemption

### 5.1 Dispatch

Dispatch selects the highest-priority runnable thread on the CPU’s run queue.

Dispatch steps:

1. choose the next runnable thread from the run queue
2. remove it from the run queue
3. switch its state from `THREAD_RUNNABLE` to `THREAD_RUNNING`
4. save current architectural state if switching from another thread
5. switch address space using `addrspace_id`
6. load the selected thread’s trap frame
7. transfer execution to the selected thread

A dispatched thread must not remain enqueued.

### 5.2 Idle behavior

If no runnable thread exists, the CPU may:

* run an idle thread, or
* enter an architecture-defined idle state

The idle thread is scheduler-owned and is not modeled as a normal user thread object.

### 5.3 Preemption

Preemption occurs when:

* a timer interrupt fires, or
* a higher-priority thread becomes runnable and the current scheduling policy requires preemption

Preemption steps:

1. save the current thread’s trap frame
2. if the current thread remains eligible to run:

   * set state to `THREAD_RUNNABLE`
   * enqueue it
3. dispatch the next selected runnable thread

A thread must not be returned to runnable if it has been retired or stopped while preemption handling is in progress.

---

## 6. Blocking and wake rules

### 6.1 Blocking sources

A thread may block only in:

* `ipc_send`
* `ipc_recv`
* notification wait
* scheduler sleep/wait primitives explicitly defined by subsystem policy

### 6.2 Blocking transition

Blocking steps are:

1. validate that the thread is currently `THREAD_RUNNING`
2. record required wait metadata
3. transition state to the correct blocked state
4. yield the CPU and dispatch another thread

A running thread is not in a run queue, so no dequeue step is required for normal blocking from `THREAD_RUNNING`.

### 6.3 Wake transition

A blocked thread may be woken only by:

* IPC reply
* IPC abort
* message delivery
* notification signal
* endpoint retire
* scheduler wake/sleep expiration primitives

Wake steps are:

1. validate that the thread is in the expected blocked state
2. clear or finalize wait metadata
3. set state to `THREAD_RUNNABLE`
4. enqueue the thread on a run queue

### 6.4 Wake atomicity

Wake must be atomic with respect to:

* retire
* abort
* competing wake paths
* run queue insertion

A single blocked wait must resolve exactly once.

Double wake is a kernel bug.

---

## 7. IPC wait integration

IPC wait state is scheduler-visible and must be consistent with `IPC.md`.

### 7.1 Send wait

A thread enters `THREAD_BLOCKED_IPC_SEND` only after:

* the endpoint operation has successfully delivered or enqueued the message
* the sender transaction has been recorded
* the thread is committed to waiting for reply or abort

While in `THREAD_BLOCKED_IPC_SEND`:

* `txn_id` must identify the in-flight transaction
* the thread must not be runnable
* the thread must not execute

Wake conditions are:

* `ipc_reply()`
* endpoint retire causing abort
* watchdog or policy abort

### 7.2 Receive wait

A thread enters `THREAD_BLOCKED_IPC_RECV` only if:

* the endpoint queue is empty
* no other receiver is blocked on the endpoint
* the endpoint waiter state has been set to this thread

Wake conditions are:

* direct message delivery
* endpoint retire causing abort
* watchdog or policy abort

### 7.3 Abort semantics

Abort must:

* wake the blocked thread
* set its state to `THREAD_RUNNABLE` unless the thread has been retired and moved to `THREAD_STOPPED`
* clear or invalidate stale IPC wait metadata
* make the aborted status observable to the resumed execution path

Abort must not:

* leave the thread blocked
* leave stale `txn_id` state active
* cause multiple completions of the same wait
* violate capability or IPC ownership invariants

### 7.4 Completion uniqueness

Every IPC wait resolves exactly once by one of:

* reply
* message delivery
* abort

Competing resolution paths must be serialized.

---

## 8. Retire and reclaim interaction

### 8.1 Thread retire

When a thread object is retired:

* the scheduler must ensure the thread cannot execute again
* if the thread is queued, it must be removed from the run queue
* if the thread is blocked, its wait must be aborted or force-resolved into stop
* if the thread is currently running, retirement must force it toward a non-runnable terminal path at the next safe scheduler control point
* the thread state must become `THREAD_STOPPED`

A retired thread must never transition back to runnable or running.

### 8.2 Running-thread retire rule

If the target thread is currently executing on some CPU, the scheduler must perform a coordinated stop mechanism, such as:

* local stop on next trap/preemption boundary, or
* cross-CPU stop request handled at a safe dispatch boundary

Immediate unsynchronized destruction of a running thread is forbidden.

### 8.3 Thread reclaim

Thread reclaim may occur only when:

* retire has completed
* quiescence has been observed
* `refcount == 0`
* no scheduler-owned references remain
* the thread is no longer current on any CPU
* the thread is not present in any run queue or wait structure

Reclaim frees:

* trap frame
* scheduler context
* thread payload

### 8.4 Endpoint retire impact

If an endpoint is retired:

* all threads blocked on that endpoint must be aborted
* such threads must leave `THREAD_BLOCKED_IPC_*`
* scheduler wake paths must not race with reclaim of the endpoint or thread state

---

## 9. Concurrency and memory ordering rules

### 9.1 Atomic fields

The following must be atomic:

* `ThreadPayload.state`
* `ThreadPayload.txn_id`
* any scheduler-visible wait metadata shared across subsystems

### 9.2 Locking and serialization rules

* run queue operations must be serialized per CPU
* cross-CPU thread migration or stop must be explicitly serialized
* blocking and wake transitions must be serialized against competing wake, abort, and retire paths
* scheduler code must not retain raw `Object *` across blocking or scheduling boundaries

### 9.3 State publication rules

A state transition must become visible before any dependent queue or wake action that assumes that state.

Examples:

* a thread must be in `THREAD_RUNNABLE` before being exposed as enqueued
* a thread must leave runnable ownership before being exposed as blocked
* a wake path must not enqueue a thread before committing its runnable state

### 9.4 Forbidden shortcuts

The following are forbidden:

* non-atomic state transitions
* modifying thread state without updating ownership structures consistently
* retaining trap-frame or object pointers without scheduler ownership rules
* allowing a retired thread to execute
* assuming a blocked thread will only ever be woken by one source without serialization

---

## 10. Forbidden patterns

The following are specification violations:

* running a thread whose `OBJ_THREAD` has been retired
* leaving a thread blocked after abort
* allowing multiple receivers to block on the same endpoint
* retaining `Object *` across scheduling boundaries
* mutating thread payload outside scheduler, trap, or explicitly authorized debug paths
* allowing a thread to appear twice in any run-queue structure
* allowing a blocked thread to remain runnable
* transitioning a stopped thread back to runnable or running

Any such change is a violation, not an optimization.

---

## 11. Implementation checklist

Before merging any change touching `/kernel/sched`:

* are all state transitions legal and atomic?
* are run queue operations serialized correctly?
* are queue membership and thread state always consistent?
* are IPC wait states integrated correctly?
* are abort and wake paths serialized and single-resolution?
* are retired threads prevented from running again?
* are reclaim preconditions fully enforced?
* are tests present for:

  * preemption
  * priority dispatch
  * FIFO within priority
  * IPC send/recv wake paths
  * abort under load
  * retire while queued
  * retire while blocked
  * retire while running
  * run queue uniqueness invariants

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 12. Ground-truth rule

This document is the ground truth for scheduling in the Zuki kernel.

If code and this document disagree, the code is wrong.
