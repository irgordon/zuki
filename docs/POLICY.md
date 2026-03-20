# Zuki Policy Engine & Refinement Script Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/services/policy`, `/kernel/policy`, and any kernel or userspace code that constructs policy snapshots, hosts refinement scripts, validates policy actions, or applies policy-driven decisions.

This document defines:

- the policy execution model
- the WASM sandbox contract
- the `PolicyCtx` interface and invariants
- action emission and application rules
- capability and object-lifetime boundaries
- conflict resolution and determinism
- restart and isolation semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Policy model overview

Zuki’s policy subsystem provides:

- deterministic refinement scripts
- sandboxed execution
- capability-mediated authority
- explicit, validated action application
- no ambient privilege
- restartable and isolated policy evaluation

Policy scripts do not run in the kernel.

They run in a WASM sandbox behind a strictly limited host interface. The kernel may participate in snapshot construction and action application where required by mechanism ownership, but policy interpretation itself is not a kernel privilege surface.

The system must remain correct even if a policy script or policy engine is:

- buggy
- malicious
- unavailable
- restarted
- slow or non-responsive

Policy execution must never compromise:

- capability invariants
- object lifetime
- scheduler correctness
- memory safety
- deterministic action application

---

## 2. Policy execution model

## 2.1 Trigger sources

A policy evaluation may be triggered by:

- a defined system event
- a user-initiated request
- a service-initiated governance event explicitly represented in the event model

A trigger source must be represented as a typed event. Vague or implicit trigger classes are forbidden.

### 2.2 Evaluation pipeline

The canonical evaluation pipeline is:

1. construct an immutable `PolicyCtx` snapshot for one event
2. invoke the WASM policy engine with that snapshot
3. execute the script deterministically
4. collect the emitted decision and action set
5. validate the decision and all actions
6. apply valid actions in canonical order
7. resolve the evaluation exactly once

### 2.3 Determinism rule

Given:

- the same `PolicyCtx`
- the same script binary
- the same event type
- the same policy-engine version and host contract

the policy engine must produce the same result and the same action sequence.

Non-deterministic behavior is forbidden.

### 2.4 Transaction rule

Each policy evaluation is one transaction.

A transaction has:

- one immutable `PolicyCtx`
- one script version identity
- one emitted result
- one validated action set
- one terminal resolution

Partial cross-transaction reuse is forbidden.

---

## 3. WASM sandbox contract

## 3.1 Execution environment

Policy scripts run in a WASM runtime with:

- no filesystem
- no network
- no timers
- no host thread creation
- no shared memory
- no host pointers
- no direct kernel-object access

### 3.2 Host interface

The sandbox exposes only the following host functions in v1.0:

- `policy_read(ctx_key)`
- `policy_emit(action)`
- `policy_log(message)` optional and bounded

No other host functions are permitted.

### 3.3 Host interface constraints

- `policy_read` is read-only and must not mutate engine or kernel state
- `policy_emit` appends a candidate action into the evaluation-local action buffer
- `policy_log` is observational only and must not affect policy outcome or enforcement

### 3.4 Resource limits

The sandbox must enforce deterministic limits for:

- instruction count
- linear memory size
- stack depth
- action count
- log volume if logging is enabled

Exceeding any limit results in deterministic evaluation failure.

### 3.5 Failure behavior

If the script:

- traps
- exceeds limits
- violates type rules
- emits malformed actions
- emits more than one terminal decision

then:

- the evaluation fails deterministically
- no actions are applied
- subsystem-specific fallback behavior is used

The fallback behavior must be defined by the calling policy site. It must not be left implicit.

---

## 4. PolicyCtx interface

## 4.1 Definition

`PolicyCtx` is a read-only, bounded snapshot of system state relevant to one policy decision.

It may contain:

- event metadata
- capability metadata
- object metadata
- thread metadata
- address-space metadata
- subsystem-specific bounded fields explicitly defined by the calling site

### 4.2 Invariants

- `PolicyCtx` is immutable once constructed
- `PolicyCtx` contains no raw pointers
- `PolicyCtx` contains only serializable, bounded data
- `PolicyCtx` exposes no kernel-internal memory layout
- `PolicyCtx` exposes no object identity beyond allowed metadata such as `ObjectID`, generation, type, and bounded policy-visible attributes

### 4.3 Lifetime

`PolicyCtx` is valid only for the lifetime of its evaluation transaction.

It must not be:

- retained by the script
- reused across evaluations
- mutated by host or guest after execution begins

### 4.4 Completeness rule

For any policy site, the fields required to make a valid deterministic decision must be fully present before script execution begins.

Lazy expansion of `PolicyCtx` during execution is forbidden in v1.0.

---

## 5. Result and action model

## 5.1 Terminal decision

Each evaluation must produce exactly one terminal decision:

- `POLICY_ALLOW`
- `POLICY_DENY`
- `POLICY_REDIRECT`
- `POLICY_FAILURE`

This terminal decision is distinct from ordinary emitted actions.

### 5.2 Action types

The v1.0 action set is:

- `ACTION_LOG`
- `ACTION_CAP_GRANT`
- `ACTION_CAP_REVOKE`
- `ACTION_LIMIT`
- `ACTION_REDIRECT_TARGET`

`ACTION_ALLOW` and `ACTION_DENY` are not ordinary actions. They are terminal decisions.

### 5.3 Action invariants

Each action must:

- be well-typed
- be fully bounded
- reference only valid policy-visible identifiers
- not fabricate capabilities
- not exceed authority granted to the policy application site
- not violate capability, object, scheduler, IPC, or memory invariants

### 5.4 Canonical action order

If the terminal decision permits action application, actions are applied in the following order:

1. `ACTION_LIMIT`
2. `ACTION_CAP_REVOKE`
3. `ACTION_CAP_GRANT`
4. `ACTION_REDIRECT_TARGET`
5. `ACTION_LOG`

This ensures:

- limiting occurs before privilege changes where relevant
- revocation precedes grant
- redirect targets are finalized after capability changes
- logging is last and non-authoritative

### 5.5 Single-resolution rule

A policy evaluation resolves exactly once as one of:

- allow
- deny
- redirect
- failure

Double resolution is forbidden.

---

## 6. Capability and object-lifetime boundaries

## 6.1 Script limitations

Policy scripts cannot:

- mint capabilities directly
- revoke capabilities directly
- modify kernel objects directly
- mutate page tables
- schedule threads
- access kernel memory
- bypass capability validation

### 6.2 Validation rule

All policy-emitted actions must be validated by the responsible host subsystem before application.

Validation must enforce:

- capability authority
- generation-based safety
- refcount correctness
- retire/reclaim invariants
- no authority amplification

### 6.3 Policy-owned authority

Capability-changing actions are permitted only through explicit policy-owned authority established outside the script.

This authority must be represented as:

- a designated policy-managed CNode or capability set, or
- another explicit, bounded capability-management domain defined by the host subsystem

The script itself does not own or fabricate authority.

### 6.4 Capability grant and revoke actions

`ACTION_CAP_GRANT` and `ACTION_CAP_REVOKE` must:

- operate only within explicitly authorized capability domains
- use the same mint and destroy semantics as `CAPABILITIES.md`
- be serialized with other capability operations
- remain safe under concurrent revoke, retire, and reclaim

---

## 7. Conflict resolution

## 7.1 Terminal decision precedence

Decision precedence is:

1. `POLICY_FAILURE`
2. `POLICY_DENY`
3. `POLICY_REDIRECT`
4. `POLICY_ALLOW`

If multiple terminal decisions are emitted or implied, the evaluation fails.

### 7.2 Action conflicts

If conflicting actions are emitted within one evaluation:

- revoke overrides grant for the same target
- a redirect target is invalid if the terminal decision is not `POLICY_REDIRECT`
- actions incompatible with a deny decision are discarded because no action application occurs on deny unless the calling site explicitly permits non-enforcement side effects such as logging
- malformed or contradictory action sets cause deterministic failure unless a narrower rule is explicitly defined for that action class

### 7.3 Malformed action sequences

Malformed sequences result in:

- deterministic failure
- no authoritative actions applied
- fallback behavior chosen by the policy site

---

## 8. Fallback, restart, and isolation semantics

## 8.1 Fallback rule

On evaluation failure, the system must follow the fallback policy defined by the invoking site.

Examples may include:

- fail closed
- fail open
- deny but continue system execution
- continue with no policy-derived refinement

Fallback must be explicit per site. Implicit default behavior is forbidden.

### 8.2 Policy engine restart

If the policy engine crashes or is restarted:

- all pending evaluations fail immediately
- no caller may remain blocked indefinitely
- no stale `PolicyCtx` may be reused
- no stale action buffer may be applied

### 8.3 Hot reload

If policy scripts are updated:

- new evaluations use the new script identity
- in-flight evaluations begun under the old script fail deterministically
- no decision or action produced under the old script may be applied after reload invalidates that evaluation
- no cross-script mutable state is preserved in v1.0

### 8.4 Isolation guarantee

Policy engine failure must not:

- corrupt kernel state
- leak capabilities
- violate scheduler invariants
- violate memory safety
- leave threads permanently blocked

---

## 9. Concurrency and ordering rules

## 9.1 Per-event ordering

Each event triggers at most one policy evaluation transaction.

Evaluations for the same event must not overlap.

### 9.2 Cross-event concurrency

No ordering is guaranteed across unrelated events unless the invoking subsystem explicitly defines one.

Concurrent evaluation across different events is permitted only if:

- each evaluation has isolated snapshot, action buffer, and result state
- action application remains serialized where subsystem invariants require serialization

### 9.3 Kernel and host ordering guarantees

The responsible host must:

- construct `PolicyCtx` before script execution
- freeze the script identity for that evaluation
- apply no authoritative action before evaluation completion
- apply validated actions only in canonical order
- reject stale or mismatched actions

### 9.4 Forbidden shortcuts

The following are forbidden:

- applying actions before script completion
- applying actions out of canonical order
- retaining `PolicyCtx` beyond evaluation
- mutating `PolicyCtx` after execution begins
- applying actions from an evaluation invalidated by crash, restart, or hot reload

---

## 10. Logging semantics

### 10.1 `policy_log`

`policy_log(message)` is optional in v1.0.

If implemented:

- message size must be bounded
- message count must be bounded by the evaluation resource limits
- logs are observational only
- logging failure must not affect enforcement outcome except by triggering evaluation failure if the runtime contract defines logging as part of the bounded execution path

### 10.2 Non-authoritative rule

Policy logs must not be used as an enforcement channel.

Logging is telemetry, not authority.

---

## 11. Forbidden patterns

The following are specification violations:

- policy scripts accessing kernel memory
- policy scripts fabricating capabilities
- applying actions without validation
- implicit fallback behavior
- unbounded policy execution
- nondeterministic policy behavior
- retaining `PolicyCtx` or transient memory windows beyond evaluation
- exposing raw pointers to policy scripts
- scripts modifying object lifetime directly
- scripts bypassing capability checks
- applying stale actions after restart or hot reload

Any such change is a violation, not an optimization.

---

## 12. Implementation checklist

Before merging any change touching `/services/policy` or `/kernel/policy`:

- is `PolicyCtx` complete, immutable, bounded, and pointer-free?
- is fallback behavior explicit for each policy site?
- are terminal decisions single-resolution and validated?
- are actions validated before application?
- are capability operations consistent with `CAPABILITIES.md`?
- are object-lifetime rules consistent with `OBJECTS.md`?
- are IPC redirect actions consistent with `IPC.md`?
- are scheduler interactions consistent with `SCHED.md`?
- are memory-related actions consistent with `MM.md`?
- are scripts sandboxed with strict deterministic limits?
- are tests present for:
  - malformed scripts
  - multi-decision failure
  - conflicting actions
  - capability grant/revoke correctness
  - redirect correctness
  - policy-engine crash
  - hot reload invalidation
  - deterministic replay
  - bounded logging
  - stale action rejection

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 13. Ground-truth rule

This document is the ground truth for policy execution in Zuki.

If code and this document disagree, the code is wrong.
