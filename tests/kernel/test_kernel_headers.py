from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INCLUDE_DIR = REPO_ROOT / "kernel" / "include"

EXPECTED_HEADER_FILES = (
    "kernel_entry.h",
    "kernel_fault_reason.h",
    "kernel_halt.h",
    "kernel_lifecycle.h",
    "kernel_panic.h",
    "kernel_status.h",
    "kernel_types.h",
)

EXPECTED_STATUS_CODES = (
    "KERNEL_STATUS_OK = 0",
    "KERNEL_STATUS_INVALID_ARGUMENT = 1",
    "KERNEL_STATUS_UNSUPPORTED = 2",
    "KERNEL_STATUS_INTERNAL_ERROR = 3",
)


class KernelHeaderTests(unittest.TestCase):
    def test_header_files_exist(self) -> None:
        self.assertEqual(tuple(path.name for path in sorted(INCLUDE_DIR.glob("*.h"))), EXPECTED_HEADER_FILES)

    def test_fixed_width_types_are_defined(self) -> None:
        text = self.read_header("kernel_types.h")
        for typedef_name in (
            "kernel_u8",
            "kernel_u16",
            "kernel_u32",
            "kernel_u64",
            "kernel_i8",
            "kernel_i16",
            "kernel_i32",
            "kernel_i64",
        ):
            with self.subTest(typedef_name=typedef_name):
                self.assertIn(typedef_name, text)

    def test_status_codes_are_stable(self) -> None:
        text = self.read_header("kernel_status.h")
        for code_line in EXPECTED_STATUS_CODES:
            with self.subTest(code_line=code_line):
                self.assertIn(code_line, text)
        self.assertIn("typedef enum kernel_status kernel_status_t;", text)

    def test_entrypoint_prototype_is_stable(self) -> None:
        text = self.read_header("kernel_entry.h")
        self.assertRegex(text, r"kernel_status_t kernel_entry\(void\);")
        self.assertNotIn("enum kernel_status kernel_entry(void);", text)

    def test_public_contract_uses_single_status_type(self) -> None:
        status_text = self.read_header("kernel_status.h")
        entry_text = self.read_header("kernel_entry.h")
        self.assertIn("kernel_status_t", status_text)
        self.assertIn("kernel_status_t kernel_entry(void);", entry_text)
        self.assertNotIn("enum kernel_status kernel_entry", entry_text)

    def test_lifecycle_contract_uses_single_canonical_state_type(self) -> None:
        text = self.read_header("kernel_lifecycle.h")
        self.assertIn("enum kernel_lifecycle_state", text)
        self.assertIn("KERNEL_LIFECYCLE_STATE_BOOTSTRAP = 0", text)
        self.assertIn("typedef enum kernel_lifecycle_state kernel_lifecycle_state_t;", text)
        self.assertIn("kernel_lifecycle_state_t kernel_lifecycle_get_state(void);", text)
        self.assertNotIn("kernel_lifecycle_phase_t", text)
        self.assertNotIn("kernel_lifecycle_enter", text)
        self.assertNotIn("kernel_lifecycle_current", text)

    def test_headers_are_source_only_and_toolchain_free(self) -> None:
        for path in sorted(INCLUDE_DIR.glob("*.h")):
            with self.subTest(header=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("cc", text)
                self.assertNotIn("gcc", text)
                self.assertNotIn("clang", text)
                self.assertNotIn("ld", text)
                self.assertNotIn("objdump", text)
                self.assertIn("#ifndef", text)
                self.assertIn("#define", text)
                self.assertIn("#endif", text)

    def test_panic_contract_is_declared_as_singular_noreturn_surface(self) -> None:
        text = self.read_header("kernel_panic.h")
        self.assertIn('#include "kernel_fault_reason.h"', text)
        self.assertNotIn("kernel_status_t reason", text)
        self.assertEqual(text.count("__attribute__((noreturn)) void kernel_panic(kernel_fault_reason_t reason);"), 1)

    def test_halt_contract_is_declared_as_singular_noreturn_surface(self) -> None:
        text = self.read_header("kernel_halt.h")
        self.assertIn('#include "kernel_status.h"', text)
        self.assertEqual(text.count("__attribute__((noreturn)) void kernel_halt(kernel_status_t reason);"), 1)

    def read_header(self, header_name: str) -> str:
        return (INCLUDE_DIR / header_name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
