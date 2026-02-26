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

Run the setup script from the repo root:

```bash
./scripts/setup_conda_nonin.sh
```

This creates the environment at:

`./conda-envs/cardioception-nonin`

## 4) Activate the environment

From the repo root:

```bash
conda activate ./conda-envs/cardioception-nonin
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

## 8) Useful optional flags

Windowed mode:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --windowed
```

Skip tutorial:

```bash
python scripts/run_hrd_nonin.py --subject-num 1 --skip-tutorial
```

## 9) Where output is saved

By default:

`./data/<subject-num><session>/`

Default session is `HRD`, so subject `1` saves to:

`./data/1HRD/`
