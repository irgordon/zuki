from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "kernel" / "src"

EXPECTED_SOURCE_FILES = (
    "kernel_assert.c",
    "kernel_contract_placeholders.c",
    "kernel_entry.c",
    "kernel_halt.c",
    "kernel_lifecycle.c",
    "kernel_panic.c",
    "kernel_status_placeholders.c",
)

FORBIDDEN_TOKENS = (
    "printf",
    "fprintf",
    "puts",
    "malloc",
    "calloc",
    "realloc",
    "free",
    "asm",
    "__asm__",
    "volatile",
    "outb",
    "inb",
)


class KernelSourceTests(unittest.TestCase):
    def test_source_files_exist(self) -> None:
        self.assertEqual(tuple(path.name for path in sorted(SOURCE_DIR.glob("*.c"))), EXPECTED_SOURCE_FILES)

    def test_sources_are_structural_and_toolchain_free(self) -> None:
        for source_path in sorted(SOURCE_DIR.glob("*.c")):
            with self.subTest(source=source_path.name):
                text = source_path.read_text(encoding="utf-8")
                self.assertNotIn("cc", text)
                self.assertNotIn("gcc", text)
                self.assertNotIn("clang", text)
                self.assertNotIn("ld", text)

    def test_sources_contain_no_forbidden_tokens_or_behavioral_forms(self) -> None:
        for source_path in sorted(SOURCE_DIR.glob("*.c")):
            with self.subTest(source=source_path.name):
                text = source_path.read_text(encoding="utf-8")
                for token in FORBIDDEN_TOKENS:
                    self.assertNotIn(token, text)
                significant_lines = tuple(
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                )
                self.assertTrue(significant_lines)
                self.assertTrue(all(
                    line.startswith("#include")
                    or line.startswith("_Static_assert")
                    or line == "__attribute__((noreturn)) void kernel_assert(kernel_fault_reason_t reason) {"
                    or line == "kernel_status_t kernel_entry(void) {"
                    or line == "__attribute__((noreturn)) void kernel_halt(kernel_status_t reason) {"
                    or line == "kernel_lifecycle_state_t kernel_lifecycle_get_state(void) {"
                    or line == "__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason) {"
                    or line == "(void)kernel_lifecycle_get_state();"
                    or line == "(void)reason;"
                    or line == "for (;;) {"
                    or line == "return KERNEL_STATUS_OK;"
                    or line == "return KERNEL_LIFECYCLE_STATE_BOOTSTRAP;"
                    or line == "__builtin_trap();"
                    or line == "__builtin_unreachable();"
                    or line == "}"
                    for line in significant_lines
                ))

    def test_kernel_entry_symbol_exists_at_source_contract_level(self) -> None:
        text = (SOURCE_DIR / "kernel_entry.c").read_text(encoding="utf-8")
        self.assertIn('#include "kernel_entry.h"', text)
        self.assertIn('#include "kernel_lifecycle.h"', text)
        self.assertIn("kernel_status_t kernel_entry(void)", text)

    def test_kernel_entry_return_behavior_is_deterministic(self) -> None:
        text = (SOURCE_DIR / "kernel_entry.c").read_text(encoding="utf-8")
        self.assertIn("return KERNEL_STATUS_OK;", text)
        self.assertEqual(text.count("return"), 1)


if __name__ == "__main__":
    unittest.main()
