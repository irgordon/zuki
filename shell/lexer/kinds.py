from __future__ import annotations

from enum import Enum


class TokenKind(str, Enum):
    IDENTIFIER = "identifier"
    STRING_LITERAL = "string_literal"
    INTEGER_LITERAL = "integer_literal"
    BOOLEAN_LITERAL = "boolean_literal"
    NULL_LITERAL = "null_literal"
    LET = "let_keyword"
    INVOKE = "invoke_keyword"
    EQUALS = "equals"
    PIPE = "pipe"
    COMMA = "comma"
    COLON = "colon"
    LEFT_BRACKET = "left_bracket"
    RIGHT_BRACKET = "right_bracket"
    LEFT_BRACE = "left_brace"
    RIGHT_BRACE = "right_brace"
