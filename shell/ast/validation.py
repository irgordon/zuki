from __future__ import annotations

from dataclasses import dataclass

from .nodes import Binding
from .nodes import BoolLiteral
from .nodes import Identifier
from .nodes import IdentifierExpr
from .nodes import IntLiteral
from .nodes import Invocation
from .nodes import InvokeForm
from .nodes import ListExpr
from .nodes import NamedArg
from .nodes import NullLiteral
from .nodes import Pipeline
from .nodes import PositionalArg
from .nodes import Program
from .nodes import RecordExpr
from .nodes import RecordField
from .nodes import StringLiteral


@dataclass(frozen=True)
class ASTValidationError(Exception):
    rule: str
    path: str
    detail: str

    def __str__(self) -> str:
        return f"{self.rule} at {self.path}: {self.detail}"


def validate_program(program: Program) -> None:
    if not isinstance(program, Program):
        raise ASTValidationError("InvalidProgram", "root", "expected Program node")
    validate_statement_sequence(program.statements, "root.statements")


def validate_statement_sequence(statements: tuple[object, ...], path: str) -> None:
    for index, statement in enumerate(statements):
        validate_statement(statement, f"{path}[{index}]")


def validate_statement(statement: object, path: str) -> None:
    if isinstance(statement, Binding):
        validate_binding(statement, path)
        return
    if isinstance(statement, Pipeline):
        validate_pipeline(statement, path)
        return
    if isinstance(statement, (Invocation, InvokeForm)):
        validate_command(statement, path)
        return
    raise ASTValidationError("InvalidStatement", path, "expected Binding, Pipeline, Invocation, or InvokeForm")


def validate_binding(binding: Binding, path: str) -> None:
    if not isinstance(binding.name, Identifier):
        raise ASTValidationError("InvalidBinding", f"{path}.name", "binding nodes must have an Identifier name")
    validate_identifier(binding.name, f"{path}.name")
    validate_value(binding.value, f"{path}.value")


def validate_pipeline(pipeline: Pipeline, path: str) -> None:
    if len(pipeline.stages) < 2:
        raise ASTValidationError("InvalidPipeline", f"{path}.stages", "pipeline length must be at least 2")
    for index, stage in enumerate(pipeline.stages):
        validate_command(stage, f"{path}.stages[{index}]")


def validate_command(command: object, path: str) -> None:
    if not isinstance(command, (Invocation, InvokeForm)):
        raise ASTValidationError("InvalidCommand", path, "expected Invocation or InvokeForm")
    if not isinstance(command.target, Identifier):
        raise ASTValidationError("InvalidInvocation", f"{path}.target", "invocation nodes must have an Identifier target")
    validate_identifier(command.target, f"{path}.target")
    if not isinstance(command.method, Identifier):
        raise ASTValidationError("InvalidInvocation", f"{path}.method", "invocation nodes must have an Identifier method")
    validate_identifier(command.method, f"{path}.method")
    for index, arg in enumerate(command.args):
        validate_argument(arg, f"{path}.args[{index}]")


def validate_argument(arg: object, path: str) -> None:
    if isinstance(arg, NamedArg):
        if not isinstance(arg.name, Identifier):
            raise ASTValidationError("InvalidArgument", f"{path}.name", "named arguments must preserve named distinction")
        validate_identifier(arg.name, f"{path}.name")
        validate_expression(arg.value, f"{path}.value")
        return
    if isinstance(arg, PositionalArg):
        validate_expression(arg.value, f"{path}.value")
        return
    raise ASTValidationError("InvalidArgument", path, "arguments must be NamedArg or PositionalArg")


def validate_value(value: object, path: str) -> None:
    if isinstance(value, (Invocation, InvokeForm)):
        validate_command(value, path)
        return
    validate_expression(value, path)


def validate_expression(expr: object, path: str) -> None:
    if isinstance(expr, IdentifierExpr):
        validate_identifier(expr.name, f"{path}.name")
        return
    if isinstance(expr, ListExpr):
        for index, element in enumerate(expr.elements):
            validate_expression(element, f"{path}.elements[{index}]")
        return
    if isinstance(expr, RecordExpr):
        for index, field in enumerate(expr.fields):
            validate_record_field(field, f"{path}.fields[{index}]")
        return
    if isinstance(expr, RecordField):
        validate_record_field(expr, path)
        return
    if isinstance(expr, (StringLiteral, IntLiteral, BoolLiteral)):
        return
    if isinstance(expr, NullLiteral):
        validate_null_literal(expr, path)
        return
    raise ASTValidationError("InvalidExpression", path, "expected shell v0 expression node")


def validate_record_field(field: RecordField, path: str) -> None:
    if not isinstance(field.name, Identifier):
        raise ASTValidationError("InvalidRecordField", f"{path}.name", "record fields must have an Identifier name")
    validate_identifier(field.name, f"{path}.name")
    validate_expression(field.value, f"{path}.value")


def validate_identifier(identifier: object, path: str) -> None:
    if not isinstance(identifier, Identifier):
        raise ASTValidationError("InvalidIdentifier", path, "expected Identifier node")
    if not isinstance(identifier.text, str) or identifier.text == "":
        raise ASTValidationError("InvalidIdentifier", f"{path}.text", "identifier text must be a non-empty string")


def validate_null_literal(null_literal: NullLiteral, path: str) -> None:
    field_names = tuple(vars(null_literal).keys())
    if field_names != ("kind",):
        raise ASTValidationError("InvalidNullLiteral", path, "null literals must not carry payload fields")
