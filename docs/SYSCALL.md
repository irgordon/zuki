# Zuki Native Syscall ABI — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/syscall` and any kernel or userspace code that issues, handles, or mediates native Zuki syscalls.

This document defines:

- the native Zuki syscall ABI
- entry mechanism and register contract
- capability-based argument passing
- user-memory argument rules
- blocking and wake semantics
- error model
- integration with scheduler, IPC, and memory subsystems
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Syscall model overview

Zuki’s native syscall interface is:

- capability-based
- deterministic
- restartable only where explicitly defined
- non-blocking unless the syscall explicitly blocks
- safe under concurrent revoke, retire, and reclaim

The kernel exposes no ambient authority.

Every syscall that touches kernel objects must validate capabilities explicitly.

Native syscalls are distinct from Linux reflection:

- native syscalls execute entirely in the kernel
- reflected syscalls are handled by RPS
- the two paths share no ABI surface

The native syscall ABI must never:

- expose raw kernel pointers
- bypass capability validation
- violate scheduler state invariants
- perform implicit authority escalation

---

## 2. Entry mechanism and calling convention

## 2.1 Entry mechanism

Native syscalls enter the kernel via the architecture-defined syscall/trap instruction:

- `SYSCALL` on x86_64
- `SVC` on AArch64
- `ECALL` on RV64

The kernel must:

1. capture user-visible architectural register state
2. decode the syscall number from the architecture-defined syscall-number register
3. decode arguments from the architecture-defined syscall argument registers
4. dispatch through the fixed native syscall table

### 2.2 Architecture-specific register mapping

The syscall ABI is defined in terms of logical argument slots:

- `sysno`
- `arg0`
- `arg1`
- `arg2`
- `arg3`
- `arg4`
- `arg5`

Each supported architecture must define a fixed mapping from logical syscall slots to real hardware registers in the architecture-specific syscall entry layer.

The common syscall layer must not assume a fictional universal register naming scheme such as `r0..r5`.

### 2.3 Return convention

Syscall return values are written to the architecture-defined primary return register.

On success:

- return value is non-negative

On failure:

- return value is negative errno

Any additional architecture-visible return-state updates must be explicitly defined by the syscall or architecture layer.

---

## 3. Argument model

## 3.1 Scalar arguments

Scalar arguments are passed in logical argument registers.

The kernel must validate scalar arguments for:

- range
- alignment where required
- enum validity where applicable
- overflow and truncation hazards

### 3.2 Capability arguments

Capabilities are not passed as raw kernel pointers.

A capability argument is passed as a capability wire tuple containing:

- `object_id`
- `gen_at_mint`
- `rights`

The architecture-specific syscall shim may place these fields in multiple registers or in a validated user argument block, but the common syscall layer must reconstruct the same logical `Capability` value.

### 3.3 User-memory arguments

If a syscall accepts a user buffer, string, or structured argument block:

- the argument is a user virtual address and explicit size or bounded format
- the kernel must validate bounds before dereference
- the kernel must not trust pointer validity based only on address range
- all user-memory access must follow mediated copy-in/copy-out rules

Raw user pointers are permitted only as user-memory references, never as kernel object references.

---

## 4. Syscall table

Zuki v1.0 defines the following native syscalls:

| Sysno | Name | Description |
|---|---|---|
| `0` | `sys_yield` | yield CPU voluntarily |
| `1` | `sys_sleep` | sleep for bounded duration |
| `2` | `sys_ipc_send` | send IPC message via endpoint |
| `3` | `sys_ipc_recv` | receive IPC message via endpoint |
| `4` | `sys_map` | map frame into address space |
| `5` | `sys_unmap` | unmap region from address space |
| `6` | `sys_cap_mint` | mint derived capability into destination CNode slot |
| `7` | `sys_cap_destroy` | destroy capability in a destination slot or current slot reference path |
| `8` | `sys_thread_exit` | terminate current thread |
| `9` | `sys_debug` | restricted debug/tracing hook |

Syscalls outside this table must fail with `-ENOSYS`.

No dynamic syscall registration is permitted in v1.0.

---

## 5. Syscall dispatch

## 5.1 Dispatch invariants

- syscall dispatch must be O(1)
- syscall lookup must be table-based
- no dynamic lookup, string matching, or reflective dispatch is permitted
- no blocking may occur before required capability validation for object-touching syscalls
- no syscall handler may continue execution if current-thread retire has been observed and the syscall is not the terminal cleanup path

### 5.2 Dispatch steps

The canonical dispatch path is:

1. capture entry register state
2. decode syscall number
3. reject unknown syscall numbers with `-ENOSYS`
4. reject syscall execution if the current thread has been retired, unless executing the terminal stop/exit path
5. decode and validate arguments
6. validate required capabilities
7. execute the syscall handler
8. return result or error, or block if the syscall explicitly blocks

### 5.3 Current-thread liveness rule

A syscall must not proceed as a normal operation after thread retire is observed for the calling thread.

The only permitted exception is the controlled terminal path needed to complete stop, abort, or exit handling.

---

## 6. Capability-based argument rules

## 6.1 Reconstruction rule

For each capability argument:

1. reconstruct a logical `Capability` from the syscall ABI representation
2. validate it with `cap_use()` using the syscall’s required rights
3. reject stale, invalid, or insufficient-rights capabilities

### 6.2 Non-amplification rule

The syscall layer must not amplify authority.

It must reject:

- missing generation fields
- forged rights
- capability tuples whose rights exceed the authority originally granted

### 6.3 Lifetime rule

Capability validation is valid only for the bounded syscall operation.

Syscall handlers must not retain raw object pointers across:

- syscall return
- blocking
- scheduling
- unrelated long-lived work

Longer-lived retention requires an explicit subsystem-defined retention mechanism.

### 6.4 Forbidden capability argument patterns

The following are forbidden:

- passing raw pointers as capabilities
- passing `ObjectID` without generation
- reconstructing capabilities with implicit or default rights
- using a validated capability outside the bounded operation in which it was checked

---

## 7. Blocking syscalls

Only the following syscalls may block in v1.0:

- `sys_sleep`
- `sys_ipc_send`
- `sys_ipc_recv`

All other native syscalls must either:

- complete immediately, or
- fail immediately

### 7.1 Blocking semantics

A blocking syscall must:

- transition the current thread to the correct blocked state
- publish any required wait metadata before yielding
- yield the CPU
- remain abortable
- resolve exactly once

### 7.2 Wake semantics

Wake from a blocking syscall must:

- set thread state to `THREAD_RUNNABLE`, unless the thread has been retired and moved to terminal stop handling
- enqueue the thread according to scheduler rules
- make the completion outcome observable to the resumed syscall path

### 7.3 Single-resolution rule

A blocking syscall may resolve exactly once by one of:

- success
- failure
- abort

Double completion is a kernel bug.

---

## 8. Error model

## 8.1 Return convention

Native syscalls return:

- non-negative values on success
- negative errno values on failure

### 8.2 Canonical errno set

| Error | Meaning |
|---|---|
| `-ENOSYS` | invalid syscall number |
| `-EINVAL` | invalid argument |
| `-EPERM` | insufficient rights or forbidden operation |
| `-EFAULT` | invalid user pointer or invalid user-memory access |
| `-EDEADLK` | deadlock-like condition detected by policy or IPC rules |
| `-EAGAIN` | operation would block in a non-blocking mode |
| `-ECANCELED` | operation aborted |
| `-EIO` | internal service failure or reflected-service failure |

### 8.3 Determinism rule

Syscalls must not return nondeterministic errors except where the syscall contract explicitly allows externally timed outcomes, such as bounded sleep or defined timeout behavior.

### 8.4 Error consistency rule

The same failure condition must map to the same errno within the same syscall contract.

Silent errno drift across code paths is forbidden.

---

## 9. Syscall definitions

## 9.1 `sys_yield()`

Yield the CPU voluntarily.

Properties:

- takes no capability arguments
- never blocks
- always succeeds
- causes scheduler handoff according to `SCHED.md`

### 9.2 `sys_sleep(duration)`

Sleep for a bounded duration.

Properties:

- blocks the current thread
- must be abortable
- duration must be validated
- must not sleep indefinitely unless such a mode is explicitly defined
- wake behavior must follow scheduler rules

### 9.3 `sys_ipc_send(...)`

Native IPC send.

This syscall is defined by `IPC.md`.

Properties:

- may block
- must validate endpoint capability and transfer authority
- must follow IPC single-resolution and abort rules

### 9.4 `sys_ipc_recv(...)`

Native IPC receive.

This syscall is defined by `IPC.md`.

Properties:

- may block
- must validate endpoint capability
- must follow single-receiver and abort rules

### 9.5 `sys_map(as_cap, frame_cap, vaddr, perms)`

Map a frame into an address space.

This syscall is defined by `MM.md`.

Properties:

- must validate both capabilities
- must serialize page-table mutation by `map_lock`
- must not amplify effective permissions
- must not block in v1.0

### 9.6 `sys_unmap(as_cap, vaddr, size)`

Unmap a region from an address space.

This syscall is defined by `MM.md`.

Properties:

- must validate address-space capability with `RIGHT_UNMAP`
- must serialize page-table mutation by `map_lock`
- must not block in v1.0

### 9.7 `sys_cap_mint(dst_cnode_cap, dst_slot, src_cap, rights)`

Mint a derived capability into a destination CNode slot.

This syscall is defined by `CAPABILITIES.md`.

Properties:

- destination authority must be validated
- source capability must be validated
- requested rights must be a subset of source rights
- destination insertion semantics must be explicit and deterministic

### 9.8 `sys_cap_destroy(cnode_cap, slot_index)`

Destroy a capability located in a destination CNode slot.

This syscall is defined by `CAPABILITIES.md`.

Properties:

- destination CNode authority must be validated
- destruction must be deterministic
- stale capability destruction must not underflow refcount

### 9.9 `sys_thread_exit()`

Terminate the current thread.

Properties:

- never returns
- forces the current thread into the scheduler’s terminal stop path
- must not leave the thread runnable
- must transfer control to the scheduler for next dispatch

### 9.10 `sys_debug(...)`

Restricted debug/tracing operation.

Properties:

- availability is build- and policy-dependent
- must not violate capability, memory, scheduler, or introspection boundaries
- must fail deterministically when unavailable

---

## 10. Integration with scheduler, IPC, and memory subsystems

## 10.1 Scheduler integration

Syscalls must obey `SCHED.md`:

- legal thread-state transitions only
- no blocking outside the defined blocking syscalls
- all wake paths must be single-resolution
- no syscall may cause a retired thread to re-enter runnable execution

### 10.2 IPC integration

IPC syscalls must obey `IPC.md`:

- endpoint validation via `cap_use()`
- bounded queues
- direct-delivery ordering rules
- capability-transfer ownership and rollback rules
- abortable waits

### 10.3 Memory integration

Memory syscalls must obey `MM.md`:

- address-space-owned page-table mutation
- `map_lock` serialization
- non-amplifying effective permissions
- correct TLB invalidation and ordering
- retire/reclaim safety

### 10.4 Capability integration

Capability-manipulating syscalls must obey `CAPABILITIES.md`:

- generation-based validation
- no raw object-pointer retention
- correct retire/reclaim interaction
- no per-capability revoke walks

---

## 11. Concurrency and memory ordering rules

## 11.1 Syscall entry

The kernel must:

- capture user-visible register state with architecture-correct ordering
- validate capabilities using the acquire/release rules defined in `CAPABILITIES.md`
- avoid exposing partially decoded syscall state to handler logic

### 11.2 Syscall execution

During syscall execution:

- handler-visible object access must go through validated capability paths
- no raw object pointer may survive a blocking transition
- state transitions must be atomic where required by subsystem rules

### 11.3 Syscall exit

On return to user mode:

- result registers must be finalized before architectural return
- no stale kernel-visible temporary state may leak into user-visible context
- blocked syscalls must not appear to have both returned and blocked

### 11.4 Forbidden shortcuts

The following are forbidden:

- retaining kernel object pointers across syscalls
- skipping capability validation
- performing non-atomic state transitions where atomicity is required
- returning partially applied state to user mode

---

## 12. Forbidden patterns

The following are specification violations:

- ambient-authority syscalls
- syscalls that implicitly modify capabilities without explicit authority
- syscalls that implicitly modify page tables outside MM rules
- syscalls that bypass the scheduler state machine
- blocking syscalls that are not abortable
- inconsistent errno mapping for the same syscall contract
- syscalls that expose kernel pointers
- syscalls that accept raw user pointers without bounds validation
- handler execution after retire is observed for the current thread, except controlled terminal handling
- ABI drift between architecture-specific entry shims and the common syscall layer

Any such change is a violation, not an optimization.

---

## 13. Implementation checklist

Before merging any change touching `/kernel/syscall`:

- are all capability arguments reconstructed and validated via `cap_use()`?
- are user-memory arguments bounds-checked and copied safely?
- are blocking syscalls abortable?
- are wake paths single-resolution?
- are mapping and unmapping operations serialized by `map_lock`?
- are IPC syscalls consistent with `IPC.md`?
- are thread-state transitions consistent with `SCHED.md`?
- are capability operations consistent with `CAPABILITIES.md`?
- are tests present for:
  - invalid syscall numbers
  - invalid capabilities
  - invalid user pointers
  - revoke during syscall
  - abort during blocking syscall
  - mapping and unmapping under load
  - IPC send/recv correctness
  - thread exit terminal behavior
  - architecture ABI conformance

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 14. Ground-truth rule

This document is the ground truth for the native Zuki syscall ABI.

If code and this document disagree, the code is wrong.
