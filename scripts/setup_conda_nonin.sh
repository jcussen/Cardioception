#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PREFIX="${1:-$REPO_ROOT/conda-envs/cardioception-nonin}"

echo "Using repo: $REPO_ROOT"
echo "Using conda env prefix: $ENV_PREFIX"

if [[ -d "$ENV_PREFIX" ]]; then
  echo "Conda environment already exists at: $ENV_PREFIX"
  echo "Remove it first if you want a clean rebuild:"
  echo "  rm -rf \"$ENV_PREFIX\""
  exit 1
fi

echo "Creating base conda environment..."
conda env create --prefix "$ENV_PREFIX" -f "$REPO_ROOT/environment_nonin.yml"

echo "Installing PsychoPy..."
conda run --prefix "$ENV_PREFIX" python -m pip install "psychopy==2025.2.4"

echo "Installing Systole and remaining Python dependencies..."
conda run --prefix "$ENV_PREFIX" python -m pip install "systole==0.3.1" --no-deps
conda run --prefix "$ENV_PREFIX" python -m pip install \
  "bokeh>=3.0.0" \
  "numba>=0.61.0" \
  "joblib>=1.3.2" \
  "sleepecg>=0.5.1" \
  "tabulate>=0.8.9" \
  "watermark>=2.5.0"

echo "Installing Cardioception fork in editable mode..."
conda run --prefix "$ENV_PREFIX" python -m pip install -e "$REPO_ROOT" --no-deps

echo "Done."
echo "Activate with:"
echo "  conda activate \"$ENV_PREFIX\""
echo "Run HRD with Nonin via:"
echo "  python \"$REPO_ROOT/scripts/run_hrd_nonin.py\" --serial-port <YOUR_PORT>"
