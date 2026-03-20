# Zuki System Model (SYSTEM.md) — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Superior for cross-cutting system invariants to all subsystem documents except *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all kernel subsystems, services, runtimes, and userspace programs  
**Purpose:** Defines the global invariants, authority structure, execution environment, and system-level rules that all components of Zuki must obey

If code and this document disagree, the code is wrong.

---

## 1. System definition

Zuki is a capability-rooted, deterministic, non-ambient operating system composed of:

- a minimal kernel implementing objects, capabilities, scheduling, memory, IPC, timer mediation, and device mediation
- a service graph composed of explicit authority-bearing services
- userspace programs executing under explicit capability-rooted authority
- runtimes and frameworks that preserve system invariants
- a global execution model that forbids ambient privilege, ambient namespaces, and implicit authority

Zuki is not:

- a POSIX system
- a namespace-rooted privilege system
- a flat handle-table system
- an identity-based privilege system
- a system with ambient filesystem, network, or device access
- a system with ambient service discovery

Zuki is an explicit authority graph, not a namespace.

---

## 2. Global system invariants

The following invariants apply system-wide.

### 2.1 No ambient authority

All authority must be:

- explicitly granted
- explicitly delegated
- explicitly transferred
- explicitly derived
- explicitly revoked or invalidated according to subsystem rules

Nothing in Zuki grants authority implicitly.

### 2.2 Capability-rooted authority

All kernel-visible authority originates from:

- capabilities
- service-owned handles or identifiers explicitly derived from valid capabilities
- explicit delegation edges rooted in capability authority

There is no authority outside the capability model.

Service-owned handles must remain subordinate to capability-rooted authority. They must not become an independent authority system.

### 2.3 Deterministic boundary behavior

All kernel and service boundaries must exhibit:

- deterministic success behavior
- deterministic failure behavior
- deterministic restart behavior
- deterministic stale-state rejection

### 2.4 Single-resolution semantics

All blocking, IPC, timer-governed, and service-mediated operations must resolve:

- exactly once
- deterministically within their contract
- without partial authoritative completion surviving another winner

### 2.5 No ambient namespaces

Zuki forbids ambient:

- filesystem namespaces
- process namespaces
- network namespaces
- device namespaces
- service registries

All discovery and membership are explicit and authority-bearing.

### 2.6 No identity-based privilege

Zuki forbids:

- UID or GID privilege
- PID-based authority
- label-based authority
- namespace-membership-based authority
- role or principal metadata as direct authority

Identity is metadata only unless converted into explicit capability-mediated authority through policy and service contracts.

---

## 3. System structure

Zuki consists of:

- the kernel
- the service graph
- userspace programs
- runtimes and frameworks

### 3.1 Kernel

The kernel provides:

- object model
- capability model
- CSpace model
- scheduling
- memory management
- IPC transport
- timer mediation
- interrupt and device mediation

The kernel does not provide high-level semantics for:

- filesystems
- network protocols
- routing
- general device-driver logic beyond mediation
- service discovery
- privilege escalation

### 3.2 Service graph

The service graph is:

- explicit
- capability-rooted
- deterministic
- restart-safe
- non-ambient

Services are:

- authority-bearing participants in the system graph
- reachable only through explicit capabilities, IPC endpoints, or delegated handles
- governed by explicit contracts

Services are not ambient OS facilities.

The system does not require all service dependencies to be globally acyclic in every implementation graph, but no service relationship may create ambient authority or hidden authority edges.

### 3.3 Userspace programs

Programs execute:

- under explicit authority
- with no ambient privileges
- with deterministic boundary behavior
- through explicit syscall, IPC, and capability semantics

### 3.4 Runtimes and frameworks

Runtimes and frameworks must:

- preserve system invariants
- not create hidden authority
- not create hidden namespace effects
- not fabricate capabilities
- not introduce ambient service access

Implementation detail is permitted. Hidden authority is not.

---

## 4. Authority model

### 4.1 Authority graph

The system’s authority is a directed graph composed of:

- CSpaces
- capabilities
- service-owned handle domains rooted in capabilities
- explicit delegation edges
- explicit IPC/service authority edges

Authority flows only along explicit edges.

### 4.2 No implicit authority edges

Zuki forbids:

- authority by name
- authority by identity
- authority by namespace membership alone
- authority by path alone
- authority by ambient discovery
- authority by undocumented service side effects

### 4.3 Revocation and invalidation

Revocation and invalidation must remain:

- explicit
- deterministic
- freshness-preserving
- non-ambient

For kernel object authority, freshness is generation-based as defined by `CAPABILITIES.md`.

This system rule does not require every service-owned teardown path to use the same implementation mechanism, but no service may preserve stale authority or simulate ambient resurrection.

### 4.4 No second authority system

No subsystem may introduce a second global authority system parallel to capabilities.

Service-owned handles, runtime objects, language references, and compatibility-layer identifiers must all remain subordinate to explicit capability-rooted authority.

---

## 5. Execution model

### 5.1 Threads

Threads are:

- explicit kernel objects
- created through explicit authority
- scheduled according to `SCHED.md`

### 5.2 Blocking

Blocking obeys:

- single-resolution semantics
- deterministic wake rules
- deterministic timeout and abort rules

### 5.3 Memory

Memory obeys:

- explicit mapping
- explicit rights
- explicit shared-memory contracts
- deterministic boundary fault behavior

### 5.4 IPC

IPC obeys:

- capability-bearing semantics
- explicit endpoints
- explicit transaction semantics
- deterministic reply and abort behavior

### 5.5 Services and runtimes

Service calls and runtime-mediated OS interactions must preserve the same execution invariants as direct program interaction. They must not create hidden privilege or hidden re-entry paths.

---

## 6. Service model

### 6.1 Services are explicit

Services must:

- expose explicit capabilities, endpoints, or delegated handles
- define explicit contracts
- define explicit authority boundaries
- define explicit startup, restart, and teardown semantics

### 6.2 No ambient service discovery

Services must not:

- register into ambient global lookup spaces
- expose authority through undocumented names
- rely on ambient discovery for correctness or privilege

Any discovery mechanism must itself be explicit and capability-scoped.

### 6.3 Service lifecycle

Services must define:

- startup invariants
- steady-state invariants
- restart invariants
- teardown invariants

Service lifecycle must preserve capability freshness and stale-state rejection across restart and teardown.

### 6.4 Service boundaries are security boundaries

Service boundaries are part of the system authority model.

A service boundary may be crossed only through explicit, capability-consistent mechanisms.

---

## 7. System lifecycle

### 7.1 Boot

Boot must:

- construct the minimal initial kernel-owned authority root
- publish the initial capability root and initial thread/address-space state
- expose no ambient authority

Initial high-level service construction is defined by `INIT.md`, not by ambient kernel behavior.

### 7.2 Initialization

Initialization must:

- construct the initial service graph explicitly
- construct initial namespaces explicitly
- distribute authority explicitly
- expose no ambient privilege

### 7.3 Restart

Restart must:

- preserve freshness and generation semantics where applicable
- reject stale authority and stale transaction state
- not resurrect stale handles, timers, replies, or service-owned state
- not widen authority

### 7.4 Shutdown and teardown

Shutdown and teardown must:

- deterministically terminate or invalidate services and in-flight operations according to subsystem contracts
- not leak authority
- not preserve stale reachable authority beyond the defined shutdown contract

This does not require one global revocation primitive. It requires that no authority remain spuriously live beyond teardown.

---

## 8. Cross-subsystem consistency rules

No subsystem may contradict the following system-level rules:

- capability-rooted authority
- no ambient namespaces
- no identity-based privilege
- deterministic stale-state rejection
- single-resolution blocking and reply semantics
- explicit service boundaries
- restart without stale-authority resurrection

If a subsystem document appears to permit one of these, that subsystem document is wrong.

Subsystems may refine implementation details, but may not weaken system invariants.

---

## 9. Forbidden patterns

The following are specification violations:

- ambient authority
- ambient namespaces
- ambient service discovery
- identity-based privilege
- capability fabrication
- capability widening
- hidden authority edges
- hidden concurrency or hidden namespace effects that create authority
- hidden service access
- nondeterministic boundary behavior
- re-entrant or multi-resolution IPC or timer-governed completion
- implicit shared memory
- implicit device access
- implicit network access
- implicit filesystem access
- service-owned handle systems that become independent authority roots
- stale authority surviving restart or teardown without explicit reconstruction

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any system-level change:

### Authority

- does it preserve capability-rooted authority?
- does it avoid ambient authority?
- does it avoid hidden authority edges or second authority systems?

### Services

- does it preserve explicit service boundaries?
- does it avoid ambient discovery?
- are lifecycle and restart rules explicit?

### IPC and execution

- does it preserve transaction and single-resolution semantics?
- does it avoid hidden re-entry or partial authoritative completion?

### Memory and concurrency

- does it preserve deterministic boundary fault behavior?
- does it avoid implicit shared memory or hidden concurrency effects that alter authority?

### Lifecycle

- does it preserve boot/init separation?
- does it preserve restart invariants?
- does it prevent stale-authority resurrection?

### Tests

- ambient-authority rejection
- namespace isolation
- stale-state rejection across restart
- service-boundary enforcement
- deterministic failure behavior
- cross-subsystem consistency checks

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for the Zuki system model.

If code and this document disagree, the code is wrong.
