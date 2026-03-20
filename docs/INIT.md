# Zuki Initialization & Service Graph — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/init`, `/services/init`, and any subsystem that participates in userspace bring-up, service construction, capability distribution, or initial namespace creation.

This document defines:

- the trusted initialization sequence
- the initial capability graph
- service graph construction
- namespace and authority bootstrapping
- restart and recovery semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Initialization model overview

Zuki’s initialization model is:

- capability-rooted
- deterministic
- minimal and explicit
- restart-safe
- non-ambient
- policy-visible

The kernel constructs only the minimal trusted bootstrap root:

- initial address space
- initial thread
- root CNode
- initial capabilities required to start the init service

Everything else, including VFS, NET, DEVICE drivers, RPS, policy engine, and user sessions, is constructed by userspace through explicit capability-mediated operations.

There is:

- no ambient global environment
- no implicit privilege
- no default namespace membership

Initialization is the explicit construction of the initial userspace authority graph. It is not a privileged escape hatch.

---

## 2. Trusted root and kernel handoff

### 2.1 Kernel responsibilities

The kernel is responsible for:

- constructing the minimal object graph defined in `BOOT.md`
- publishing the root CNode and initial capabilities
- creating and starting the init service in its own address space
- transferring execution to scheduler-governed userspace bring-up

### 2.2 Kernel responsibilities end at handoff

After handoff to init, the kernel does not:

- create additional high-level services
- populate namespaces
- fabricate new high-level authority
- assign identity, labels, or roles as authority
- bypass capability or policy rules on behalf of init

### 2.3 Handoff invariant

At the moment of handoff:

- init must have only explicitly granted capabilities
- all kernel bootstrap invariants must already hold
- no later service may assume authority not present in the handed-off graph

---

## 3. Init service trust model

### 3.1 Init trust level

The init service is:

- trusted to bootstrap the initial service graph
- not trusted to bypass capability rules
- not trusted to bypass policy rules
- restartable only under controlled conditions

Init is not a superuser.

Init is only the first userspace principal, holding a specific bounded capability set.

### 3.2 No implicit init privilege

Init must not receive authority merely because it is “init.”

Every operation performed by init must succeed only because init holds:

- the required explicit capabilities, and
- any required policy authorization

Any behavior that treats init as ambiently privileged is a specification violation.

---

## 4. Initial capability graph

### 4.1 Capabilities granted to init

Init receives only the capabilities necessary to bootstrap the system, such as:

- a capability to its own address space
- a capability to its root CNode
- capabilities to essential kernel interfaces, including IPC, timers, and memory-management entry points as defined by subsystem contracts
- capabilities to device-enumeration or device-publication interfaces where boot design requires them
- capability authority to spawn new processes or construct new address spaces, where defined by the process model

The exact minimal set is architecture- and build-specific, but it must remain explicit, bounded, and auditable.

### 4.2 Capabilities not granted to init

Init must not receive:

- wildcard filesystem access
- wildcard network access
- wildcard device access
- ambient namespace membership
- implicit administrator authority of any kind

### 4.3 Explicit construction rule

All authority beyond the initial graph must be constructed explicitly through:

- capability derivation
- policy-mediated grants
- namespace creation under explicit authority
- service-defined object construction

No implicit authority exists.

---

## 5. Service graph construction

### 5.1 Explicit graph construction

Init is responsible for explicitly constructing the initial service graph, including:

- launching core services such as VFS, NET, DEVICE, POLICY, and RPS
- constructing initial namespaces
- distributing capabilities to services
- establishing dependency relationships between services

The service graph is an explicit capability graph, not an ambient startup list.

### 5.2 Service isolation

Each service:

- runs in its own address space unless a narrower design explicitly defines otherwise
- receives only the capabilities it needs
- must not infer or assume ambient authority
- must not access other services except through explicit IPC endpoints or transferred capabilities

### 5.3 Capability distribution

Init must:

- distribute capabilities explicitly
- never widen rights beyond what is required
- give each service only the minimum authority needed for its role
- ensure distribution is deterministic and auditable

### 5.4 Dependency rule

A service may depend on another service only through explicit, reconstructible authority edges.

Hidden side dependencies, ambient startup assumptions, or undocumented ordering dependencies are forbidden.

---

## 6. Namespace bootstrapping

### 6.1 No ambient namespaces

There is no ambient filesystem root, ambient network namespace, or ambient device namespace.

If an initial namespace exists, it exists only because init explicitly created it or was explicitly granted authority to reference it.

### 6.2 Namespace creation

Init may create:

- the initial filesystem namespace
- the initial network namespace
- the initial device namespace

but only if it holds the explicit authority required by the responsible subsystem.

Namespace creation authority is not implied by being init.

### 6.3 Namespace authority

Namespace creation and membership must be:

- explicit
- capability-scoped
- policy-visible
- non-ambient

Init may bootstrap namespaces, but cannot create ambient access to them.

### 6.4 Identity and policy bootstrapping

Init may:

- create initial identity metadata
- configure the policy engine
- establish initial policy rules

Identity remains metadata only. Authority still flows through capabilities.

---

## 7. Process creation and lifecycle

### 7.1 Spawn semantics

Init spawns processes using:

- explicit capability transfer
- explicit namespace membership
- explicit policy context where required

No process inherits ambient authority.

### 7.2 Process lifetime

Processes:

- may be restarted
- may be replaced
- must not retain stale capabilities across restart
- must not receive capabilities implicitly from init or any other service

### 7.3 Service restart

Restart of a service must:

- revoke or invalidate stale capabilities and handles according to subsystem rules
- rebuild service-owned state explicitly
- reject stale timers, queue entries, handles, and replies
- rejoin namespaces explicitly if namespace membership is still intended

Restart must not silently preserve authority.

---

## 8. Policy integration

### 8.1 Init is subject to policy

Init is not exempt from policy.

Where policy is defined as part of a bootstrap call path, policy may:

- deny
- narrow
- redirect

Policy must not amplify authority.

### 8.2 Policy bootstrapping

Init may configure the policy engine, but init:

- cannot bypass it where policy is required
- cannot grant itself new authority outside explicit capability rules
- cannot create an ambient root role through policy metadata

### 8.3 Determinism and boundedness

Policy used during initialization must remain:

- deterministic
- bounded
- restart-safe
- non-ambient

Bootstrap must not depend on unbounded policy execution.

---

## 9. Restart and recovery semantics

### 9.1 Init failure

If init fails, the system must enter a controlled recovery path.

A controlled recovery path means:

- the kernel does not grant new authority
- recovery occurs only through explicitly defined restart authority
- stale init-owned state is rejected
- no ambient privilege is introduced during recovery

### 9.2 Init restart

If init is restarted, it must receive only the capability set explicitly defined by the restart contract.

That set must not exceed the bounded authority originally intended for init after boot, unless a separate, explicitly defined recovery contract says otherwise.

Restart must not silently widen authority.

### 9.3 Service restart

Restart of any service must:

- not leak authority
- not preserve stale state
- not create new ambient access paths
- require explicit reconstruction of all authority

### 9.4 Dynamic change

Dynamic changes, including:

- device hotplug
- namespace creation
- policy updates
- service replacement

must:

- not implicitly grant authority
- not bypass capability validation
- not create ambient visibility
- publish new authority only through explicit capability-scoped construction

---

## 10. Forbidden patterns

The following are specification violations:

- ambient authority during initialization
- implicit privilege for init or any service
- default global namespaces
- identity-based privilege without capability mediation
- service startup that bypasses policy where policy is required
- implicit capability inheritance
- restart behavior that preserves or widens authority without explicit reconstruction
- cross-service shortcuts that bypass IPC or capability checks
- kernel-resident service semantics beyond the minimal bootstrap role
- hidden startup dependencies that are not expressed through explicit capability edges

Any such change is a violation, not an optimization.

---

## 11. Implementation checklist

Before merging any change touching initialization or service bring-up:

### Authority

- is every capability grant explicit?
- does init receive only bounded minimal authority?
- is every newly created authority capability-scoped and auditable?

### Isolation

- are services isolated by address-space and capability boundaries?
- is namespace creation explicit and non-ambient?
- are service dependencies explicit rather than ambient?

### Policy

- is policy consulted where required?
- can policy only narrow or deny authority at this stage?
- is bootstrap policy bounded and deterministic?

### Restart

- are stale generations rejected?
- does restart require explicit reconstruction of authority?
- can recovery occur without widening authority?

### Failure behavior

- does init failure fail closed into a controlled recovery path?
- are service failures contained?
- are no new ambient authorities introduced during recovery?

### Tests

- capability distribution correctness
- namespace bootstrapping
- service graph dependency correctness
- service restart with stale-handle rejection
- policy enforcement during initialization
- hotplug authority correctness
- init restart without authority widening

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 12. Ground-truth rule

This document is the ground truth for initialization and service graph semantics in Zuki.

If code and this document disagree, the code is wrong.
