#!/usr/bin/env bash
set -euo pipefail
LC_ALL=C
export LC_ALL

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

failures=0

required_checks=(
  "ARCH_RULES.md|No Ambient Authority"
  "ARCH_RULES.md|Deterministic Boundary Behavior"
  "TASK_TEMPLATE.md|Objective"
  "TASK_TEMPLATE.md|Scope"
  "TASK_TEMPLATE.md|Invariants"
  "TASK_TEMPLATE.md|Exit Criteria"
  "VERIFY.md|make verify"
  "VERIFY.md|Verification Status: PASS or FAIL"
  "AGENTS.md|ARCH_RULES.md"
  "AGENTS.md|TASK_TEMPLATE.md"
  "AGENTS.md|VERIFY.md"
)

checked_files=()
for check in "${required_checks[@]}"; do
  file="${check%%|*}"
  marker="${check#*|}"

  if [[ ! -f "${file}" ]]; then
    if [[ " ${checked_files[*]} " != *" ${file} "* ]]; then
      echo "FAIL: missing required file '${file}'"
      checked_files+=("${file}")
      failures=1
    fi
    continue
  fi

  if ! grep -F -q -- "${marker}" "${file}"; then
    echo "FAIL: file '${file}' missing marker '${marker}'"
    failures=1
  fi
done

if [[ "${failures}" -ne 0 ]]; then
  exit 1
fi

echo "OK: schema verification passed"
