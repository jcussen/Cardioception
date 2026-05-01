# Cardioception Nonin HRD: Simple Run Guide

This guide explains how to run the HRD task from scratch on a new machine.

## 1) What you need

- A computer with Conda installed (`conda` command available)
- A USB mouse
- A Nonin USB pulse oximeter connected to the computer
- This repository cloned locally

## 2) Clone the repository

```bash
git clone --depth 1 --single-branch https://github.com/jcussen/Cardioception.git
cd Cardioception
```

## 3) Create the Conda environment

### macOS / Linux

Run the setup script from the repo root:

```bash
./scripts/setup_conda_nonin.sh
```

This creates the environment at:

`./conda-envs/cardioception-nonin`

### Windows

Use Anaconda Prompt or Miniforge Prompt from the repo root:

```bat
conda env create --prefix .\conda-envs\cardioception-nonin -f environment_nonin.yml
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install "psychopy==2025.2.4"
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install "systole==0.3.1" --no-deps
conda run --prefix .\conda-envs\cardioception-nonin python -m pip install -e . --no-deps
```

## 4) Activate the environment

From the repo root:

```bash
conda activate ./conda-envs/cardioception-nonin
```

On Windows:

```bat
conda activate .\conda-envs\cardioception-nonin
```

## 5) Connect equipment

- Plug in the Nonin USB device
- Ensure the USB mouse is connected
- Keep the participant still during heart-listening periods

## 6) Run the task

From the repo root, run:

```bash
python scripts/run_hrd_nonin.py --subject-num 1
```

Notes:

- `--subject-num` is required.
- Subject number must be unique. If data already exists for that participant, the script stops and asks for a new subject number.
- The script tries to auto-detect the Nonin serial port.
- Default HRD length is 60 experimental trials: 40 interoceptive and 20 exteroceptive.
- The tutorial uses one practice trial per modality.

## 7) If auto-detection fails, pass port manually

### macOS

Find available USB serial ports where Nonin device is connected:

```bash
ls /dev/cu.usb* /dev/tty.usb*
```

Run with explicit port:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --serial-port /dev/cu.usbmodemXXXX
```

### Windows

Use the COM port in Device Manager:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --serial-port COM5
```

If auto-detection fails on Windows, use the COM port shown in Device Manager.

## 8) Useful optional flags

Windowed mode:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --windowed
```

Skip tutorial:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --skip-tutorial
```

Override trial counts:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --intero-trials 40 --extero-trials 20
```

## 9) Where output is saved

By default:

`./data/<subject-num><session>/`

Default session is `HRD`, so subject `1` saves to:

`./data/1HRD/`

During the task, `<subject-num><session>.txt` is updated after every completed
trial. If the participant stops early with Escape or the run is interrupted with
Ctrl-C, the task also saves partial outputs when at least one experimental trial
has completed:

- `<subject-num><session>_partial_final.txt`
- `<subject-num>Intero_posterior_partial.npy` and, if present, `<subject-num>Extero_posterior_partial.npy`
- `<subject-num>_signal_partial.txt`
- `<subject-num>_parameters_partial.pickle`

If the computer loses power or Python is force-killed, the per-trial
`<subject-num><session>.txt` file should still contain data through the last
completed trial, but the partial posterior and signal files may not be written.
