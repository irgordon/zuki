#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common import Violation, emit_failures, emit_ok, list_repo_files, main_guard, read_text, rel

STAGE = "verify_determinism"

CHECKED_FILES = {
    "Makefile",
    "ARCH_RULES.md",
    "TASK_TEMPLATE.md",
    "VERIFY.md",
    "AGENTS.md",
    "HARNESS_CONTRACT.md",
}

CHECKED_PREFIXES = [
    "tools/",
]

BANNED_TOKENS = [
    "date",
    "uuidgen",
    "/dev/urandom",
    "$RANDOM",
    "shuf",
    "curl",
    "wget",
]


def should_scan(path: Path) -> bool:
    rp = rel(path)
    if rp in CHECKED_FILES:
        return True
    return any(rp.startswith(prefix) for prefix in CHECKED_PREFIXES)


def run() -> int:
    violations: list[Violation] = []

    for path in list_repo_files():
        if not should_scan(path):
            continue
        lines = read_text(path).splitlines()
        for token in BANNED_TOKENS:
            for i, line in enumerate(lines, start=1):
                if token in line:
                    detail = f"{token} @ line {i}: {line}"
                    violations.append(Violation(STAGE, "nondeterministic_token", rel(path), detail))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "determinism verification passed")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
