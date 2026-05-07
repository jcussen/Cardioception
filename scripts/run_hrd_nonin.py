#!/usr/bin/env python3
"""Run Cardioception HRD with a Nonin USB pulse oximeter."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_SESSION = "HRD"
BREATHWORK_PHASES = {
    "1": ("before", "1 - Before breathwork"),
    "2": ("after", "2 - After breathwork"),
}
BREATHWORK_PHASE_ALIASES = {
    "1": "1",
    "before": "1",
    "before breathwork": "1",
    "pre": "1",
    "pre-breathwork": "1",
    "pre_breathwork": "1",
    "pre breathwork": "1",
    "2": "2",
    "after": "2",
    "after breathwork": "2",
    "post": "2",
    "post-breathwork": "2",
    "post_breathwork": "2",
    "post breathwork": "2",
}


class NoninConnectionError(RuntimeError):
    """Raised when the Nonin pulse oximeter cannot be found or opened."""


def validate_participant_id(value: object) -> str:
    participant = "" if value is None else str(value).strip()
    if not participant:
        raise ValueError("Participant ID is required.")
    if any(char in participant for char in ("/", "\\", ":", "*", "?", "[", "]")):
        raise ValueError(
            "Participant ID contains characters that are unsafe for filenames."
        )
    return participant


def normalize_breathwork_phase(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("Breathwork timing is required.")

    phase = str(value).strip().lower()
    phase = phase.split("-", 1)[0].strip()
    if phase in BREATHWORK_PHASE_ALIASES:
        return BREATHWORK_PHASE_ALIASES[phase]

    raise ValueError("Breathwork timing must be 1 (before) or 2 (after).")


def build_session_label(base_session: str, breathwork_phase_code: str) -> str:
    return f"{base_session}{breathwork_phase_code}"


def prompt_run_details(
    default_participant: Optional[str],
    default_phase_code: Optional[str],
) -> Tuple[str, str]:
    """Ask the RA for startup fields that should not require CLI entry."""
    from psychopy import gui

    phase_choices = [BREATHWORK_PHASES["1"][1], BREATHWORK_PHASES["2"][1]]
    initial_phase = BREATHWORK_PHASES.get(
        default_phase_code or "", BREATHWORK_PHASES["1"]
    )[1]
    error_message = None

    while True:
        dialog = gui.Dlg(title="HRD setup")
        if error_message:
            dialog.addText(error_message)
        dialog.addField("Participant ID:", initial=default_participant or "")
        dialog.addField(
            "Breathwork timing:",
            choices=phase_choices,
            initial=initial_phase,
        )
        data = dialog.show()

        if not dialog.OK:
            raise SystemExit("HRD setup cancelled\n")

        default_participant = str(data[0]).strip()
        try:
            initial_phase = BREATHWORK_PHASES[normalize_breathwork_phase(data[1])][1]
        except ValueError:
            pass

        try:
            participant_id = validate_participant_id(data[0])
            phase_code = normalize_breathwork_phase(data[1])
        except ValueError as exc:
            error_message = str(exc)
        else:
            return participant_id, phase_code


def resolve_run_details(args: argparse.Namespace) -> Tuple[str, str, str, str]:
    participant_id = None
    phase_code = None
    validation_errors = []

    if args.subject_num is not None:
        try:
            participant_id = validate_participant_id(args.subject_num)
        except ValueError as exc:
            validation_errors.append(str(exc))

    if args.breathwork_phase is not None:
        try:
            phase_code = normalize_breathwork_phase(args.breathwork_phase)
        except ValueError as exc:
            validation_errors.append(str(exc))

    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    if participant_id is None or phase_code is None:
        participant_id, phase_code = prompt_run_details(participant_id, phase_code)

    phase_name = BREATHWORK_PHASES[phase_code][0]
    session = build_session_label(args.session, phase_code)
    return participant_id, phase_code, phase_name, session


def configure_audio_backend(backend: str) -> None:
    """Force a PsychoPy audio backend with explicit dependency checks."""
    from psychopy import prefs
    from psychopy.sound import Sound as PsychoPySound

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


def list_serial_ports() -> list[tuple[str, str]]:
    """Return visible serial ports as (device, description) pairs."""
    from serial.tools import list_ports

    ports = []
    for port in list_ports.comports():
        details = []
        for value in (port.description, port.manufacturer, port.product, port.hwid):
            value = str(value or "").strip()
            if value and value not in details:
                details.append(value)
        ports.append((str(port.device or ""), "; ".join(details)))
    return ports


def format_serial_port_list(ports: list[tuple[str, str]]) -> list[str]:
    if not ports:
        return ["- No serial ports are currently visible to Python."]
    return [
        f"- {device}" + (f" ({description})" if description else "")
        for device, description in ports
    ]


def nonin_help_message(summary: str, ports: list[tuple[str, str]]) -> str:
    lines = [
        "",
        "Nonin pulse oximeter connection problem",
        "-----------------------------------------",
        summary,
        "",
        "What to check:",
        "- Confirm the Nonin USB device is plugged in.",
        "- Unplug and reconnect the Nonin device, then run the task again.",
        "- Close any other program that may be using the same serial port.",
        "- On Windows, check Device Manager for the COM port.",
        "- On macOS, check for /dev/cu.usb* or /dev/tty.usb* ports.",
        "- If you know the port, run with --serial-port, for example:",
        "  python scripts/run_hrd_nonin.py --serial-port COM5",
        "  python scripts/run_hrd_nonin.py --serial-port /dev/cu.usbmodemXXXX",
        "",
        "Serial ports currently visible:",
        *format_serial_port_list(ports),
    ]
    return "\n".join(lines)


def detect_nonin_port(explicit_port: Optional[str]) -> str:
    """Resolve serial port from explicit argument or auto-detection."""
    if explicit_port:
        return explicit_port

    candidates = []
    ports = list_serial_ports()
    for device, description in ports:
        fields = [
            device,
            description,
        ]
        meta = " ".join(fields).lower()
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
        raise NoninConnectionError(
            nonin_help_message(
                "The task could not auto-detect a Nonin serial port.",
                ports,
            )
        )
    raise NoninConnectionError(
        nonin_help_message(
            "Multiple possible Nonin serial ports were found: "
            + ", ".join(candidates)
            + ". Please rerun with the correct --serial-port value.",
            ports,
        )
    )


def is_likely_nonin_exception(exc: BaseException) -> bool:
    try:
        from serial import SerialException
    except Exception:
        serial_exception_types = ()
    else:
        serial_exception_types = (SerialException,)

    current: Optional[BaseException] = exc
    while current is not None:
        if serial_exception_types and isinstance(current, serial_exception_types):
            return True
        message = str(current).lower()
        if any(
            marker in message
            for marker in (
                "serial",
                "port",
                "nonin",
                "device",
                "resource busy",
                "permission",
                "timeout",
                "timed out",
                "could not open",
            )
        ):
            return True
        current = current.__cause__ or current.__context__
    return False


def nonin_startup_failure_message(serial_port: str, exc: BaseException) -> str:
    return nonin_help_message(
        (
            f"The task found serial port {serial_port}, but could not start "
            f"reading from the Nonin device.\n\nUnderlying error: {exc}"
        ),
        list_serial_ports(),
    )


def format_existing_paths(paths: list[Path], max_items: int = 12) -> list[str]:
    if not paths:
        return ["- No participant-specific files were found in this folder."]

    sorted_paths = sorted(paths, key=lambda path: str(path))
    lines = [f"- {path.resolve()}" for path in sorted_paths[:max_items]]
    remaining = len(sorted_paths) - max_items
    if remaining > 0:
        lines.append(f"- ... and {remaining} more")
    return lines


def duplicate_data_message(
    participant_id: str,
    session: str,
    output_dir: Path,
    participant_files: list[Path],
    custom_result_path: bool,
) -> str:
    lines = [
        "",
        "Existing HRD data found",
        "-----------------------",
        f"Participant ID: {participant_id}",
        f"Session: {session}",
        f"Result folder: {output_dir.resolve()}",
        "",
        "Existing participant files/folders:",
        *format_existing_paths(participant_files),
        "",
        "The task stopped to avoid overwriting existing data.",
        "",
        "To continue safely:",
        "- Choose a new participant ID or session, or",
    ]

    if custom_result_path:
        lines.extend(
            [
                "- Move/delete the listed participant files from the custom "
                "result folder if this exact run should be repeated.",
            ]
        )
    else:
        lines.extend(
            [
                "- Move/delete this result folder if this exact run should be "
                "repeated:",
                f"  {output_dir.resolve()}",
            ]
        )

    lines.append("Only remove old data after confirming it is no longer needed.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Heart Rate Discrimination with Nonin3231USB (behavioral setup)."
    )
    parser.add_argument(
        "--subject-num",
        "--participant-id",
        dest="subject_num",
        default=None,
        help="Participant ID. If omitted, a startup dialog asks for it.",
    )
    parser.add_argument(
        "--breathwork-phase",
        default=None,
        help=(
            "Breathwork timing: 1=before breathwork, 2=after breathwork. "
            "If omitted, a startup dialog asks for it."
        ),
    )
    parser.add_argument(
        "--session",
        default=DEFAULT_SESSION,
        help="Base session label. The breathwork timing code is appended.",
    )
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
    parser.add_argument(
        "--n-trials",
        type=int,
        default=None,
        help=(
            "Total experimental trials. If omitted with exteroception enabled, "
            "the task uses 40 interoceptive and 20 exteroceptive trials. If "
            "provided without --intero-trials/--extero-trials, trials are split "
            "evenly across modalities."
        ),
    )
    parser.add_argument(
        "--intero-trials",
        type=int,
        default=None,
        help="Explicit number of interoceptive experimental trials.",
    )
    parser.add_argument(
        "--extero-trials",
        type=int,
        default=None,
        help="Explicit number of exteroceptive experimental trials.",
    )
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

    try:
        participant_id, phase_code, phase_name, session = resolve_run_details(args)
    except ValueError as exc:
        parser.error(str(exc))

    n_trials = args.n_trials
    n_intero_trials = args.intero_trials
    n_extero_trials = args.extero_trials

    if args.no_exteroception:
        if n_extero_trials not in (None, 0):
            parser.error("--extero-trials must be omitted or 0 with --no-exteroception")
        n_trials = 60 if n_trials is None else n_trials
        if n_intero_trials is None:
            n_intero_trials = n_trials
        n_extero_trials = 0
    else:
        if (n_intero_trials is None) and (n_extero_trials is None):
            if n_trials is None:
                n_intero_trials = 40
                n_extero_trials = 20
                n_trials = n_intero_trials + n_extero_trials
            else:
                n_intero_trials = None
                n_extero_trials = None
        elif (n_intero_trials is None) or (n_extero_trials is None):
            parser.error("--intero-trials and --extero-trials must be provided together")
        else:
            n_trials = n_intero_trials + n_extero_trials

    # Prevent accidental overwrite if data already exists for this participant.
    result_path: Optional[str] = args.result_path
    output_dir = (
        Path(result_path)
        if result_path is not None
        else Path.cwd() / "data" / f"{participant_id}{session}"
    )
    if output_dir.exists():
        participant_files = list(output_dir.glob(f"{participant_id}*"))
        if participant_files:
            parser.exit(
                1,
                duplicate_data_message(
                    participant_id=participant_id,
                    session=session,
                    output_dir=output_dir,
                    participant_files=participant_files,
                    custom_result_path=result_path is not None,
                )
                + "\n",
            )

    try:
        configure_audio_backend(args.audio_backend)
        serial_port = detect_nonin_port(args.serial_port)
    except NoninConnectionError as exc:
        parser.exit(2, f"{exc}\n")

    from cardioception.HRD.parameters import getParameters
    from cardioception.HRD.task import run

    try:
        parameters = getParameters(
            participant=participant_id,
            session=session,
            serialPort=serial_port,
            setup="behavioral",
            stairType=args.stair_type,
            exteroception=not args.no_exteroception,
            catchTrials=args.catch_trials,
            nTrials=n_trials,
            nInteroTrials=n_intero_trials,
            nExteroTrials=n_extero_trials,
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
    except Exception as exc:
        if is_likely_nonin_exception(exc):
            parser.exit(2, f"{nonin_startup_failure_message(serial_port, exc)}\n")
        raise
    parameters["breathworkPhaseCode"] = phase_code
    parameters["breathworkPhase"] = phase_name

    try:
        run(
            parameters,
            confidenceRating=not args.no_confidence,
            runTutorial=not args.skip_tutorial,
        )
    except Exception as exc:
        if is_likely_nonin_exception(exc):
            print(nonin_startup_failure_message(serial_port, exc), file=sys.stderr)
            return 2
        raise
    finally:
        if "win" in parameters and parameters["win"] is not None:
            parameters["win"].close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
