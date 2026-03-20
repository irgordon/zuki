# VERIFY.md — Repository Verification Contract

Status: Binding  
Scope: Entire repository  
Purpose: Define the behavior of `make verify`.

`make verify` is the single authoritative validation entry point.

All code changes must pass verification before merge.

---

# 1. Verification Model

Verification is deterministic.

Verification must:

- run automatically
- produce explicit results
- fail fast on violation
- detect architectural drift

Verification must not:

- rely on developer judgment
- depend on external state
- skip validation steps

---

# 2. Verification Stages

Verification runs in strict order.

---

## Stage 1 — Repository Integrity

Checks:

- required directories exist
- required configuration files exist
- repository structure is valid

Failure condition:

Missing required structure.

---

## Stage 2 — Static Policy Enforcement

Checks:

- banned imports
- forbidden patterns
- layer violations
- global mutable state
- implicit authority sources

Failure condition:

Any prohibited pattern detected.

---

## Stage 3 — Schema Validation

Checks:

- AST node definitions match schema
- error categories match specification
- command set matches canonical list

Failure condition:

Schema mismatch detected.

---

## Stage 4 — Unit Tests

Checks:

- parser behavior
- AST construction
- error handling
- deterministic execution plan generation

Failure condition:

Any test fails.

---

## Stage 5 — Determinism Tests

Checks:

- identical input produces identical AST
- execution plan stability
- failure reproducibility

Failure condition:

Non-deterministic behavior detected.

---

## Stage 6 — Resource Safety Checks

Checks:

- pipeline buffers are bounded
- recursion depth is bounded
- memory allocation limits respected

Failure condition:

Unbounded resource usage detected.

---

## Stage 7 — Final Gate

Checks:

- all prior stages succeeded
- repository state is consistent

If any stage fails:

Verification fails immediately.

---

# 3. Output Requirements

Verification must print:

Verification Status: PASS or FAIL

If FAIL:

It must print:

- failing stage
- failing rule
- file location
- line number (if applicable)

No silent failures.

---

# 4. Exit Codes

```

0 — Verification succeeded
1 — Verification failed
2 — Internal verification error

```

---

# 5. Required Command

The repository must provide:

```

make verify

```

This command must:

- execute all verification stages
- produce deterministic output
- return correct exit code

No alternate verification entry points are permitted.

---

# 6. Continuous Integration Rule

CI must run:

```

make verify

```

on:

- every commit
- every pull request
- every agent-generated patch

Merge is prohibited if verification fails.

---

# End of VERIFY.md
