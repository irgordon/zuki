# Zuki AArch64 Application Binary Interface — Implementer Specification v1.0

**Status:** Canonical  
**Authority:** Subordinate to *Zuki Abstract ABI v1.0-Canonical* and *Zuki System Architecture v1.0-Canonical*  
**Scope:** Binding for all AArch64 code under `/kernel/entry`, `/kernel/sys`, and any AArch64 userspace component that invokes syscalls or crosses the user/kernel boundary.

This document maps the abstract ABI onto AArch64 and defines:

- syscall entry and return mechanism
- concrete register assignments for logical slots
- exception-frame invariants
- clobber and preservation rules
- capability wire handling
- user/kernel memory-boundary rules

If code and this document disagree, the code is wrong.

---

## 1. Entry and return on AArch64

### 1.1 Entry instruction

- Syscalls enter the kernel via `SVC #0` executed at EL0.
- `SMC`, `HVC`, and vendor-specific mechanisms are not part of the canonical v1.0 syscall ABI.

### 1.2 Privilege transition

On `SVC #0`:

- the CPU traps from EL0 to EL1 through the synchronous exception path
- `ESR_EL1` encodes the exception class and immediate value
- `ELR_EL1` contains the user return PC
- `SPSR_EL1` contains the saved user `PSTATE`

The kernel must treat `ELR_EL1` and `SPSR_EL1` as part of the architectural syscall-entry contract.

### 1.3 Entry-state invariants

On entry:

- `x8` contains the syscall number
- `x0`–`x5` contain logical argument slots `arg0`–`arg5`
- `ELR_EL1` contains the user return PC
- `SPSR_EL1` contains the saved user `PSTATE`

The kernel must not reinterpret these fields beyond the abstract ABI’s logical-slot semantics.

### 1.4 Return path

- The canonical return from EL1 to EL0 is `ERET`.
- Before executing `ERET`, the kernel must restore:
  - `ELR_EL1` to the validated user return PC
  - `SPSR_EL1` to the sanitized user `PSTATE`

If return state is invalid or unsafe, the kernel must fail closed rather than attempt an undefined or non-canonical return path.

### 1.5 Return-state sanitization

Before returning to EL0, the kernel must ensure:

- return PC is valid for EL0
- `PSTATE` fields are sanitized according to architectural and security rules
- no EL1 privilege state leaks into EL0-visible execution state

---

## 2. Logical slots to AArch64 registers

### 2.1 Syscall number

- Logical syscall number is passed in `x8`.
- On return, `x0` carries `ret0`, the primary return value or error code.

### 2.2 Argument slots

Logical argument slots map to registers as follows:

- `arg0` → `x0`
- `arg1` → `x1`
- `arg2` → `x2`
- `arg3` → `x3`
- `arg4` → `x4`
- `arg5` → `x5`

No additional arguments are implicitly read from the user stack.

### 2.3 Return slots

- `ret0` → `x0`
- `ret1` → `x1` only when the syscall contract explicitly defines a secondary return value

If a syscall does not define `ret1`, `x1` is caller-clobbered.

---

## 3. Clobber and preservation rules

### 3.1 Caller-clobbered across syscall

Userspace must treat the following registers as volatile across a syscall:

- `x0`–`x17`
- condition flags in user-visible `PSTATE`

This is the Zuki syscall ABI contract for volatile state across kernel entry and return.

`x30` is not preserved as a syscall call/return register in the way a normal BL/RET function call would preserve control flow. Userspace must not assume syscall preserves link-register semantics.

### 3.2 Preserved across syscall return

The kernel must preserve and restore:

- `x19`–`x29`
- user `SP_EL0`
- user-visible SIMD/FPU state according to the selected AArch64 FP/SIMD state-management mechanism

Any chosen FP/SIMD save/restore policy must preserve the architectural contract visible to userspace. Optimizations must not weaken correctness.

### 3.3 `x18` rule

The treatment of `x18` must be defined consistently with the chosen AArch64 userspace ABI environment.

If Zuki userspace reserves `x18` as platform state, the kernel must preserve that contract exactly and must not allow syscall handling to violate it.

---

## 4. Exception-frame and stack invariants

### 4.1 User stack on entry

On syscall entry:

- `SP_EL0` is the user-mode stack pointer value
- the kernel must treat it as untrusted user state
- the kernel must not dereference user stack memory without explicit validation

The abstract ABI does not require the kernel to consume syscall arguments from the stack.

### 4.2 Alignment

User code must obey the AArch64 userspace stack-alignment rules, including 16-byte alignment.

The kernel must not assume any additional stack layout beyond what is required for correct userspace execution and validated user-memory access.

### 4.3 Kernel stack

- each thread has a kernel stack configured by the entry and scheduler code
- the entry path must execute on the correct EL1 stack before calling the common syscall handler
- the kernel must never expose kernel stack addresses or contents to userspace

---

## 5. Capability wire format on AArch64

### 5.1 CapWire layout

The canonical `CapWire` structure on AArch64 is:

```c
typedef struct CapWire {
    uint64_t object_id;
    uint64_t gen_at_mint;
    uint64_t rights;
} CapWire;
````

Requirements:

* field order is fixed
* each field is 64-bit
* layout must remain stable for the ABI version

### 5.2 Passing capabilities

When a syscall takes a capability argument, the syscall contract must define whether it is passed as:

* a user pointer to a `CapWire`, or
* an inline encoding built from syscall argument slots

If a pointer form is used, the kernel must:

* treat the pointer as a user virtual address
* validate the address range
* validate that the address is valid under the configured EL0 virtual-address rules
* copy the `CapWire` into kernel memory
* reconstruct a logical capability
* validate it via `cap_use()`

Raw integers must never be interpreted as kernel object references unless the syscall contract explicitly defines an inline encoding consistent with the abstract ABI.

---

## 6. User-memory access rules

Any user pointer carried in syscall arguments or nested argument structures must be treated as a user virtual address only.

The kernel must:

* validate address range
* validate that the address is valid under the configured EL0 virtual-address rules, including any active top-byte-ignore or tagged-address policy
* perform explicit copy-in or copy-out
* handle faults deterministically using the syscall’s defined failure model

The kernel must not:

* dereference user pointers directly in kernel context without validation
* rely on user stack or heap layout for security decisions
* treat a faulting user address as a reason to widen authority or partially complete an operation

---

## 7. Error and return semantics on AArch64

* `x0` carries the primary return value or error code
* `x1` carries `ret1` only when the syscall contract explicitly defines a secondary return value
* no thread-local errno or ambient error channel exists at the ABI layer

The exact success and failure encoding is defined by `SYSCALL.md` and the abstract ABI, and this AArch64 mapping must implement it exactly.

---

## 8. Blocking, abort, and restart on AArch64

The AArch64 mapping does not alter the abstract rules:

* blocking is governed by `SCHED.md`, `IPC.md`, `TIMERS.md`, and `DEVICE.md`
* abortability and restart semantics are as defined in `SYSCALL.md` and `ABI.md`

The AArch64 entry and return path must:

* not leak partial register or stack state that could be interpreted as authority
* not widen authority on restart
* not complete a syscall twice
* not allow stale return-path state to bind to a new operation

---

## 9. Forbidden patterns

On AArch64, the following are specification violations:

* using `SMC`, `HVC`, or vendor-specific mechanisms as the canonical syscall ABI
* interpreting raw register values as kernel object references without capability reconstruction
* relying on unvalidated user register or stack contents for security decisions
* passing capabilities outside the defined `CapWire` or explicitly defined inline encoding
* using `x1` as `ret1` when the syscall contract does not define it
* clobbering preserved registers across syscall handling
* violating the chosen `x18` contract for the userspace ABI environment
* leaking kernel stack contents, kernel register contents, or unsanitized return state back to userspace
* executing `ERET` with invalid or unsafe return state

Any such change is a violation, not an optimization.

---

## 10. Implementation checklist

Before merging any AArch64 ABI-related change:

### Entry and return

* is `SVC #0` used consistently as the canonical entry mechanism?
* are `ELR_EL1` and `SPSR_EL1` handled correctly?
* is `ERET` used only with validated return state?

### Registers

* do `x8`, `x0`–`x5` map correctly to logical slots?
* are preserved registers saved and restored correctly?
* is the `x18` contract consistent and enforced?

### Capabilities

* is `CapWire` layout correct and stable?
* are capability arguments reconstructed and validated via `cap_use()`?

### User memory

* are user pointers validated and copied safely?
* are EL0 address checks and fault handling correct and deterministic?

### Tests

* syscall number decoding
* argument mapping correctness
* capability wire handling
* preserved-register integrity
* return-state sanitization
* error and return behavior
* interaction with `SYSCALL.md` invariants

If any answer is no, unknown, or hand-waved, the change is invalid.

---

## 11. Ground-truth rule

This document is the ground truth for the AArch64 mapping of Zuki’s abstract ABI.

If code and this document disagree, the code is wrong.
