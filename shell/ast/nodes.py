from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .kinds import NodeKind


@dataclass(frozen=True)
class Identifier:
    text: str
    kind: NodeKind = NodeKind.IDENTIFIER


@dataclass(frozen=True)
class StringLiteral:
    value: str
    kind: NodeKind = NodeKind.STRING_LITERAL


@dataclass(frozen=True)
class IntLiteral:
    value: int
    kind: NodeKind = NodeKind.INT_LITERAL


@dataclass(frozen=True)
class BoolLiteral:
    value: bool
    kind: NodeKind = NodeKind.BOOL_LITERAL


@dataclass(frozen=True)
class NullLiteral:
    kind: NodeKind = NodeKind.NULL_LITERAL


Literal = Union[StringLiteral, IntLiteral, BoolLiteral, NullLiteral]


@dataclass(frozen=True)
class IdentifierExpr:
    name: Identifier
    kind: NodeKind = NodeKind.IDENTIFIER_EXPR


@dataclass(frozen=True)
class ListExpr:
    elements: tuple["Expr", ...]
    kind: NodeKind = NodeKind.LIST_EXPR


@dataclass(frozen=True)
class RecordField:
    name: Identifier
    value: "Expr"
    kind: NodeKind = NodeKind.RECORD_FIELD


@dataclass(frozen=True)
class RecordExpr:
    fields: tuple[RecordField, ...]
    kind: NodeKind = NodeKind.RECORD_EXPR


Expr = Union[Literal, IdentifierExpr, ListExpr, RecordExpr]


@dataclass(frozen=True)
class NamedArg:
    name: Identifier
    value: Expr
    kind: NodeKind = NodeKind.NAMED_ARG


@dataclass(frozen=True)
class PositionalArg:
    value: Expr
    kind: NodeKind = NodeKind.POSITIONAL_ARG


Arg = Union[NamedArg, PositionalArg]


@dataclass(frozen=True)
class Invocation:
    target: Identifier
    method: Identifier
    args: tuple[Arg, ...]
    kind: NodeKind = NodeKind.INVOCATION


@dataclass(frozen=True)
class InvokeForm:
    target: Identifier
    method: Identifier
    args: tuple[Arg, ...]
    kind: NodeKind = NodeKind.INVOKE_FORM


Command = Union[Invocation, InvokeForm]


@dataclass(frozen=True)
class Binding:
    name: Identifier
    value: Union[Expr, Command]
    kind: NodeKind = NodeKind.BINDING


@dataclass(frozen=True)
class Pipeline:
    stages: tuple[Command, ...]
    kind: NodeKind = NodeKind.PIPELINE

    def __post_init__(self) -> None:
        if len(self.stages) < 2:
            raise ValueError("pipeline requires at least two stages")


Statement = Union[Binding, Pipeline, Command]


@dataclass(frozen=True)
class Program:
    statements: tuple[Statement, ...]
    kind: NodeKind = NodeKind.PROGRAM
