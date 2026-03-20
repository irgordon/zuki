# Zuki Network Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/services/net`, `/services/dev`, `/kernel/dev`, `/kernel/ipc`, and any userspace component that interacts with NICs, packet queues, DMA windows, IRQ endpoints, socket capabilities, or network namespaces.

This document defines:

- the network capability model
- NIC access and driver isolation
- socket and protocol semantics (userspace-owned)
- network namespaces
- packet I/O queues
- DMA and memory-safety rules
- routing and addressing
- integration with timers, scheduler, IPC, and policy
- restart and failure semantics
- forbidden patterns
- implementation checklist

If code and this document disagree, the code is wrong.

---

## 1. Network model overview

Zuki’s network subsystem is:

- capability-rooted
- namespace-scoped
- driver-isolated
- restart-safe
- deterministic
- policy-mediated
- userspace-implemented for protocol and socket semantics

The kernel does not implement:

- TCP
- UDP
- QUIC
- routing tables
- socket state machines
- firewall rules
- NAT state
- connection tracking

These are implemented by the network service, which is:

- untrusted
- restartable
- capability-scoped
- sandboxed

The kernel provides only:

- NIC device capabilities
- DMA windows
- packet I/O queues
- IRQ delivery
- memory safety
- capability validation

No ambient network authority exists.

---

## 2. Network object model

## 2.1 Kernel-owned network objects

The following are kernel objects governed by `OBJECTS.md`:

- `OBJ_NIC` — abstract network interface
- `OBJ_NET_DMA_WINDOW` — DMA region for NIC access
- `OBJ_NET_QUEUE` — packet I/O queue
- `OBJ_NET_IRQ` — interrupt endpoint

These objects enforce:

- DMA boundaries
- queue safety
- interrupt routing
- device isolation

### 2.2 Userspace-owned network objects

The following are userspace-owned objects managed by the network service:

- socket handles
- protocol state
- routing tables
- firewall rules
- NAT state
- connection tracking
- network namespaces

These are **not** kernel objects and are **not** governed by `OBJECTS.md`.

The kernel sees them only through opaque capabilities or IPC-visible identifiers defined by the network service contract.

### 2.3 Userspace object lifetime rule

The network service must ensure for its own objects:

- bounded lifetime tracking
- no use-after-close
- no stale handle reuse without service-defined generation or equivalent protection
- no authority amplification through restart or handle replay

The kernel does not manage userspace network object lifetime.

---

## 3. Capability rights

Each NIC, DMA, queue, or IRQ capability carries a rights mask. The v1.0 network/device-facing right set includes:

- `RIGHT_MMIO` — map MMIO regions belonging to the NIC
- `RIGHT_NET_TX` — submit transmit packets
- `RIGHT_NET_RX` — receive or acknowledge receive completions
- `RIGHT_NET_DMA` — create or use DMA windows
- `RIGHT_NET_IRQ_BIND` — bind interrupt delivery
- `RIGHT_NET_CONFIG` — configure NIC parameters
- `RIGHT_NET_NAMESPACE` — manage or join authorized network namespaces

Rules:

- rights must be validated on every operation
- rights must not be amplified
- rights must be monotonic under derivation
- userspace protocol or socket authority must not exceed the NIC/namespace authority from which it is derived

---

## 4. NIC access and driver isolation

## 4.1 NIC drivers run in userspace

NIC drivers are:

- untrusted
- restartable
- capability-scoped
- sandboxed

They interact with NICs only via:

- MMIO mappings explicitly authorized by capability
- DMA windows
- packet queues
- IRQ endpoints

### 4.2 Isolation invariants

Drivers must not:

- access kernel memory
- access MMIO without `RIGHT_MMIO`
- perform DMA without `RIGHT_NET_DMA`
- receive interrupts without `RIGHT_NET_IRQ_BIND`
- retain stale device state after restart or hotplug

### 4.3 Restart rule

On driver failure or restart:

- all in-flight packets must resolve exactly once as completion or abort
- all DMA windows must be revoked
- all IRQ bindings must be removed
- all queues must be reset or retired
- the NIC must be placed into a safe state or reset path

No stale kernel object, DMA mapping, queue entry, or IRQ binding may survive driver restart.

---

## 5. Packet I/O queues

## 5.1 Queue model

`OBJ_NET_QUEUE` represents a packet I/O queue shared between:

- NIC hardware
- NIC driver
- network service, where the design requires service-visible queue mediation

Queue memory must:

- reside in DMA-safe memory
- be explicitly allocated
- be bounded
- not overlap unrelated memory
- have explicit ownership and reset semantics

### 5.2 Queue operations

- `queue_tx_submit` — requires `RIGHT_NET_TX`
- `queue_rx_complete` — requires `RIGHT_NET_RX`

Any additional queue operations must preserve the same authority and lifetime rules.

### 5.3 Queue invariants

- bounded queue size
- no torn writes
- no stale entry reuse
- architecture-correct memory visibility
- abortable operations
- no queue operation may outlive the queue, device, or driver instance that owns it

### 5.4 Concurrency

Queue access must be:

- atomic where required
- ordered under producer/consumer semantics
- safe under concurrent NIC and userspace execution
- restart-safe under queue reset and device retire

### 5.5 Queue teardown

On queue reset, driver restart, or NIC retire:

- pending queue transactions must resolve exactly once
- stale queue entries must not be reused
- queue memory must not remain DMA-visible beyond the teardown contract

---

## 6. Network namespaces

## 6.1 Namespace model

A network namespace is a userspace-owned object managed by the network service.

It defines:

- routing tables
- firewall rules
- socket visibility
- interface bindings
- address assignments

### 6.2 Kernel boundary

The kernel does not interpret namespace contents.

The kernel enforces only:

- capability-scoped NIC access
- DMA and queue isolation
- interrupt routing safety
- no ambient global namespace

### 6.3 Namespace isolation

Namespaces must be:

- capability-scoped
- restart-safe
- isolated from each other
- non-ambient

No process may access another namespace without explicit capability transfer or policy-authorized bind/join semantics.

### 6.4 Membership rule

Namespace membership must always be explicit.

There is no implicit default namespace authority beyond what a process has been explicitly granted.

---

## 7. Sockets and protocol semantics

## 7.1 Socket model

Sockets are userspace-owned objects managed by the network service.

The kernel does not:

- track socket state
- enforce socket lifetime
- maintain protocol state machines
- allocate ambient ports or wildcard binds

### 7.2 Socket capability model

A socket capability grants only the rights explicitly represented by the network service contract, such as:

- send or receive through the network service
- bind, listen, connect, or accept where policy permits
- join or operate within a namespace where authority exists

These are userspace service capabilities, not kernel object capabilities.

### 7.3 Protocol invariants

The network service must ensure:

- deterministic protocol behavior under fixed inputs
- bounded memory usage
- restart-safe connection teardown
- no authority amplification
- no ambient wildcard bind
- no implicit global routing or address visibility

### 7.4 Bind and allocation rule

Wildcard bind, wildcard address visibility, and ephemeral port allocation must be explicit service operations mediated by policy and namespace authority.

Implicit ambient bind behavior is forbidden.

### 7.5 Forbidden protocol patterns

The following are forbidden:

- implicit bind to `0.0.0.0` or equivalent wildcard authority
- implicit wildcard port allocation without explicit service semantics
- ambient access to NICs or namespaces
- kernel-resident socket state

---

## 8. Routing and addressing

## 8.1 Routing tables

Routing tables are userspace-owned objects.

The kernel does not:

- parse routing entries
- enforce routing correctness
- maintain routing state

### 8.2 Address assignment

Address assignment is:

- namespace-scoped
- capability-mediated
- policy-visible
- explicit

### 8.3 Kernel enforcement

The kernel enforces only:

- NIC capability boundaries
- DMA boundaries
- queue safety
- interrupt routing

The kernel must not become an implicit routing authority.

---

## 9. Policy integration

All network operations are policy sites.

Policy may:

- allow
- deny
- redirect
- apply rate limits
- restrict namespace membership
- restrict NIC binding
- constrain socket creation or bind authority

Policy must not:

- fabricate NIC, queue, DMA, IRQ, or socket authority
- bypass rights
- mutate kernel objects directly

Fallback behavior for policy failure must be explicit at each calling site, consistent with `POLICY.md`.

---

## 10. Timer and scheduler integration

## 10.1 Timers

Network operations may use timers for:

- retransmission
- connection timeout
- handshake deadlines
- backoff
- watchdog deadlines

Timers must obey `TIMERS.md`:

- monotonic
- abortable
- single-resolution
- restart-safe

### 10.2 Scheduler

Network operations may block only via:

- IPC to the network service
- driver waits
- timer-governed waits

All blocking must be abortable and must obey `SCHED.md`.

### 10.3 Single-resolution rule

For any network operation governed by timers, IPC, or restart:

- success
- failure
- timeout
- abort

are competing resolution paths, and exactly one may win.

---

## 11. Restart and failure semantics

## 11.1 Network service restart

On network service restart:

- all socket state is invalidated
- all in-flight operations abort
- all service-owned timers are canceled
- all namespace state is rebuilt or re-established explicitly
- no stale userspace handles may survive
- no stale reply, timeout, or queue completion may bind to a new-generation service object

### 11.2 Driver restart

Driver restart must:

- revoke DMA windows
- reset queues
- unbind IRQs
- abort dependent operations
- reject stale generation state

### 11.3 NIC hotplug and removal

On NIC removal:

- `OBJ_NIC` is retired
- dependent capabilities become invalid through normal object rules
- dependent DMA windows, IRQ bindings, and queues are torn down
- all dependent operations abort
- no stale queue or timer state may survive against a replacement NIC instance

### 11.4 Failure isolation

Driver, network-service, or NIC failure must not:

- corrupt kernel state
- leak capabilities
- violate scheduler invariants
- leak namespace authority across restarts

---

## 12. Forbidden patterns

The following are specification violations:

- kernel-resident socket state
- ambient network namespace
- wildcard bind without explicit authority and policy mediation
- unbounded DMA
- NIC access without capability validation
- cross-namespace leakage
- non-abortable network waits
- stale socket handles after restart
- protocol state surviving service restart
- implicit routing or address assignment
- stale queue, IRQ, DMA, or timer state surviving restart or hotplug

Any such change is a violation, not an optimization.

---

## 13. Implementation checklist

Before merging any network-related change:

- are all NIC, DMA, queue, and IRQ operations capability-validated?
- are DMA windows bounded and revocable?
- are packet queues safe, bounded, and restartable?
- are namespaces isolated and explicitly joined?
- are socket operations deterministic?
- are policy hooks present for all authority-bearing operations?
- are timers monotonic, abortable, and single-resolution?
- are scheduler wake paths correct?
- are stale generations and stale completions rejected across restart?

Tests must include:

- NIC DMA boundary violations
- queue overflow and recovery
- driver restart
- network-service restart
- namespace isolation
- socket capability transfer
- explicit wildcard-bind policy enforcement
- policy allow/deny/redirect
- timer-driven network timeouts
- stale completion rejection after restart or hotplug

---

## 14. Ground-truth rule

This document is the ground truth for network semantics in Zuki.

If code and this document disagree, the code is wrong.
