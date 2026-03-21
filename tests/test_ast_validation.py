from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import ast as shell_ast


class AstValidationTests(unittest.TestCase):
    def test_valid_program_passes_validation(self) -> None:
        program = shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="home"),
                value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="root")),
            ),
            shell_ast.Pipeline(stages=(
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="svc"),
                    method=shell_ast.Identifier(text="open"),
                    args=(),
                ),
                shell_ast.InvokeForm(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(
                        shell_ast.NamedArg(
                            name=shell_ast.Identifier(text="mode"),
                            value=shell_ast.StringLiteral(value="fast"),
                        ),
                    ),
                ),
            )),
        ))
        shell_ast.validate_program(program)

    def test_pipeline_length_violation_fails_deterministically(self) -> None:
        invalid = self.make_invalid_pipeline()
        error = self.capture_validation_error(shell_ast.Program(statements=(invalid,)))
        self.assertEqual(error, shell_ast.ASTValidationError(
            rule="InvalidPipeline",
            path="root.statements[0].stages",
            detail="pipeline length must be at least 2",
        ))

    def test_binding_without_name_fails_deterministically(self) -> None:
        program = shell_ast.Program(statements=(
            shell_ast.Binding(
                name=None,
                value=shell_ast.IntLiteral(value=1),
            ),
        ))
        error = self.capture_validation_error(program)
        self.assertEqual(error, shell_ast.ASTValidationError(
            rule="InvalidBinding",
            path="root.statements[0].name",
            detail="binding nodes must have an Identifier name",
        ))

    def test_invocation_without_target_fails_deterministically(self) -> None:
        program = shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=None,
                method=shell_ast.Identifier(text="run"),
                args=(),
            ),
        ))
        error = self.capture_validation_error(program)
        self.assertEqual(error, shell_ast.ASTValidationError(
            rule="InvalidInvocation",
            path="root.statements[0].target",
            detail="invocation nodes must have an Identifier target",
        ))

    def test_invalid_argument_shape_fails_deterministically(self) -> None:
        program = shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="bad")),
                ),
            ),
        ))
        error = self.capture_validation_error(program)
        self.assertEqual(error, shell_ast.ASTValidationError(
            rule="InvalidArgument",
            path="root.statements[0].args[0]",
            detail="arguments must be NamedArg or PositionalArg",
        ))

    def test_null_literal_with_payload_fails_deterministically(self) -> None:
        null_literal = self.make_invalid_null_literal()
        program = shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="empty"),
                value=null_literal,
            ),
        ))
        error = self.capture_validation_error(program)
        self.assertEqual(error, shell_ast.ASTValidationError(
            rule="InvalidNullLiteral",
            path="root.statements[0].value",
            detail="null literals must not carry payload fields",
        ))

    def test_identical_invalid_asts_yield_identical_failures(self) -> None:
        first = self.capture_validation_error(shell_ast.Program(statements=(self.make_invalid_pipeline(),)))
        second = self.capture_validation_error(shell_ast.Program(statements=(self.make_invalid_pipeline(),)))
        self.assertEqual(first, second)

    def capture_validation_error(self, program: shell_ast.Program) -> shell_ast.ASTValidationError:
        with self.assertRaises(shell_ast.ASTValidationError) as ctx:
            shell_ast.validate_program(program)
        return ctx.exception

    def make_invalid_pipeline(self) -> shell_ast.Pipeline:
        pipeline = object.__new__(shell_ast.Pipeline)
        object.__setattr__(pipeline, "stages", (
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(),
            ),
        ))
        object.__setattr__(pipeline, "kind", shell_ast.NodeKind.PIPELINE)
        return pipeline

    def make_invalid_null_literal(self) -> shell_ast.NullLiteral:
        null_literal = shell_ast.NullLiteral()
        object.__setattr__(null_literal, "value", "payload")
        return null_literal


if __name__ == "__main__":
    unittest.main()
