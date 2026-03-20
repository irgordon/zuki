# Zuki Runtime Model — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*, `PROGRAMMING-MODEL.md`, `CAPABILITIES.md`, `CSPACE.md`, `OBJECTS.md`, `SYSCALL.md`, `IPC.md`, `MM.md`, and `SCHED.md`  
**Scope:** Binding for all userspace runtimes, interpreters, JITs, VMs, garbage collectors, and language frameworks executing code on Zuki.

This document defines:

- the execution contract for runtimes
- memory and pointer-boundary rules
- capability handling rules
- concurrency and thread-management rules
- IPC and service-interaction rules
- JIT and code-generation rules
- GC and safepoint rules
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Runtime definition

A runtime is any userspace component that:

- executes developer-authored code
- manages memory on behalf of that code
- may create or coordinate threads
- may issue syscalls
- may perform IPC
- may manage capability-bearing values or service-owned handles
- may generate, interpret, or transform code

Examples include:

- C/C++ runtime and standard-library layers
- Rust runtime components
- Go runtime
- Java or .NET runtimes
- WASM engines
- JavaScript engines
- Python interpreters
- Lua VMs

A runtime is not privileged.

A runtime has no ambient authority.

A runtime is bound by the same capability and service-authority model as any other userspace program.

---

## 2. Runtime authority model

## 2.1 No ambient authority

A runtime may not:

- fabricate capabilities
- widen authority
- implicitly create authority-bearing CNodes
- implicitly create authority-bearing threads
- implicitly map authority-bearing memory regions
- implicitly open files, sockets, devices, or services
- implicitly discover services through ambient OS state

All authority must come from:

- initial capabilities
- explicit delegation
- explicit IPC
- explicit syscalls
- explicit service-owned handles derived lawfully from existing authority

### 2.2 Capability handling

A runtime may, subject to the capabilities it holds:

- store capabilities
- pass capabilities through IPC
- derive narrower capabilities
- insert, delete, or move capabilities in CNodes it controls

A runtime may not:

- widen rights
- modify generation or freshness state
- bypass CSpace traversal
- reinterpret arbitrary integers or pointers as kernel object authority

### 2.3 Capability lifetime

A runtime must:

- treat stale capabilities as invalid
- propagate capability-use failures deterministically
- not convert stale, denied, or revoked authority into ambient success through hidden fallback paths

A runtime may implement documented retry logic for higher-level operations, but retry must not weaken authority semantics or obscure deterministic failure at the kernel or service boundary.

---

## 3. Memory model for runtimes

## 3.1 User memory at the kernel boundary

Runtimes must treat all memory crossing the kernel boundary as subject to explicit kernel validation.

Runtimes must not assume that passing a pointer to the kernel implies:

- validity
- sharing
- pinning
- authority

### 3.2 Allocation

Runtimes may:

- allocate memory within their own address space
- manage heaps, arenas, pools, regions, and object spaces

Runtimes may not assume:

- contiguous virtual memory
- kernel overcommit behavior
- implicit paging semantics
- implicit shared memory
- stable address identity beyond their own mapping and GC contracts

### 3.3 Copy-in and copy-out discipline

Runtimes must prepare syscall and IPC arguments using explicit copy semantics consistent with the syscall or service contract.

Runtimes must:

- bound-check buffers according to their own API contracts
- handle partial-copy or fault outcomes deterministically
- propagate kernel-visible failure rather than masking it as ambient success

Kernel validation remains authoritative.

### 3.4 Memory mapping

Memory mapping requires:

- explicit authority
- explicit syscalls
- explicit rights
- explicit service or kernel contract

Runtimes may not implicitly map:

- files
- devices
- shared memory
- executable memory

### 3.5 No implicit shared memory

Shared memory exists only when it is:

- explicitly created
- explicitly mapped
- explicitly granted or delegated

A runtime must not create the appearance of ambient shared memory where none exists in the underlying authority graph.

---

## 4. Concurrency and thread model

## 4.1 Thread creation

Runtimes may create threads only through:

- explicit capability-bearing syscalls
- explicit developer request, or
- explicit runtime contract that is documented and does not introduce hidden authority or hidden namespace effects

Runtimes may not create threads in ways that silently widen authority.

### 4.2 Blocking and scheduling

Runtimes must obey:

- single-resolution blocking semantics
- deterministic wake semantics
- deterministic timeout semantics

Runtimes may not:

- spin indefinitely in kernel-visible ways when an explicit blocking primitive is required
- rely on undocumented scheduler fairness
- assume priority behavior beyond `SCHED.md`

### 4.3 Synchronization

Runtimes may use:

- userspace synchronization primitives
- kernel-mediated wait and wake syscalls
- shared memory where explicitly granted

Runtimes may not:

- rely on undefined memory ordering
- assume implicit fences
- assume hidden kernel-mediated locking or fairness guarantees

### 4.4 Hidden concurrency effects

Runtime-internal worker threads, GC threads, or scheduler threads are permitted only if:

- they are part of the documented runtime contract
- they do not create ambient authority
- they do not silently join namespaces or acquire services
- they preserve the same capability and IPC invariants as visible application threads

---

## 5. IPC and service interaction

## 5.1 IPC is explicit

Runtimes must:

- issue IPC only through explicit syscalls or service bindings
- treat IPC as authority-bearing
- propagate IPC failures deterministically

### 5.2 No ambient service discovery

Runtimes may not:

- scan for services through ambient OS mechanisms
- assume global service registries unless explicitly provided as a capability-scoped service
- assume ambient filesystem or network namespaces

### 5.3 Reply and completion semantics

Runtimes must follow the canonical IPC transaction and reply model defined by `IPC.md`.

Runtimes must not:

- invent a second ambient reply model
- rely on thread identity as authority for replies
- assume synchronous request/response behavior unless explicitly defined by the service contract

### 5.4 Capability-bearing messages

When a runtime transfers capabilities through IPC, it must preserve:

- explicit transfer intent
- deterministic failure behavior
- no authority amplification
- single-resolution completion semantics

---

## 6. JIT, interpreter, and code-generation rules

## 6.1 Executable memory

Executable memory requires:

- explicit allocation or mapping
- explicit rights
- explicit transition into executable state
- explicit runtime or developer opt-in where required by policy or runtime contract

Runtimes may not:

- implicitly allocate executable memory
- keep memory writable and executable simultaneously unless a narrower architecture- and policy-approved mechanism explicitly permits it
- implicitly JIT in a way that creates hidden authority or hidden MM behavior

### 6.2 W^X rule

Runtimes must preserve a write-xor-execute discipline unless a narrower exception is explicitly defined by the memory and security model.

A runtime must not rely on ambient permission changes to produce executable code.

### 6.3 JIT determinism

JIT engines must:

- produce deterministic code given the same inputs, configuration, and visible environment
- not depend on ambient system authority
- not emit code that violates architecture or ABI invariants

### 6.4 Interpreter determinism

Interpreters must:

- not introduce hidden nondeterministic authority behavior
- not mask kernel or service-boundary faults as ambient success
- not fabricate or widen authority

---

## 7. Garbage collection and safepoints

## 7.1 Safepoints

GC safepoints must:

- be explicit in the runtime design
- not block indefinitely
- not violate single-resolution semantics
- not assume special kernel cooperation beyond the documented scheduler, timer, and syscall contracts

### 7.2 GC behavior

GC must:

- not fabricate memory mappings
- not access unmapped memory intentionally
- not assume contiguous heaps
- not assume kernel paging behavior beyond explicit mapping semantics

### 7.3 GC and capability safety

GC must not:

- move capabilities in ways that violate CSpace or service-handle invariants
- duplicate capabilities implicitly
- delete or revoke authority-bearing state implicitly as a side effect of object movement or collection

Dropping a language-level reference is not itself an authority event unless the runtime explicitly performs the matching capability deletion or service-handle teardown.

### 7.4 Safepoint and thread interaction

GC and safepoints must not create hidden thread-state transitions that violate `SCHED.md` or the runtime’s documented thread model.

---

## 8. Runtime initialization

## 8.1 Initial state

A runtime begins with:

- an initial address space
- an initial thread
- a root CSpace or equivalent reachable authority graph
- an initial set of capabilities or explicit service-owned handles

### 8.2 No implicit bootstrap authority

A runtime may perform internal initialization of its own heaps, metadata, and scheduler structures.

A runtime may not perform authority-bearing OS actions such as:

- creating services
- creating authority-bearing CNodes
- creating authority-bearing threads
- mapping memory with new authority
- opening files
- opening sockets
- joining namespaces

unless explicitly instructed by the developer, the service graph, or the runtime’s documented contract under already-granted authority.

---

## 9. Forbidden patterns

The following are specification violations:

- ambient authority
- implicit capability creation
- implicit capability widening
- implicit authority-bearing CNode creation
- implicit authority-bearing thread creation outside the documented runtime contract
- implicit executable memory
- ambient filesystem access
- ambient network access
- ambient device access
- hidden authority-bearing syscalls
- hidden authority-bearing IPC
- relying on PID, UID, label, or namespace identity as authority
- assuming global namespaces
- assuming global handles
- assuming ambient shared memory
- assuming ambient service discovery
- masking kernel or service-boundary faults in ways that weaken security invariants
- violating single-resolution semantics

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any runtime-related change:

### Authority

- does the runtime preserve capability semantics?
- does it avoid ambient authority?
- does it avoid hidden authority creation or widening?

### Memory

- does it preserve deterministic kernel-boundary fault behavior?
- does it avoid implicit executable memory or unauthorized mapping effects?

### Concurrency

- does it preserve single-resolution semantics?
- does it avoid hidden authority-bearing thread or namespace effects?

### IPC

- does it preserve capability-bearing message semantics?
- does it avoid ambient service discovery?
- does it follow the canonical reply and completion model?

### JIT and interpreter behavior

- does it avoid implicit JIT authority?
- does it preserve determinism?
- does it preserve W^X or the explicitly defined exception model?

### GC

- does it preserve capability and handle safety?
- does it avoid implicit authority changes during collection or movement?

### Tests

- capability preservation and stale-capability failure
- deterministic fault behavior
- IPC transfer correctness
- runtime behavior under restart and stale-handle conditions
- hidden-thread and hidden-authority checks
- JIT executable-memory transitions
- GC capability/handle safety

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for the Zuki runtime model.

If code and this document disagree, the code is wrong.
