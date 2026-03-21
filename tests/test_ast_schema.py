from __future__ import annotations

import sys
import unittest
from dataclasses import fields
from pathlib import Path
from typing import get_args

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import ast as shell_ast


EXPECTED_EXPORTS = (
    "ASTValidationError",
    "Arg",
    "Binding",
    "BoolLiteral",
    "Command",
    "Expr",
    "Identifier",
    "IdentifierExpr",
    "IntLiteral",
    "Invocation",
    "InvokeForm",
    "ListExpr",
    "Literal",
    "NamedArg",
    "NodeKind",
    "NullLiteral",
    "Pipeline",
    "PositionalArg",
    "Program",
    "RecordExpr",
    "RecordField",
    "Statement",
    "StringLiteral",
    "validate_program",
)

EXPECTED_NODE_KIND_VALUES = (
    "Program",
    "Binding",
    "Pipeline",
    "Invocation",
    "InvokeForm",
    "NamedArg",
    "PositionalArg",
    "IdentifierExpr",
    "ListExpr",
    "RecordExpr",
    "RecordField",
    "StringLiteral",
    "IntLiteral",
    "BoolLiteral",
    "NullLiteral",
    "Identifier",
)

EXPECTED_FIELDS = {
    shell_ast.Identifier: ("text", "kind"),
    shell_ast.StringLiteral: ("value", "kind"),
    shell_ast.IntLiteral: ("value", "kind"),
    shell_ast.BoolLiteral: ("value", "kind"),
    shell_ast.NullLiteral: ("kind",),
    shell_ast.IdentifierExpr: ("name", "kind"),
    shell_ast.ListExpr: ("elements", "kind"),
    shell_ast.RecordField: ("name", "value", "kind"),
    shell_ast.RecordExpr: ("fields", "kind"),
    shell_ast.NamedArg: ("name", "value", "kind"),
    shell_ast.PositionalArg: ("value", "kind"),
    shell_ast.Invocation: ("target", "method", "args", "kind"),
    shell_ast.InvokeForm: ("target", "method", "args", "kind"),
    shell_ast.Binding: ("name", "value", "kind"),
    shell_ast.Pipeline: ("stages", "kind"),
    shell_ast.Program: ("statements", "kind"),
}


class AstSchemaTests(unittest.TestCase):
    def make_invocation(self, target: str, method: str) -> shell_ast.Invocation:
        return shell_ast.Invocation(
            target=shell_ast.Identifier(text=target),
            method=shell_ast.Identifier(text=method),
            args=(),
        )

    def test_ast_exports_match_placeholder_surface(self) -> None:
        self.assertEqual(tuple(shell_ast.__all__), EXPECTED_EXPORTS)

    def test_node_kind_enum_matches_canonical_node_names(self) -> None:
        self.assertEqual(tuple(kind.value for kind in shell_ast.NodeKind), EXPECTED_NODE_KIND_VALUES)

    def test_node_dataclasses_are_frozen_and_have_expected_fields(self) -> None:
        for node_type, expected_fields in EXPECTED_FIELDS.items():
            with self.subTest(node_type=node_type.__name__):
                self.assertTrue(node_type.__dataclass_params__.frozen)
                self.assertEqual(tuple(field.name for field in fields(node_type)), expected_fields)

    def test_type_aliases_reference_expected_node_classes(self) -> None:
        self.assertEqual(get_args(shell_ast.Literal), (
            shell_ast.StringLiteral,
            shell_ast.IntLiteral,
            shell_ast.BoolLiteral,
            shell_ast.NullLiteral,
        ))
        self.assertEqual(get_args(shell_ast.Arg), (
            shell_ast.NamedArg,
            shell_ast.PositionalArg,
        ))
        self.assertEqual(get_args(shell_ast.Command), (
            shell_ast.Invocation,
            shell_ast.InvokeForm,
        ))
        self.assertEqual(get_args(shell_ast.Statement), (
            shell_ast.Binding,
            shell_ast.Pipeline,
            shell_ast.Invocation,
            shell_ast.InvokeForm,
        ))

    def test_program_preserves_statement_order(self) -> None:
        first = self.make_invocation("vfs", "open")
        second = self.make_invocation("inspect", "run")
        program = shell_ast.Program(statements=(first, second))
        self.assertEqual(program.statements, (first, second))

    def test_pipeline_requires_at_least_two_stages(self) -> None:
        first = self.make_invocation("dev", "list")
        second = self.make_invocation("inspect", "run")
        self.assertEqual(shell_ast.Pipeline(stages=(first, second)).stages, (first, second))
        with self.assertRaisesRegex(ValueError, "at least two stages"):
            shell_ast.Pipeline(stages=(first,))

    def test_invocation_forms_remain_distinct_node_kinds(self) -> None:
        target = shell_ast.Identifier(text="svc")
        method = shell_ast.Identifier(text="call")
        invocation = shell_ast.Invocation(target=target, method=method, args=())
        invoke_form = shell_ast.InvokeForm(target=target, method=method, args=())
        self.assertIsNot(type(invocation), type(invoke_form))
        self.assertEqual(invocation.kind, shell_ast.NodeKind.INVOCATION)
        self.assertEqual(invoke_form.kind, shell_ast.NodeKind.INVOKE_FORM)

    def test_runtime_only_values_are_not_literal_syntax_nodes(self) -> None:
        self.assertEqual(get_args(shell_ast.Literal), (
            shell_ast.StringLiteral,
            shell_ast.IntLiteral,
            shell_ast.BoolLiteral,
            shell_ast.NullLiteral,
        ))

    def test_identifier_preserves_lexical_text_exactly(self) -> None:
        identifier = shell_ast.Identifier(text="svc.open.raw")
        self.assertEqual(identifier.text, "svc.open.raw")

    def test_null_literal_has_no_payload_fields(self) -> None:
        payload_fields = tuple(field.name for field in fields(shell_ast.NullLiteral) if field.name != "kind")
        self.assertEqual(payload_fields, ())


if __name__ == "__main__":
    unittest.main()
