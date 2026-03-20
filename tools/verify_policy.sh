#!/usr/bin/env bash
set -euo pipefail

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
for pattern in "${banned_patterns[@]}"; do
  while IFS= read -r match; do
    echo "FAIL: banned pattern '${pattern}' found in ${match}"
    violations=1
  done < <(LC_ALL=C grep -R -F -l --exclude-dir=.git --exclude=verify_policy.sh -- "${pattern}" . | LC_ALL=C sort)
done

if [[ "${violations}" -ne 0 ]]; then
  exit 1
fi

echo "OK: policy verification passed"
