from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParseError(Exception):
    position: int
    detail: str

    @property
    def error_type(self) -> str:
        return type(self).__name__

    @property
    def message(self) -> str:
        return self.detail

    def __str__(self) -> str:
        return f"{self.error_type} at {self.position}: {self.detail}"


@dataclass(frozen=True)
class UnexpectedToken(ParseError):
    pass


@dataclass(frozen=True)
class MissingToken(ParseError):
    pass


@dataclass(frozen=True)
class InvalidLiteral(ParseError):
    pass


@dataclass(frozen=True)
class UnterminatedString(ParseError):
    pass


@dataclass(frozen=True)
class InvalidPipeline(ParseError):
    pass
