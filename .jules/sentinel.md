## 2025-05-15 - [DoS Prevention via Input Length Limits]
**Vulnerability:** Resource exhaustion (DoS) through unbounded lexical token sizes (identifiers, string literals, and integer digits).
**Learning:** A shell or DSL that does not enforce length limits on its primary tokens is susceptible to memory exhaustion and processing delays. Applying these limits at both the lexer (early rejection) and AST validation (defense-in-depth) provides a robust security posture.
**Prevention:** Always define and enforce reasonable maximum lengths for all user-controllable inputs, especially during the earliest phases of parsing.
