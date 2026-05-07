# Cardioception Breathwork HRD

This repository contains the breathwork study version of the Cardioception Heart
Rate Discrimination task. It is configured for the Nonin USB pulse oximeter and
adds a startup dialog for research assistants to enter:

- Participant ID
- Breathwork timing: `1` for before breathwork or `2` for after breathwork

The task can be run by double-clicking the launcher files in the repository root,
or from the command line when troubleshooting.

## Equipment

- A computer with Conda, Anaconda, or Miniforge installed
- A USB mouse
- A Nonin USB pulse oximeter
- This repository cloned locally

## Install The Environment

The environment is installed inside the repository at:

```text
conda-envs/cardioception-nonin
```

### macOS

Open Terminal in the repository root and run:

```bash
./scripts/setup_conda_nonin.sh
```

If macOS says the setup script is not executable, run:

```bash
chmod +x scripts/setup_conda_nonin.sh
./scripts/setup_conda_nonin.sh
```

### Windows

Open Anaconda Prompt or Miniforge Prompt in the repository root and run:

```bat
conda env create --prefix .\conda-envs\cardioception-nonin -f environment_nonin.yml
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install "psychopy==2025.2.4"
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install "systole==0.3.1" --no-deps
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install -e . --no-deps
```

## Run By Double-Clicking

Connect the Nonin device and USB mouse before starting the task.

### macOS

Double-click:

```text
Run_HRD.command
```

If macOS blocks the file because it was downloaded, right-click
`Run_HRD.command`, choose `Open`, and approve it once.

If the file is not executable, run this once from Terminal:

```bash
chmod +x Run_HRD.command
```

### Windows

Double-click:

```text
Run_HRD.bat
```

The launcher opens a command window, starts the HRD task, and keeps the window
open if there is an error.

### Desktop Shortcuts

You can create Desktop shortcuts to the launcher files:

- macOS: right-click `Run_HRD.command`, choose `Make Alias`, then move the alias
  to the Desktop.
- Windows: right-click `Run_HRD.bat`, choose `Show more options`, then
  `Send to` > `Desktop (create shortcut)`.

Do not commit machine-specific Desktop shortcut files. Commit the launcher
scripts instead.

## Startup Dialog

When the task starts, a popup asks for:

- `Participant ID`
- `Breathwork timing`

Use:

- `1 - Before breathwork` for the pre-breathwork HRD task
- `2 - After breathwork` for the post-breathwork HRD task

The participant ID and breathwork timing must be correct before the task starts.

## Output Files

By default, data is saved under:

```text
data/<participant-id><session>/
```

The default session is `HRD` plus the breathwork timing code:

- Participant `1` before breathwork saves to `data/1HRD1/`
- Participant `1` after breathwork saves to `data/1HRD2/`

The main trial file is updated after every completed trial:

```text
<participant-id><session>.txt
```

The trial file includes:

- `BreathworkPhaseCode`
- `BreathworkPhase`

If the task is interrupted after at least one completed experimental trial, it
also saves partial output files.

## Run From Command Line

Command-line running is useful for troubleshooting, explicit serial ports, or
non-default settings.

### Activate The Environment

macOS:

```bash
conda activate ./conda-envs/cardioception-nonin
```

Windows:

```bat
conda activate .\conda-envs\cardioception-nonin
```

### Basic Run

From the repository root:

```bash
python scripts/run_hrd_nonin.py
```

This still opens the startup dialog for participant ID and breathwork timing.

### Bypass The Startup Dialog

Before breathwork:

```bash
python scripts/run_hrd_nonin.py --participant-id 1 --breathwork-phase 1
```

After breathwork:

```bash
python scripts/run_hrd_nonin.py --participant-id 1 --breathwork-phase 2
```

The older `--subject-num` flag still works as an alias for `--participant-id`.

### Explicit Serial Port

The script tries to auto-detect the Nonin serial port. If auto-detection fails,
pass the port manually.

macOS example:

```bash
python scripts/run_hrd_nonin.py --serial-port /dev/cu.usbmodemXXXX
```

Windows example:

```bat
python scripts/run_hrd_nonin.py --serial-port COM5
```

On Windows, the COM port can be checked in Device Manager.

On macOS, possible USB serial ports can be listed with:

```bash
ls /dev/cu.usb* /dev/tty.usb*
```

### Useful Optional Flags

Run windowed:

```bash
python scripts/run_hrd_nonin.py --windowed
```

Skip the tutorial:

```bash
python scripts/run_hrd_nonin.py --skip-tutorial
```

Change trial counts:

```bash
python scripts/run_hrd_nonin.py --intero-trials 40 --extero-trials 20
```

Swap mouse response buttons:

```bash
python scripts/run_hrd_nonin.py --mouse-more-button left --mouse-less-button right
```

Show all command-line options:

```bash
python scripts/run_hrd_nonin.py --help
```

## Troubleshooting

If the launcher says it cannot find the Python environment, install the
environment first using the instructions above.

If data already exists for the same participant and session, the task stops to
avoid overwriting data. Use the correct breathwork timing, or use a unique
participant ID/session if you are intentionally repeating a run. The error
message lists the exact result folder and existing participant files to
move/delete if the old run should be discarded.

If the Nonin port is not detected automatically, run from the command line with
`--serial-port`.

When the Nonin device is missing, unplugged, busy, or not recognised, the task
prints a `Nonin pulse oximeter connection problem` message. That message lists
the serial ports currently visible to Python and gives the exact `--serial-port`
command format to try next.

## Analysis

Analysis materials remain in `R_analysis/` and `docs/source/examples/`.
For the breathwork task workflow, the key acquisition instructions are in this
README.

## Credit

This study workflow is based on Cardioception by Nicolas Legrand, Micah Allen,
and the Embodied Computation Group. The acquisition workflow here has been
adapted for the breathwork HRD protocol.
