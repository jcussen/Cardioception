# Authors: Nicolas Legrand and Micah Allen, 2019-2022. Contact: micah@cfin.au.dk
# Maintained by the Embodied Computation Group, Aarhus University

"""Compatibility wrapper for the breathwork HRD launcher.

The maintained Nonin HRD entry point lives in scripts/run_hrd_nonin.py. Keeping
this wrapper as a redirect avoids a second PsychoPy GUI startup path.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_launcher():
    repo_root = Path(__file__).resolve().parents[1]
    launcher_path = repo_root / "scripts" / "run_hrd_nonin.py"
    spec = importlib.util.spec_from_file_location("run_hrd_nonin", launcher_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load HRD launcher: {launcher_path}")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


if __name__ == "__main__":
    raise SystemExit(_load_launcher().main())
