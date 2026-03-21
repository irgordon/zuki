#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

from common import Violation, emit_failures, emit_ok, list_repo_files, main_guard, read_scan_text, rel

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

EXCLUDED_FILES = {
    "tools/harness/verify_determinism.py",
}

BANNED_PATTERNS = [
    ("date", re.compile(r"\bdate\b")),
    ("uuidgen", re.compile(r"\buuidgen\b")),
    ("/dev/urandom", re.compile(r"/dev/urandom")),
    ("$RANDOM", re.compile(r"\$RANDOM\b")),
    ("shuf", re.compile(r"\bshuf\b")),
    ("curl", re.compile(r"\bcurl\b")),
    ("wget", re.compile(r"\bwget\b")),
]


def should_scan(path: Path) -> bool:
    rp = rel(path)
    if rp in EXCLUDED_FILES:
        return False
    if rp in CHECKED_FILES:
        return True
    return any(rp.startswith(prefix) for prefix in CHECKED_PREFIXES)


def run() -> int:
    violations: list[Violation] = []

    for path in list_repo_files():
        if not should_scan(path):
            continue
        text = read_scan_text(path)
        if text is None:
            continue
        lines = text.splitlines()
        for token, pattern in BANNED_PATTERNS:
            for i, line in enumerate(lines, start=1):
                if pattern.search(line):
                    detail = f"{token} @ line {i}: {line}"
                    violations.append(Violation(STAGE, "nondeterministic_token", rel(path), detail))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "determinism verification passed")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
