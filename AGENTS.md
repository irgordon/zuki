# AGENTS.md — Agent Execution Gate

Status: Binding  
Scope: All automated agents and code assistants  
Purpose: Constrain agent behavior to prevent architectural drift.

This repository is governed by four canonical control documents:

- ARCH_RULES.md
- TASK_TEMPLATE.md
- VERIFY.md
- AGENTS.md

Agents must follow them exactly.  
No additional interpretation is permitted.

---

# 1. Initialization Rule

Before performing any action, an agent must:

1. Read `ARCH_RULES.md`
2. Read `TASK_TEMPLATE.md`
3. Read `VERIFY.md`
4. Operate only within the bounds of an active task written using `TASK_TEMPLATE.md`

If any required document is missing, unreadable, or ambiguous:

**Stop immediately.**

---

# 2. Task Rule

An agent may act **only** when a valid task is active.

A valid task:

- uses `TASK_TEMPLATE.md`
- defines a bounded objective
- defines allowed paths
- defines forbidden paths
- defines required behavior
- defines invariants
- defines exit criteria

Agents must not:

- invent tasks  
- expand task scope  
- reinterpret task requirements  
- continue after task completion  

If the task is incomplete or unclear:

**Stop.**

---

# 3. Modification Rule

Agents may modify **only** the files explicitly listed in the task’s “Scope” section.

Agents must not:

- modify forbidden paths  
- modify control documents  
- modify unrelated modules  
- introduce new dependencies  
- restructure directories  
- alter build or CI configuration  

Unauthorized modifications are defects.

---

# 4. Execution Rule

Agents must:

- follow architectural guardrails in `ARCH_RULES.md`
- maintain deterministic behavior
- preserve layering boundaries
- avoid ambient authority
- avoid hidden concurrency
- avoid unbounded resources

Agents must not:

- infer missing architecture  
- generate speculative improvements  
- introduce fallback logic  
- create implicit authority  
- perform implicit retries  
- widen capability rights  

If uncertain:

**Stop.**

---

# 5. Verification Rule

Before producing a final patch, an agent must run:

```
make verify
```

Verification must:

- complete successfully  
- produce deterministic output  
- show no warnings  
- show no skipped tests  

If verification fails:

**Stop. Do not proceed.**

Agents must not attempt to “fix” verification by modifying forbidden files.

---

# 6. Governance Rule

The following files are protected:

- ARCH_RULES.md  
- TASK_TEMPLATE.md  
- VERIFY.md  
- AGENTS.md  

Agents must not modify these files unless executing an explicit governance task.

Governance tasks may only be created by maintainers.

---

# 7. Default Rule

If an agent encounters:

- ambiguity  
- missing information  
- conflicting instructions  
- unclear authority  
- unclear scope  
- unclear invariants  
- unclear expected behavior  

The agent must:

**Stop.**

Agents must never guess, infer, or assume.

---

# End of AGENTS.md 

Just tell me which one you want next.
