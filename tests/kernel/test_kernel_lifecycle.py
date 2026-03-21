from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIFECYCLE_HEADER = REPO_ROOT / "kernel" / "include" / "kernel_lifecycle.h"
LIFECYCLE_SOURCE = REPO_ROOT / "kernel" / "src" / "kernel_lifecycle.c"

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
    "interrupt",
    "scheduler",
    "mm_",
    "ipc_",
    "syscall",
)


class KernelLifecycleTests(unittest.TestCase):
    def test_lifecycle_header_exists(self) -> None:
        self.assertTrue(LIFECYCLE_HEADER.exists())

    def test_lifecycle_symbols_are_declared(self) -> None:
        text = self.read_text(LIFECYCLE_HEADER)
        self.assertIn("enum kernel_lifecycle_state", text)
        self.assertIn("KERNEL_LIFECYCLE_STATE_BOOTSTRAP = 0", text)
        self.assertIn("typedef enum kernel_lifecycle_state kernel_lifecycle_state_t;", text)
        self.assertIn("kernel_lifecycle_state_t kernel_lifecycle_get_state(void);", text)
        self.assertNotIn("kernel_lifecycle_phase_t", text)
        self.assertNotIn("kernel_lifecycle_enter", text)
        self.assertNotIn("kernel_lifecycle_current", text)

    def test_lifecycle_source_definitions_exist(self) -> None:
        text = self.read_text(LIFECYCLE_SOURCE)
        self.assertIn('#include "kernel_lifecycle.h"', text)
        self.assertIn("kernel_lifecycle_state_t kernel_lifecycle_get_state(void) {", text)
        self.assertIn("return KERNEL_LIFECYCLE_STATE_BOOTSTRAP;", text)
        self.assertNotIn("kernel_lifecycle_enter", text)
        self.assertNotIn("kernel_lifecycle_current", text)

    def test_lifecycle_source_is_inert_and_toolchain_free(self) -> None:
        text = self.read_text(LIFECYCLE_SOURCE)
        for token in FORBIDDEN_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)
        self.assertEqual(text.count("return"), 1)
        self.assertNotRegex(text, r"\bif\b")
        self.assertNotRegex(text, r"\bswitch\b")
        self.assertNotRegex(text, r"\bfor\b")
        self.assertNotRegex(text, r"\bwhile\b")
        self.assertNotRegex(text, r"\bdo\b")

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
