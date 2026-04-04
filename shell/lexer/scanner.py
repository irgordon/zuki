from __future__ import annotations

from dataclasses import dataclass

from .tokens import BooleanLiteralToken
from .tokens import ColonToken
from .tokens import CommaToken
from .tokens import EqualsToken
from .tokens import IdentifierToken
from .tokens import IntegerLiteralToken
from .tokens import InvokeKeywordToken
from .tokens import LeftBraceToken
from .tokens import LeftBracketToken
from .tokens import LetKeywordToken
from .tokens import NullLiteralToken
from .tokens import PipeToken
from .tokens import RightBraceToken
from .tokens import RightBracketToken
from .limits import MAX_IDENTIFIER_LENGTH
from .limits import MAX_INTEGER_DIGITS
from .limits import MAX_STRING_LENGTH
from .tokens import StringLiteralToken
from .tokens import Token


@dataclass(frozen=True)
class LexError(Exception):
    position: int
    detail: str

    def __str__(self) -> str:
        return f"lex error at {self.position}: {self.detail}"


PUNCTUATION_TOKENS = {
    "=": EqualsToken,
    "|": PipeToken,
    ",": CommaToken,
    ":": ColonToken,
    "[": LeftBracketToken,
    "]": RightBracketToken,
    "{": LeftBraceToken,
    "}": RightBraceToken,
}

KEYWORD_TOKENS = {
    "let": LetKeywordToken,
    "invoke": InvokeKeywordToken,
}

BOOLEAN_VALUES = {
    "true": True,
    "false": False,
}

ESCAPE_VALUES = {
    '"': '"',
    "\\": "\\",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def scan_tokens(source: str) -> tuple[Token, ...]:
    tokens: list[Token] = []
    cursor = 0
    limit = len(source)

    while cursor < limit:
        ch = source[cursor]

        if ch.isspace():
            cursor += 1
            continue

        if ch == "#":
            cursor = skip_comment(source, cursor)
            continue

        token_factory = PUNCTUATION_TOKENS.get(ch)
        if token_factory is not None:
            tokens.append(token_factory())
            cursor += 1
            continue

        if ch == '"':
            token, cursor = scan_string_literal(source, cursor)
            tokens.append(token)
            continue

        if ch.isdecimal():
            token, cursor = scan_integer_literal(source, cursor)
            tokens.append(token)
            continue

        if is_identifier_start(ch):
            token, cursor = scan_identifier_like(source, cursor)
            tokens.append(token)
            continue

        raise LexError(cursor, f"invalid token start {ch!r}")

    return tuple(tokens)


def skip_comment(source: str, start: int) -> int:
    cursor = start
    limit = len(source)
    while cursor < limit and source[cursor] != "\n":
        cursor += 1
    return cursor


def scan_string_literal(source: str, start: int) -> tuple[StringLiteralToken, int]:
    cursor = start + 1
    limit = len(source)
    decoded: list[str] = []

    while cursor < limit:
        if (cursor - start) > MAX_STRING_LENGTH:
            raise LexError(start, "string literal too long")
        ch = source[cursor]
        if ch == '"':
            raw_text = source[start:cursor + 1]
            return StringLiteralToken(raw_text=raw_text, value="".join(decoded)), cursor + 1
        if ch == "\\":
            cursor += 1
            if cursor >= limit:
                raise LexError(start, "unterminated string literal")
            escape = source[cursor]
            if escape not in ESCAPE_VALUES:
                raise LexError(cursor, f"unsupported string escape {escape!r}")
            decoded.append(ESCAPE_VALUES[escape])
            cursor += 1
            continue
        decoded.append(ch)
        cursor += 1

    raise LexError(start, "unterminated string literal")


def scan_integer_literal(source: str, start: int) -> tuple[IntegerLiteralToken, int]:
    cursor = start
    limit = len(source)
    while cursor < limit and source[cursor].isdecimal():
        cursor += 1
        if (cursor - start) > MAX_INTEGER_DIGITS:
            raise LexError(start, "integer literal too long")

    if cursor < limit and is_identifier_continue(source[cursor]):
        raise LexError(cursor, "invalid decimal literal boundary")

    return IntegerLiteralToken(text=source[start:cursor]), cursor


def scan_identifier_like(source: str, start: int) -> tuple[Token, int]:
    cursor = start
    limit = len(source)
    while cursor < limit and is_identifier_continue(source[cursor]):
        cursor += 1
        if (cursor - start) > MAX_IDENTIFIER_LENGTH:
            raise LexError(start, "identifier too long")

    text = source[start:cursor]

    keyword_factory = KEYWORD_TOKENS.get(text)
    if keyword_factory is not None:
        return keyword_factory(), cursor

    boolean_value = BOOLEAN_VALUES.get(text)
    if boolean_value is not None:
        return BooleanLiteralToken(text=text, value=boolean_value), cursor

    if text == "null":
        return NullLiteralToken(), cursor

    return IdentifierToken(text=text), cursor


def is_identifier_start(ch: str) -> bool:
    return ch.isalpha() or ch == "_"


def is_identifier_continue(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "."}
