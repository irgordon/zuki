# Zuki Shell v0 Grammar — Structural Specification v1.0

This grammar defines the *shape* of valid Zuki shell expressions.  
It is intentionally minimal, structural, and non-prescriptive.  
It constrains implementers without freezing surface syntax.

This document defines syntax only.  
Execution semantics, authority rules, and lifecycle behavior are defined in `SHELL.md`.

EBNF conventions:

- `[...]` optional  
- `{...}` zero or more  
- `|` choice  

Whitespace and comments are lexical and not part of the grammar.

---

# 1. Input and Statements

```

input          ::= { separator statement } [ separator ] [ statement ] [ separator ]

separator      ::= ws
| comment
| ";"

statement      ::= binding
| pipeline
| command

```

There is no `empty` statement class.  
Whitespace and comments are handled lexically.

Each statement parsed by this grammar maps to exactly one execution unit.

---

# 2. Binding Forms

```

binding        ::= "let" identifier "=" expr

```

Bindings are explicit and scoped.

Normative constraints:

- Scope elevation must be explicit.  
- Implicit scope promotion is prohibited.  
- Binding does not create authority.  
- Binding replacement creates a new value.

---

# 3. Pipelines

```

pipeline       ::= command { "|" command }

```

A pipeline constitutes a single execution unit.

Pipeline semantics (normative):

- left-to-right evaluation  
- deterministic ordering  
- explicit data flow  
- bounded buffering  
- deterministic backpressure  
- upstream blocking must be scheduler-visible  
- upstream blocking must be interruptible  
- upstream blocking must be bounded by explicit policy  
- upstream must block under scheduler control or fail deterministically  
- no silent truncation  
- no implicit retry  

Pipeline execution must not reorder operations.

---

# 4. Commands

```

command        ::= invoke_form
| invocation

```

## 4.1 Canonical invocation

```

invoke_form    ::= "invoke" target method [ arg_list ]

```

## 4.2 Invocation (sugar)

To avoid ambiguity, v0 uses a single unambiguous form:

```

invocation     ::= target method [ arg_list ]

```

Constraints:

- No bare `target`
- No bare `method`
- No implicit callable resolution

Invocation validity beyond syntactic form is defined by the command contract.  
The grammar does not enforce argument count or parameter requirements.

---

# 5. Targets, Methods, and Arguments

```

target         ::= identifier
method         ::= identifier

arg_list       ::= arg { arg }

arg            ::= named_arg
| positional_arg

named_arg      ::= identifier "=" expr

positional_arg ::= expr

```

Normative constraints:

- Arguments are token-delimited expression units.  
- Expression forms must be self-delimiting.  
- No ambiguity between adjacent expressions.  
- No implicit concatenation.

Argument evaluation rules:

- Arguments must be evaluated left-to-right.  
- Argument evaluation must complete before any effectful operation begins.

Resolution sources:

- builtins  
- services explicitly bound into the current execution context  
- user-defined functions  
- explicit capability references  

No PATH lookup.  
No ambient discovery.

Identifiers containing `.` are single tokens and not namespace paths.

---

# 6. Expressions and Values

```

expr           ::= literal
| identifier
| list_expr
| record_expr

```

## 6.1 Lists

```

list_expr      ::= "[" [ expr { "," expr } ] "]"

```

## 6.2 Records

```

record_expr    ::= "{" [ record_field { "," record_field } ] "}"

record_field   ::= identifier ":" expr

```

## 6.3 Value semantics (normative)

Values are immutable once produced.  
Replacement creates a new value.

Value types:

- scalar  
- list  
- record  
- byte buffer (runtime only)  
- stream (runtime only)  
- capability reference (runtime only)  
- service handle (runtime only)  
- error (runtime only)  
- null  

Not all runtime value classes require literal syntax in v0.

Byte buffers, streams, capability references, service handles, and errors may arise from command results and bindings without direct literal forms.

---

# 7. Capability References (Normative)

Capability references must satisfy:

- explicit acquisition  
- explicit transfer  
- explicit revocation visibility  
- generation correctness  

A capability reference must fail deterministically if:

- revoked  
- stale  
- closed  
- type-incompatible  

Capability validity must be checked at:

- resolution, or  
- authority validation, or  
- first use  

Failure timing must be deterministic.

---

# 8. Literals

```

literal        ::= string_lit
| int_lit
| bool_lit
| null_lit

string_lit     ::= '"' { string_char } '"'

string_char    ::= any_char_except_quote_or_backslash
| escape_sequence

escape_sequence ::= "" ( "" | '"' | "n" | "t" )

int_lit        ::= digit { digit }

bool_lit       ::= "true"
| "false"

null_lit       ::= "null"

```

String literals are UTF-8 byte sequences.

Escape semantics are deterministic and non-extensible in v0.

---

# 9. Identifiers

```

identifier     ::= ident_start { ident_part }

ident_start    ::= letter
| "_"

ident_part     ::= letter
| digit
| "_"
| "."

letter         ::= "A".."Z"
| "a".."z"

digit          ::= "0".."9"

```

Reserved keywords:

```

let
invoke
true
false
null

```

Reserved keywords must not be recognized as identifiers.

Normative constraints:

- Identifiers resolve only within bounded scopes.  
- Resolution is deterministic and single-step.  
- Resolution results must remain stable for the duration of the execution unit.  
- `.` inside identifiers is lexical only.  
- `.` does not imply hierarchical lookup.

---

# 10. Comments and Whitespace

```

comment        ::= "#" { any_char_except_newline }

```

Whitespace and comments are lexical.

Normative constraints:

- Comments do not nest.  
- A comment terminates at the first newline.  
- Whitespace has no authority semantics.  
- Whitespace must not alter command resolution.

Lexical analysis must produce deterministic token boundaries before parsing begins.

---

# 11. Pre-Execution Failure Classes (Normative)

The parser and runtime must enforce the following detection boundaries.

```

SyntaxError
ResolutionError
TypeError

```

Definitions:

SyntaxError:

- malformed input
- invalid structure
- invalid token sequence

SyntaxError must be detected before execution.

ResolutionError:

- identifier cannot be resolved
- callable cannot be resolved
- binding target cannot be resolved

ResolutionError must be detected before effectful execution when resolvable at parse or resolve time.

TypeError:

- value structurally valid but incompatible with command contract

TypeError must be detected before effectful execution when contractually checkable.

If a TypeError cannot be determined before execution, the command must fail before reaching its commit boundary.

Errors may also arise at authority validation or first use, consistent with `SHELL.md`.

---

# 12. Examples Accepted by the Grammar

```

let home = vfs open "/home"
let logs = vfs open "/var/log"

vfs list home

dev list
| filter class="net"
| first
| inspect

invoke net connect sock addr="example.com" port=443

text read logs
| text grep "error"
| text head 20

```

These examples demonstrate:

- explicit invocation
- structured pipelines
- deterministic argument ordering
- explicit data flow

---

# 13. Explicitly Excluded from v0

The following features are intentionally not part of the grammar.

- subshells  
- control flow  
- heredocs  
- implicit text mode  
- implicit PATH lookup  
- implicit job control  
- wildcard expansion  
- globbing  
- implicit type coercion  
- implicit command chaining  

These exclusions preserve deterministic execution and capability-rooted authority.

Future versions may introduce additional constructs only with explicit semantic definitions.

---

# End of Zuki Shell v0 Grammar
