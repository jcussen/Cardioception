#!/bin/zsh
set -u

REPO_DIR="${0:A:h}"
PYTHON_BIN="$REPO_DIR/conda-envs/cardioception-nonin/bin/python"
TASK_SCRIPT="$REPO_DIR/scripts/run_hrd_nonin.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Could not find the Cardioception Nonin Python environment:"
    echo "$PYTHON_BIN"
    echo
    echo "Create it first by running:"
    echo "./scripts/setup_conda_nonin.sh"
    echo
    read "REPLY?Press Return to close this window..."
    exit 1
fi

cd "$REPO_DIR"
"$PYTHON_BIN" "$TASK_SCRIPT"
status=$?

if [[ $status -ne 0 ]]; then
    echo
    echo "HRD task exited with an error."
    read "REPLY?Press Return to close this window..."
fi

exit $status
