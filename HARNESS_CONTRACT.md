# HARNESS_CONTRACT.md — Verification Harness Contract

Status: Binding  
Scope: `tools/`, `tools/harness/`, `Makefile` verification stages  
Authority: Subordinate to `ARCH_RULES.md`, `VERIFY.md`, and `AGENTS.md`

This document defines the repository verification harness.

The harness verifies repository state.  
It does not verify host state.

## 1. Harness Laws

The harness must be:

- closed-world
- deterministic
- authority-free
- schema-driven
- repository-rooted
- non-probing
- non-discovering

The harness must behave as a pure function over:

- repository files
- canonical schemas
- static rule definitions

The harness must not depend on:

- host package state
- installed tool discovery
- OS identity
- kernel version
- locale
- timezone
- environment-derived authority

## 2. Allowed Inputs

Allowed inputs are limited to:

- files inside the repository root
- static constants encoded in harness code
- canonical schemas stored in the repository

No other inputs are permitted.

## 3. Forbidden Inputs

The harness must not read from:

- `/etc`
- `/usr`
- `/proc`
- `/sys`
- `$HOME`
- network resources
- mounted external repositories

The harness must not inspect:

- installed binaries
- package managers
- host configuration
- current user identity

## 4. Runtime Model

The harness may use:

- minimal Bash wrappers
- repo-local Python implementations

The Bash wrappers must only:

- establish deterministic shell flags
- set deterministic locale/timezone
- resolve repository root
- invoke repo-local Python entry points

All verification logic must exist in Python under `tools/harness/`.

## 5. Output Contract

Each verification stage must emit exactly one terminal result.

Success output:

- one structured success line

Failure output:

- one structured failure object per violation
- deterministic ordering
- no warnings
- no retries
- no fallback logic

The final process exit code must be:

- `0` on success
- nonzero on failure

## 6. Structured Output Format

Harness tools must emit newline-delimited JSON.

Success line shape:

```json
{"status":"ok","stage":"verify_structure","message":"repository structure verified"}
````

Failure line shape:

```json
{"status":"fail","stage":"verify_policy","rule":"banned_pattern","path":"tools/example.sh","detail":"PATH="}
```

Output ordering must be deterministic.

## 7. Stage Contracts

### 7.1 verify_structure

Checks:

* required control files exist
* required verification scripts exist
* required harness files exist

### 7.2 verify_policy

Checks:

* banned patterns
* forbidden host-authority constructs
* forbidden implicit lookup constructs

### 7.3 verify_schema

Checks:

* governance files contain required canonical markers

### 7.4 run_tests

Checks:

* repo-local Python unit tests under approved paths
* deterministic execution
* no network

If no tests exist, the stage succeeds deterministically.

### 7.5 verify_determinism

Checks:

* no nondeterministic tokens in governed files
* no wall-clock sampling
* no randomness
* no network fetch commands

### 7.6 verify_resources

Checks:

* bounded file sizes for harness sources
* bounded line lengths
* no obvious infinite shell loops in wrappers
* bounded test/runtime bootstrap footprint

## 8. Determinism Rules

Harness behavior must not vary with:

* file enumeration order
* locale
* timezone
* current directory
* shell PATH lookup
* host-installed optional tools

All file traversal must be explicitly sorted.

## 9. Failure Rules

Harness stages must:

* fail closed
* report all violations for that stage
* never partially succeed
* never suppress a violation

## 10. Governance

Any change to:

* `tools/harness/*`
* `tools/*.sh`
* `Makefile`
* `HARNESS_CONTRACT.md`

must preserve this contract.

If implementation and this contract disagree, the implementation is wrong.

---
