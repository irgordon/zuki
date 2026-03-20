#!/usr/bin/env bash
set -euo pipefail

banned_patterns=(
  "PA""TH="
  "get""env("
  "os.Ge""tenv"
  "std::""env"
  "subprocess.""Popen"
  "fo""rk("
  "exec""vp"
  "dae""mon("
  "no""hup"
)

for pattern in "${banned_patterns[@]}"; do
  while IFS= read -r match; do
    echo "FAIL: banned pattern '${pattern}' found in ${match}"
    exit 1
  done < <(LC_ALL=C grep -R -F -l --exclude-dir=.git -- "${pattern}" . | LC_ALL=C sort)
done

echo "OK: policy verification passed"
