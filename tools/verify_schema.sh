#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C
export TZ=UTC
PATH="/usr/bin:/bin"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

python3 "$REPO_ROOT/tools/harness/verify_schema.py"
