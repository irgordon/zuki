#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "ARCH_RULES.md"
  "TASK_TEMPLATE.md"
  "VERIFY.md"
  "AGENTS.md"
  "Makefile"
  "tools/verify_structure.sh"
  "tools/verify_policy.sh"
  "tools/verify_schema.sh"
  "tools/run_tests.sh"
  "tools/verify_determinism.sh"
  "tools/verify_resources.sh"
)

missing=0
for file in "${required_files[@]}"; do
  if [[ ! -e "${file}" ]]; then
    echo "FAIL: missing required file: ${file}"
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi

echo "OK: repository structure verified"
