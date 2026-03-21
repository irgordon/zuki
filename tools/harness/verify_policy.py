#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common import Violation, emit_failures, emit_ok, list_repo_files, main_guard, read_text, rel, repo_root

STAGE = "verify_policy"

BANNED_PATTERNS = [
    "PATH=",
    "getenv(",
    "os.Getenv",
    "std::env",
    "subprocess.Popen",
    "fork(",
    "execvp",
    "daemon(",
    "nohup",
]

EXCLUDED_PREFIXES = [
    ".git/",
    ".github/workflows/",
]

EXCLUDED_FILES = {
    "tools/verify_policy.sh",
    "tools/harness/verify_policy.py",
}


def should_scan(path: Path) -> bool:
    rp = rel(path)
    if rp in EXCLUDED_FILES:
        return False
    for prefix in EXCLUDED_PREFIXES:
        if rp.startswith(prefix):
            return False
    return True


def run() -> int:
    violations: list[Violation] = []

    for path in list_repo_files():
        if not should_scan(path):
            continue
        text = read_text(path)
        lines = text.splitlines()
        for pattern in BANNED_PATTERNS:
            for i, line in enumerate(lines, start=1):
                if pattern in line:
                    detail = f"{pattern} @ line {i}: {line}"
                    violations.append(Violation(STAGE, "banned_pattern", rel(path), detail))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "policy verification passed")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
