#!/usr/bin/env bash
set -euo pipefail
LC_ALL=C
export LC_ALL

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
cd "${repo_root}"

banned_patterns=(
  "PATH="
  "getenv("
  "os.Getenv"
  "std::env"
  "subprocess.Popen"
  "fork("
  "execvp"
  "daemon("
  "nohup"
)

violations=0

while IFS= read -r file; do
  for pattern in "${banned_patterns[@]}"; do
    while IFS= read -r match_line; do
      [[ -z "${match_line}" ]] && continue
      echo "FAIL: banned pattern '${pattern}' found in ${file}"
      echo "${match_line}"
      violations=1
    done < <(grep -nF -- "${pattern}" "${file}" || true)
  done
done < <(
  find . \
    -path "./.git" -prune -o \
    -path "./.github/workflows" -prune -o \
    -path "./tools/verify_policy.sh" -prune -o \
    -type f -print | sort
)

if [[ "${violations}" -ne 0 ]]; then
  exit 1
fi

echo "OK: policy verification passed"
