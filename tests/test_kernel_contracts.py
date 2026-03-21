from __future__ import annotations

import inspect
import sys
import unittest
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import kernel as shell_kernel


EXPECTED_EXPORTS = (
    "KernelError",
    "KernelErrorKind",
    "KernelRuntimeContract",
    "ReceiveRequest",
    "ReceiveResult",
    "SendRequest",
    "SendResult",
    "ShutdownRequest",
    "ShutdownResult",
    "SpawnRequest",
    "SpawnResult",
)

EXPECTED_METHODS = (
    ("spawn", "request", shell_kernel.SpawnRequest, shell_kernel.SpawnResult),
    ("send", "request", shell_kernel.SendRequest, shell_kernel.SendResult),
    ("receive", "request", shell_kernel.ReceiveRequest, shell_kernel.ReceiveResult),
    ("shutdown", "request", shell_kernel.ShutdownRequest, shell_kernel.ShutdownResult),
)


class KernelContractTests(unittest.TestCase):
    def test_public_contract_surface_exists(self) -> None:
        self.assertEqual(tuple(shell_kernel.__all__), EXPECTED_EXPORTS)

    def test_error_surface_is_structural_and_explicit(self) -> None:
        self.assertEqual(tuple(kind.value for kind in shell_kernel.KernelErrorKind), (
            "spawn",
            "send",
            "receive",
            "shutdown",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.KernelError)), (
            "kind",
            "code",
            "detail",
        ))

    def test_request_parameter_definitions_exist(self) -> None:
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.SpawnRequest)), (
            "plan_id",
            "capability_handles",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.SendRequest)), (
            "handle_id",
            "payload",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.ReceiveRequest)), (
            "handle_id",
            "max_items",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.ShutdownRequest)), (
            "handle_id",
        ))

    def test_return_value_definitions_exist(self) -> None:
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.SpawnResult)), (
            "accepted",
            "handle_id",
            "error",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.SendResult)), (
            "accepted",
            "sequence_id",
            "error",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.ReceiveResult)), (
            "messages",
            "error",
        ))
        self.assertEqual(tuple(field.name for field in fields(shell_kernel.ShutdownResult)), (
            "accepted",
            "error",
        ))

    def test_kernel_contract_method_signatures_are_deterministic(self) -> None:
        for method_name, parameter_name, request_type, return_type in EXPECTED_METHODS:
            with self.subTest(method_name=method_name):
                method = getattr(shell_kernel.KernelRuntimeContract, method_name)
                signature = inspect.signature(method)
                type_hints = get_type_hints(method)
                parameters = tuple(signature.parameters.values())
                self.assertEqual(len(parameters), 2)
                self.assertEqual(parameters[1].name, parameter_name)
                self.assertEqual(type_hints[parameter_name], request_type)
                self.assertEqual(type_hints["return"], return_type)


if __name__ == "__main__":
    unittest.main()
