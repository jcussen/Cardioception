#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "scripts/setup_conda_nonin.sh has been replaced."
echo "Using scripts/setup_cardioception_env.sh instead."
echo

exec "$SCRIPT_DIR/setup_cardioception_env.sh" "$@"
