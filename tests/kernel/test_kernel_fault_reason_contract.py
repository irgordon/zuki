from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_PATH = REPO_ROOT / "kernel" / "include" / "kernel_fault_reason.h"

FORBIDDEN_IDENTIFIER_PATTERNS = (
    r"\brecover\b",
    r"\bretry\b",
    r"\brestart\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhandler\b",
    r"\bcallback\b",
    r"\bdispatch\b",
    r"\bschedule\b",
    r"\bthread\b",
    r"\bprocess\b",
    r"\bdevice\b",
    r"\bmemory\b",
    r"\binterrupt\b",
)

FORBIDDEN_INCLUDE_PATTERNS = (
    r'#include\s+<stdio\.h>',
    r'#include\s+<stdlib\.h>',
    r'#include\s+<string\.h>',
    r'#include\s+<assert\.h>',
    r'#include\s+<errno\.h>',
)


class KernelFaultReasonContractTests(unittest.TestCase):
    def test_fault_reason_header_exists(self) -> None:
        self.assertTrue(HEADER_PATH.exists())

    def test_fault_reason_type_is_defined_as_single_enum(self) -> None:
        text = self.read_text()
        self.assertEqual(text.count("typedef enum kernel_fault_reason"), 1)
        self.assertEqual(text.count("kernel_fault_reason_t;"), 1)
        self.assertNotIn("fault classification", self.scrub_comments_and_strings(text))

    def test_fault_reason_enum_contains_explicit_values(self) -> None:
        text = self.read_text()
        enumerators = re.findall(r'^\s*(KERNEL_FAULT_[A-Z0-9_]+)\s*=\s*([0-9]+)\s*,?$', text, flags=re.M)
        self.assertTrue(enumerators)
        self.assertIn(("KERNEL_FAULT_NONE", "0"), enumerators)
        for name, value in enumerators:
            with self.subTest(name=name):
                self.assertTrue(name.startswith("KERNEL_FAULT_"))
                self.assertEqual(name, name.upper())
                self.assertTrue(value.isdecimal())

    def test_fault_reason_header_has_exactly_one_include_guard(self) -> None:
        text = self.read_text()
        self.assertEqual(len(re.findall(r'^#ifndef\s+\w+$', text, flags=re.M)), 1)
        self.assertEqual(len(re.findall(r'^#define\s+\w+$', text, flags=re.M)), 1)
        self.assertEqual(len(re.findall(r'^#endif$', text, flags=re.M)), 1)

    def test_fault_reason_header_has_no_functions_or_extra_macros(self) -> None:
        text = self.read_text()
        scrubbed = self.scrub_comments_and_strings(text)
        self.assertEqual(len(re.findall(r'^#(ifndef|define|endif)\b', text, flags=re.M)), 3)
        self.assertIsNone(re.search(r'\b[A-Za-z_]\w*\s+\**\s*[A-Za-z_]\w*\s*\([^;{}]*\)\s*;', scrubbed))
        self.assertIsNone(re.search(r'^\s*#(?!ifndef\b|define\b|endif\b)', text, flags=re.M))

    def test_fault_reason_header_has_no_forbidden_includes(self) -> None:
        text = self.read_text()
        for pattern in FORBIDDEN_INCLUDE_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, text))

    def test_fault_reason_header_has_no_alternate_fault_reason_types(self) -> None:
        text = self.read_text()
        typedefs = re.findall(r'typedef\s+enum\s+([A-Za-z_]\w*)\s*\{', text)
        self.assertEqual(typedefs, ["kernel_fault_reason"])
        self.assertEqual(re.findall(r'}\s*([A-Za-z_]\w*)\s*;', text), ["kernel_fault_reason_t"])

    def test_fault_reason_header_has_no_forbidden_semantic_identifiers(self) -> None:
        scrubbed = self.scrub_comments_and_strings(self.read_text())
        for pattern in FORBIDDEN_IDENTIFIER_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, scrubbed))

    def read_text(self) -> str:
        return HEADER_PATH.read_text(encoding="utf-8")

    def scrub_comments_and_strings(self, text: str) -> str:
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        text = re.sub(r"//.*", " ", text)
        text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        return text


if __name__ == "__main__":
    unittest.main()
