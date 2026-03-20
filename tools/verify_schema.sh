#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

failures=0
declare -A missing_file_reported=()

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

for check in "${required_checks[@]}"; do
  file="${check%%|*}"
  marker="${check#*|}"

  if [[ ! -f "${file}" ]]; then
    if [[ -z "${missing_file_reported["${file}"]+x}" ]]; then
      echo "FAIL: missing required file '${file}'"
      missing_file_reported["${file}"]=1
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
