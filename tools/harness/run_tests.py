#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from common import Violation, emit_failures, emit_ok, main_guard, repo_root, rel

STAGE = "run_tests"


def discover_test_files() -> list[Path]:
    root = repo_root()
    test_dir = root / "tests"
    if not test_dir.exists():
        return []
    files = [p for p in test_dir.rglob("test_*.py") if p.is_file()]
    files.sort(key=lambda p: rel(p))
    return files


def load_suite(files: list[Path]) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader

    for path in files:
        module_name = "zuki_" + rel(path).replace("/", "_").replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load test module: {rel(path)}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


def run() -> int:
    files = discover_test_files()
    if not files:
        return emit_ok(STAGE, "no tests discovered")

    suite = load_suite(files)
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=1)
    result = runner.run(suite)
    if not result.wasSuccessful():
        violations = [Violation(STAGE, "test_failure", "tests", f"failures={len(result.failures)} errors={len(result.errors)}")]
        return emit_failures(STAGE, violations)
    return emit_ok(STAGE, f"tests passed: {suite.countTestCases()}")


if __name__ == "__main__":
    raise SystemExit(main_guard(STAGE, run))
