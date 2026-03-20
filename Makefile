# Makefile — Canonical Verification Entry Point
#
# Status: Binding
# Scope: Entire repository
# Purpose: Provide a single deterministic verification command.
#
# This Makefile must remain minimal and must not introduce:
# - implicit dependencies
# - network access
# - nondeterministic behavior
# - hidden authority sources
#
# All verification logic must be implemented in scripts/tools invoked here,
# not embedded directly in the Makefile.

SHELL := bash
.SHELLFLAGS := -euo pipefail -c

.DEFAULT_GOAL := verify

.PHONY: verify \
	verify-preflight \
	verify-structure \
	verify-policy \
	verify-schema \
	verify-tests \
	verify-determinism \
	verify-resources

# ---------------------------------------------------------------------------
# Verification Pipeline
# ---------------------------------------------------------------------------

verify: verify-preflight verify-structure verify-policy verify-schema verify-tests verify-determinism verify-resources
	@echo "Verification Status: PASS"

verify-preflight:
	@echo "==> Preflight: Verification Tooling"
	@test -x ./tools/verify_structure.sh
	@test -x ./tools/verify_policy.sh
	@test -x ./tools/verify_schema.sh
	@test -x ./tools/run_tests.sh
	@test -x ./tools/verify_determinism.sh
	@test -x ./tools/verify_resources.sh

# ---------------------------------------------------------------------------
# Stage 1 — Repository Structure
# ---------------------------------------------------------------------------

verify-structure:
	@echo "==> Stage 1: Repository Structure"
	./tools/verify_structure.sh

# ---------------------------------------------------------------------------
# Stage 2 — Static Policy Enforcement
# ---------------------------------------------------------------------------

verify-policy:
	@echo "==> Stage 2: Static Policy Enforcement"
	./tools/verify_policy.sh

# ---------------------------------------------------------------------------
# Stage 3 — Schema Validation
# ---------------------------------------------------------------------------

verify-schema:
	@echo "==> Stage 3: Schema Validation"
	./tools/verify_schema.sh

# ---------------------------------------------------------------------------
# Stage 4 — Unit Tests
# ---------------------------------------------------------------------------

verify-tests:
	@echo "==> Stage 4: Unit Tests"
	./tools/run_tests.sh

# ---------------------------------------------------------------------------
# Stage 5 — Determinism Tests
# ---------------------------------------------------------------------------

verify-determinism:
	@echo "==> Stage 5: Determinism Tests"
	./tools/verify_determinism.sh

# ---------------------------------------------------------------------------
# Stage 6 — Resource Safety Checks
# ---------------------------------------------------------------------------

verify-resources:
	@echo "==> Stage 6: Resource Safety Checks"
	./tools/verify_resources.sh
