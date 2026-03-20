# Zuki Kernel IPC Subsystem — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all code under `/kernel/ipc` and any kernel code that performs inter-process communication, endpoint operations, blocking or wake coordination for IPC, or interacts with the Zuki-Bus.

This document defines:

- the IPC message model and in-kernel wire representation
- the synchronous send/receive protocol
- queue semantics and bounded-capacity rules
- capability transfer semantics
- reply tracking and wait resolution
- abort and failure behavior
- ordering guarantees
- concurrency and locking rules
- integration with `OBJ_ENDPOINT`, `OBJ_THREAD`, and retire/reclaim

If code and this document disagree, the code is wrong.

---

## 1. IPC model overview

Zuki’s IPC subsystem (“Zuki-Bus”) provides:

1. synchronous, bounded IPC between threads via `OBJ_ENDPOINT`
2. optional capability transfer as part of a message
3. deterministic, breakable waits
4. FIFO queueing at the endpoint
5. explicit reply, failure, or abort completion for blocked senders

All IPC operations:

- are mediated by capabilities to `OBJ_ENDPOINT`
- must obey the capability and object invariants defined in `CAPABILITIES.md` and `OBJECTS.md`
- must remain correct under concurrent revoke, retire, abort, and reclaim

No IPC wait may be uninterruptible.

---

## 2. IPC object and execution model

### 2.1 Endpoint role

An endpoint is a kernel object that accepts sent messages and delivers them to a receiver.

In v1.0, an endpoint supports:

- zero or one blocked receiver
- zero or more queued messages up to fixed capacity
- zero or more blocked senders waiting for reply on already-delivered messages, as tracked by scheduler/IPC wait state

### 2.2 Single-receiver rule

Each endpoint may have at most one blocked receiver at a time.

If a second receiver attempts to wait on the same endpoint while another receiver is already blocked, the operation must fail immediately with a kernel error.

This rule is mandatory in v1.0 and is required by the single `waiter_thread_id` model.

### 2.3 Reply model

`ipc_send()` is synchronous from the sender’s perspective, but reply state is not stored in the endpoint queue.

Instead:

- message delivery transfers the request to the receiver
- the sender then blocks in a scheduler-visible IPC wait state associated with:
  - sender thread id
  - endpoint id
  - message transaction state

A send completes only when exactly one of the following occurs:

- the receiver issues a reply through the IPC reply path
- the kernel returns failure before delivery
- the blocked wait is aborted

Reply tracking is therefore part of the IPC/scheduler interaction, not part of the endpoint queue payload itself.

---

## 3. Core IPC data structures

## 3.1 IPC message payload

```c
typedef struct ipc_message_t {
    uint32_t    label;
    uint32_t    flags;
    uint64_t    data[4];
} ipc_message_t;
````

### Invariants

* `label` is interpreted only by the receiver or higher-level protocol
* `flags` are IPC-local transport flags only
* `data[]` is opaque to the kernel except for copying and transport
* capability validity is never encoded in message payload fields

---

## 3.2 Message slot

```c
typedef struct MessageSlot {
    ipc_message_t  message;
    Capability    *caps;
    size_t         cap_count;
    ObjectID       sender_thread_id;
    uint64_t       txn_id;
} MessageSlot;
```

### Invariants

* `caps` points to fixed-capacity storage owned by the endpoint
* `cap_count` must not exceed per-message configured capability capacity
* `sender_thread_id` identifies the blocked sender awaiting reply
* `txn_id` uniquely identifies the in-flight transaction for reply matching
* message-slot fields are mutated only while the slot is owned under endpoint serialization rules

---

## 3.3 Endpoint payload

```c
typedef struct EndpointPayload {
    _Atomic ObjectID waiter_thread_id;
    MessageSlot     *queue;
    size_t           queue_len;
    size_t           queue_cap;
    size_t           head;
    size_t           tail;
    lock_t           queue_lock;
} EndpointPayload;
```

### Invariants

* `queue` identity is immutable after publication
* `queue_cap` is immutable after publication
* `queue_len`, `head`, and `tail` are mutated only while holding `queue_lock`
* `waiter_thread_id` is either a valid thread object id or `OBJECT_ID_INVALID`
* endpoint queue storage is fixed-capacity in v1.0
* queue resizing is forbidden in v1.0

---

## 4. Kernel IPC API

The conceptual kernel IPC API is:

```c
int ipc_send(const Capability    *endpoint_cap,
             const ipc_message_t *msg,
             Capability          *caps,
             size_t               cap_count,
             ipc_message_t       *reply_out);

int ipc_recv(const Capability *endpoint_cap,
             ipc_message_t    *msg_out,
             Capability       *caps_out,
             size_t            caps_out_cap);

int ipc_reply(ObjectID             endpoint_id,
              uint64_t             txn_id,
              const ipc_message_t *reply_msg);
```

### Semantics

* `ipc_send()` blocks until reply, failure, or abort
* `ipc_recv()` blocks until message delivery or abort
* `ipc_reply()` resolves exactly one blocked sender transaction

All endpoint access must validate the endpoint through `cap_use()` with the appropriate right.

---

## 5. Rights model

The endpoint rights model is:

| Right            | Meaning                             |
| ---------------- | ----------------------------------- |
| `RIGHT_SEND`     | send messages to the endpoint       |
| `RIGHT_RECV`     | receive messages from the endpoint  |
| `RIGHT_TRANSFER` | transfer capabilities with messages |

Rules:

* send requires `RIGHT_SEND`
* receive requires `RIGHT_RECV`
* sending one or more capabilities requires `RIGHT_TRANSFER` on the endpoint and valid source capability authority for each transferred capability

Rights may not be amplified during transfer.

---

## 6. Ordering and delivery guarantees

### 6.1 Queue ordering

Endpoint queue order is FIFO.

If messages `A` and `B` are both successfully enqueued on the same endpoint, and `A` is enqueued before `B`, the receiver must dequeue `A` before `B`.

### 6.2 Direct-delivery ordering

If a receiver is already blocked on an endpoint, a send may bypass queue insertion and deliver directly to that receiver.

This does not violate FIFO because direct delivery is permitted only when no earlier queued message exists.

Therefore:

* if `queue_len > 0`, the receiver must consume from the queue before any new direct-delivery send may bypass it
* direct-delivery is permitted only when `queue_len == 0` and a receiver is already waiting

### 6.3 Per-sender behavior

For a given `(sender_thread, endpoint)` pair:

* sends issued sequentially by that sender must be observed in program order
* a sender may not have more than one in-flight synchronous send on the same thread at a time

### 6.4 Cross-sender behavior

* no ordering is guaranteed between different senders beyond FIFO queue insertion order
* no global ordering exists across endpoints

### 6.5 Determinism

Given:

* a fixed schedule
* fixed IPC inputs
* fixed abort/failure injections

IPC behavior must be deterministic.

---

## 7. Send and receive protocol

## 7.1 Send path

High-level send behavior:

1. validate endpoint via `cap_use(endpoint_cap, RIGHT_SEND)`
2. if `cap_count > 0`, also require endpoint transfer rights
3. prepare transferable capability state before publication to endpoint storage
4. acquire `queue_lock`
5. if endpoint is retired or invalidated under the current operation, release lock and fail
6. if `queue_len == 0` and `waiter_thread_id != OBJECT_ID_INVALID`:

   * deliver directly to waiting receiver
   * clear `waiter_thread_id`
   * associate delivered message with sender transaction state
   * wake receiver
   * release lock
   * block sender awaiting reply or abort
7. else if queue is full:

   * release lock
   * roll back any prepared transfer state
   * return immediate failure
8. else:

   * enqueue message at `tail`
   * publish transfer payload into the message slot
   * record `sender_thread_id` and `txn_id`
   * update `tail` and `queue_len`
   * release lock
   * block sender awaiting reply or abort

### 7.2 Receive path

High-level receive behavior:

1. validate endpoint via `cap_use(endpoint_cap, RIGHT_RECV)`
2. acquire `queue_lock`
3. if endpoint is retired or invalidated under the current operation, release lock and fail or abort as appropriate
4. if `queue_len > 0`:

   * dequeue from `head`
   * copy out message and transferred capabilities
   * update `head` and `queue_len`
   * release lock
   * return success
5. else if `waiter_thread_id != OBJECT_ID_INVALID`:

   * release lock
   * fail immediately because only one blocked receiver is permitted
6. else:

   * set `waiter_thread_id` to current thread id
   * release lock
   * block receiver until:

     * direct message delivery occurs, or
     * endpoint retire triggers abort, or
     * watchdog/policy abort triggers abort

### 7.3 Reply path

The receiver replies using the sender transaction metadata associated with the delivered request.

Reply behavior:

1. validate the transaction is still waiting
2. copy reply payload into sender-visible reply buffer or scheduler-owned reply state
3. wake the blocked sender
4. mark transaction resolved

A reply must resolve exactly one waiting sender.

Double reply, late reply, or reply to an aborted transaction must fail.

---

## 8. Capability transfer semantics

## 8.1 Transfer model

Capabilities transferred through IPC are transported as capability values under kernel ownership.

The kernel must ensure:

* rights are not amplified
* generation invariants remain intact
* refcounts are updated correctly
* transfer ownership is unambiguous at every stage

### 8.2 Supported forms

In v1.0, IPC transfer may be implemented as either:

* **copy transfer**: mint derived capabilities into message-owned storage
* **move transfer**: remove capabilities from sender-owned slots and transfer ownership into message-owned storage

The implementation must choose one well-defined path per transferred capability. Mixed ownership ambiguity is forbidden.

### 8.3 Message-owned transfer state

While a message is queued or delivered but not yet fully handed off, transferred capabilities are owned by the message slot or transaction state, not by sender or receiver CNodes.

This ownership must be explicit in implementation.

### 8.4 Send-side validation

For each transferred capability:

* validate source authority
* ensure the endpoint transfer right is present
* ensure transfer does not amplify rights
* ensure message-owned capability state is fully formed before enqueue publication

### 8.5 Receive-side handoff

On successful receive:

* transferred capabilities become receiver-owned only when inserted into receiver-visible destination state
* partial handoff is forbidden unless the API explicitly defines a partial result contract

If insertion into receiver state fails, the kernel must follow the defined rollback path.

### 8.6 Failure and abort rollback

If failure or abort occurs before receiver ownership is established, the kernel must execute exactly one rollback outcome per transferred capability:

* return to sender ownership, or
* destroy message-owned transfer state

No leak, duplication, or ambiguous ownership is permitted.

---

## 9. Failure and abort semantics

## 9.1 Outcome space

Every synchronous send resolves in exactly one of:

* **Reply**
* **Failure**
* **Abort**

Every blocking receive resolves in exactly one of:

* **Message delivery**
* **Failure**
* **Abort**

### 9.2 Failure

Failure is an immediate kernel-generated error.

Examples include:

* invalid or revoked endpoint capability
* wrong endpoint rights
* endpoint retired or unavailable before wait establishment
* queue full
* invalid transfer set
* receiver-side single-waiter violation

Failure properties:

* no blocking
* no partially published queue entry
* no leaked transfer ownership
* endpoint remains internally consistent

### 9.3 Abort

Abort occurs when a blocked wait is forcibly broken.

Examples include:

* endpoint retire while sender or receiver is blocked
* watchdog or policy cancellation
* system shutdown or wider abort condition

Abort properties:

* must unblock all affected waiters
* must be observable as distinct from failure
* must leave queue and transaction state consistent
* must execute transfer rollback for any not-yet-consumed capabilities

No IPC wait may be unbreakable.

---

## 10. Concurrency and locking rules

## 10.1 Endpoint locking

`queue_lock` or an equivalent endpoint serialization primitive must protect:

* `queue_len`
* `head`
* `tail`
* queue slot publication and dequeue
* transfer-state publication into queue slots
* consistency between queue contents and waiter/direct-delivery decisions

### 10.2 Atomic fields

`waiter_thread_id` is atomic and may be read lock-free only where doing so cannot create inconsistent delivery behavior.

Any decision that depends on both queue state and waiter state must be made under endpoint serialization.

### 10.3 Thread blocking and wake

* IPC blocking and wake transitions must be coordinated with the scheduler subsystem
* IPC code must not retain raw `Object *` across blocking
* persistent IPC wait state must use `ObjectID`, `txn_id`, or scheduler-owned stable references

### 10.4 Retire/reclaim interaction

If an endpoint is retired while threads are blocked:

* all blocked receivers on that endpoint must be aborted
* all blocked senders awaiting reply on that endpoint must be aborted
* no new send or receive may succeed after retire is observed

Reclaim must not free the endpoint while:

* any thread remains blocked on it
* any queued message remains present
* any message-owned capability transfer state remains live
* any reply transaction state still references the endpoint

---

## 11. Integration with objects and capabilities

## 11.1 Endpoint object invariants

From `OBJECTS.md`:

* endpoint payload identity is immutable after publication
* queue capacity is fixed
* retire increments generation and does not free payload
* reclaim frees payload only after quiescence and `refcount == 0`

### 11.2 Capability invariants

From `CAPABILITIES.md`:

* all endpoint access goes through `cap_use()`
* no raw endpoint object pointer may survive beyond a bounded operation
* generation-based revoke must be respected by all IPC operations
* no per-capability revoke walk is permitted

---

## 12. Retire and reclaim rules for IPC state

### 12.1 Retire

Endpoint retire must:

* invalidate new capability-based access through generation increment
* prevent new send/receive operations from succeeding
* abort blocked senders and receivers
* mark queued but not yet consumed messages for drain or destruction according to endpoint teardown rules

### 12.2 Queue drain

Queued messages remaining at retire must be explicitly drained before reclaim.

For each queued message:

* message-owned capability transfer state must be destroyed or rolled back according to transfer ownership rules
* sender wait state must be resolved as abort if still pending

Queued messages must not be silently discarded without ownership cleanup.

### 12.3 Reclaim

Endpoint reclaim may occur only after:

* retire has completed
* quiescence has been observed
* no blocked waiters remain
* queue is empty
* no message-owned capability state remains
* object `refcount == 0`

---

## 13. Forbidden patterns

The following are specification violations:

* unbounded IPC queues
* blocking `ipc_send()` due only to queue saturation
* permitting direct delivery while older queued messages remain
* retaining `EndpointPayload *` across blocking or scheduling
* modifying endpoint queue state without required serialization
* partial enqueue on failure
* ambiguous capability ownership during transfer
* per-capability revoke walks through endpoint queues
* using telemetry or introspection for enforcement decisions
* fast paths that bypass `cap_use()` or endpoint synchronization rules

Any such change is a violation, not an optimization.

---

## 14. Implementation checklist

Before merging any change touching `/kernel/ipc` or endpoint behavior:

* does every IPC operation validate endpoint access through `cap_use()`?
* are queue mutations serialized correctly?
* is the single-receiver rule enforced?
* are all waits breakable by abort?
* is queue capacity bounded and enforced?
* is direct delivery forbidden when queued messages already exist?
* are send-side failures free of partial enqueue?
* are transfer ownership and rollback rules explicit and correct?
* does endpoint retire abort blocked operations and drain queued ownership safely?
* does reclaim wait for empty queue, no blocked waiters, and no live transfer state?
* are tests present for:

  * concurrent send/recv under load
  * FIFO queue behavior
  * direct-delivery vs queued ordering
  * queue overflow failure
  * abort under cyclic wait conditions
  * endpoint retire with blocked senders and receivers
  * capability transfer correctness under reply, failure, and abort

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 15. Ground-truth rule

This document, together with `CAPABILITIES.md` and `OBJECTS.md`, defines the kernel mechanism layer for IPC in Zuki.

If code and this document disagree, the code is wrong.
