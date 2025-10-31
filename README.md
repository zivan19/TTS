# tts-edge

tts-edge is a command-line toolkit for chunking, synthesizing, and stitching large text-to-speech projects using Microsoft's edge-tts service. It is designed for workflows that produce long-form audio with aligned subtitles and configurable post-processing.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .[dev]
```

## Install FFmpeg

FFmpeg is required for audio processing via `pydub` and `ffmpeg-python`.

- **macOS (Homebrew):** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y ffmpeg`
- **Windows (chocolatey):** `choco install ffmpeg`

Verify the installation with `ffmpeg -version`.

## CLI Usage

After installation, the Typer-based CLI exposes a `tts-edge` command. Use `--help` to see available commands and options:

```bash
tts-edge --help
```

To print the installed version, run:

```bash
tts-edge version
```
