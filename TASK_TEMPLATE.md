# TASK_TEMPLATE.md — Agent Task Specification

Status: Binding  
Scope: All agent-generated code  
Purpose: Constrain implementation scope and prevent architectural drift.

Every task must follow this format.

---

# Task Title

Short, specific description of the implementation objective.

Example:

Implement AST node definitions for binding and invocation.

---

# Objective

Describe exactly what must be implemented.

The objective must be:

- measurable
- bounded
- deterministic

Do not describe intent.  
Describe deliverable behavior.

---

# Scope

List the files or directories that may be modified.

Example:

Allowed paths:

shell/ast/**
shell/parser/**
tests/parser/**

All other files are read-only.

---

# Forbidden Changes

Explicitly list prohibited modifications.

Example:

Must not modify:

runtime/**
kernel/**
scheduler/**
capabilities/**
network/**
filesystem/**

---

# Required Behavior

Define observable behavior that must exist after implementation.

Example:

Parser must:

- parse binding statements
- parse invocation statements
- parse pipelines
- produce canonical AST nodes
- reject invalid syntax deterministically

---

# Invariants

List architectural rules that must remain true.

Example:

- execution units produce exactly one result
- resolution is deterministic
- authority is explicit
- buffers remain bounded

---

# Validation Requirements

Define the tests that must pass.

Example:

Required:

- parser unit tests pass
- invalid syntax tests fail deterministically
- AST normalization tests pass
- verification pipeline succeeds

---

# Non-Goals

Explicitly list what must NOT be implemented.

Example:

Do not implement:

- runtime execution
- capability validation
- scheduling
- concurrency
- filesystem access

---

# Deliverables

List expected outputs.

Example:

- AST node definitions
- parser implementation
- unit tests
- documentation update (if required)

---

# Exit Criteria

The task is complete only if:

- all tests pass
- verification succeeds
- no forbidden files changed
- invariants remain true

Partial completion is not acceptable.

---

# End of TASK_TEMPLATE.md
