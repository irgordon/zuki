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

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c

.DEFAULT_GOAL := verify

.PHONY: verify verify-preflight \
	verify-structure verify-policy verify-schema verify-tests verify-determinism verify-resources

verify: verify-preflight verify-structure verify-policy verify-schema verify-tests verify-determinism verify-resources
	@printf '%s\n' 'Verification Status: PASS'

verify-preflight:
	@test -x ./tools/verify_structure.sh
	@test -x ./tools/verify_policy.sh
	@test -x ./tools/verify_schema.sh
	@test -x ./tools/run_tests.sh
	@test -x ./tools/verify_determinism.sh
	@test -x ./tools/verify_resources.sh

verify-structure:
	./tools/verify_structure.sh

verify-policy:
	./tools/verify_policy.sh

verify-schema:
	./tools/verify_schema.sh

verify-tests:
	./tools/run_tests.sh

verify-determinism:
	./tools/verify_determinism.sh

verify-resources:
	./tools/verify_resources.sh
