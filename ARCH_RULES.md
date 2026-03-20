# ARCH_RULES.md — Architectural Guardrails (Canonical)

Status: Binding  
Scope: All code in this repository  
Authority: Subordinate to docs/SYSTEM.md and docs/INVARIANTS.md  
Purpose: Prevent architectural drift during implementation and agent-assisted development.

These rules are enforceable.  
Violations are defects, not optimization opportunities.

---

# 1. Core Architectural Laws

## 1.1 No Ambient Authority

Authority must be explicit.

Code must not:

- search filesystem paths implicitly
- rely on environment variables for authority
- infer authority from identity
- use global discovery mechanisms
- auto-connect to services

All authority must originate from:

- explicit startup configuration
- explicit delegation
- explicit IPC transfer
- explicit capability derivation

---

## 1.2 Deterministic Boundary Behavior

All execution units must:

- produce exactly one terminal result
- be restart-safe
- have explicit failure boundaries
- avoid hidden side effects

Allowed terminal results:

- success
- failure
- timeout
- abort

Multiple terminal results are prohibited.

---

## 1.3 Explicit Resolution Only

Resolution must be:

- deterministic
- single-step
- scope-bounded

Code must not:

- perform implicit lookup
- perform recursive search
- fall back to alternate resolution paths
- infer behavior from naming patterns

---

## 1.4 No Hidden Concurrency

Concurrency must be explicit.

Code must not:

- spawn threads implicitly
- create background work without caller control
- retry operations silently
- perform implicit scheduling

All concurrency must be visible in control flow.

---

## 1.5 No Global Mutable Authority State

Global mutable authority is prohibited.

Forbidden patterns:

- global capability registries
- implicit singletons with authority
- static mutable service handles
- hidden shared state

Immutable configuration is permitted.

---

# 2. Layering Rules

The system is strictly layered.

```

Shell
Runtime
Kernel Contracts
Platform / OS

```

Lower layers must not depend on higher layers.

---

## 2.1 Allowed Dependencies

Shell may depend on:

- runtime interfaces
- AST structures
- validation utilities

Runtime may depend on:

- contracts
- scheduler interfaces
- capability interfaces

Contracts must not depend on runtime or shell.

---

## 2.2 Forbidden Dependencies

Code must not:

- import upward in the layer hierarchy
- bypass contract interfaces
- call private runtime internals
- access kernel state directly

---

# 3. Capability Safety Rules

Capabilities must be:

- immutable
- unforgeable
- validated on use
- explicitly transferred

Code must not:

- fabricate capability objects
- widen capability rights
- bypass generation checks
- store raw pointers as capability identity

---

# 4. Pipeline Safety Rules

Pipelines must:

- preserve command order
- enforce bounded buffers
- propagate failure deterministically

Pipelines must not:

- reorder stages
- drop results silently
- retry implicitly
- allocate unbounded memory

---

# 5. Restart Safety Rules

Restart must not:

- duplicate completed operations
- resurrect stale tasks
- widen authority
- reuse invalid handles

Incomplete operations must fail deterministically.

---

# 6. Forbidden Implementation Patterns

The following patterns are prohibited:

- PATH-style executable lookup
- PID-based job control
- implicit retry loops
- unbounded queues
- hidden fallback logic
- silent error suppression
- implicit resource creation
- implicit capability discovery

---

# 7. Code Review Gate

A change must be rejected if any answer is:

- no
- unknown
- hand-waved

Required checks:

- execution remains deterministic
- authority remains explicit
- restart behavior remains safe
- dependencies remain layered
- buffers remain bounded

---

# 8. Enforcement

These rules are enforced through:

- static validation
- automated tests
- CI verification
- agent task constraints

No exception process exists.

---

# End of ARCH_RULES.md
