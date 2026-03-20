# Zuki Virtual Filesystem Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/services/vfs`, and any kernel or userspace code that performs path resolution, file I/O, mount operations, or interacts with VFS-backed capabilities.

This document defines:

- the VFS object model
- path-resolution semantics
- file descriptor and handle rules
- mount namespaces
- I/O operations and blocking semantics
- capability and authority boundaries
- integration with policy, IPC, scheduler, and RPS
- restart and failure semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. VFS model overview

Zuki’s VFS is:

- capability-rooted
- deterministic
- namespace-scoped
- policy-mediated
- service-implemented (not kernel-resident)
- restart-safe

The kernel does not implement filesystem semantics.

The kernel is responsible only for:

- capability validation
- memory safety
- IPC delivery
- enforcing object and scheduling invariants

The VFS service is responsible for:

- path resolution
- mount namespace management
- file I/O semantics
- directory traversal
- metadata operations
- backing store integration

---

## 2. VFS object model

VFS objects are **userspace-owned objects managed by the VFS service**.

They are not kernel objects and are not governed by OBJECTS.md.

The kernel observes them only through opaque capabilities.

### 2.1 Object types

- `OBJ_VNODE` — abstract filesystem node
- `OBJ_FILE` — open file handle
- `OBJ_DIR` — open directory handle
- `OBJ_MOUNT` — mount namespace root
- `OBJ_FDSPACE` — per-process file descriptor table

### 2.2 Lifetime model

The VFS service must enforce:

- reference-counted lifetime for all VFS objects
- no use-after-close
- no stale handle reuse without generation protection (service-defined)

The kernel does not manage VFS object lifetime.

---

## 3. Capability rights

Each VFS capability carries a rights mask:

- `RIGHT_READ`
- `RIGHT_WRITE`
- `RIGHT_EXEC`
- `RIGHT_STAT`
- `RIGHT_LIST`
- `RIGHT_OPEN`
- `RIGHT_MOUNT`
- `RIGHT_CREATE`
- `RIGHT_DELETE`

Rules:

- rights must be validated on every operation
- rights must not be amplified
- rights must be monotonic under derivation

---

## 4. Path resolution

### 4.1 Authority root

All path resolution is anchored to a **starting directory capability**.

There is no global root.

“/” exists only if represented by a capability.

### 4.2 Determinism rule

Path resolution must be:

- deterministic
- bounded
- free of ambient authority

### 4.3 Resolution algorithm

Given:

- starting directory capability
- path string
- mount namespace

Steps:

1. validate starting directory capability (RIGHT_LIST or stronger)
2. normalize path (collapse `.` and `..`)
3. for each component:
   - check mount redirection
   - resolve directory entry
   - validate traversal rights
4. return a resolved `OBJ_VNODE` capability or failure

### 4.4 Boundary rules

- traversal above the starting directory is forbidden
- no implicit global namespace access
- no implicit `$PWD`
- all traversal must remain within capability authority

### 4.5 Symlink rule

Symlink expansion:

- is not implicit
- must be explicitly requested by the caller
- must be mediated by policy
- must be bounded (no unbounded recursion)

---

## 5. File descriptors and FD spaces

### 5.1 FDSPACE model

Each process holds an `OBJ_FDSPACE` capability.

It maps:

```

fd → OBJ_FILE | OBJ_DIR

```

### 5.2 Invariants

- each FD refers to at most one object
- each object may be referenced by multiple FDs
- FD entries must be refcounted
- FD operations must be atomic

### 5.3 Operations

- `fd_open`
- `fd_close`
- `fd_dup`
- `fd_move`

All operations must:

- validate capability rights
- maintain refcount correctness
- be single-resolution

### 5.4 Concurrency rule

FDSPACE operations must be:

- serialized per FDSPACE
- safe under concurrent close/dup

### 5.5 Inheritance rule

FD inheritance is forbidden unless explicitly performed via:

- capability transfer
- policy-controlled spawn rules

---

## 6. Mount namespaces

### 6.1 Model

A mount namespace is represented by an `OBJ_MOUNT`.

It defines a mapping from directory nodes to mounted targets.

### 6.2 Invariants

- namespaces are capability-scoped
- namespaces are not globally visible
- no implicit sharing across processes

### 6.3 Operations

- `mount(parent_dir, target_vnode, flags)`
- `umount(target)`

Requirements:

- RIGHT_MOUNT on namespace
- RIGHT_LIST on parent
- RIGHT_OPEN on target

### 6.4 Isolation rule

- no cross-namespace access without capability transfer
- mount resolution must not escape namespace boundaries

---

## 7. I/O operations

### 7.1 General rules

All I/O operations:

- must validate rights
- may block
- must be abortable
- must be bounded

### 7.2 Read

Requires:

- RIGHT_READ
- valid OBJ_FILE

### 7.3 Write

Requires:

- RIGHT_WRITE

Must:

- respect file and filesystem limits

### 7.4 Metadata operations

- `stat` → RIGHT_STAT
- directory listing → RIGHT_LIST

### 7.5 Open

Requires:

- RIGHT_OPEN on directory
- RIGHT_CREATE if creating

### 7.6 Delete

Requires:

- RIGHT_DELETE

---

## 8. Blocking and scheduler integration

### 8.1 Blocking model

All blocking VFS operations must:

- use IPC to the VFS service
- place the thread in a scheduler-defined blocked state
- be abortable via scheduler or policy

### 8.2 Wake conditions

Threads must be woken on:

- I/O completion
- abort
- service failure
- timeout (if defined)

Blocking must obey SCHED.md invariants.

---

## 9. Integration with policy engine

All VFS operations are policy sites.

Policy may:

- allow
- deny
- redirect
- apply limits
- request capability adjustments (within authority)

Policy must not:

- fabricate capabilities
- bypass rights
- mutate kernel objects

---

## 10. Integration with RPS

Linux syscalls are translated via RPS.

RPS must:

- map Linux flags → VFS rights
- construct deterministic VFS operations
- not amplify authority
- not bypass capability validation

---

## 11. Restart and failure semantics

### 11.1 Service failure

If the VFS service fails:

- all in-flight operations must abort
- blocked threads must be woken
- operations must return deterministic failure (e.g., -EIO)

### 11.2 Restart

On restart:

- no stale handles may be reused
- FDSPACE entries referencing stale objects must fail on use
- new operations proceed with fresh state

### 11.3 Isolation guarantee

VFS failure must not:

- corrupt kernel state
- leak capabilities
- violate scheduler invariants

---

## 12. Forbidden patterns

The following are specification violations:

- ambient filesystem access
- implicit global root
- traversal outside capability root
- implicit symlink expansion
- FD inheritance without explicit transfer
- VFS fabricating capabilities
- kernel performing filesystem logic
- unbounded or non-deterministic resolution
- blocking without abortability
- cross-namespace leakage

Any such change is a violation, not an optimization.

---

## 13. Implementation checklist

Before merging any VFS change:

- are all operations capability-validated?
- is path resolution deterministic and bounded?
- are namespace boundaries enforced?
- are FD operations atomic and refcount-correct?
- are blocking operations abortable?
- are policy hooks present?
- are RPS mappings correct?
- are restart semantics safe?

Tests must include:

- path traversal edge cases
- namespace isolation
- FD duplication/closure races
- blocking I/O under load
- policy enforcement
- service restart behavior

---

## 14. Ground-truth rule

This document is the ground truth for the Zuki VFS subsystem.

If code and this document disagree, the code is wrong.
