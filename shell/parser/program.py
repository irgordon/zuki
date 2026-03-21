from __future__ import annotations

from shell.ast import Binding
from shell.ast import BoolLiteral
from shell.ast import Identifier
from shell.ast import IdentifierExpr
from shell.ast import IntLiteral
from shell.ast import Invocation
from shell.ast import InvokeForm
from shell.ast import NamedArg
from shell.ast import NullLiteral
from shell.ast import Pipeline
from shell.ast import PositionalArg
from shell.ast import Program
from shell.ast import StringLiteral
from shell.lexer import BooleanLiteralToken
from shell.lexer import EqualsToken
from shell.lexer import IdentifierToken
from shell.lexer import IntegerLiteralToken
from shell.lexer import InvokeKeywordToken
from shell.lexer import LexError
from shell.lexer import LetKeywordToken
from shell.lexer import NullLiteralToken
from shell.lexer import PipeToken
from shell.lexer import StringLiteralToken
from shell.lexer import Token
from shell.lexer import scan_tokens

from .errors import InvalidLiteral
from .errors import InvalidPipeline
from .errors import MissingToken
from .errors import ParseError
from .errors import UnexpectedToken
from .errors import UnterminatedString


def parse_program(source: str) -> Program:
    try:
        tokens = scan_tokens(source)
    except LexError as exc:
        raise map_lex_error(exc) from None
    return parse_tokens(tokens)


def parse_tokens(tokens: tuple[Token, ...]) -> Program:
    return Parser(tokens).parse_program()


class Parser:
    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self.tokens = tokens
        self.cursor = 0

    def parse_program(self) -> Program:
        statements: list[Binding | Invocation | InvokeForm | Pipeline] = []
        while not self.is_at_end():
            statements.append(self.parse_statement())
        return Program(statements=tuple(statements))

    def parse_statement(self) -> Binding | Invocation | InvokeForm | Pipeline:
        token = self.peek()
        if isinstance(token, LetKeywordToken):
            return self.parse_binding()
        if self.can_start_command():
            return self.parse_command_statement()
        raise UnexpectedToken(self.cursor, "expected statement")

    def parse_command_statement(self) -> Invocation | InvokeForm | Pipeline:
        first_stage = self.parse_command()
        if not isinstance(self.peek(), PipeToken):
            return first_stage

        stages = [first_stage]
        while isinstance(self.peek(), PipeToken):
            self.cursor += 1
            if not self.can_start_command():
                raise InvalidPipeline(self.cursor, "expected pipeline stage")
            stages.append(self.parse_command())
        return Pipeline(stages=tuple(stages))

    def parse_binding(self) -> Binding:
        self.require_token_type(LetKeywordToken, "expected let keyword")
        name_token = self.require_token_type(IdentifierToken, "expected binding identifier")
        self.require_text("=", "expected equals token")
        value = self.parse_expression()
        return Binding(
            name=Identifier(text=name_token.text),
            value=value,
        )

    def parse_command(self) -> Invocation | InvokeForm:
        token = self.peek()
        if isinstance(token, InvokeKeywordToken):
            return self.parse_invoke_form()
        if isinstance(token, IdentifierToken):
            return self.parse_invocation()
        raise UnexpectedToken(self.cursor, "expected command")

    def parse_invocation(self) -> Invocation:
        target_token = self.require_token_type(IdentifierToken, "expected invocation target")
        method_token = self.require_token_type(IdentifierToken, "expected invocation method")
        args = self.parse_arguments()
        return Invocation(
            target=Identifier(text=target_token.text),
            method=Identifier(text=method_token.text),
            args=args,
        )

    def parse_invoke_form(self) -> InvokeForm:
        self.require_token_type(InvokeKeywordToken, "expected invoke keyword")
        target_token = self.require_token_type(IdentifierToken, "expected invocation target")
        method_token = self.require_token_type(IdentifierToken, "expected invocation method")
        args = self.parse_arguments()
        return InvokeForm(
            target=Identifier(text=target_token.text),
            method=Identifier(text=method_token.text),
            args=args,
        )

    def parse_arguments(self) -> tuple[NamedArg | PositionalArg, ...]:
        args: list[NamedArg | PositionalArg] = []
        while self.can_start_expression():
            args.append(self.parse_argument())
        return tuple(args)

    def parse_argument(self) -> NamedArg | PositionalArg:
        if isinstance(self.peek(), IdentifierToken) and isinstance(self.peek_next(), EqualsToken):
            name_token = self.require_token_type(IdentifierToken, "expected named argument name")
            self.require_text("=", "expected equals token")
            value = self.parse_expression()
            return NamedArg(
                name=Identifier(text=name_token.text),
                value=value,
            )
        return PositionalArg(value=self.parse_expression())

    def parse_expression(self) -> StringLiteral | IntLiteral | BoolLiteral | NullLiteral | IdentifierExpr:
        token = self.peek()
        if token is None:
            raise MissingToken(self.cursor, "expected expression")

        if isinstance(token, IdentifierToken):
            self.cursor += 1
            return IdentifierExpr(name=Identifier(text=token.text))
        if isinstance(token, StringLiteralToken):
            self.cursor += 1
            return StringLiteral(value=token.value)
        if isinstance(token, IntegerLiteralToken):
            self.cursor += 1
            return IntLiteral(value=int(token.text))
        if isinstance(token, BooleanLiteralToken):
            self.cursor += 1
            return BoolLiteral(value=token.value)
        if isinstance(token, NullLiteralToken):
            self.cursor += 1
            return NullLiteral()

        raise UnexpectedToken(self.cursor, f"unsupported expression token {type(token).__name__}")

    def require_token_type(self, token_type: type, detail: str):
        token = self.peek()
        if token is None:
            raise MissingToken(self.cursor, detail)
        if not isinstance(token, token_type):
            raise UnexpectedToken(self.cursor, detail)
        self.cursor += 1
        return token

    def require_text(self, text: str, detail: str):
        token = self.peek()
        if token is None:
            raise MissingToken(self.cursor, detail)
        if getattr(token, "text", None) != text:
            raise MissingToken(self.cursor, detail)
        self.cursor += 1
        return token

    def peek(self) -> Token | None:
        if self.is_at_end():
            return None
        return self.tokens[self.cursor]

    def peek_next(self) -> Token | None:
        next_index = self.cursor + 1
        if next_index >= len(self.tokens):
            return None
        return self.tokens[next_index]

    def can_start_expression(self) -> bool:
        token = self.peek()
        return isinstance(
            token,
            (
                IdentifierToken,
                StringLiteralToken,
                IntegerLiteralToken,
                BooleanLiteralToken,
                NullLiteralToken,
            ),
        )

    def can_start_command(self) -> bool:
        token = self.peek()
        return isinstance(token, (IdentifierToken, InvokeKeywordToken))

    def is_at_end(self) -> bool:
        return self.cursor >= len(self.tokens)


def map_lex_error(error: LexError) -> ParseError:
    if error.detail == "unterminated string literal":
        return UnterminatedString(error.position, error.detail)
    if error.detail == "invalid decimal literal boundary" or error.detail.startswith("unsupported string escape"):
        return InvalidLiteral(error.position, error.detail)
    return UnexpectedToken(error.position, error.detail)
