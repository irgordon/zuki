# Zuki Linux Personality & RPS Translation Layer — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*, `SYSCALL.md`, `SECURITY.md`, `INIT.md`, and `ABI.md`  
**Scope:** Binding for all code under `/services/rps-linux`, any kernel shim explicitly involved in personality handoff, and any component that participates in translating Linux syscalls, ABIs, or Linux-visible semantics into Zuki’s capability-rooted model.

This document defines:

- the Linux personality model in Zuki
- the RPS-Linux translation contract
- syscall and ABI translation rules
- capability, FD, PID, and namespace mapping
- restart and failure semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Linux personality model overview

Zuki’s Linux personality is:

- implemented in userspace by the RPS-Linux service
- non-privileged in the kernel sense
- capability-rooted and policy-mediated
- restartable and non-ambient
- a compatibility layer, not a security boundary

The kernel does not:

- implement Linux syscalls natively
- expose a Linux syscall table as part of the canonical kernel ABI
- implement Linux errno as a kernel ABI concept
- implement Linux `/proc`, `/sys`, or Linux VFS semantics directly

The Linux personality is a userspace runtime that:

- receives Linux-facing syscall requests or compatibility traps through the defined personality entry model
- translates them into Zuki syscalls, IPC, and service operations
- preserves Linux-visible compatibility only to the extent that doing so does not weaken Zuki’s invariants

Linux compatibility must never override capability, namespace, restart, or policy rules.

---

## 2. Canonical Linux entry model

## 2.1 Personality entry rule

Linux-targeting runtimes must enter the Linux personality through a defined personality entry path.

That path may be implemented as:

- a userspace thunk or vDSO-like entry into RPS-Linux, or
- a kernel-mediated reflection handoff into RPS-Linux, if and only if the kernel treats the Linux-facing request as personality transport and not as a native kernel Linux syscall ABI

There must be exactly one canonical configured entry model for a given build or target environment.

### 2.2 No native Linux kernel ABI

The kernel must not:

- expose a native Linux syscall table as a first-class ABI
- decode Linux syscall numbers as part of the canonical Zuki syscall ABI
- special-case Linux semantics in the generic syscall-dispatch path

Any kernel participation in Linux compatibility must remain a transport shim into RPS-Linux, not a native Linux semantic implementation.

### 2.3 Kernel visibility rule

The kernel sees only:

- Zuki syscalls and ABI contracts
- personality transport metadata where explicitly defined
- capability-validated service interactions

Linux syscall semantics remain outside the kernel.

---

## 3. RPS-Linux service contract

## 3.1 Service role

RPS-Linux is a userspace service that:

- implements Linux syscall and process-visible semantics as best-effort compatibility
- maps Linux concepts such as FDs, PIDs, signals, mount views, and namespaces onto Zuki capabilities, services, and namespace contracts
- mediates all Linux-facing operations through Zuki’s capability and policy model

### 3.2 Trust and authority model

RPS-Linux:

- runs with a bounded capability set granted by init
- receives only the capabilities required to perform its compatibility role
- must not fabricate or widen authority beyond what it holds

RPS-Linux is not trusted to bypass:

- capability checks
- policy decisions
- namespace isolation
- restart and stale-state rules

### 3.3 Linux process model boundary

Linux-targeted tasks may still correspond to real Zuki processes and threads.

However:

- Linux-visible process semantics are mediated by RPS-Linux
- Linux-visible identifiers are not kernel principals
- Linux-visible authority must still be derived from explicit Zuki capabilities and service-owned state

Linux processes are therefore compatibility tenants of RPS-Linux, not ambient kernel authorities.

---

## 4. Syscall translation model

## 4.1 Linux syscall decoding

RPS-Linux must:

- decode Linux syscall numbers and arguments within the personality layer
- maintain the Linux syscall table inside the service, not in the kernel
- treat unknown or unsupported Linux syscalls as deterministic failures

### 4.2 Mapping to Zuki operations

Each Linux syscall must be implemented as:

- one or more Zuki syscalls
- one or more IPC operations to Zuki services
- userspace translation logic in RPS-Linux
- any required policy and capability checks

Examples:

- `linux_openat` → RPS-Linux VFS client → VFS service IPC
- `linux_socket` → RPS-Linux NET client → NET service IPC
- `linux_mmap` → RPS-Linux MM client → Zuki memory syscalls plus service bookkeeping

No Linux syscall may map to a privileged kernel path that bypasses the Zuki service graph.

### 4.3 Translation determinism

Given the same Linux-visible input, service state, policy state, and Zuki-visible authority, RPS-Linux must produce the same translation and result.

### 4.4 Error and errno mapping

RPS-Linux must:

- translate Zuki errors into Linux errno values deterministically
- maintain errno or equivalent Linux-visible error state as userspace process-local compatibility state, not as a kernel ABI feature
- document the mapping for unsupported or lossy cases

The same translated failure condition must produce the same Linux-visible error outcome under the same compatibility contract.

---

## 5. Capability, FD, PID, and namespace mapping

## 5.1 File descriptors

Linux file descriptors are:

- RPS-Linux-owned compatibility handles
- mapped to Zuki capabilities and/or service-owned handles
- not directly exposed as kernel object references to Linux processes

RPS-Linux must:

- maintain an FD table per Linux-visible process or equivalent compatibility domain
- ensure FD lifetime, duplication, close, and reuse obey the Linux compatibility contract
- ensure FD reuse is protected by generation or an equivalent freshness mechanism so stale FDs cannot bind to new authority accidentally

### 5.2 PIDs and process model

Linux PIDs are:

- RPS-Linux-owned identifiers
- mapped onto Zuki process capabilities, process records, or internal translation state

RPS-Linux must:

- not treat Linux PIDs as kernel principals
- ensure PID reuse cannot violate freshness, generation, or restart rules
- reject stale PID-based references after restart or teardown

### 5.3 Namespaces

Linux-like namespaces such as mount, net, and pid namespaces are:

- compatibility-layer constructs owned by RPS-Linux
- backed by explicit Zuki namespaces and capabilities where appropriate
- always capability-scoped and policy-visible

RPS-Linux must not:

- create ambient global namespaces
- bypass Zuki namespace isolation
- create a second authority system parallel to Zuki namespaces

Linux namespace semantics are an emulation layer over explicit Zuki authority, not an independent source of privilege.

---

## 6. Signals, threads, and scheduling

## 6.1 Signals

Linux signals are:

- RPS-Linux-level compatibility events
- delivered via RPS-Linux bookkeeping and explicit interactions with Zuki processes and threads

The kernel does not implement Linux signal semantics.

Signal delivery must be:

- deterministic
- restart-safe
- single-resolution with respect to the affected wait or delivery event

### 6.2 Threads

Linux threads such as those created through `clone` or pthread runtimes are:

- mapped by RPS-Linux onto Zuki threads and processes
- subject to Zuki scheduler, capability, and restart rules

RPS-Linux must:

- not assume ambient thread-creation authority
- use explicit process and thread capabilities granted through init/service-graph construction
- not allow Linux thread semantics to bypass `SCHED.md`

### 6.3 Scheduling boundary

Linux-visible scheduling effects are compatibility behavior only.

The underlying scheduler remains Zuki’s scheduler, and Linux compatibility must not weaken:

- thread-state transition rules
- blocking and abort semantics
- timer and wake invariants

---

## 7. Restart, failure, and stale-state semantics

## 7.1 RPS-Linux restart

On RPS-Linux restart:

- all Linux-visible process state managed solely by RPS-Linux is invalidated unless explicitly reconstructed
- all in-flight Linux syscalls must resolve exactly once as success, failure, timeout, or abort
- stale Linux FDs, PIDs, signals, namespace handles, and translation state must be rejected
- no stale completion, reply, or timeout may bind to a new-generation RPS-Linux instance

RPS-Linux must not:

- silently preserve or resurrect Linux-visible authority across restart
- leak Zuki capabilities during restart or failure

### 7.2 Kernel and service failures

Kernel or service failures affecting VFS, NET, DEVICE, POLICY, or other dependencies must:

- surface to RPS-Linux as deterministic failures or aborts
- be translated into Linux-visible errors, interrupted operations, or process termination according to the compatibility contract
- remain faithful to Zuki’s security and single-resolution rules

RPS-Linux must not hide security-relevant failures behind ambient compatibility behavior.

### 7.3 Stale-state rejection

RPS-Linux must reject stale:

- FD references
- PID references
- namespace references
- pending syscall completions
- pending signal deliveries
- timer-governed operation state

Freshness must be enforced through generation, transaction identity, or an equivalent bounded mechanism.

---

## 8. Policy and security integration

## 8.1 Policy

All authority-bearing operations performed on behalf of Linux processes are policy sites where the underlying Zuki service contracts require policy.

Policy may:

- deny
- narrow
- redirect

Policy must not fabricate new authority.

RPS-Linux must:

- consult policy where required by the underlying service contracts
- not cache or assume policy decisions beyond their defined lifetime
- treat policy results as narrowing constraints, not ambient permissions

### 8.2 Security invariants

RPS-Linux must obey:

- `SECURITY.md` — no ambient authority, no identity-based privilege
- `INIT.md` — bounded authority, explicit service graph
- `CAPABILITIES.md` — no authority amplification
- `VFS.md`, `NET.md`, `DEVICE.md` — no bypass of service boundaries
- `TIMERS.md` and `SCHED.md` — no multi-resolution wait completion
- `ABI.md` and `SYSCALL.md` — only Zuki syscall semantics at the kernel boundary

Linux compatibility must never weaken Zuki’s security model.

### 8.3 Identity rule

Linux credentials such as UIDs, GIDs, supplementary groups, and similar metadata are compatibility-layer identity data.

They may influence policy and compatibility behavior, but they are not authority by themselves.

---

## 9. Forbidden patterns

The following are specification violations:

- implementing Linux syscall semantics directly in the kernel
- exposing a Linux syscall table as a native kernel ABI
- treating Linux PIDs, UIDs, or GIDs as kernel principals
- mapping Linux FDs directly to kernel objects visible to Linux processes without compatibility mediation
- creating ambient global namespaces for Linux compatibility
- bypassing policy or capability checks in the name of compatibility
- preserving Linux-visible authority across RPS-Linux restart without explicit reconstruction
- treating Linux identity or credentials as authority rather than metadata
- allowing stale completions, signals, or handles to bind after restart

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any RPS-Linux-related change:

### Translation

- is each Linux syscall mapped to explicit Zuki service calls and/or syscalls?
- are error mappings deterministic and documented?
- is unsupported behavior rejected deterministically?

### Authority

- are all authority-bearing operations capability-validated?
- does RPS-Linux hold only bounded, explicit capabilities?
- is Linux identity kept as metadata rather than authority?

### State and restart

- are Linux FDs, PIDs, signals, and namespaces backed by restart-safe structures?
- are stale Linux handles, completions, and signals rejected after restart?
- do in-flight operations resolve exactly once?

### Security and policy

- does the change preserve Zuki security invariants?
- are policy hooks present where required?
- is no ambient namespace or ambient privilege introduced for compatibility?

### Tests

- Linux syscall translation correctness
- deterministic errno mapping
- FD and PID lifetime and reuse
- namespace isolation under Linux personality
- signal delivery and stale-signal rejection
- RPS-Linux restart with stale-handle rejection
- policy allow/deny/redirect behavior under Linux workloads

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for Linux personality and RPS translation semantics in Zuki.

If code and this document disagree, the code is wrong.
