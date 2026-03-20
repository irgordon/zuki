# Zuki Programming Model — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*, `CAPABILITIES.md`, `CSPACE.md`, `OBJECTS.md`, `SYSCALL.md`, `IPC.md`, `MM.md`, and `SCHED.md`  
**Scope:** Binding for all userspace runtimes, libraries, frameworks, and developer-facing APIs that execute code on Zuki.

This document defines:

- the userspace execution model
- the authority model exposed to programs
- the memory and concurrency model
- the IPC and service-interaction model
- the rules for capability use, transfer, and delegation
- the structure of Zuki programs and services
- the invariants that all runtimes and frameworks must preserve

If code and this document disagree, the code is wrong.

---

## 1. Userspace execution model

A Zuki program executes as:

- one or more threads
- within an address space
- with a root CSpace or equivalent explicit reachable authority graph
- with an initial set of capabilities or service-owned handles derived from explicit capabilities
- under the scheduler defined in `SCHED.md`
- with no ambient authority

### 1.1 No ambient authority

Programs receive only the authority explicitly provided through:

- process creation
- service startup
- IPC receipt
- explicit delegation
- explicit service-defined handle construction rooted in capability authority

There is no ambient:

- global namespace
- global filesystem
- global PID table
- network access
- device access
- service discovery

### 1.2 Deterministic authority

A program’s kernel-visible authority is exactly the set of capabilities reachable from its CSpace plus any service-owned authority derived explicitly and lawfully from those capabilities.

Nothing else grants authority.

### 1.3 Execution invariants

Userspace execution must preserve:

- single-resolution blocking semantics
- deterministic syscall behavior
- deterministic capability consumption
- deterministic fault behavior at the kernel boundary
- deterministic restart behavior within the contracts of the participating services and runtimes

---

## 2. Capability use in programs

## 2.1 Capabilities as authority-bearing values

Capabilities are:

- unforgeable as authority
- opaque except for the explicit ABI/service representations used to pass them
- transferable only through defined mechanisms
- validated by the kernel or responsible service on use

Userspace may hold capability values or service-level wrappers around them, but must not be able to create new authority by guessing, fabricating, or reinterpretation.

### 2.2 Capability operations

Programs may, subject to the capabilities they hold:

- store capabilities
- transfer capabilities via IPC
- derive narrower capabilities
- insert, delete, or move capabilities in CNodes they are authorized to modify

Programs may not:

- widen authority
- fabricate capabilities
- modify generation or freshness state
- bypass explicit CSpace traversal
- infer authority from object identity alone

### 2.3 Capability lifetime

A capability remains usable only while:

- the underlying object remains fresh under generation rules
- the capability remains reachable in an authority-bearing container such as a CSpace or explicitly defined service-owned handle domain
- the capability has not been deleted, revoked, or invalidated by restart or teardown rules

Stale capabilities must fail deterministically.

Loss of an application-level reference is not itself a kernel authority event unless it is reflected in explicit capability deletion or service-owned handle teardown.

---

## 3. Memory model

## 3.1 User memory at the kernel boundary

The kernel treats all user memory as:

- untrusted
- requiring explicit validation
- subject to deterministic fault behavior

### 3.2 Copy-in and copy-out

Syscalls and kernel-mediated IPC interactions use:

- explicit copy-in
- explicit copy-out
- deterministic fault semantics

Programs and runtimes must not assume that passing a pointer implicitly shares authority or memory.

### 3.3 Address-space invariants

Programs must not assume:

- any kernel-side memory layout
- implicit shared memory
- stable object placement in memory
- pointer validity outside explicitly mapped user memory

Programs and runtimes must respect:

- alignment requirements
- mapping validity
- explicit shared-memory contracts where those exist

### 3.4 No implicit shared memory

Shared memory exists only when it is:

- explicitly created
- explicitly mapped
- explicitly delegated or shared through capability-mediated or service-defined mechanisms

---

## 4. Concurrency model

## 4.1 Threads

Threads are:

- explicit kernel objects
- created through explicit, authority-bearing operations
- scheduled by the kernel
- subject to blocking, abort, and wake rules defined in `SCHED.md`

### 4.2 Blocking

Blocking obeys:

- single-resolution rules
- deterministic wake semantics
- deterministic timeout semantics
- explicit abort behavior

### 4.3 Synchronization

Programs may use:

- purely userspace synchronization primitives
- kernel-mediated wait and wake through syscalls or service IPC
- shared memory where explicitly granted

Programs and runtimes may not rely on:

- undefined wake behavior
- hidden scheduler guarantees beyond the documented contract
- implicit memory ordering stronger than the architecture and explicit synchronization provide

### 4.4 No implicit concurrency authority

Creating threads, shared memory, or cross-process coordination authority must always be explicit.

Concurrency must not create ambient privilege.

---

## 5. IPC and service interaction

## 5.1 IPC is authority-bearing

IPC messages may carry:

- data
- capabilities
- transaction-specific reply state as defined by `IPC.md`
- service-specific payloads

IPC must not become an ambient discovery or authority channel.

### 5.2 No ambient service discovery

Programs discover and use services only through:

- initial capabilities
- explicit delegation
- explicit service-graph construction
- explicit service-owned handles derived from valid authority

### 5.3 Message invariants

IPC obeys:

- single-resolution semantics
- deterministic delivery behavior within the IPC contract
- deterministic failure behavior
- deterministic capability transfer semantics

### 5.4 Reply semantics

Replies must:

- be single-resolution
- use the explicit IPC transaction model defined by `IPC.md`
- not rely on ambient thread identity, ambient process identity, or hidden service state

Programs and runtimes must not invent a parallel reply model that bypasses the canonical IPC contract.

---

## 6. Program and service structure

## 6.1 Programs are capability-rooted

A program begins with:

- a root CSpace or equivalent explicit reachable authority graph
- an initial thread
- an initial address space
- an initial set of capabilities or explicit service-owned handles derived from those capabilities

### 6.2 No ambient filesystem

Programs interact with storage only through:

- VFS-rooted capabilities or service-owned handles
- service-mediated operations
- explicit delegation

### 6.3 No ambient network

Programs interact with the network only through:

- NET-rooted capabilities or service-owned handles
- service-mediated operations
- explicit delegation

### 6.4 No ambient device access

Programs interact with devices only through:

- DEVICE-rooted capabilities
- service-mediated operations
- explicit delegation

### 6.5 Services are part of the authority graph

Services are not ambient OS facilities.

They are explicit participants in the authority graph and must be reached through explicit capabilities, IPC endpoints, or delegated handles.

---

## 7. Runtimes and language bindings

## 7.1 Runtime obligations

Language runtimes, standard libraries, and frameworks must preserve:

- capability semantics
- CSpace semantics
- single-resolution semantics
- deterministic syscall and IPC boundary behavior
- non-ambient authority rules

### 7.2 Hidden implementation vs hidden authority

Runtimes may issue syscalls, IPC operations, or service calls as part of implementing documented abstractions.

They must not:

- create hidden authority paths
- introduce ambient privileges
- widen authority beyond explicit inputs
- silently change namespace membership
- create threads, CNodes, or shared-memory authority in ways that violate the published runtime contract

Implementation detail is permitted. Hidden authority is not.

### 7.3 Fault and pointer discipline

Runtimes must:

- preserve the kernel boundary’s explicit pointer and copy semantics
- not reinterpret faults in ways that hide security-relevant failure at the boundary
- validate inputs according to their own language/runtime contracts without weakening kernel-visible invariants

Kernel validation remains the kernel’s responsibility.

### 7.4 Service-facing bindings

Bindings for VFS, NET, DEVICE, and other services must reflect the real authority model of those services.

They must not present ambient success paths that do not exist in the underlying system.

---

## 8. Forbidden patterns

The following are specification violations:

- ambient authority
- implicit capability creation
- implicit capability widening
- implicit CNode creation when not explicitly part of the runtime contract and authority model
- implicit thread creation that introduces hidden authority or hidden namespace effects
- ambient filesystem access
- ambient network access
- ambient device access
- relying on PID, UID, label, or namespace identity as authority
- assuming global namespaces
- assuming global handle tables
- assuming ambient shared memory
- assuming ambient service discovery
- relying on undefined scheduler behavior
- creating a runtime abstraction that bypasses the underlying capability or IPC contract

Any such change is a violation, not an optimization.

---

## 9. Implementation checklist

Before merging any programming-model-related change:

### Authority

- does the change preserve capability semantics?
- does it avoid ambient authority?
- does it keep service access explicit?

### Memory

- does it preserve deterministic kernel-boundary fault behavior?
- does it avoid implicit shared memory or implicit pointer authority?

### Concurrency

- does it preserve single-resolution semantics?
- does it avoid hidden concurrency authority or hidden namespace effects?

### IPC

- does it preserve capability-bearing message semantics?
- does it avoid ambient service discovery?
- does it preserve the canonical reply model?

### Runtimes

- does the runtime preserve all authority and boundary invariants?
- does it avoid hidden privilege edges?
- are any implicit syscalls or service calls purely implementation detail rather than authority creation?

### Tests

- explicit authority propagation
- stale capability failure
- deterministic fault behavior
- IPC transfer correctness
- service discovery without ambient paths
- runtime behavior under restart and stale-handle conditions
- absence of hidden authority escalation

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 10. Ground-truth rule

This document is the ground truth for the Zuki programming model.

If code and this document disagree, the code is wrong.
