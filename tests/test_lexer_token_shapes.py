from __future__ import annotations

import sys
import unittest
from dataclasses import fields
from pathlib import Path
from typing import get_args

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shell import ast as shell_ast
from shell import lexer as shell_lexer


EXPECTED_EXPORTS = (
    "BooleanLiteralToken",
    "ColonToken",
    "CommaToken",
    "EqualsToken",
    "IdentifierToken",
    "IntegerLiteralToken",
    "InvokeKeywordToken",
    "LexError",
    "LeftBraceToken",
    "LeftBracketToken",
    "LetKeywordToken",
    "NullLiteralToken",
    "PipeToken",
    "RightBraceToken",
    "RightBracketToken",
    "scan_tokens",
    "StringLiteralToken",
    "Token",
    "TokenKind",
)

EXPECTED_TOKEN_KIND_VALUES = (
    "identifier",
    "string_literal",
    "integer_literal",
    "boolean_literal",
    "null_literal",
    "let_keyword",
    "invoke_keyword",
    "equals",
    "pipe",
    "comma",
    "colon",
    "left_bracket",
    "right_bracket",
    "left_brace",
    "right_brace",
)


class LexerTokenShapeTests(unittest.TestCase):
    def test_public_surface_matches_required_token_classes(self) -> None:
        self.assertEqual(tuple(shell_lexer.__all__), EXPECTED_EXPORTS)
        self.assertEqual(tuple(kind.value for kind in shell_lexer.TokenKind), EXPECTED_TOKEN_KIND_VALUES)

    def test_identifiers_are_case_sensitive(self) -> None:
        lower = shell_lexer.IdentifierToken(text="service")
        upper = shell_lexer.IdentifierToken(text="Service")
        self.assertNotEqual(lower.text, upper.text)
        self.assertEqual(lower.kind, shell_lexer.TokenKind.IDENTIFIER)
        self.assertEqual(upper.kind, shell_lexer.TokenKind.IDENTIFIER)

    def test_identifier_allows_dot_without_hierarchical_lookup_state(self) -> None:
        token = shell_lexer.IdentifierToken(text="svc.open.raw")
        self.assertEqual(token.text, "svc.open.raw")
        self.assertNotIn("segments", tuple(field.name for field in fields(shell_lexer.IdentifierToken)))
        self.assertNotIn("path", tuple(field.name for field in fields(shell_lexer.IdentifierToken)))

    def test_reserved_keywords_are_distinct_from_identifiers(self) -> None:
        identifier = shell_lexer.IdentifierToken(text="let")
        keyword = shell_lexer.LetKeywordToken()
        self.assertIsNot(type(identifier), type(keyword))
        self.assertNotEqual(identifier.kind, keyword.kind)
        self.assertEqual(shell_lexer.InvokeKeywordToken().kind, shell_lexer.TokenKind.INVOKE)

    def test_string_literal_preserves_decoded_payload_text(self) -> None:
        token = shell_lexer.StringLiteralToken(raw_text='"a\\n"', value="a\n")
        self.assertEqual(token.raw_text, '"a\\n"')
        self.assertEqual(token.value, "a\n")

    def test_integer_literals_accept_decimal_token_shapes_only(self) -> None:
        token = shell_lexer.IntegerLiteralToken(text="42")
        self.assertEqual(token.text, "42")
        with self.assertRaisesRegex(ValueError, "decimal"):
            shell_lexer.IntegerLiteralToken(text="0x2a")

    def test_literal_token_surface_excludes_runtime_only_values(self) -> None:
        literal_types = get_args(shell_lexer.Token)
        self.assertIn(shell_lexer.StringLiteralToken, literal_types)
        self.assertNotIn("CapabilityToken", shell_lexer.__all__)
        self.assertNotIn("StreamToken", shell_lexer.__all__)
        self.assertNotIn("ErrorToken", shell_lexer.__all__)
        self.assertNotIn("HandleToken", shell_lexer.__all__)

    def test_null_literal_shape_is_distinct_and_fixed(self) -> None:
        token = shell_lexer.NullLiteralToken()
        self.assertEqual(token.text, "null")
        self.assertEqual(token.kind, shell_lexer.TokenKind.NULL_LITERAL)

    def test_symbol_token_shapes_match_required_punctuation(self) -> None:
        self.assertEqual(shell_lexer.EqualsToken().text, "=")
        self.assertEqual(shell_lexer.PipeToken().text, "|")
        self.assertEqual(shell_lexer.CommaToken().text, ",")
        self.assertEqual(shell_lexer.ColonToken().text, ":")
        self.assertEqual(shell_lexer.LeftBracketToken().text, "[")
        self.assertEqual(shell_lexer.RightBracketToken().text, "]")
        self.assertEqual(shell_lexer.LeftBraceToken().text, "{")
        self.assertEqual(shell_lexer.RightBraceToken().text, "}")

    def test_whitespace_and_comments_do_not_produce_ast_nodes(self) -> None:
        self.assertNotIn("WhitespaceToken", shell_lexer.__all__)
        self.assertNotIn("CommentToken", shell_lexer.__all__)
        self.assertNotIn("Whitespace", shell_ast.__all__)
        self.assertNotIn("Comment", shell_ast.__all__)

    def test_scan_tokens_emits_required_surface_for_valid_input(self) -> None:
        tokens = shell_lexer.scan_tokens('let svc.open = invoke runner go [42, true, null, "a\\n"] | {name:"x"} # tail')
        self.assertEqual(tokens, (
            shell_lexer.LetKeywordToken(),
            shell_lexer.IdentifierToken(text="svc.open"),
            shell_lexer.EqualsToken(),
            shell_lexer.InvokeKeywordToken(),
            shell_lexer.IdentifierToken(text="runner"),
            shell_lexer.IdentifierToken(text="go"),
            shell_lexer.LeftBracketToken(),
            shell_lexer.IntegerLiteralToken(text="42"),
            shell_lexer.CommaToken(),
            shell_lexer.BooleanLiteralToken(text="true", value=True),
            shell_lexer.CommaToken(),
            shell_lexer.NullLiteralToken(),
            shell_lexer.CommaToken(),
            shell_lexer.StringLiteralToken(raw_text='"a\\n"', value="a\n"),
            shell_lexer.RightBracketToken(),
            shell_lexer.PipeToken(),
            shell_lexer.LeftBraceToken(),
            shell_lexer.IdentifierToken(text="name"),
            shell_lexer.ColonToken(),
            shell_lexer.StringLiteralToken(raw_text='"x"', value="x"),
            shell_lexer.RightBraceToken(),
        ))

    def test_scan_tokens_keeps_keyword_and_identifier_classification_distinct(self) -> None:
        tokens = shell_lexer.scan_tokens("let Let invoke invoke.run false False null nullish")
        self.assertEqual(tokens, (
            shell_lexer.LetKeywordToken(),
            shell_lexer.IdentifierToken(text="Let"),
            shell_lexer.InvokeKeywordToken(),
            shell_lexer.IdentifierToken(text="invoke.run"),
            shell_lexer.BooleanLiteralToken(text="false", value=False),
            shell_lexer.IdentifierToken(text="False"),
            shell_lexer.NullLiteralToken(),
            shell_lexer.IdentifierToken(text="nullish"),
        ))

    def test_scan_tokens_skips_whitespace_and_hash_comments(self) -> None:
        tokens = shell_lexer.scan_tokens(" \tfoo # first comment\n  bar\t# second\n baz ")
        self.assertEqual(tokens, (
            shell_lexer.IdentifierToken(text="foo"),
            shell_lexer.IdentifierToken(text="bar"),
            shell_lexer.IdentifierToken(text="baz"),
        ))

    def test_scan_tokens_is_deterministic_for_identical_input(self) -> None:
        source = 'invoke svc run {"key":"value"}'
        first = shell_lexer.scan_tokens(source)
        second = shell_lexer.scan_tokens(source)
        self.assertEqual(first, second)

    def test_scan_tokens_fails_deterministically_for_invalid_input(self) -> None:
        with self.assertRaisesRegex(shell_lexer.LexError, r"lex error at 0: invalid token start '@'"):
            shell_lexer.scan_tokens("@")
        with self.assertRaisesRegex(shell_lexer.LexError, r"lex error at 1: invalid decimal literal boundary"):
            shell_lexer.scan_tokens("1a")
        with self.assertRaisesRegex(shell_lexer.LexError, r"lex error at 0: unterminated string literal"):
            shell_lexer.scan_tokens('"unterminated')


if __name__ == "__main__":
    unittest.main()
