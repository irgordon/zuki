# Zuki Shell v0 AST — Canonical Structural Model v1.1

This document defines the canonical Abstract Syntax Tree (AST) for the Zuki Shell v0 grammar.

The AST is the **semantic representation** of parsed input.  
It is independent of surface syntax and stable across parser implementations.

Execution semantics, authority rules, and lifecycle behavior are defined in `SHELL.md`.

All valid v0 programs must reduce **only** to the node types defined here.  
No additional node kinds are permitted.

---

# 1. Root

## 1.1 Program

```text
Program {
    statements: [Statement]   // preserves source order
}
```

Invariants:

- `statements` preserves source order.
- Each `Statement` is one execution unit.

---

# 2. Statements

```text
Statement =
    | Binding
    | Pipeline
    | Command
```

No empty statements.  
Whitespace and comments do not produce AST nodes.

---

# 3. Binding

```text
Binding {
    name: Identifier
    value: Expr
}
```

Invariants:

- Binding does not create authority.
- Replacement creates a new value (no in-place mutation).

---

# 4. Pipelines

```text
Pipeline {
    stages: [Command]
}
```

Invariants:

- `len(stages) >= 2` — parser must reject shorter pipelines.
- Stages execute in list order.
- Pipeline is a single execution unit.

---

# 5. Commands

```text
Command =
    | InvokeForm
    | Invocation
```

`InvokeForm` and `Invocation` are **semantically equivalent** execution shapes.  
Downstream execution must treat them identically.

---

# 6. Invocation Forms

## 6.1 Canonical invocation

```text
Invocation {
    target: Identifier
    method: Identifier
    args: [Arg]
}
```

## 6.2 Explicit invoke-form

```text
InvokeForm {
    target: Identifier
    method: Identifier
    args: [Arg]
}
```

Invariants:

- No bare commands: both `target` and `method` are always present.
- Argument count and contracts are enforced outside the AST.

---

# 7. Arguments

```text
Arg =
    | NamedArg
    | PositionalArg
```

## 7.1 Named argument

```text
NamedArg {
    name: Identifier
    value: Expr
}
```

## 7.2 Positional argument

```text
PositionalArg {
    value: Expr
}
```

Invariants:

- Arguments are evaluated left-to-right.
- All argument evaluation completes before any effectful operation begins.

---

# 8. Expressions

```text
Expr =
    | Literal
    | IdentifierExpr
    | ListExpr
    | RecordExpr
```

Runtime-only value classes (capabilities, streams, errors, handles) appear only as **values**, never as literal syntax.

---

# 9. Expression Forms

## 9.1 Identifier expression

```text
IdentifierExpr {
    name: Identifier
}
```

Invariants:

- Resolution is not encoded in the AST.
- Resolution happens after parsing.

---

## 9.2 List expression

```text
ListExpr {
    elements: [Expr]
}
```

---

## 9.3 Record expression

```text
RecordExpr {
    fields: [RecordField]
}

RecordField {
    name: Identifier
    value: Expr
}
```

---

# 10. Literals

```text
Literal =
    | StringLiteral
    | IntLiteral
    | BoolLiteral
    | NullLiteral
```

## 10.1 String literal

```text
StringLiteral {
    value: String   // UTF-8, escapes resolved
}
```

## 10.2 Integer literal

```text
IntLiteral {
    value: Integer
}
```

## 10.3 Boolean literal

```text
BoolLiteral {
    value: true | false
}
```

## 10.4 Null literal

```text
NullLiteral {}
```

---

# 11. Identifiers

```text
Identifier {
    text: String   // exact lexical form
}
```

Invariants:

- `text` is preserved exactly as lexically parsed.
- No case normalization, rewriting, or canonicalization.
- `.` inside identifiers is lexical only and does **not** imply hierarchical lookup.

---

# 12. AST Invariants

1. **Closed node set**  
   All valid v0 programs use only the node types defined here.

2. **No bare commands**  
   Every `Command` is `Invocation` or `InvokeForm` with both `target` and `method`.

3. **Pipelines have ≥ 2 stages**  
   Enforced by the parser.

4. **Ordering is preserved**  
   `Program.statements` and `Pipeline.stages` preserve source order.

5. **Arguments are self-delimiting**  
   No ambiguity between adjacent expressions.

6. **Identifier resolution is external**  
   AST does not encode resolution or authority.

7. **Runtime-only values are not literals**  
   Capabilities, streams, errors, and handles appear only as evaluation results.

8. **Immutability**  
   AST nodes become immutable immediately after construction.  
   All transformations produce new nodes; no in-place mutation.

9. **Determinism**  
   Equivalent input must produce equivalent ASTs.

---

# 13. Example ASTs

## 13.1 Binding

Input:

```text
let home = vfs open "/home"
```

AST:

```text
Binding {
    name: Identifier("home"),
    value: Invocation {
        target: Identifier("vfs"),
        method: Identifier("open"),
        args: [
            PositionalArg {
                value: StringLiteral { value: "/home" }
            }
        ]
    }
}
```

---

## 13.2 Pipeline

Input:

```text
dev list | filter apply class="net" | inspect run
```

AST:

```text
Pipeline {
    stages: [
        Invocation {
            target: Identifier("dev"),
            method: Identifier("list"),
            args: []
        },
        Invocation {
            target: Identifier("filter"),
            method: Identifier("apply"),
            args: [
                NamedArg {
                    name: Identifier("class"),
                    value: StringLiteral { value: "net" }
                }
            ]
        },
        Invocation {
            target: Identifier("inspect"),
            method: Identifier("run"),
            args: []
        }
    ]
}
```

---

# 14. Node Kind Enumeration (Recommended)

For implementers, a closed enum of node kinds:

```text
NodeKind =
    | Program
    | Binding
    | Pipeline
    | Invocation
    | InvokeForm
    | NamedArg
    | PositionalArg
    | IdentifierExpr
    | ListExpr
    | RecordExpr
    | RecordField
    | StringLiteral
    | IntLiteral
    | BoolLiteral
    | NullLiteral
    | Identifier
```

---

# End of Zuki Shell v0 AST Specification
