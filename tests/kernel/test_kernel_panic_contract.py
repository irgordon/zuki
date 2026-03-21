from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INCLUDE_DIR = REPO_ROOT / "kernel" / "include"
SOURCE_DIR = REPO_ROOT / "kernel" / "src"
PANIC_HEADER = INCLUDE_DIR / "kernel_panic.h"
PANIC_SOURCE = SOURCE_DIR / "kernel_panic.c"

PANIC_DECLARATION = "__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason);"
PANIC_DEFINITION = "__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason) {"

FORBIDDEN_INCLUDES = (
    "#include <stdio.h>",
    "#include <stdlib.h>",
    "#include <assert.h>",
    "#include <string.h>",
)

FORBIDDEN_CALLS = (
    "printf",
    "fprintf",
    "puts",
    "malloc",
    "calloc",
    "realloc",
    "free",
    "scheduler",
    "mm_",
    "ipc_",
    "outb",
    "inb",
    "device_",
)

FORBIDDEN_ALTERNATE_SYMBOLS = (
    r"\bpanic_now\b",
    r"\bkernel_panic_now\b",
    r"\bkernel_fatal\b",
)


class KernelPanicContractTests(unittest.TestCase):
    def test_kernel_panic_header_exists(self) -> None:
        self.assertTrue(PANIC_HEADER.exists())

    def test_kernel_panic_declaration_is_exact_and_singular(self) -> None:
        text = self.read_text(PANIC_HEADER)
        self.assertIn('#include "kernel_fault_reason.h"', text)
        self.assertEqual(text.count(PANIC_DECLARATION), 1)
        self.assertNotIn("kernel_status_t reason", text)
        self.assertNotRegex(text, r"\bint\s+kernel_panic\b")
        self.assertNotRegex(text, r"\bunsigned\s+kernel_panic\b")
        self.assertNotRegex(text, r"\blong\s+kernel_panic\b")
        self.assertNotIn("void *", text)
        self.assertNotIn("const char *", text)

    def test_kernel_panic_definition_is_exact_and_singular(self) -> None:
        text = self.read_text(PANIC_SOURCE)
        self.assertEqual(text.count(PANIC_DEFINITION), 1)
        self.assertEqual(text.count("__builtin_trap();"), 1)
        self.assertEqual(text.count("__builtin_unreachable();"), 1)
        self.assertNotIn("kernel_status_t reason", text)

    def test_kernel_panic_source_has_no_branching_or_reason_inspection(self) -> None:
        text = self.read_text(PANIC_SOURCE)
        self.assertIn("(void)reason;", text)
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotIn("?", text)
        self.assertNotRegex(text, r"\bfor\b")
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")
        self.assertNotIn("reason =", text)
        self.assertEqual(len(re.findall(r"\breason\b", text)), 2)

    def test_kernel_panic_source_has_no_forbidden_includes_calls_or_globals(self) -> None:
        text = self.read_text(PANIC_SOURCE)
        for token in FORBIDDEN_INCLUDES + FORBIDDEN_CALLS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)
        top_level_lines = tuple(
            line
            for line in text.splitlines()
            if line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        )
        self.assertEqual(top_level_lines, (PANIC_DEFINITION, "}"))

    def test_no_alternate_panic_symbols_exist_in_headers_or_sources(self) -> None:
        texts = tuple(
            path.read_text(encoding="utf-8")
            for path in sorted(INCLUDE_DIR.glob("*.h")) + sorted(SOURCE_DIR.glob("*.c"))
        )
        joined = "\n".join(texts)
        for pattern in FORBIDDEN_ALTERNATE_SYMBOLS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, joined))

    def test_panic_and_halt_use_canonical_distinct_taxonomies(self) -> None:
        panic_header = self.read_text(PANIC_HEADER)
        halt_header = (INCLUDE_DIR / "kernel_halt.h").read_text(encoding="utf-8")
        panic_source = self.read_text(PANIC_SOURCE)
        halt_source = (SOURCE_DIR / "kernel_halt.c").read_text(encoding="utf-8")
        self.assertIn("kernel_fault_reason_t reason", panic_header)
        self.assertIn("kernel_fault_reason_t reason", panic_source)
        self.assertIn("kernel_status_t reason", halt_header)
        self.assertIn("kernel_status_t reason", halt_source)
        self.assertNotIn("kernel_status_t reason", panic_header)
        self.assertNotIn("kernel_status_t reason", panic_source)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
