#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from common import Violation, emit_failures, emit_ok, list_repo_files, main_guard, read_text, rel

STAGE = "verify_resources"

MAX_HARNESS_FILE_BYTES = 64 * 1024
MAX_LINE_LENGTH = 200
OBVIOUS_LOOP_MARKERS = (
    "while" + " true",
    "until" + " false",
)

WRAPPER_FILES = {
    "tools/verify_structure.sh",
    "tools/verify_policy.sh",
    "tools/verify_schema.sh",
    "tools/run_tests.sh",
    "tools/verify_determinism.sh",
    "tools/verify_resources.sh",
}


def run() -> int:
    violations: list[Violation] = []

    for path in list_repo_files():
        rp = rel(path)
        if rp.startswith("tools/harness/") or rp in WRAPPER_FILES:
            size = path.stat().st_size
            if size > MAX_HARNESS_FILE_BYTES:
                violations.append(Violation(STAGE, "file_too_large", rp, f"bytes={size} max={MAX_HARNESS_FILE_BYTES}"))

            for i, line in enumerate(read_text(path).splitlines(), start=1):
                if len(line) > MAX_LINE_LENGTH:
                    violations.append(Violation(STAGE, "line_too_long", rp, f"line={i} len={len(line)} max={MAX_LINE_LENGTH}"))

                if any(marker in line for marker in OBVIOUS_LOOP_MARKERS):
                    violations.append(Violation(STAGE, "obvious_unbounded_loop", rp, f"line={i}: {line}"))

    if violations:
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, "resource verification passed")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
