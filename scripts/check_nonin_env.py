#!/usr/bin/env python3
"""Preflight dependency checks for the Cardioception Nonin HRD environment."""

from __future__ import annotations

import importlib
import os
import sys


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

REQUIRED_IMPORTS = [
    "numpy",
    "pandas",
    "serial",
    "pygame",
    "sounddevice",
    "soundfile",
    "systole",
    "bokeh",
    "numba",
    "joblib",
    "tabulate",
    "watermark",
    "sleepecg",
    "papermill",
    "pingouin",
    "requests",
    "tqdm",
]


def main() -> int:
    errors = []

    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            errors.append(f"- Cannot import {module_name}: {exc}")

    try:
        import soundfile as sf

        if not getattr(sf, "_libname", None):
            errors.append("- soundfile imported but no libsndfile library was loaded.")
    except Exception as exc:
        errors.append(f"- Cannot load soundfile/libsndfile: {exc}")

    try:
        from psychopy import prefs  # noqa: F401
        from psychopy.sound import Sound  # noqa: F401
    except Exception as exc:
        errors.append(f"- Cannot load PsychoPy sound: {exc}")

    try:
        from systole.detection import ppg_peaks  # noqa: F401
        from systole.recording import Nonin3231USB, Oximeter  # noqa: F401
    except Exception as exc:
        errors.append(f"- Cannot load Systole Nonin support: {exc}")

    if errors:
        print("")
        print("Cardioception environment check failed")
        print("--------------------------------------")
        print("The task environment is missing or cannot load required packages:")
        print("")
        print("\n".join(errors))
        print("")
        print("From Anaconda Prompt or Miniforge Prompt in the repository root, try:")
        print(
            "  conda install --prefix .\\conda-envs\\cardioception-nonin "
            '-c conda-forge libsndfile python-soundfile "pandas>=2.2.3" '
            "requests tqdm"
        )
        print("")
        print("If that does not fix it, delete conda-envs\\cardioception-nonin and")
        print("recreate the environment from README.md.")
        return 1

    print("Cardioception environment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
