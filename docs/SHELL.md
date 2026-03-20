# Zuki Shell Interface Specification (SHELL.md) — Implementer Specification v1.0

**Status:** Canonical
**Authority:**

* Subordinate to *SYSTEM.md*, *PROGRAMMING-MODEL.md*, and *RUNTIME-MODEL.md*
* Coordinates with *IPC.md*, *CAPABILITIES.md*, *CSPACE.md*, and *SCHED.md*
* Superior, for interactive command semantics, to user-facing CLI tools and scripting environments

**Scope:**
Binding for all interactive shells, command interpreters, REPL environments, scripting runtimes, and CLI interfaces executing on Zuki.

**Purpose:**
Defines the canonical interactive execution model: command invocation, capability handling, task management, structured pipelines, error behavior, and forbidden patterns.

If shell behavior and this document disagree, the shell is wrong.

---

# 1. Shell model overview

The Zuki shell is:

* capability-rooted
* non-ambient
* deterministic at the boundary
* service-oriented
* restart-safe
* explicit
* inspectable
* scriptable

The shell is the primary interactive interface to the system authority graph.

The shell is **not**:

* a POSIX shell
* a namespace-based command interpreter
* a fork/exec orchestration layer
* a process-control interface
* a privilege management mechanism

The shell does not create authority.
The shell operates only on authority already granted.

---

# 2. Core shell invariants

The shell must obey all global system invariants defined in `INVARIANTS.md`.

In addition, the shell must preserve the following interactive invariants.

---

## 2.1 No ambient authority

The shell must not grant authority implicitly.

Authority may originate only from:

* initial capabilities provided at startup
* capabilities received through IPC
* capabilities explicitly delegated
* capabilities derived with narrowed rights

The shell must not rely on:

* current working directory
* environment variables
* PATH lookup
* user identity
* implicit service discovery

---

## 2.2 Explicit command resolution

Commands must resolve through explicit authority.

Valid command sources:

* shell builtins
* services explicitly bound into the current execution context
* explicitly referenced program capabilities
* user-defined functions

The shell must not search ambient directories for executables.

Resolution must be:

* deterministic
* single-step
* scope-bounded

---

## 2.3 Deterministic execution

Command execution must produce:

* deterministic success or failure
* deterministic error results
* deterministic task resolution
* deterministic restart behavior

The shell must not introduce nondeterministic behavior at the system boundary.

---

## 2.4 Structured interaction

The shell operates on structured values, not implicit byte streams.

Structured values include:

* scalars
* byte buffers
* lists
* records
* capability references
* service handles
* streams
* errors

Text processing is a supported mode but not the default execution model.

---

# 3. Shell execution model

---

## 3.1 Command invocation

A shell command represents:

* a builtin operation
* a service method invocation
* a program execution request
* a user-defined function

Conceptual form:

```
invoke <target> <method> [arguments]
```

Friendly syntax may provide shorthand, but the underlying semantics must remain explicit.

---

## 3.2 Invocation semantics

Command execution must:

* validate authority before invocation
* resolve arguments deterministically
* verify capability validity at the earliest deterministic boundary
* produce exactly one success or one failure result

A command must not:

* complete more than once
* produce partial authoritative state
* widen authority implicitly

---

## 3.3 Command completion

A command resolves as exactly one of:

* success
* failure
* timeout
* abort

Exactly one result may win.

---

## 3.4 Execution unit

An execution unit is the smallest indivisible shell operation boundary.

An execution unit may be:

* a single command invocation
* a pipeline
* a script statement

All resolution, validation, execution, and failure semantics apply to the execution unit as a whole.

An execution unit must produce exactly one terminal result:

* success
* failure
* timeout
* abort

No partial completion may be externally visible.

---

# 4. Shell state model

Shell state is explicit and non-authoritative unless it contains capability references.

---

## 4.1 Shell state components

The shell may maintain:

* variables
* aliases
* functions
* command history
* session configuration
* task table
* current context handles

State changes must be explicit.

---

## 4.2 Context handles

Context handles represent:

* working directory capability
* active service connection
* selected device
* default execution context

Context handles are convenience references only.
They do not grant authority.

---

# 5. Capability handling

---

## 5.1 Capability representation

Capabilities in the shell are opaque values.

Capabilities must:

* remain unforgeable
* remain immutable
* remain validated on use

The shell must not interpret capability contents.

---

## 5.2 Capability operations

The shell may:

* store capabilities
* pass capabilities to commands
* transfer capabilities through IPC
* derive capabilities with narrowed rights
* delete capabilities explicitly

Capability transfer must preserve generation integrity.

A transferred capability must be validated before use in the receiving context.

Capability validation must occur independently in each execution context.

Validation in one context must not imply validity in another.

The shell must not:

* fabricate capabilities
* widen capability rights
* modify capability generation
* bypass validation

---

## 5.3 Capability lifetime

A capability becomes invalid when:

* the underlying object generation changes
* the object is retired
* the capability is explicitly destroyed

Capability validity must be checked at:

* resolution, or
* authority validation, or
* first use

Failure timing must be deterministic.

---

# 6. Task model

The shell tracks command execution as tasks.

Tasks are explicit execution units managed by the scheduler.

---

## 6.1 Task states

A task may exist in one of:

* ready
* running
* blocked
* completed
* failed
* aborted

Task state transitions must obey `SCHED.md`.

---

## 6.2 Task operations

The shell must support:

* task creation
* task inspection
* task cancellation
* task waiting

Task cancellation must produce a deterministic terminal state transition.

A cancelled task must resolve as exactly one of:

* aborted
* failed

Cancellation must not leave a task in:

* running
* blocked
* indeterminate

Task state after cancellation must be observable deterministically.

Task operations must be explicit.

---

## 6.3 No implicit job control

The shell must not rely on:

* PID-based job control
* implicit background execution
* signal-based task management

All task management must be explicit.

---

# 7. Pipeline model

---

## 7.1 Structured pipelines

Pipelines connect command outputs to inputs.

Pipelines operate on structured values.

Conceptual form:

```
list devices | filter class="net" | inspect
```

Pipelines must preserve:

* deterministic ordering
* explicit data flow
* bounded buffering
* deterministic backpressure

Upstream blocking must be:

* scheduler-visible
* interruptible
* bounded by explicit policy

Upstream execution must:

* block under scheduler control, or
* fail deterministically

No silent truncation.
No implicit retry.

---

## 7.2 Stream pipelines

Byte-stream pipelines are permitted only when explicitly requested.

Example:

```
text.read logs | text.grep "error" | text.head 20
```

Stream processing must remain explicit.

---

## 7.3 Pipeline safety

Pipelines must not:

* create hidden authority
* reorder operations nondeterministically
* expose externally visible partial results after abort

Each pipeline stage must define its commit boundary explicitly.

A pipeline must expose one externally visible completion boundary.

Rollback behavior must be defined by each command contract.

Implicit partial rollback is prohibited.

---

# 8. Error model

---

## 8.1 Explicit error reporting

Command failures must return structured errors.

Errors must include:

* error_category
* error_code
* error_message
* operation_context

---

## 8.2 Deterministic failure

Errors must be:

* deterministic
* reproducible
* bounded
* explicit

---

## 8.3 Error propagation

Failures must propagate through pipelines deterministically.

A failure must not:

* silently disappear
* produce multiple results
* corrupt pipeline state

---

# 9. Scripting model

---

## 9.1 Script execution

Scripts execute as deterministic command sequences.

Scripts must:

* operate within explicit authority
* preserve capability semantics
* produce deterministic results

---

## 9.2 Script isolation

Scripts must not:

* modify global system state implicitly
* introduce ambient authority
* rely on external environment mutation

---

## 9.3 Script restart behavior

Each script operation must define a restart-safe completion boundary.

If a restart occurs before that boundary:

* the operation must be treated as failed

If a restart occurs after that boundary:

* the operation must not be re-executed automatically

Replay without explicit instruction is prohibited.

Scripts must not:

* duplicate authority
* complete operations twice
* accept stale state

---

# 10. Builtin command set (minimum)

The canonical shell must provide at least:

```
help
let
set
unset
echo
pwd
cd
ls
inspect
invoke
grant
drop
task.list
task.wait
task.cancel
exit
```

Builtin commands possess no inherent authority.

A builtin command may operate only on authority explicitly provided as input or present in the execution context.

Builtin commands must obey the same capability validation rules as external programs.

Additional builtins may be added without breaking compatibility.

---

# 11. Shell startup model

---

## 11.1 Initial state

The shell starts with:

* a root capability space
* an initial thread
* a bounded capability set
* an explicitly defined initial execution context

---

## 11.2 No implicit initialization

Shell startup must not:

* open files implicitly
* connect to services implicitly
* discover devices implicitly
* create capabilities implicitly

All initialization must be explicit.

---

# 12. Restart and session semantics

---

## 12.1 Restart safety

Restart must not:

* resurrect stale tasks
* duplicate command execution
* widen authority

---

## 12.2 Session recovery

If the shell restarts:

* stale state must be rejected
* incomplete commands must fail deterministically
* tasks must not resume without explicit restart

---

# 13. Security invariants

The shell must preserve:

* capability isolation
* deterministic execution
* explicit authority boundaries
* restart safety
* bounded resource behavior

The shell must not introduce:

* ambient authority
* hidden privilege escalation
* implicit service discovery
* implicit capability creation

---

# 14. Forbidden patterns

The following are specification violations:

* ambient command lookup
* implicit executable search paths
* hidden capability derivation
* hidden service discovery
* identity-based privilege
* PID-based job control
* implicit task creation
* implicit authority widening
* nondeterministic command resolution
* unbounded pipeline resource usage

Any such behavior is a violation, not an optimization.

---

# 15. Implementation checklist

Before merging any shell-related change:

* does command execution remain deterministic?
* are capability semantics preserved?
* are tasks single-resolution?
* are errors explicit and deterministic?
* is authority explicit and capability-scoped?
* are restart semantics safe?
* are pipelines deterministic and scheduler-safe?
* are forbidden patterns absent?

If any answer is no, unknown, or hand-waved, the change is invalid.

---

# 16. Ground-truth rule

This document is the ground truth for the Zuki shell interface.

If shell behavior and this document disagree, the shell is wrong.

---
