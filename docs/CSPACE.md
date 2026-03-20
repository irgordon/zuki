# Zuki Capability Space (CSPACE) — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*, `CAPABILITIES.md`, `OBJECTS.md`, and `SYSCALL.md`  
**Scope:** Binding for all code under `/kernel/cspace`, `/kernel/sys`, `/kernel/ipc`, and any userspace component that constructs, manipulates, transfers, or delegates capabilities.

This document defines:

- the structure and semantics of capability spaces (CSpaces)
- CNode object semantics
- slot semantics
- addressing model
- derivation and authority narrowing
- revocation and freshness
- traversal rules
- cross-subsystem invariants
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. CSpace model overview

A Zuki CSpace is:

- a hierarchical graph of CNodes addressed by explicit slot traversal
- composed of fixed-size capability slots
- addressed by explicit index paths
- deterministic and restart-safe
- non-ambient and non-implicit
- generation-protected
- capability-rooted

A CSpace is not:

- a flat handle table
- a namespace
- a privilege domain
- a process identity
- a source of ambient authority

A CSpace is the explicit structural representation of reachable authority for a process, service, or other authority-bearing domain.

Ownership of a CSpace is external to the CSpace itself. The CSpace is not identity.

---

## 2. CNode object model

## 2.1 CNode definition

A CNode is a kernel object with:

- a fixed number of slots (`CSPACE_CNODE_SLOTS`, constant per build or per object class as explicitly defined)
- each slot containing either:
  - one capability, or
  - the empty value

CNodes are kernel objects and must be referenced via capabilities.

### 2.2 Slot invariants

Each slot:

- contains at most one capability
- is typed only by the capability it contains
- has no ambient metadata
- has no implicit authority
- has no inheritance semantics

Slot contents must always be explicit and deterministic.

### 2.3 CNode invariants

A CNode must:

- have a stable `object_id`
- have a stable generation
- have a stable slot count
- never implicitly grow or shrink
- never implicitly allocate or free slots

CNodes are immutable in shape.

Slot contents may change only through explicit capability operations authorized by the capability model.

---

## 3. Addressing model

## 3.1 Path-based addressing

Capabilities are addressed by explicit path traversal:

```text
root CNode → slot[i] → child CNode → slot[j] → … → final slot
````

Each index is:

* a fixed-width integer
* interpreted only as a slot index
* not a handle
* not a name
* not a namespace key

### 3.2 No ambient lookup

The kernel must not:

* search for capabilities
* perform wildcard lookup
* perform prefix lookup
* perform name-based lookup
* infer a path from object identity or service context

All traversal is explicit.

### 3.3 Addressing invariants

Addressing must be:

* deterministic
* restart-safe
* explicit at every step
* generation-checked at every capability dereference

If any step fails, the entire lookup fails.

---

## 4. Slot operations: insertion, deletion, and movement

## 4.1 Insertion

A capability may be inserted into a slot only if:

* the caller holds authority to modify the target CNode
* the target slot is empty
* the capability being inserted is valid and fresh

Insertion must not:

* implicitly overwrite an existing slot
* implicitly upgrade rights
* implicitly derive a narrower or wider capability
* implicitly create the target CNode

### 4.2 Deletion

Deleting a capability from a slot:

* removes that slot’s capability
* does not affect other slots
* does not affect the underlying object directly
* does not affect other capabilities to the same object except through ordinary object-lifetime effects

Deletion must not implicitly revoke authority elsewhere.

### 4.3 Movement

Movement is logically:

* remove from one slot
* insert into another slot

Movement must be atomic with respect to CSpace observers and must preserve refcount correctness.

Movement must not widen authority.

---

## 5. Derivation and authority narrowing

## 5.1 Derivation rule

A capability may be derived only if:

* the caller holds a capability with derivation authority
* the derivation operation narrows authority
* the resulting capability has:

  * the same `object_id`
  * the same `gen_at_mint`
  * a strict or equal subset of rights as permitted by the derivation contract

### 5.2 No authority amplification

Derivation must not:

* widen rights
* change object identity
* change freshness generation
* create new authority ex nihilo

### 5.3 Derivation invariants

Derived capabilities must be:

* deterministic
* non-amplifying
* restart-safe
* valid only under the same generation-based freshness rules as any other capability

Derivation remains subordinate to `CAPABILITIES.md`.

---

## 6. Revocation and freshness

## 6.1 Generation-based freshness

Every capability contains:

* `object_id`
* `gen_at_mint`
* `rights`

Freshness is enforced by comparing `gen_at_mint` to the object’s current generation.

### 6.2 Revocation rule

Revocation is:

* generation increment on the object
* not subtree walking
* not slot scanning
* not CSpace traversal

Revocation must be:

* O(1)
* deterministic
* restart-safe

### 6.3 Stale capability rejection

Any capability whose `gen_at_mint` does not match the object’s current generation must be rejected by:

* `cap_use()`
* all capability-bearing syscalls
* all service operations that consume capabilities

Stale capabilities must not bind to new authority.

### 6.4 CSpace shape vs revocation

The hierarchical structure of a CSpace is an addressing and delegation structure, not a revocation tree.

No implementation may infer subtree-walking revocation semantics from CSpace hierarchy.

---

## 7. Traversal rules

## 7.1 Explicit traversal

Traversal from one CNode to another must:

* use explicit slot indices
* validate the slot contents at each step
* validate freshness at each step
* validate that the intermediate capability authorizes traversal to a child CNode

### 7.2 Traversal authority

An intermediate capability used for traversal must:

* designate a CNode object
* be fresh
* carry the rights required for traversal and, where applicable, mutation or derivation at the destination

Traversal rights must be defined consistently with the capability rights model. They must never be ambient.

### 7.3 No implicit traversal

The kernel must not:

* follow chains automatically
* infer traversal paths
* perform recursive lookup without an explicit path
* continue traversal after a failed step

### 7.4 Traversal failure

Traversal fails if:

* any slot is empty
* any intermediate capability is stale
* any intermediate capability is not a CNode capability
* any intermediate capability lacks the required traversal or modification rights
* any addressed CNode is invalid

Traversal failure must be deterministic.

---

## 8. Cross-subsystem integration

CSPACE must obey:

* `CAPABILITIES.md` for capability semantics
* `OBJECTS.md` for object invariants
* `SYSCALL.md` for capability-bearing syscalls
* `SECURITY.md` for global invariants
* `INIT.md` for bootstrap CSpace construction
* `IPC.md` for capability transfer
* `MM.md` for user-memory validation where CSpace paths are passed through syscall interfaces
* `DEVICE.md` for device capability boundaries
* `NET.md` for NIC and network-related capability boundaries

Timers are not capability objects in canonical v1.0 and therefore are not part of CSPACE semantics unless a later document explicitly introduces timer capabilities.

CSPACE is the structural substrate that binds authority distribution together.

---

## 9. Forbidden patterns

The following are specification violations:

* flat ambient handle tables used as authority in place of CSpace traversal
* ambient lookup
* implicit traversal
* implicit authority inheritance
* capability amplification
* stale capability acceptance
* subtree-walking revocation
* slot overwriting without explicit deletion or defined atomic replace semantics
* CNode resizing
* implicit CNode creation
* implicit CNode destruction
* using slot indices as names or identities
* treating CSpace as a namespace
* inferring revocation semantics from CSpace hierarchy

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any CSpace-related change:

### Structure

* are CNodes fixed-size and immutable in shape?
* are slot semantics explicit and deterministic?

### Addressing

* is traversal explicit and index-based?
* are all traversal steps validated?
* are traversal rights defined and enforced explicitly?

### Derivation

* does derivation strictly narrow authority?
* are `object_id` and generation preserved correctly?

### Revocation

* is revocation O(1) via generation increment?
* are stale capabilities rejected everywhere?
* does no code path perform subtree-walking revocation?

### Security

* is no ambient authority introduced?
* are no implicit privileges created?
* is CSpace hierarchy kept distinct from revocation semantics?

### Tests

* traversal correctness
* traversal-right rejection
* stale capability rejection
* derivation correctness
* revocation correctness
* slot insertion, deletion, and movement correctness
* restart safety

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for Zuki’s capability-space model.

If code and this document disagree, the code is wrong.
