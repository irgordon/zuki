#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class Violation:
    stage: str
    rule: str
    path: str
    detail: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    return path.resolve().relative_to(repo_root()).as_posix()


def emit_ok(stage: str, message: str) -> int:
    print(json.dumps({
        "status": "ok",
        "stage": stage,
        "message": message,
    }, sort_keys=True))
    return 0


def emit_failures(stage: str, violations: Iterable[Violation]) -> int:
    count = 0
    for v in sorted(violations, key=lambda x: (x.path, x.rule, x.detail)):
        print(json.dumps({
            "status": "fail",
            "stage": stage,
            "rule": v.rule,
            "path": v.path,
            "detail": v.detail,
        }, sort_keys=True))
        count += 1
    return 1 if count else 0


def list_repo_files() -> List[Path]:
    root = repo_root()
    files: List[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if parts and parts[0] == ".git":
            continue
        files.append(p)
    files.sort(key=lambda p: rel(p))
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_executable(path: Path) -> bool:
    return os.access(path, os.X_OK)


def main_guard(stage: str, fn) -> int:
    try:
        return fn()
    except Exception as exc:  # fail closed
        v = Violation(stage=stage, rule="internal_error", path=".", detail=str(exc))
        return emit_failures(stage, [v])


if __name__ == "__main__":
    raise SystemExit("import only")
