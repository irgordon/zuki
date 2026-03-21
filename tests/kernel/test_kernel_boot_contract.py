from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY_HEADER = REPO_ROOT / "kernel" / "include" / "kernel_entry.h"
LIFECYCLE_HEADER = REPO_ROOT / "kernel" / "include" / "kernel_lifecycle.h"
LIFECYCLE_SOURCE = REPO_ROOT / "kernel" / "src" / "kernel_lifecycle.c"
ENTRY_SOURCE = REPO_ROOT / "kernel" / "src" / "kernel_entry.c"

ENTRY_DECLARATION = "kernel_status_t kernel_entry(void);"
ENTRY_DEFINITION_SIGNATURE = "kernel_status_t kernel_entry(void) {"
ENTRY_RETURN = "return KERNEL_STATUS_OK;"
LIFECYCLE_DECLARATION = "kernel_lifecycle_state_t kernel_lifecycle_get_state(void);"
LIFECYCLE_DEFINITION_SIGNATURE = "kernel_lifecycle_state_t kernel_lifecycle_get_state(void) {"
LIFECYCLE_RETURN = "return KERNEL_LIFECYCLE_STATE_BOOTSTRAP;"

FORBIDDEN_SOURCE_TOKENS = (
    "printf",
    "fprintf",
    "puts",
    "malloc",
    "calloc",
    "realloc",
    "free",
    "getenv",
    "environ",
    "fork",
    "exec",
    "open(",
    "read(",
    "write(",
    "volatile",
    "asm",
    "__asm__",
    "outb",
    "inb",
    "interrupt",
    "scheduler",
    "mm_",
    "ipc_",
    "syscall",
    "kernel_lifecycle_enter",
    "kernel_lifecycle_phase_t",
    "kernel_lifecycle_current",
)

class KernelBootContractTests(unittest.TestCase):
    def test_exactly_one_public_entrypoint_declaration_exists(self) -> None:
        text = self.read_text(ENTRY_HEADER)
        self.assertEqual(text.count(ENTRY_DECLARATION), 1)

    def test_exactly_one_entry_implementation_exists(self) -> None:
        text = self.read_text(ENTRY_SOURCE)
        self.assertEqual(text.count(ENTRY_DEFINITION_SIGNATURE), 1)
        self.assertEqual(text.count("kernel_entry("), 1)

    def test_lifecycle_contract_is_state_based_and_accessor_only(self) -> None:
        header_text = self.read_text(LIFECYCLE_HEADER)
        source_text = self.read_text(LIFECYCLE_SOURCE)
        self.assertIn("kernel_lifecycle_state_t", header_text)
        self.assertIn("KERNEL_LIFECYCLE_STATE_BOOTSTRAP", header_text)
        self.assertEqual(header_text.count(LIFECYCLE_DECLARATION), 1)
        self.assertEqual(source_text.count(LIFECYCLE_DEFINITION_SIGNATURE), 1)
        self.assertEqual(source_text.count(LIFECYCLE_RETURN), 1)
        self.assertNotIn("kernel_status_t kernel_lifecycle", header_text)
        self.assertNotIn("kernel_status_t kernel_lifecycle", source_text)

    def test_entry_contract_uses_exactly_one_result_type(self) -> None:
        header_text = self.read_text(ENTRY_HEADER)
        source_text = self.read_text(ENTRY_SOURCE)
        self.assertEqual(header_text.count("kernel_status_t"), 1)
        self.assertEqual(source_text.count("kernel_status_t"), 1)
        self.assertNotIn("enum kernel_status kernel_entry", header_text)
        self.assertNotIn("enum kernel_status kernel_entry", source_text)

    def test_entry_return_contract_is_single_and_deterministic(self) -> None:
        text = self.read_text(ENTRY_SOURCE)
        self.assertEqual(text.count(ENTRY_RETURN), 1)
        self.assertEqual(text.count("return"), 1)
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotRegex(text, r"\bfor\b")
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")

    def test_entry_includes_lifecycle_and_calls_accessor_once(self) -> None:
        text = self.read_text(ENTRY_SOURCE)
        self.assertIn('#include "kernel_lifecycle.h"', text)
        self.assertEqual(text.count("kernel_lifecycle_get_state("), 1)
        self.assertIn("(void)kernel_lifecycle_get_state();", text)

    def test_boot_path_is_linear_entry_to_lifecycle_to_return(self) -> None:
        text = self.read_text(ENTRY_SOURCE)
        include_index = text.index('#include "kernel_lifecycle.h"')
        call_index = text.index("(void)kernel_lifecycle_get_state();")
        return_index = text.index(ENTRY_RETURN)
        self.assertLess(include_index, call_index)
        self.assertLess(call_index, return_index)

    def test_entry_source_has_no_hidden_global_mutable_authority(self) -> None:
        text = self.read_text(ENTRY_SOURCE)
        top_level_lines = tuple(
            line
            for line in text.splitlines()
            if line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        )
        self.assertEqual(top_level_lines, (ENTRY_DEFINITION_SIGNATURE, "}"))
        for token in FORBIDDEN_SOURCE_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_lifecycle_source_has_no_hidden_global_mutable_authority(self) -> None:
        text = self.read_text(LIFECYCLE_SOURCE)
        top_level_lines = tuple(
            line
            for line in text.splitlines()
            if line
            and not line.startswith(" ")
            and not line.startswith("\t")
            and not line.startswith("#")
        )
        self.assertEqual(top_level_lines, (LIFECYCLE_DEFINITION_SIGNATURE, "}"))
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotRegex(text, r"\bfor\b")
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")
        for token in FORBIDDEN_SOURCE_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
