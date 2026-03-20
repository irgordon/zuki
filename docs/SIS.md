# Zuki System Call Interface Specification (SIS.md) — Implementer Specification v1.0

**Status:** Canonical  
**Authority:**  
- Subordinate to *SYSTEM-ARCHITECTURE.md* and *SYSTEM.md*  
- Subordinate to *SYSCALL.md* for execution semantics  
- Subordinate to *ABI-SYSCALL.md* for calling conventions  
- Superior, for syscall-surface semantics, to subsystem documents (`IPC.md`, `MM.md`, `SCHED.md`, `TIMERS.md`, `DEVICE.md`, `NET.md`, `CAPABILITIES.md`, `CSPACE.md`, `INIT.md`)

**Scope:** Binding for all code under `/kernel/sys`, `/kernel/ipc`, `/kernel/mm`, `/kernel/sched`, `/kernel/timers`, `/kernel/dev`, and any userspace component that invokes kernel entrypoints.

**Purpose:** Defines the canonical syscall surface: syscall table, semantics, capability requirements, blocking and error behavior, cross-subsystem invariants, and forbidden patterns.

If code and this document disagree, the code is wrong.

---

## 1. Syscall model overview

Zuki’s syscall interface is:

- capability-validated  
- deterministic  
- non-ambient  
- restart-safe  
- single-resolution  
- minimal and explicit  

Syscalls are the only kernel entrypoint available to userspace.

The kernel syscall surface does not implement high-level service semantics such as:

- filesystem semantics  
- network protocol state  
- routing logic  
- socket state  
- high-level device protocols  
- identity-based privilege  

Those semantics live in userspace services.

Syscalls operate only on:

- kernel objects defined by `OBJECTS.md`  
- capability arguments  
- user-memory arguments  
- IPC endpoints  
- scheduler state  
- timers and timeouts  
- memory mappings  
- device queues, DMA windows, and IRQ objects  

---

## 2. Canonical syscall table (v1.0)

The syscall table is fixed and versioned.

Unknown syscall numbers must fail with the canonical invalid-syscall error (`-ENOSYS` as defined by `ABI-SYSCALL.md`).

Syscall numbers must remain stable across compatible kernel versions.  
New syscalls may be added only at previously unused numbers.  
Existing numbers must not be reassigned or repurposed.

Reserved ranges:

- `0x70–0x7F` — experimental / development syscalls  
- `0x80–0xFF` — future expansion  

### 2.1 IPC syscalls

| Name           | Number | Description                           |
|----------------|-------:|---------------------------------------|
| `sys_ipc_send` | `0x01` | send a message to an IPC endpoint     |
| `sys_ipc_recv` | `0x02` | receive a message from an IPC endpoint |

`sys_ipc_call` is **not** part of the required canonical surface in v1.0 unless implemented strictly as an ABI wrapper over the same IPC transaction rules as `send` followed by reply wait. It must not introduce a second IPC semantic model.

Requirements:

- endpoint capability validated with the required rights  
- blocking behavior obeys `IPC.md` and `SCHED.md`  
- stale replies must be rejected  
- completion is single-resolution  

### 2.2 Memory-management syscalls

| Name            | Number | Description                                  |
|-----------------|-------:|----------------------------------------------|
| `sys_map`       | `0x10` | map a frame into an address space           |
| `sys_unmap`     | `0x11` | unmap a region from an address space        |
| `sys_protect`   | `0x12` | change mapping permissions within authority |
| `sys_as_create` | `0x13` | create a new address space                  |

Requirements:

- address-space capability required  
- frame capability required where applicable  
- all operations obey `MM.md`  
- operations must not leave partial mappings or stale TLB-visible state  

Frame allocation is not part of the canonical kernel syscall surface.  
Physical memory allocation authority must be provided through explicit service construction or delegated authority mechanisms.  
The kernel does not expose a general-purpose frame allocator syscall.

### 2.3 Scheduler and thread syscalls

| Name                  | Number | Description                                  |
|-----------------------|-------:|----------------------------------------------|
| `sys_yield`           | `0x20` | yield CPU voluntarily                        |
| `sys_thread_create`   | `0x21` | create a new thread                          |
| `sys_thread_exit`     | `0x22` | terminate current thread                     |
| `sys_thread_set_state`| `0x23` | modify scheduler-defined thread parameters within authority |

Requirements:

- thread and address-space capabilities validated where applicable  
- thread-state transitions obey `SCHED.md`  
- dead or retired threads must not be resurrected  

Thread state modification must be restricted to parameters explicitly authorized by the provided capability.  
No syscall may allow modification of scheduling parameters that would grant priority escalation beyond the caller's authority.

### 2.4 Timer syscalls

| Name        | Number | Description                          |
|-------------|-------:|--------------------------------------|
| `sys_sleep` | `0x30` | block current thread for a duration  |

`sys_timer_create` and `sys_timer_cancel` are not required canonical v1.0 syscalls unless timers are explicitly exposed as kernel objects. `TIMERS.md` currently defines timers as kernel-resident scheduling primitives, not user-visible capability objects.

Requirements:

- `sys_sleep` uses monotonic time only  
- blocking is abortable  
- stale expirations must be rejected  
- no timer state may outlive the owning wait  
- `sys_sleep` must not be implemented using wall-clock time; time adjustments, clock synchronization, or leap corrections must not affect sleep duration or timeout semantics  

### 2.5 Device and low-level I/O syscalls

| Name                    | Number | Description               |
|-------------------------|-------:|---------------------------|
| `sys_dma_window_create` | `0x40` | create a DMA window       |
| `sys_dma_window_revoke` | `0x41` | revoke a DMA window       |
| `sys_queue_submit`      | `0x42` | submit to a device queue  |
| `sys_queue_complete`    | `0x43` | acknowledge queue completion |
| `sys_irq_bind`          | `0x44` | bind an IRQ endpoint      |

Requirements:

- device, queue, DMA, and IRQ capabilities validated explicitly  
- operations obey `DEVICE.md`  
- stale queue entries, DMA windows, and IRQ state must be rejected after restart, retire, or hotplug  

### 2.6 Authority-domain and capability-space syscalls

| Name                 | Number | Description                                      |
|----------------------|-------:|--------------------------------------------------|
| `sys_domain_create`  | `0x50` | create a new authority domain                   |
| `sys_domain_exit`    | `0x51` | terminate current authority domain              |
| `sys_cap_transfer`   | `0x52` | transfer capability through explicit destination authority |
| `sys_cnode_create`   | `0x53` | create a new CNode if supported by authority model |

Requirements:

- semantics must remain consistent with `INIT.md` and the explicit service graph  
- no implicit domain privilege  
- no capability leakage  

### 2.7 Capability syscalls

| Name             | Number | Description                                  |
|------------------|-------:|----------------------------------------------|
| `sys_cap_derive` | `0x60` | derive a new capability with narrowed rights |
| `sys_cap_destroy`| `0x61` | destroy a capability in an explicitly addressed slot |
| `sys_cap_inspect`| `0x62` | inspect bounded capability metadata          |

Inspection must expose only capability metadata explicitly defined as observable, including:

- object type  
- rights mask  
- generation value  
- bounded state flags  

Inspection must not expose:

- kernel memory addresses  
- object pointers  
- internal scheduler state  
- timing-sensitive or security-sensitive metadata  

`sys_cap_revoke` must not imply per-capability subtree walking unless a separate revocation structure is explicitly defined. The canonical revocation model remains generation-based as defined in `CAPABILITIES.md`.

---

## 3. Calling convention and argument model

SIS is semantic and defers ABI details to `ABI-SYSCALL.md`. It constrains how arguments are interpreted, not which registers they occupy.

### 3.1 Entry mechanism

Native syscalls enter through the architecture-defined trap/syscall instruction:

- `SYSCALL` on x86_64  
- `SVC` on AArch64  
- `ECALL` on RV64  

The architecture-specific entry layer must define:

- syscall-number register  
- argument registers  
- return registers  
- stack alignment requirements  

The common syscall layer must not invent a fake universal register model.

### 3.2 Capability argument wire format

Capability arguments must be passed as an explicit wire tuple containing:

- `object_id`  
- `gen_at_mint`  
- `rights`  

The kernel reconstructs a logical `Capability` and validates it via `cap_use()`.

Raw pointers are never valid kernel object references.

### 3.3 User-memory arguments

If a syscall accepts user buffers or structured argument blocks:

- the pointer must be treated as a user virtual address only  
- bounds must be validated before access  
- copy-in/copy-out must be explicit  
- no user-memory argument may be trusted based on address value alone  

---

## 4. Capability validation rules

Every authority-bearing syscall must validate:

- capability existence  
- capability type  
- capability rights  
- capability freshness via generation  
- compatibility with the target operation  

No syscall may succeed without explicit capability authority.

No syscall may rely on:

- identity  
- path  
- ambient namespace membership  
- implicit process or domain privilege  
- default service ownership  

“Capability ownership” must not be interpreted as an ambient check. Any ownership rule must be represented through explicit capability or destination-authority semantics.

---

## 5. Error and idempotence model

### 5.1 Deterministic return model

Syscalls return:

- success values on success  
- explicit negative failure codes on failure  

Error results must be:

- deterministic  
- explicit  
- local to the syscall result  
- free of global ambient error state  

### 5.2 No partial success

Syscalls must be atomic with respect to the state they modify, including:

- capability state  
- object state  
- memory mappings  
- queue entries  
- timer-governed waits  
- IPC transactions  

If a syscall fails or aborts, it must not leave partial authoritative state live.

### 5.3 Single-resolution rule

A syscall may resolve as exactly one of:

- success  
- failure  
- timeout  
- abort  

Exactly one may win.

### 5.4 Idempotence rule

Syscalls must be idempotent with respect to retry after failure or restart.  
A retry must not:

- duplicate authority  
- leak resources  
- produce multiple completions  

---

## 6. Blocking and abort semantics

### 6.1 Blocking sources

Syscalls may block only through:

- IPC waits  
- timer-governed waits  
- scheduler-governed waits explicitly permitted by subsystem contract  

### 6.2 Abortability

All blocking must be abortable via the subsystem-defined resolution paths, including:

- timeout  
- thread retire or kill  
- authority-domain termination  
- service restart  
- device removal  
- endpoint retire  

### 6.3 No stale state after abort

Abort must not leave behind:

- stale queue entries  
- stale timers  
- stale IPC waits  
- stale replies  
- stale partially applied mappings  
- stale transaction identities  

---

## 7. Restart and stale-state semantics

### 7.1 Restart safety

Restart must not:

- widen authority  
- resurrect stale state  
- complete a syscall twice  
- allow stale replies, queue completions, or timer expirations to bind to new operations  

### 7.2 Stale-state rejection

Syscalls and their participating subsystems must reject:

- stale capabilities  
- stale queue entries  
- stale timer expirations  
- stale IPC replies  
- stale restart-era transaction state  

Freshness must be enforced through generation, transaction id, or an equivalent bounded mechanism.

---

## 8. Cross-subsystem integration

Syscalls must obey:

- `OBJECTS.md` for object invariants  
- `CAPABILITIES.md` for capability derivation, validation, and lifetime  
- `IPC.md` for message and endpoint semantics  
- `MM.md` for mapping and TLB safety  
- `SCHED.md` for blocking and wake rules  
- `TIMERS.md` for timeout semantics  
- `DEVICE.md` for DMA, queue, and IRQ safety  
- `NET.md` for NIC access boundaries  
- `VFS.md` only through service IPC boundaries, not direct kernel VFS semantics  
- `POLICY.md` for narrowing authority where policy is part of a call path  
- `SECURITY.md` for global invariants  
- `INIT.md` for bootstrap and service-graph constraints  

---

## 9. Forbidden patterns

The following are specification violations:

- ambient authority  
- ambient namespaces  
- identity-based privilege  
- implicit capability inheritance  
- syscalls that fabricate authority  
- syscalls that bypass required policy or subsystem validation  
- syscalls that leave partial authoritative state live  
- syscalls that depend on userspace correctness for kernel safety  
- syscalls that resurrect stale state  
- syscalls that complete more than once  
- syscalls that widen authority on restart  
- capability subtree revoke semantics that contradict the generation-based revocation model without an explicitly defined new revocation structure  

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any syscall-related change:

- are all capability arguments reconstructed and validated correctly?  
- are user-memory arguments bounds-checked and copied safely?  
- are error paths deterministic?  
- are blocking paths abortable?  
- are restart paths single-resolution?  
- are stale generations and transactions rejected?  
- are subsystem invariants preserved?  
- is any new authority explicit and capability-scoped?  
- are tests present for:  
  - capability misuse  
  - invalid user-memory arguments  
  - stale generation rejection  
  - timeout and abort correctness  
  - restart safety  
  - deterministic error behavior  
  - stale reply/completion rejection  

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for syscall surface semantics in Zuki.

If code and this document disagree, the code is wrong.
