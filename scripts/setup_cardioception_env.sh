#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${1:-$REPO_ROOT/conda-envs/cardioception-hrd}"
ENV_FILE="$REPO_ROOT/environment_cardioception.yml"

echo "Using repository:"
echo "  $REPO_ROOT"
echo
echo "Creating Cardioception environment:"
echo "  $ENV_PREFIX"
echo

if ! command -v conda >/dev/null 2>&1; then
  echo "Could not find conda. Open Terminal after installing Anaconda or Miniforge."
  exit 1
fi

if [[ -x "$ENV_PREFIX/bin/python" ]]; then
  echo "The Cardioception environment already exists:"
  echo "  $ENV_PREFIX"
  echo
  echo "To rebuild it, delete this folder first:"
  echo "  rm -rf \"$ENV_PREFIX\""
  exit 1
fi

conda env create --prefix "$ENV_PREFIX" -f "$ENV_FILE"

echo
echo "Installing PsychoPy..."
conda run --prefix "$ENV_PREFIX" python -m pip install "psychopy==2025.2.4"

echo
echo "Installing Systole..."
conda run --prefix "$ENV_PREFIX" python -m pip install "systole==0.3.1" --no-deps

echo
echo "Installing Cardioception..."
conda run --prefix "$ENV_PREFIX" python -m pip install -e "$REPO_ROOT" --no-deps

echo
echo "Checking the environment..."
conda run --prefix "$ENV_PREFIX" python "$REPO_ROOT/scripts/check_nonin_env.py"

echo
echo "Setup complete. You can now double-click Run_HRD.command."
