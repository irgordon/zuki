# Zuki Timer Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/timers`, `/kernel/sched`, and any subsystem that schedules sleeps, timeouts, delayed operations, watchdog deadlines, or timer-driven aborts.

This document defines:

- the timer model
- timeout semantics
- sleep and delay operations
- integration with scheduler and IPC
- subsystem timeout rules
- cancellation and abort semantics
- restart and failure semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Timer model overview

Zuki’s timer subsystem is:

- deterministic
- monotonic
- scheduler-integrated
- abort-safe
- bounded
- restart-safe

Timers are kernel-resident scheduling primitives, not user-visible objects.

Timers drive:

- `sys_sleep`
- IPC timeouts
- driver I/O deadlines
- policy evaluation deadlines
- interrupt backoff
- watchdog deadlines
- service restart deadlines

Timers do not confer authority.

A timer may only influence the operation, thread, or subsystem that explicitly created it. A timer must never create ambient authority or act as an out-of-band capability.

The timer subsystem must never:

- leak authority
- create ambient channels
- violate scheduler invariants
- resolve one wait more than once
- produce nondeterministic timeout outcomes

---

## 2. Timer data model

## 2.1 Timer structure requirements

Zuki v1.0 uses a hierarchical timer wheel or an equivalent structure with the same observable properties.

Required properties:

- insertion O(1)
- cancellation O(1)
- expiration O(1) amortized
- bounded drift
- monotonic expiration behavior

### 2.2 Timer entry model

Each timer entry contains at minimum:

- monotonic expiration timestamp
- timer class
- target thread id or subsystem-owned target identifier
- cancellation token
- generation or epoch field sufficient to reject stale firings
- flags indicating one-shot behavior

Periodic timers are not part of the required v1.0 contract unless explicitly introduced by a narrower subsystem specification.

### 2.3 Invariants

- timers must not fire before their expiration time
- timers may fire late only within bounded drift
- timers must be cancelable until resolved
- each timer must resolve at most once
- stale or reused timer entries must be detectable and rejectable

---

## 3. Time source model

## 3.1 Monotonic clock

All timer semantics are defined against the monotonic clock.

The monotonic clock must:

- never go backward
- be independent of wall-clock adjustment
- be normalized into a kernel-defined time unit

### 3.2 Wall-clock exclusion

Wall-clock time is not part of timer correctness.

No timer may depend on wall-clock time for:

- expiration
- cancellation
- ordering
- timeout outcome

If a higher-level service exposes wall-clock-oriented APIs, it must convert them into monotonic deadlines before entering the timer subsystem.

---

## 4. Timer ownership and lifetime

## 4.1 Ownership rule

Every timer is owned by exactly one operation, thread wait, or subsystem transaction.

A timer must not outlive the entity that owns it.

### 4.2 Lifetime rule

A timer remains valid only while:

- its owning operation is unresolved
- its owning thread or subsystem remains live
- its cancellation token remains current

Once the owning operation resolves, the timer must be canceled or consumed and must not fire later.

### 4.3 Stale firing rule

A timer firing after cancellation, completion, retire, restart, or generation mismatch must be ignored as stale and must not mutate system state.

---

## 5. Sleep and delay semantics

## 5.1 `sys_sleep(duration)`

`sys_sleep`:

- blocks the current thread
- installs a one-shot timer
- must be abortable
- wakes only on:
  - timer expiration
  - abort
  - thread retire
  - shutdown or wider scheduler stop condition

### 5.2 Invariants

- sleep duration must be validated
- zero-duration sleep is permitted only if explicitly defined and must not block
- sleep must not undersleep
- sleep may oversleep only within bounded scheduler and timer drift
- sleep must not survive thread retire

### 5.3 Forbidden sleep patterns

The following are forbidden:

- busy-wait loops as syscall sleep implementation
- unbounded sleep without explicit contract
- sleep that remains pending after thread retire
- sleep completion that races into double wake

---

## 6. IPC timeouts

## 6.1 Timeout forms

IPC operations may specify:

- no timeout
- bounded timeout
- immediate timeout for non-blocking behavior

### 6.2 Timeout behavior

On timeout:

- the blocked thread must wake
- the IPC operation must resolve deterministically
- no stale reply may later complete that timed-out operation
- no partial completion state may remain live

### 6.3 Cancellation rule

IPC timeout timers must be canceled when:

- IPC completes successfully
- IPC aborts
- the thread is retired
- the endpoint is retired
- the wait is otherwise force-resolved

### 6.4 Single-resolution rule

IPC completion, abort, and timeout are competing resolution paths.

Exactly one may win.

---

## 7. Driver and device timeouts

## 7.1 Driver timeout model

Drivers may request bounded timers for:

- queue submission deadlines
- completion deadlines
- DMA completion windows
- interrupt backoff
- reset windows

### 7.2 Invariants

- all driver timeouts must be bounded
- all driver timeouts must be abortable
- driver timers must not survive driver restart
- driver timers must not leak across device boundaries
- driver timers must not outlive the queue, device, or transaction they govern

### 7.3 Device failure integration

On device failure or device retire:

- all dependent driver timers must be canceled or resolved as abort
- all dependent operations must resolve exactly once
- no stale timer may fire after device teardown

---

## 8. Policy timeouts

## 8.1 Policy deadline model

Policy evaluation deadlines may limit:

- monotonic elapsed execution time
- instruction count
- action count

### 8.2 Timer integration

When a policy deadline is enforced by the timer subsystem:

- evaluation must abort deterministically
- no authoritative action may be applied
- no partial policy result may survive

### 8.3 Wall-clock prohibition

Policy deadlines must not use wall-clock time.

Any externally expressed wall-clock budget must be translated into a monotonic deadline before evaluation begins.

---

## 9. Cancellation and abort semantics

## 9.1 Cancellation triggers

A timer may be canceled:

- explicitly by its owner
- implicitly when the operation completes
- by thread retire
- by endpoint retire
- by subsystem shutdown
- by driver restart
- by device removal
- by service restart

### 9.2 Cancellation properties

Cancellation must be:

- O(1)
- deterministic
- race-safe
- idempotent

Canceling an already resolved or already canceled timer must not corrupt state.

### 9.3 Abort semantics

When a timer causes timeout or abort:

- the owning thread or subsystem wait must resolve exactly once
- any blocked thread must be woken unless already terminally stopped
- no stale completion may later succeed
- no partial state may remain live

### 9.4 Callback rule

Timer expiry must not directly perform arbitrary subsystem mutation.

A timer expiry may only:

- mark an operation timed out
- schedule a bounded wake or abort action
- enqueue a scheduler-visible timeout resolution
- trigger a subsystem-defined bounded teardown path

Direct authority-bearing mutation from timer interrupt context is forbidden.

---

## 10. Scheduler integration

## 10.1 Blocked-state integration

Timer-driven waits must integrate with the canonical scheduler states defined in `SCHED.md`.

The timer subsystem must not invent new persistent thread states outside the scheduler contract.

### 10.2 Wake semantics

Timer expiration may wake a blocked thread only through scheduler-approved wake paths.

Wake must:

- validate the target wait is still current
- preserve single-resolution semantics
- transition the thread according to `SCHED.md`

### 10.3 Ordering guarantees

The timer subsystem guarantees:

- expiration ordering by monotonic deadline
- deterministic tie-breaking for equal deadlines within the implementation-defined ordering rule

It does not guarantee unrelated global fairness beyond the scheduler contract.

### 10.4 Preemption

Timer interrupts may trigger scheduler activity.

Such activity must:

- respect legal thread-state transitions
- not reorder already established timeout winners
- not allow one expired timer to resolve twice

---

## 11. Restart and failure semantics

## 11.1 Kernel restart

On kernel panic or reboot:

- all timers are destroyed
- no timer state persists unless explicitly defined by a later persistence contract

### 11.2 Service restart

If a service restarts, including RPS, VFS, or a driver service:

- all timers owned by that service or its in-flight operations must be canceled or resolved as abort
- no stale timer may fire after restart
- no stale timeout may act on a new generation of that service

### 11.3 Hotplug and device removal

Device removal must:

- cancel all device-owned timers
- abort all dependent operations
- prevent stale timer reuse against a replacement device instance

### 11.4 Timer subsystem failure

If the timer subsystem detects internal corruption or impossible state:

- the kernel must fail closed into panic or a defined fatal path
- it must not continue with silently corrupted timeout ordering

---

## 12. Bounded drift and overflow rules

## 12.1 Drift bound

Implementation must define and document the maximum timer drift relative to the kernel monotonic time base and scheduling granularity.

Timer expiry later than this bound is a correctness failure.

### 12.2 Counter overflow

Timer arithmetic must be overflow-safe.

The implementation must reject or safely clamp timer requests that would overflow internal deadline computation.

Silent wraparound is forbidden.

### 12.3 Wheel overflow behavior

Timer-wheel or equivalent structure overflow must be explicitly handled.

Overflow must not:

- corrupt unrelated timers
- fire timers early
- lose cancellation state silently

---

## 13. Forbidden patterns

The following are specification violations:

- timers tied to wall-clock time
- non-abortable waits
- unbounded sleeps
- timer expiry paths that directly bypass scheduler or subsystem validation
- timer paths that bypass capability checks where capability-bearing consequences exist
- timers surviving thread retire
- timers surviving driver or service restart
- stale timer firings affecting new operations
- timer drift beyond defined bounds
- timer operations that violate the required complexity guarantees

Any such change is a violation, not an optimization.

---

## 14. Implementation checklist

Before merging any timer-related change:

- are all timers based on the monotonic clock?
- are all waits abortable?
- are timeout winners single-resolution?
- are IPC timeouts deterministic and stale-reply-safe?
- are driver and device timers revocable?
- are policy deadlines monotonic and bounded?
- are timer cancellations race-safe and idempotent?
- are scheduler wake paths consistent with `SCHED.md`?
- is overflow handled safely?
- are tests present for:
  - sleep correctness
  - undersleep/oversleep bounds
  - IPC timeout correctness
  - stale reply rejection after timeout
  - driver timeout correctness
  - device removal
  - service restart invalidation
  - timer-wheel overflow
  - cancellation races
  - equal-deadline tie-breaking

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 15. Ground-truth rule

This document is the ground truth for timer and timeout semantics in Zuki.

If code and this document disagree, the code is wrong.
