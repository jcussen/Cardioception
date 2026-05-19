#!/bin/zsh
set -u

REPO_DIR="${0:A:h}"
ENV_DIR="$REPO_DIR/conda-envs/cardioception-hrd"
PYTHON_BIN="$ENV_DIR/bin/python"
CHECK_SCRIPT="$REPO_DIR/scripts/check_nonin_env.py"
TASK_SCRIPT="$REPO_DIR/scripts/run_hrd_nonin.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Could not find the Cardioception Python environment:"
    echo "$PYTHON_BIN"
    echo
    echo "Create it first by running:"
    echo "./scripts/setup_cardioception_env.sh"
    echo
    read "REPLY?Press Return to close this window..."
    exit 1
fi

cd "$REPO_DIR"
export CONDA_PREFIX="$ENV_DIR"
export CONDA_DEFAULT_ENV="cardioception-hrd"
export PATH="$ENV_DIR/bin:$PATH"

"$PYTHON_BIN" "$CHECK_SCRIPT"
exit_status=$?

if [[ $exit_status -ne 0 ]]; then
    echo
    echo "HRD environment check failed."
    read "REPLY?Press Return to close this window..."
    exit $exit_status
fi

"$PYTHON_BIN" "$TASK_SCRIPT"
exit_status=$?

if [[ $exit_status -ne 0 ]]; then
    echo
    echo "HRD task exited with an error."
    read "REPLY?Press Return to close this window..."
fi

exit $exit_status
