from __future__ import annotations

from enum import Enum


class NodeKind(str, Enum):
    PROGRAM = "Program"
    BINDING = "Binding"
    PIPELINE = "Pipeline"
    INVOCATION = "Invocation"
    INVOKE_FORM = "InvokeForm"
    NAMED_ARG = "NamedArg"
    POSITIONAL_ARG = "PositionalArg"
    IDENTIFIER_EXPR = "IdentifierExpr"
    LIST_EXPR = "ListExpr"
    RECORD_EXPR = "RecordExpr"
    RECORD_FIELD = "RecordField"
    STRING_LITERAL = "StringLiteral"
    INT_LITERAL = "IntLiteral"
    BOOL_LITERAL = "BoolLiteral"
    NULL_LITERAL = "NullLiteral"
    IDENTIFIER = "Identifier"
