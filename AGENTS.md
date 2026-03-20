# AGENTS.md — Agent Execution Gate

Status: Binding  
Scope: All automated agents and code assistants

This repository is controlled by three canonical files:

- ARCH_RULES.md
- TASK_TEMPLATE.md
- VERIFY.md

Agents must follow them.  
No additional interpretation is permitted.

---

# Required Behavior

Before performing any work, an agent must:

1. Read ARCH_RULES.md
2. Read TASK_TEMPLATE.md
3. Read VERIFY.md
4. Execute only a valid task defined using TASK_TEMPLATE.md

If any of these are missing or unclear:

Stop.

---

# Execution Rule

Agents may modify only files explicitly allowed by the active task.

Agents must not:

- expand scope
- invent architecture
- modify control files
- bypass validation

---

# Verification Rule

All changes must pass:

make verify

If verification fails:

Stop.

Do not proceed.

---

# Governance Rule

The following files are protected:

- ARCH_RULES.md
- TASK_TEMPLATE.md
- VERIFY.md
- AGENTS.md

They may be modified only by explicit governance tasks.

---

# Default Rule

If uncertain:

Stop.

---

# End of AGENTS.md
