from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INCLUDE_DIR = REPO_ROOT / "kernel" / "include"
SOURCE_DIR = REPO_ROOT / "kernel" / "src"
ASSERT_HEADER = INCLUDE_DIR / "kernel_assert.h"
ASSERT_SOURCE = SOURCE_DIR / "kernel_assert.c"

ASSERT_DECLARATION = "__attribute__((noreturn)) void kernel_assert(kernel_fault_reason_t reason);"
ASSERT_DEFINITION = "__attribute__((noreturn)) void kernel_assert(kernel_fault_reason_t reason) {"

FORBIDDEN_INCLUDES = (
    "#include <stdio.h>",
    "#include <stdlib.h>",
    "#include <assert.h>",
    "#include <string.h>",
)

FORBIDDEN_ALTERNATE_ASSERT_PATTERNS = (
    r"\bkernel_assert_fail\b",
    r"\bassert_fail\b",
    r"\bassert_now\b",
    r"\bkernel_fail\b",
)


class KernelAssertContractTests(unittest.TestCase):
    def test_kernel_assert_header_exists(self) -> None:
        self.assertTrue(ASSERT_HEADER.exists())

    def test_kernel_assert_source_exists(self) -> None:
        self.assertTrue(ASSERT_SOURCE.exists())

    def test_kernel_assert_declaration_is_exact_and_singular(self) -> None:
        text = self.read_text(ASSERT_HEADER)
        self.assertIn('#include "kernel_fault_reason.h"', text)
        self.assertEqual(text.count(ASSERT_DECLARATION), 1)

    def test_kernel_assert_definition_is_exact_and_singular(self) -> None:
        text = self.read_text(ASSERT_SOURCE)
        self.assertEqual(text.count(ASSERT_DEFINITION), 1)

    def test_kernel_assert_is_noreturn_and_uses_canonical_fault_type(self) -> None:
        header_text = self.read_text(ASSERT_HEADER)
        source_text = self.read_text(ASSERT_SOURCE)
        self.assertIn("__attribute__((noreturn))", header_text)
        self.assertIn("__attribute__((noreturn))", source_text)
        self.assertIn("kernel_fault_reason_t reason", header_text)
        self.assertIn("kernel_fault_reason_t reason", source_text)
        self.assertNotIn("kernel_status_t reason", header_text)
        self.assertNotIn("kernel_status_t reason", source_text)

    def test_kernel_assert_source_is_inert_and_contains_one_empty_for_loop(self) -> None:
        text = self.read_text(ASSERT_SOURCE)
        self.assertEqual(text.count("for (;;) {"), 1)
        self.assertRegex(text, r"for\s*\(\s*;\s*;\s*\)\s*\{\s*\}")
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotIn("?", text)
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")
        self.assertEqual(len(re.findall(r"\breason\b", text)), 1)

    def test_kernel_assert_source_has_no_file_scope_variables(self) -> None:
        text = self.read_text(ASSERT_SOURCE)
        top_level_lines = tuple(
            line
            for line in text.splitlines()
            if line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        )
        self.assertEqual(top_level_lines, (ASSERT_DEFINITION, "}"))

    def test_kernel_assert_has_no_forbidden_includes_or_alternate_symbols(self) -> None:
        header_text = self.read_text(ASSERT_HEADER)
        source_text = self.read_text(ASSERT_SOURCE)
        for token in FORBIDDEN_INCLUDES:
            with self.subTest(token=token):
                self.assertNotIn(token, header_text)
                self.assertNotIn(token, source_text)
        scrubbed = "\n".join(
            self.scrub_comments_and_strings(path.read_text(encoding="utf-8"))
            for path in sorted(INCLUDE_DIR.glob("*.h")) + sorted(SOURCE_DIR.glob("*.c"))
        )
        for pattern in FORBIDDEN_ALTERNATE_ASSERT_PATTERNS:
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
