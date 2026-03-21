#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common import Violation, emit_failures, emit_ok, is_executable, main_guard, repo_root

STAGE = "verify_structure"

REQUIRED_FILES = [
    "ARCH_RULES.md",
    "TASK_TEMPLATE.md",
    "VERIFY.md",
    "AGENTS.md",
    "HARNESS_CONTRACT.md",
    "Makefile",
    "tools/verify_structure.sh",
    "tools/verify_policy.sh",
    "tools/verify_schema.sh",
    "tools/run_tests.sh",
    "tools/verify_determinism.sh",
    "tools/verify_resources.sh",
    "tools/harness/common.py",
    "tools/harness/verify_structure.py",
    "tools/harness/verify_policy.py",
    "tools/harness/verify_schema.py",
    "tools/harness/run_tests.py",
    "tools/harness/verify_determinism.py",
    "tools/harness/verify_resources.py",
]

REQUIRED_EXECUTABLES = [
    "tools/verify_structure.sh",
    "tools/verify_policy.sh",
    "tools/verify_schema.sh",
    "tools/run_tests.sh",
    "tools/verify_determinism.sh",
    "tools/verify_resources.sh",
]


def run() -> int:
    root = repo_root()
    violations: list[Violation] = []

    for rel_path in REQUIRED_FILES:
        p = root / rel_path
        if not p.exists():
            violations.append(Violation(STAGE, "missing_required_file", rel_path, "file not found"))

    for rel_path in REQUIRED_EXECUTABLES:
        p = root / rel_path
        if p.exists() and not is_executable(p):
            violations.append(Violation(STAGE, "non_executable_required_file", rel_path, "expected executable bit"))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "repository structure verified")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
