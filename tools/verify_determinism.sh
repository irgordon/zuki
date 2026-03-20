#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

files=(
  "Makefile"
  "ARCH_RULES.md"
  "TASK_TEMPLATE.md"
  "VERIFY.md"
  "AGENTS.md"
)

while IFS= read -r tool_file; do
  files+=("${tool_file}")
done < <(find tools -maxdepth 1 -type f -name '*.sh' -print | sort)

tokens=(
  $'\x64\x61\x74\x65'
  $'\x75\x75\x69\x64\x67\x65\x6e'
  $'\x2f\x64\x65\x76\x2f\x75\x72\x61\x6e\x64\x6f\x6d'
  $'\x24\x52\x41\x4e\x44\x4f\x4d'
  $'\x73\x68\x75\x66'
  $'\x63\x75\x72\x6c'
  $'\x77\x67\x65\x74'
)
fixed_token_a=$'\x2f\x64\x65\x76\x2f\x75\x72\x61\x6e\x64\x6f\x6d'
fixed_token_b=$'\x24\x52\x41\x4e\x44\x4f\x4d'
token_urandom="${fixed_token_a}"
token_random_var="${fixed_token_b}"
token_boundary='(^|[^[:alnum:]_])'

violations=0
for file in "${files[@]}"; do
  [[ -f "${file}" ]] || continue
  for token in "${tokens[@]}"; do
    if [[ "${token}" == "${token_urandom}" || "${token}" == "${token_random_var}" ]]; then
      pattern="${token}"
      matcher=(-F)
    else
      pattern="${token_boundary}${token}($|[^[:alnum:]_])"
      matcher=(-E)
    fi

    while IFS= read -r match_line; do
      [[ -n "${match_line}" ]] || continue
      echo "FAIL: banned token '${token}' in ${file}: ${match_line}"
      violations=1
    done < <(grep -n "${matcher[@]}" -- "${pattern}" "${file}" || true)
  done
done

if [[ "${violations}" -ne 0 ]]; then
  exit 1
fi

echo "OK: determinism verification passed"
