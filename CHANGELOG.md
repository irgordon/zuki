# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this repository uses Semantic Versioning.
Version numbers must not be incremented automatically.
Version changes require explicit authorization.

Version numbers must not be incremented without explicit instruction.
All entries remain under v0.0.0 until authorized.

## [v0.0.0]

### Added

- Canonical shell v0 AST placeholder package with deterministic schema and normalization tests.
- Deterministic shell v0 AST structural validator with single-failure validation tests.
- Canonical shell v0 lexer token surface with deterministic token-shape tests and minimal scanner support.
- Deterministic shell v0 kernel contract surface covering `spawn`, `send`, `receive`, and `shutdown` interfaces with contract tests.
- Kernel C directory skeleton, public contract headers, and inert freestanding source placeholders with structural validation tests.
- Kernel lifecycle, panic, halt, and fault reason contract surfaces with deterministic source-inspection tests.
- Initial deterministic shell v0 parser support for `Program`, `Binding`, `Invocation`, and `InvokeForm` nodes with parser tests.
- Deterministic shell v0 execution plan model with validated AST to plan conversion tests.
- Minimal shell v0 runtime skeleton that accepts an execution plan and returns a stable placeholder result.
- Repository changelog bootstrap under the fixed authorized version `v0.0.0`.

### Changed

- Harness structure and schema verification now enforce the presence and bootstrap markers of `CHANGELOG.md`.
- Kernel entry, lifecycle, panic, and halt contracts now use aligned canonical types and structurally verified no-op control surfaces.
- Shell v0 parser now supports deterministic pipeline parsing and explicit syntax error classification for bindings, invocations, pipelines, and literal failures.

### Fixed

- Harness repository scanning now skips non-text and generated cache artifacts deterministically during broad verification scans.
- Resource verification no longer self-flags its own obvious-loop rule literals.

### Removed

### Security
