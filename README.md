# tts-edge

`tts-edge` is a self-contained demonstration of an end-to-end text-to-speech
pipeline. It ships a Typer-powered CLI that loads plain text, chunks it,
synthesizes deterministic audio, stitches the results, and optionally produces
SRT subtitles – all with Rich-powered progress feedback.

## Installation

The project uses a standard `pyproject.toml` with a `setuptools` build backend.
Install it in an isolated virtual environment (recommended) or via `pipx`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install .
```

### macOS / Linux (bash or zsh)

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
```

### pipx (cross-platform)

```bash
pipx install .
```

## Usage

The CLI exposes a single `synth` command. Use `--help` to explore options.

```bash
tts-edge synth input.txt --out output-directory
```

### Windows example

```powershell
tts-edge synth .\samples\story.txt --out .\artifacts --voice narrator --rate 1.1 --pitch 2 --volume 0.8
```

### macOS example

```bash
tts-edge synth samples/story.txt --out artifacts --voice storyteller --crossfade-ms 50 --resume
```

### Linux example

```bash
tts-edge synth samples/story.txt --out artifacts --no-srt --concurrency 4
```

### Command reference

```text
Usage: tts-edge synth TEXT_FILE [OPTIONS]

Arguments:
  TEXT_FILE  Path to the input text file.  [required]

Options:
  --out DIRECTORY               Directory where artifacts will be written.  [required]
  --voice TEXT                  Logical voice identifier.  [default: standard]
  --rate FLOAT                  Playback rate multiplier.  [default: 1.0]
  --pitch FLOAT                 Pitch adjustment in semitones.  [default: 0.0]
  --volume FLOAT                Output volume multiplier.  [default: 1.0]
  --max-len INTEGER             Maximum characters per chunk.  [default: 2500]
  --concurrency INTEGER         Number of concurrent synthesis workers.  [default: 2]
  --crossfade-ms INTEGER        Crossfade duration between chunks.  [default: 20]
  --no-srt                      Disable subtitle generation.
  --resume / --no-resume        Reuse previously synthesized chunks if available.  [default: --no-resume]
  --help                        Show this message and exit.
```

When the run completes you will see a Rich summary panel containing the number
of chunks produced, the synthesized audio duration, and the generated artifact
paths.
