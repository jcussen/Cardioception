#!/usr/bin/env python3
"""Run Cardioception HRD with a Nonin USB pulse oximeter."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Optional

from psychopy import prefs
from psychopy.sound import Sound as PsychoPySound
from serial.tools import list_ports

from cardioception.HRD.parameters import getParameters
from cardioception.HRD.task import run


def configure_audio_backend(backend: str) -> None:
    """Force a PsychoPy audio backend with explicit dependency checks."""
    if backend == "pygame":
        if importlib.util.find_spec("pygame") is None:
            raise RuntimeError(
                "Audio backend 'pygame' is not installed. "
                "Install it with: conda install -c conda-forge pygame"
            )
        prefs.hardware["audioLib"] = ["pygame", "ptb"]
        PsychoPySound.backend = "pygame"
    elif backend == "ptb":
        if importlib.util.find_spec("psychtoolbox") is None:
            raise RuntimeError(
                "Audio backend 'ptb' requires psychtoolbox. "
                "Install it with: pip install psychtoolbox (or use --audio-backend pygame)."
            )
        prefs.hardware["audioLib"] = ["ptb", "pygame"]
        PsychoPySound.backend = "ptb"
    else:
        raise ValueError("audio backend must be 'pygame' or 'ptb'")
    print(f"Using PsychoPy audio backend: {PsychoPySound.backend}")


def detect_nonin_port(explicit_port: Optional[str]) -> str:
    """Resolve serial port from explicit argument or auto-detection."""
    if explicit_port:
        return explicit_port

    candidates = []
    for port in list_ports.comports():
        fields = [
            str(port.device or ""),
            str(port.description or ""),
            str(port.manufacturer or ""),
            str(port.product or ""),
            str(port.hwid or ""),
        ]
        meta = " ".join(fields).lower()
        device = str(port.device or "")
        device_l = device.lower()

        if (
            ("nonin" in meta)
            or ("usbmodem" in device_l)
            or ("usbserial" in device_l)
        ):
            # On macOS prefer /dev/cu.* over /dev/tty.* for active serial comms.
            if device.startswith("/dev/tty."):
                candidates.append("/dev/cu." + device.split("/dev/tty.", 1)[1])
            else:
                candidates.append(device)

    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        resolved = candidates[0]
        print(f"Auto-detected serial port: {resolved}")
        return resolved
    if len(candidates) == 0:
        raise RuntimeError(
            "Could not auto-detect Nonin serial port. Please pass --serial-port."
        )
    raise RuntimeError(
        "Multiple possible serial ports found: "
        + ", ".join(candidates)
        + ". Please pass --serial-port."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Heart Rate Discrimination with Nonin3231USB (behavioral setup)."
    )
    parser.add_argument(
        "--subject-num",
        required=True,
        type=int,
        help="Numeric subject identifier (required, e.g. 12).",
    )
    parser.add_argument("--session", default="HRD", help="Session label")
    parser.add_argument(
        "--serial-port",
        default=None,
        help=(
            "Serial port for the Nonin device "
            "(e.g. COM5 or /dev/cu.usbmodem-XXXX). "
            "If omitted, auto-detection is attempted."
        ),
    )
    parser.add_argument(
        "--language",
        default="english",
        choices=["english", "danish", "danish_children", "french"],
    )
    parser.add_argument("--device", default="mouse", choices=["mouse", "keyboard"])
    parser.add_argument("--stair-type", default="psi", choices=["psi", "updown"])
    parser.add_argument("--n-trials", type=int, default=120)
    parser.add_argument("--catch-trials", type=float, default=0.0)
    parser.add_argument("--break-every", type=int, default=20)
    parser.add_argument("--screen", type=int, default=0, help="Display index for PsychoPy")
    parser.add_argument(
        "--result-path",
        default=None,
        help="Optional output directory. Defaults to ./data/<participant><session>.",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Run windowed instead of fullscreen.",
    )
    parser.add_argument(
        "--no-exteroception",
        action="store_true",
        help="Run only interoception trials.",
    )
    parser.add_argument(
        "--no-confidence",
        action="store_true",
        help="Disable confidence ratings.",
    )
    parser.add_argument(
        "--skip-tutorial",
        action="store_true",
        help="Skip tutorial.",
    )
    parser.add_argument(
        "--audio-backend",
        default="pygame",
        choices=["pygame", "ptb"],
        help="PsychoPy audio backend to use.",
    )
    parser.add_argument(
        "--mouse-more-button",
        default="right",
        choices=["left", "middle", "right"],
        help="Mouse button used for a 'faster/more' decision.",
    )
    parser.add_argument(
        "--mouse-less-button",
        default="left",
        choices=["left", "middle", "right"],
        help="Mouse button used for a 'slower/less' decision.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.mouse_more_button == args.mouse_less_button:
        parser.error("--mouse-more-button and --mouse-less-button must be different")

    participant_id = str(args.subject_num)

    # Prevent accidental overwrite if data already exists for this participant.
    result_path: Optional[str] = args.result_path
    output_dir = (
        Path(result_path)
        if result_path is not None
        else Path.cwd() / "data" / f"{participant_id}{args.session}"
    )
    if output_dir.exists():
        participant_files = list(output_dir.glob(f"{participant_id}*"))
        if participant_files:
            parser.exit(
                1,
                (
                    f"data already exists for participant {args.subject_num}, "
                    "please provide unique subject number\n"
                ),
            )

    configure_audio_backend(args.audio_backend)
    serial_port = detect_nonin_port(args.serial_port)

    parameters = getParameters(
        participant=participant_id,
        session=args.session,
        serialPort=serial_port,
        setup="behavioral",
        stairType=args.stair_type,
        exteroception=not args.no_exteroception,
        catchTrials=args.catch_trials,
        nTrials=args.n_trials,
        device=args.device,
        screenNb=args.screen,
        fullscr=not args.windowed,
        nBreaking=args.break_every,
        resultPath=result_path,
        language=args.language,
        mouse_response_buttons={
            "More": args.mouse_more_button,
            "Less": args.mouse_less_button,
        },
    )

    try:
        run(
            parameters,
            confidenceRating=not args.no_confidence,
            runTutorial=not args.skip_tutorial,
        )
    finally:
        if "win" in parameters and parameters["win"] is not None:
            parameters["win"].close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
