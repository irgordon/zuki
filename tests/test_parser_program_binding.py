from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import ast as shell_ast
from shell import parser as shell_parser


class ProgramBindingParserTests(unittest.TestCase):
    def test_parse_program_preserves_statement_order(self) -> None:
        program = shell_parser.parse_program('let alpha = 1 let beta = "x"')
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="alpha"),
                value=shell_ast.IntLiteral(value=1),
            ),
            shell_ast.Binding(
                name=shell_ast.Identifier(text="beta"),
                value=shell_ast.StringLiteral(value="x"),
            ),
        )))

    def test_parse_binding_supports_identifier_and_literal_expressions(self) -> None:
        program = shell_parser.parse_program("let name = svc.open let truth = true let empty = null")
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="name"),
                value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="svc.open")),
            ),
            shell_ast.Binding(
                name=shell_ast.Identifier(text="truth"),
                value=shell_ast.BoolLiteral(value=True),
            ),
            shell_ast.Binding(
                name=shell_ast.Identifier(text="empty"),
                value=shell_ast.NullLiteral(),
            ),
        )))

    def test_parse_program_accepts_empty_token_stream(self) -> None:
        program = shell_parser.parse_program("   # comment only\n")
        self.assertEqual(program, shell_ast.Program(statements=()))

    def test_identical_inputs_yield_identical_asts(self) -> None:
        source = 'let item = "value" let count = 42'
        first = shell_parser.parse_program(source)
        second = shell_parser.parse_program(source)
        self.assertEqual(first, second)

    def test_identical_invalid_inputs_yield_identical_failures(self) -> None:
        first = self.capture_parse_error("svc")
        second = self.capture_parse_error("svc")
        self.assertEqual(first, second)
        self.assertIsInstance(first, shell_parser.MissingToken)
        self.assertEqual(str(first), "MissingToken at 1: expected invocation method")

    def test_parser_fails_without_recovery_on_truncated_binding(self) -> None:
        error = self.capture_parse_error("let value =")
        self.assertEqual(error, shell_parser.MissingToken(position=3, detail="expected expression"))

    def test_parser_emits_unexpected_token_for_unsupported_expression_tokens(self) -> None:
        error = self.capture_parse_error("let value = invoke")
        self.assertEqual(error, shell_parser.UnexpectedToken(position=3, detail="unsupported expression token InvokeKeywordToken"))

    def test_parse_simple_invocation(self) -> None:
        program = shell_parser.parse_program("svc run")
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(),
            ),
        )))

    def test_parse_invocation_with_positional_arguments(self) -> None:
        program = shell_parser.parse_program('svc run 42 "x" true null path.to.item')
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.PositionalArg(value=shell_ast.IntLiteral(value=42)),
                    shell_ast.PositionalArg(value=shell_ast.StringLiteral(value="x")),
                    shell_ast.PositionalArg(value=shell_ast.BoolLiteral(value=True)),
                    shell_ast.PositionalArg(value=shell_ast.NullLiteral()),
                    shell_ast.PositionalArg(
                        value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="path.to.item")),
                    ),
                ),
            ),
        )))

    def test_parse_invocation_with_named_arguments(self) -> None:
        program = shell_parser.parse_program('svc run mode="fast" retries=3 enabled=false')
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="mode"),
                        value=shell_ast.StringLiteral(value="fast"),
                    ),
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="retries"),
                        value=shell_ast.IntLiteral(value=3),
                    ),
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="enabled"),
                        value=shell_ast.BoolLiteral(value=False),
                    ),
                ),
            ),
        )))

    def test_parse_explicit_invoke_form(self) -> None:
        program = shell_parser.parse_program("invoke svc run item=42 path.to.value")
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.InvokeForm(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="item"),
                        value=shell_ast.IntLiteral(value=42),
                    ),
                    shell_ast.PositionalArg(
                        value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="path.to.value")),
                    ),
                ),
            ),
        )))

    def test_parse_program_preserves_binding_then_invocation_order(self) -> None:
        program = shell_parser.parse_program('let home = root svc run target=home')
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Binding(
                name=shell_ast.Identifier(text="home"),
                value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="root")),
            ),
            shell_ast.Invocation(
                target=shell_ast.Identifier(text="svc"),
                method=shell_ast.Identifier(text="run"),
                args=(
                    shell_ast.NamedArg(
                        name=shell_ast.Identifier(text="target"),
                        value=shell_ast.IdentifierExpr(name=shell_ast.Identifier(text="home")),
                    ),
                ),
            ),
        )))

    def test_parse_invoke_form_requires_target_and_method(self) -> None:
        error = self.capture_parse_error("invoke svc")
        self.assertEqual(error, shell_parser.MissingToken(position=2, detail="expected invocation method"))

    def test_parse_minimal_valid_pipeline(self) -> None:
        program = shell_parser.parse_program("svc run | inspect show")
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Pipeline(stages=(
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="svc"),
                    method=shell_ast.Identifier(text="run"),
                    args=(),
                ),
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(),
                ),
            )),
        )))

    def test_parse_multi_stage_pipeline_preserves_stage_order(self) -> None:
        program = shell_parser.parse_program('invoke svc run 1 | filter apply mode="fast" | inspect show')
        self.assertEqual(program, shell_ast.Program(statements=(
            shell_ast.Pipeline(stages=(
                shell_ast.InvokeForm(
                    target=shell_ast.Identifier(text="svc"),
                    method=shell_ast.Identifier(text="run"),
                    args=(
                        shell_ast.PositionalArg(value=shell_ast.IntLiteral(value=1)),
                    ),
                ),
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="filter"),
                    method=shell_ast.Identifier(text="apply"),
                    args=(
                        shell_ast.NamedArg(
                            name=shell_ast.Identifier(text="mode"),
                            value=shell_ast.StringLiteral(value="fast"),
                        ),
                    ),
                ),
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(),
                ),
            )),
        )))

    def test_parse_program_with_binding_pipeline_and_invocation_preserves_order(self) -> None:
        program = shell_parser.parse_program('let home = root svc open | inspect show invoke audit run')
        self.assertEqual(program, shell_ast.Program(statements=(
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
                shell_ast.Invocation(
                    target=shell_ast.Identifier(text="inspect"),
                    method=shell_ast.Identifier(text="show"),
                    args=(),
                ),
            )),
            shell_ast.InvokeForm(
                target=shell_ast.Identifier(text="audit"),
                method=shell_ast.Identifier(text="run"),
                args=(),
            ),
        )))

    def test_single_stage_command_does_not_reduce_to_pipeline(self) -> None:
        program = shell_parser.parse_program("svc run")
        self.assertIsInstance(program.statements[0], shell_ast.Invocation)
        self.assertNotIsInstance(program.statements[0], shell_ast.Pipeline)

    def test_parse_trailing_pipe_fails_deterministically(self) -> None:
        first = self.capture_parse_error("svc run |")
        second = self.capture_parse_error("svc run |")
        self.assertEqual(first, second)
        self.assertEqual(first, shell_parser.InvalidPipeline(position=3, detail="expected pipeline stage"))

    def test_binding_missing_identifier_uses_unexpected_token(self) -> None:
        error = self.capture_parse_error("let = 1")
        self.assertEqual(error, shell_parser.UnexpectedToken(position=1, detail="expected binding identifier"))

    def test_invalid_decimal_literal_uses_invalid_literal(self) -> None:
        error = self.capture_parse_error("let value = 1a")
        self.assertEqual(error, shell_parser.InvalidLiteral(position=13, detail="invalid decimal literal boundary"))

    def test_unterminated_string_uses_specific_error(self) -> None:
        error = self.capture_parse_error('let value = "oops')
        self.assertEqual(error, shell_parser.UnterminatedString(position=12, detail="unterminated string literal"))

    def test_identical_invalid_literal_inputs_yield_identical_type_and_location(self) -> None:
        first = self.capture_parse_error("let value = 1a")
        second = self.capture_parse_error("let value = 1a")
        self.assertEqual(type(first), type(second))
        self.assertEqual(first.position, second.position)
        self.assertEqual(first.detail, second.detail)

    def capture_parse_error(self, source: str) -> shell_parser.ParseError:
        with self.assertRaises(shell_parser.ParseError) as ctx:
            shell_parser.parse_program(source)
        return ctx.exception


if __name__ == "__main__":
    unittest.main()
