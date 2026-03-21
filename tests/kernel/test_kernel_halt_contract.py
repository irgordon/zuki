from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INCLUDE_DIR = REPO_ROOT / "kernel" / "include"
SOURCE_DIR = REPO_ROOT / "kernel" / "src"
HALT_HEADER = INCLUDE_DIR / "kernel_halt.h"
HALT_SOURCE = SOURCE_DIR / "kernel_halt.c"

HALT_DECLARATION = "__attribute__((noreturn)) void kernel_halt(kernel_status_t reason);"
HALT_DEFINITION = "__attribute__((noreturn)) void kernel_halt(kernel_status_t reason) {"

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

FORBIDDEN_ALTERNATE_SYMBOL_PATTERNS = (
    r"\bhalt_now\b",
    r"\bkernel_halt_now\b",
    r"\bkernel_stop\b",
    r"\bkernel_shutdown\b",
)


class KernelHaltContractTests(unittest.TestCase):
    def test_kernel_halt_header_exists(self) -> None:
        self.assertTrue(HALT_HEADER.exists())

    def test_kernel_halt_declaration_is_exact_and_singular(self) -> None:
        text = self.read_text(HALT_HEADER)
        self.assertIn('#include "kernel_status.h"', text)
        self.assertEqual(text.count(HALT_DECLARATION), 1)

    def test_kernel_halt_definition_is_exact_and_singular(self) -> None:
        text = self.read_text(HALT_SOURCE)
        self.assertEqual(text.count(HALT_DEFINITION), 1)

    def test_kernel_halt_has_exactly_one_empty_for_loop_and_no_other_branching(self) -> None:
        text = self.read_text(HALT_SOURCE)
        self.assertEqual(text.count("for (;;) {"), 1)
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotIn("?", text)
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")
        self.assertEqual(text.count("for"), 1)
        self.assertRegex(text, r"for\s*\(\s*;\s*;\s*\)\s*\{\s*\}")

    def test_kernel_halt_does_not_use_reason_or_define_globals(self) -> None:
        text = self.read_text(HALT_SOURCE)
        self.assertEqual(text.count("reason"), 1)
        top_level_lines = tuple(
            line
            for line in text.splitlines()
            if line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        )
        self.assertEqual(top_level_lines, (HALT_DEFINITION, "}"))

    def test_kernel_halt_has_no_forbidden_includes_calls_or_alternate_symbols(self) -> None:
        header_text = self.read_text(HALT_HEADER)
        source_text = self.read_text(HALT_SOURCE)
        for token in FORBIDDEN_INCLUDES:
            with self.subTest(token=token):
                self.assertNotIn(token, header_text)
                self.assertNotIn(token, source_text)
        for token in FORBIDDEN_CALLS:
            with self.subTest(token=token):
                self.assertNotIn(token, source_text)
        scrubbed = "\n".join(
            self.scrub_comments_and_strings(path.read_text(encoding="utf-8"))
            for path in sorted(INCLUDE_DIR.glob("*.h")) + sorted(SOURCE_DIR.glob("*.c"))
        )
        for pattern in FORBIDDEN_ALTERNATE_SYMBOL_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, scrubbed))

    def scrub_comments_and_strings(self, text: str) -> str:
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = re.sub(r"//.*", " ", text)
        text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        return text

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
