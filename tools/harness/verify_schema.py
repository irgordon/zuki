#!/usr/bin/env python3
from __future__ import annotations

from common import Violation, emit_failures, emit_ok, main_guard, read_text, repo_root

STAGE = "verify_schema"

REQUIRED_MARKERS = {
    "ARCH_RULES.md": [
        "No Ambient Authority",
        "Deterministic Boundary Behavior",
    ],
    "TASK_TEMPLATE.md": [
        "Objective",
        "Scope",
        "Invariants",
        "Exit Criteria",
    ],
    "VERIFY.md": [
        "make verify",
        "Verification Status: PASS or FAIL",
    ],
    "AGENTS.md": [
        "ARCH_RULES.md",
        "TASK_TEMPLATE.md",
        "VERIFY.md",
    ],
    "HARNESS_CONTRACT.md": [
        "closed-world",
        "structured success line",
        "newline-delimited JSON",
    ],
}


def run() -> int:
    root = repo_root()
    violations: list[Violation] = []

    for rel_path, markers in sorted(REQUIRED_MARKERS.items()):
        p = root / rel_path
        if not p.exists():
            violations.append(Violation(STAGE, "missing_required_file", rel_path, "file not found"))
            continue
        text = read_text(p)
        for marker in markers:
            if marker not in text:
                violations.append(Violation(STAGE, "missing_required_marker", rel_path, marker))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "schema verification passed")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
