# Zuki Security Invariants — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel`, core services under `/services/*`, and any component that defines, enforces, or depends on security-relevant behavior, including capabilities, policy, isolation, privilege transitions, restart behavior, and subsystem boundaries.

This document defines:

- global security model
- capability and authority invariants
- isolation and containment rules
- privilege and identity semantics
- cross-subsystem security boundaries
- restart and failure security semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Global security model

Zuki’s security model is:

- capability-rooted
- least-authority by construction
- isolation-first
- deterministic under adversarial input
- restart-safe
- hostile to ambient authority and implicit privilege

Security is not a separate layer. It is the emergent property of:

- `OBJECTS.md` (object model)
- `CAPABILITIES.md` (capability semantics)
- `BOOT.md` (trusted root)
- `MM.md` (memory safety)
- `IPC.md` (communication)
- `SCHED.md` (execution)
- `VFS.md`, `DEVICE.md`, `NET.md` (I/O and external interfaces)
- `TIMERS.md` (timeouts and aborts)
- `POLICY.md` (policy evaluation)

This document defines the cross-cutting invariants all of those specifications must obey.

---

## 2. Capability and authority invariants

### 2.1 Capability as the only authority

- All authority is represented by capabilities or by explicitly defined kernel mechanisms that remain subordinate to capability-mediated control.
- No operation may succeed based on identity, path, ambient context, or implicit role alone.
- There is no ambient root, superuser, or global administrator bit.

Kernel objects may embody protected state, but they do not create ambient authority. Authority to act on them must still be obtained through the defined capability and syscall/interface model.

### 2.2 Non-amplification

- No subsystem may amplify authority beyond what is present in its validated input capabilities and explicit policy constraints.
- Derived capabilities must have rights that are a subset of their parents.
- Policy may deny or narrow authority, but must not fabricate new authority.

### 2.3 Explicit construction

- All authority-bearing objects, whether kernel-owned or service-owned, must be created through explicit, audited paths.
- No implicit authority acquisition is permitted through enumeration, default namespaces, wildcard binds, ambient inheritance, or service restart.

### 2.4 Revocation and lifetime

- Authority must not outlive the object, process, namespace, or service generation that granted it.
- Stale capabilities, handles, queue entries, timer state, and replies must be rejected through generation or equivalent freshness checks.
- Restart must not silently resurrect or preserve authority beyond the explicit restart contract.

---

## 3. Isolation and containment

### 3.1 Process and address-space isolation

- Each address space is isolated by default.
- No process may access another process’s memory without explicit, capability-mediated sharing.
- `MM.md` invariants must hold at all times.

### 3.2 Object and subsystem isolation

- Kernel objects are isolated by type, ownership, and subsystem contract.
- Subsystems such as VFS, NET, DEVICE, RPS, and policy must not reach into each other’s internal state except through defined interfaces.
- No cross-subsystem backdoor, shortcut, or fast path may bypass capability validation or object-lifetime rules.

### 3.3 Namespace isolation

- Filesystem, network, and other namespaces are capability-scoped and non-ambient.
- No implicit membership in a global namespace exists.
- Creating, joining, or transferring namespace authority must be explicit and policy-visible.

### 3.4 Driver and service isolation

- Drivers and core services are untrusted and sandboxed.
- They must not gain authority beyond their explicit capabilities and policy-mediated grants.
- Failure or compromise of one service must not compromise kernel integrity or grant ambient authority over other services.

---

## 4. Identity, policy, and privilege

### 4.1 Identity as data, not authority

- Identity, including user IDs, labels, principals, or roles, is metadata, not authority.
- Identity may influence policy evaluation, but identity alone must never cause an operation to succeed.
- Any authority effect derived from identity must be realized only through explicit, capability-mediated decisions.

### 4.2 Policy as a narrowing function

- Policy may only narrow, deny, redirect, or otherwise constrain authority.
- Policy must not amplify authority beyond the explicit authority domain of the calling site.
- Policy decisions must be deterministic, bounded, and auditable.
- Policy evaluation must obey `POLICY.md` and `TIMERS.md`.

### 4.3 Privilege transitions

Any privilege transition, including:

- gaining new capabilities
- joining a namespace
- adopting a role
- acquiring access to a new service domain

must be:

- explicit
- policy-mediated where required
- observable at the responsible subsystem boundary

Logging may be required by policy or audit configuration, but observability of the transition at the enforcing layer is mandatory.

No implicit escalation via setuid-like behavior, environment, ambient inheritance, or restart side effects is permitted.

---

## 5. Cross-subsystem security boundaries

### 5.1 Boot and trust root

- `BOOT.md` defines the only trusted root of execution.
- No subsystem may introduce a second root or root-equivalent ambient authority.
- Boot constructs the minimal initial object graph and capability root. All later authority must be derived from that root.

### 5.2 Kernel vs userspace

- Kernel code must never depend on userspace correctness for security.
- Userspace services, including VFS, NET, RPS, policy, and drivers, must be treated as adversarial for enforcement purposes.
- Kernel interfaces must remain correct under malformed, malicious, replayed, or stale inputs.

### 5.3 IPC and message boundaries

- All IPC endpoints are capability-scoped.
- No ambient broadcast or global message bus exists.
- Messages must be validated at subsystem boundaries.
- No blind deserialization into authority-bearing structures is permitted.

### 5.4 Timers and timeout boundaries

- Timers must not create new ambient authority or unauthorized signaling paths.
- Timeout paths must be single-resolution and must not leave partial state live.
- Timer-driven aborts must fail closed.

### 5.5 I/O and service boundaries

- Filesystem, device, and network semantics must remain in their designated service layers.
- The kernel must not silently absorb high-level service semantics in ways that bypass capability, policy, or restart rules.
- Service restart must not become an authority-preserving side channel.

---

## 6. Restart, failure, and compromise semantics

### 6.1 Fail-closed principle

On detection of:

- internal inconsistency
- impossible state
- security invariant violation

the system must fail closed.

At kernel level, this means panic or an equivalent fatal path.

At service level, this means restart, teardown, or refusal of the affected operation, without silently preserving corrupted authority or partial state.

Continuing with silently corrupted state is forbidden.

### 6.2 Restart and stale state

On restart of any service, including VFS, NET, RPS, drivers, or policy:

- all in-flight operations must resolve exactly once
- all service-owned authority must be explicitly re-established
- stale handles, timers, queue entries, replies, and transaction state must be rejected through generation or equivalent freshness checks
- no authority may silently persist across restart beyond what is explicitly reconstructed

### 6.3 Compromise containment

Assume any userspace service can be compromised.

The system must ensure compromise of one service cannot:

- read or write arbitrary kernel memory
- access other services’ internal state without explicit authority
- gain new capabilities beyond its initial set and explicit grants
- bypass scheduler, MMU, object, or timer invariants

### 6.4 Hotplug and dynamic change

Device hotplug, NIC changes, namespace changes, policy updates, and dynamic service replacement must:

- not leak authority
- not leave stale state reachable
- not create new ambient access paths
- publish any new authority only through explicit capability-scoped construction

---

## 7. Forbidden patterns

The following are specification violations:

- ambient authority, including global root, implicit admin, or default full access
- identity-based success without capability validation
- authority amplification without explicit, policy-mediated transition
- kernel-resident service semantics that bypass capability and policy layers
- cross-subsystem shortcuts that skip validation
- non-abortable waits or timeouts that leave partial state live
- stale handles, timers, replies, or queue entries affecting new operations
- relying on userspace correctness for kernel security
- silent recovery from security-relevant corruption
- restart behavior that preserves authority without explicit reconstruction

Any such change is a violation, not an optimization.

---

## 8. Implementation checklist

Before merging any change that touches security-relevant behavior in the kernel or core services:

### Authority

- is every authority-bearing operation capability-validated?
- does any code path succeed due to identity, path, ambient context, or restart state alone?
- is any new authority explicitly constructed and bounded?

### Isolation

- does the change preserve process, namespace, driver, and subsystem isolation?
- does it introduce new shared state, backdoor paths, or unauthorized visibility?

### Policy

- is policy consulted where required?
- can policy only narrow or deny authority at this call site?
- is fallback behavior explicit and fail-safe?

### Restart and lifetime

- are stale generations, handles, timers, queue entries, and replies rejected after restart or teardown?
- do all in-flight operations resolve exactly once?
- does any authority survive restart without explicit reconstruction?

### Failure behavior

- does the system fail closed on invariant violation?
- are error paths deterministic and non-leaky?
- does a service-level failure remain contained?

### Tests

- capability misuse and denial
- namespace isolation
- malicious or malformed service inputs
- restart with stale handles, timers, queues, and replies
- policy allow/deny/redirect correctness
- hotplug and dynamic policy changes
- compromise-containment assumptions for core services

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 9. Ground-truth rule

This document is the ground truth for security invariants in Zuki.

If code and this document disagree, the code is wrong.
