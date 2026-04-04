import unittest
from shell.lexer.scanner import scan_tokens, LexError
from shell.lexer.limits import MAX_IDENTIFIER_LENGTH, MAX_STRING_LENGTH, MAX_INTEGER_DIGITS
from shell.ast.nodes import Identifier, StringLiteral, IntLiteral, Program
from shell.ast.validation import validate_program, ASTValidationError

class TestSecurityLimits(unittest.TestCase):
    def test_lexer_identifier_limit(self) -> None:
        long_id = "a" * (MAX_IDENTIFIER_LENGTH + 1)
        with self.assertRaisesRegex(LexError, "identifier too long"):
            scan_tokens(long_id)

    def test_lexer_string_limit(self) -> None:
        long_str = '"' + ("a" * MAX_STRING_LENGTH) + 'b"'
        with self.assertRaisesRegex(LexError, "string literal too long"):
            scan_tokens(long_str)

    def test_lexer_integer_limit(self) -> None:
        long_int = "1" * (MAX_INTEGER_DIGITS + 1)
        with self.assertRaisesRegex(LexError, "integer literal too long"):
            scan_tokens(long_int)

    def test_ast_identifier_limit(self) -> None:
        long_id = "a" * (MAX_IDENTIFIER_LENGTH + 1)
        program = Program(statements=())
        # We need a node to test. validate_program starts with statements.
        # Let's mock a simple binding.
        from shell.ast.nodes import Binding
        node = Binding(name=Identifier(text=long_id), value=IntLiteral(value=1))
        program = Program(statements=(node,))
        with self.assertRaisesRegex(ASTValidationError, "identifier exceeds maximum length"):
            validate_program(program)

    def test_ast_string_limit(self) -> None:
        long_val = "a" * (MAX_STRING_LENGTH + 1)
        from shell.ast.nodes import Binding
        node = Binding(name=Identifier(text="valid"), value=StringLiteral(value=long_val))
        program = Program(statements=(node,))
        with self.assertRaisesRegex(ASTValidationError, "string exceeds maximum length"):
            validate_program(program)

    def test_ast_integer_limit(self) -> None:
        long_val = int("1" * (MAX_INTEGER_DIGITS + 1))
        from shell.ast.nodes import Binding
        node = Binding(name=Identifier(text="valid"), value=IntLiteral(value=long_val))
        program = Program(statements=(node,))
        with self.assertRaisesRegex(ASTValidationError, "integer exceeds maximum digits"):
            validate_program(program)

if __name__ == "__main__":
    unittest.main()
