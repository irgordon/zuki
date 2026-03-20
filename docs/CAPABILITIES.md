# Zuki Kernel Capability Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** This document is binding for all code under `/kernel/cap` and any kernel code that manipulates capabilities, object metadata, or object lifetime.

This document defines the concrete invariants, access patterns, and lifecycle rules for Zuki’s capability subsystem.

Code in `/kernel/cap` must be written top-down, readable, and structurally obvious. Live code should remain comment-minimal. This document carries the explanatory burden.

---

## 1. Core model

Zuki’s capability subsystem enforces four non-negotiable properties:

1. A capability is valid if and only if its minted generation matches the current object generation.
2. Revocation is constant-time and performed only by generation increment.
3. No object slot may be reused until retire/reclaim conditions are satisfied.
4. All object access must pass through `cap_use()`.

No optimization may weaken these properties.

---

## 2. Core data structures

All capability and object access must go through these structures and their invariants.

### 2.1 Constants and sentinel values

```c
typedef uint32_t ObjectID;
typedef uint32_t Rights;
typedef uint64_t CapabilityID;

enum {
    OBJECT_ID_INVALID = UINT32_MAX
};
