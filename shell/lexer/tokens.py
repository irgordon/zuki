from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from .kinds import TokenKind


@dataclass(frozen=True)
class IdentifierToken:
    text: str
    kind: TokenKind = TokenKind.IDENTIFIER


@dataclass(frozen=True)
class StringLiteralToken:
    raw_text: str
    value: str
    kind: TokenKind = TokenKind.STRING_LITERAL


@dataclass(frozen=True)
class IntegerLiteralToken:
    text: str
    kind: TokenKind = TokenKind.INTEGER_LITERAL

    def __post_init__(self) -> None:
        if not self.text.isdecimal():
            raise ValueError("integer literal token shape must be decimal")


@dataclass(frozen=True)
class BooleanLiteralToken:
    text: str
    value: bool
    kind: TokenKind = TokenKind.BOOLEAN_LITERAL

    def __post_init__(self) -> None:
        if self.text not in {"true", "false"}:
            raise ValueError("boolean literal token shape must be true or false")


@dataclass(frozen=True)
class NullLiteralToken:
    text: str = "null"
    kind: TokenKind = TokenKind.NULL_LITERAL

    def __post_init__(self) -> None:
        if self.text != "null":
            raise ValueError("null literal token shape must be null")


@dataclass(frozen=True)
class LetKeywordToken:
    text: str = "let"
    kind: TokenKind = TokenKind.LET

    def __post_init__(self) -> None:
        if self.text != "let":
            raise ValueError("let keyword token shape must be let")


@dataclass(frozen=True)
class InvokeKeywordToken:
    text: str = "invoke"
    kind: TokenKind = TokenKind.INVOKE

    def __post_init__(self) -> None:
        if self.text != "invoke":
            raise ValueError("invoke keyword token shape must be invoke")


@dataclass(frozen=True)
class EqualsToken:
    text: str = "="
    kind: TokenKind = TokenKind.EQUALS


@dataclass(frozen=True)
class PipeToken:
    text: str = "|"
    kind: TokenKind = TokenKind.PIPE


@dataclass(frozen=True)
class CommaToken:
    text: str = ","
    kind: TokenKind = TokenKind.COMMA


@dataclass(frozen=True)
class ColonToken:
    text: str = ":"
    kind: TokenKind = TokenKind.COLON


@dataclass(frozen=True)
class LeftBracketToken:
    text: str = "["
    kind: TokenKind = TokenKind.LEFT_BRACKET


@dataclass(frozen=True)
class RightBracketToken:
    text: str = "]"
    kind: TokenKind = TokenKind.RIGHT_BRACKET


@dataclass(frozen=True)
class LeftBraceToken:
    text: str = "{"
    kind: TokenKind = TokenKind.LEFT_BRACE


@dataclass(frozen=True)
class RightBraceToken:
    text: str = "}"
    kind: TokenKind = TokenKind.RIGHT_BRACE


Token = Union[
    IdentifierToken,
    StringLiteralToken,
    IntegerLiteralToken,
    BooleanLiteralToken,
    NullLiteralToken,
    LetKeywordToken,
    InvokeKeywordToken,
    EqualsToken,
    PipeToken,
    CommaToken,
    ColonToken,
    LeftBracketToken,
    RightBracketToken,
    LeftBraceToken,
    RightBraceToken,
]
