# Zuki Abstract Application Binary Interface — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/sys`, `/kernel/entry`, `/kernel/mm`, `/kernel/ipc`, `/kernel/sched`, `/kernel/timers`, and any userspace component that invokes syscalls or crosses the user/kernel boundary.

This document defines:

- the abstract ABI model
- syscall entry and return semantics
- argument passing rules
- capability wire format
- user-memory access rules
- error and return-value semantics
- restart and stale-state semantics
- cross-subsystem invariants
- forbidden patterns
- implementation checklist

Architecture-specific ABI mappings such as `ABI-x86_64.md`, `ABI-AArch64.md`, and `ABI-RV64.md` must implement this abstract ABI exactly.

If code and this document disagree, the code is wrong.

---

## 1. ABI model overview

Zuki’s abstract ABI is:

- architecture-neutral
- capability-rooted
- deterministic
- restart-safe
- non-ambient
- single-resolution
- minimal and explicit

The abstract ABI defines:

- how syscalls enter the kernel logically
- how argument slots are interpreted
- how capabilities are represented on the wire
- how user memory is accessed
- how results and errors are returned
- how blocking and abort semantics propagate
- how stale state is rejected

The abstract ABI does not define:

- high-level service semantics
- filesystem or network protocols
- identity-based privilege
- ambient namespaces
- concrete per-architecture register assignments
- concrete per-architecture stack layouts beyond the abstract invariants

Those are defined elsewhere.

---

## 2. Syscall entry model

### 2.1 Entry mechanism

Syscalls enter the kernel through an architecture-defined trap or syscall instruction.

The abstract ABI defines:

- the meaning of the syscall number
- the meaning of logical argument slots
- the meaning of logical return slots

Architecture-specific ABI documents define:

- the concrete entry instruction
- which registers or stack positions carry those logical slots
- stack alignment requirements
- clobber and preservation rules

### 2.2 Syscall number

Every syscall has a unique, stable, versioned number defined in `SYSCALL.md`.

Unknown syscall numbers must fail deterministically with the canonical invalid-syscall error.

### 2.3 No ambient entrypoints

The kernel must not expose:

- hidden syscalls
- undocumented multiplexed entrypoints
- architecture-specific backdoor syscalls
- identity-based privileged syscalls

All kernel entrypoints must be listed in the canonical syscall table.

---

## 3. Argument passing model

### 3.1 Logical argument slots

The abstract ABI defines six logical argument slots:

- `arg0`
- `arg1`
- `arg2`
- `arg3`
- `arg4`
- `arg5`

Architecture-specific ABI documents map these logical slots to concrete registers or stack positions.

The common kernel syscall layer must reason in terms of logical slots, not hard-coded architecture register names.

### 3.2 Capability arguments

Capability arguments must be passed as an explicit wire tuple:

```c
typedef struct CapWire {
    uint64_t object_id;
    uint64_t gen_at_mint;
    uint64_t rights;
} CapWire;
````

Field widths may be narrowed by the architecture-specific ABI only if the narrowing is lossless with respect to the canonical kernel representation.

The kernel reconstructs a logical capability and validates it via `cap_use()`.

Raw pointers or integers must never be interpreted as kernel object references.

### 3.3 User-memory arguments

User pointers passed as arguments:

* are treated as user virtual addresses only
* must be bounds-checked before access
* must be copied in or out explicitly
* must not be trusted based on address value alone

No syscall may dereference user memory without explicit validation.

### 3.4 No implicit context

Syscalls must not infer:

* identity
* namespace membership
* process privilege
* default capabilities
* ambient service ownership

All authority must be passed explicitly.

---

## 4. Return-value and error model

### 4.1 Logical return slots

The abstract ABI defines:

* `ret0` — primary return value
* `ret1` — optional secondary return value when a syscall contract explicitly defines one

Architecture-specific ABIs map these to concrete return registers or equivalent locations.

No syscall may rely on an implicit ambient error channel.

### 4.2 Deterministic error codes

Errors must be:

* explicit
* deterministic
* local to the syscall result
* not stored in global or ambient state

There is no thread-local errno-style side channel in the abstract ABI.

### 4.3 No partial success

Syscalls must be atomic with respect to the authority-bearing state they modify, including:

* capability state
* object state
* memory mappings
* queue entries
* timer-governed waits
* IPC transactions

If a syscall fails, aborts, or times out, it must not leave partial authoritative state live.

### 4.4 Single-resolution

A syscall may resolve as exactly one of:

* success
* failure
* timeout
* abort

Exactly one may win.

---

## 5. Blocking and abort semantics

### 5.1 Blocking sources

Syscalls may block only through:

* IPC waits
* timer-governed waits
* scheduler-governed waits explicitly permitted by subsystem contract

### 5.2 Abortability

All blocking must be abortable via:

* timeout
* thread retire or termination
* process termination
* service restart
* device removal
* endpoint retire
* subsystem-specific explicit abort paths defined by contract

### 5.3 No stale state after abort

Abort must not leave behind:

* stale queue entries
* stale timers
* stale IPC waits
* stale replies
* stale transaction identifiers
* stale partially applied authoritative state

---

## 6. Restart and stale-state semantics

### 6.1 Restart safety

Restart must not:

* widen authority
* resurrect stale state
* complete a syscall twice
* allow stale replies or completions to bind to new operations

### 6.2 Stale-state rejection

Syscalls must reject:

* stale capabilities
* stale queue entries
* stale timer expirations
* stale IPC replies
* stale transaction IDs

Freshness must be enforced through generation or an equivalent bounded freshness mechanism.

---

## 7. Stack and register invariants

### 7.1 Stack invariants

The abstract ABI requires:

* the user stack pointer must refer to valid user memory if it is used by the calling convention
* stack alignment must satisfy the architecture-specific ABI contract
* the kernel must not trust user stack contents without validation

### 7.2 Register and state invariants

The abstract ABI defines that architecture-specific ABI documents must specify:

* which concrete registers carry syscall number, arguments, and returns
* which concrete registers or architectural state are preserved across syscall return
* which concrete registers or architectural state may be clobbered

The abstract ABI itself defines only the logical contract, not the physical register mapping.

### 7.3 No authority from register state

The kernel must not:

* infer authority from arbitrary register contents
* treat register values as ambient privilege context
* rely on unvalidated user register state for security decisions

---

## 8. Cross-subsystem integration

Syscalls and the ABI must obey:

* `OBJECTS.md` for object invariants
* `CAPABILITIES.md` for capability semantics
* `IPC.md` for message boundaries
* `MM.md` for memory safety
* `SCHED.md` for blocking and wake rules
* `TIMERS.md` for timeout semantics
* `DEVICE.md` for DMA, queue, and IRQ safety
* `NET.md` for NIC access boundaries
* `VFS.md` only through service IPC, never direct kernel semantics
* `POLICY.md` for narrowing authority
* `SECURITY.md` for global invariants
* `INIT.md` for bootstrap constraints
* `SYSCALL.md` for syscall semantics

The ABI is the abstract glue layer that binds these together.

---

## 9. Forbidden patterns

The following are specification violations:

* ambient authority
* identity-based privilege
* implicit capability inheritance
* syscall arguments interpreted as kernel objects without capability reconstruction
* user pointers dereferenced without validation
* partial authoritative state remaining live after failure or abort
* stale state affecting new operations
* architecture-specific behavior leaking into the abstract ABI contract
* restart behavior that widens authority
* ABI drift across architectures

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any ABI-related change:

### Argument and capability handling

* are capability arguments reconstructed and validated correctly?
* are user-memory arguments bounds-checked and copied safely?

### Error and return semantics

* are error paths deterministic?
* are return values explicit and non-ambient?
* is `ret1` used only where the syscall contract explicitly defines it?

### Blocking and abort

* are blocking paths abortable?
* is no partial authoritative state left behind?

### Restart and stale-state

* are stale generations rejected?
* are stale replies and completions rejected?
* is restart single-resolution?

### Cross-subsystem correctness

* does the change preserve invariants from all referenced subsystem specs?
* does it introduce any new ambient authority?
* does it leak architecture-specific assumptions into the abstract ABI?

### Tests

* capability misuse
* invalid user-memory arguments
* stale generation rejection
* timeout and abort correctness
* restart safety
* deterministic error behavior
* architecture mapping conformance

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for the abstract ABI in Zuki.

Architecture-specific ABI documents must implement this specification exactly.

If code and this document disagree, the code is wrong.
