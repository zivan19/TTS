# tts-edge

Command-line helpers for Microsoft Edge Text-to-Speech.

## Installation

```bash
pip install .
```

To install development dependencies (including the test suite):

```bash
pip install .[test]
```

## Usage

List voices retrieved from the Edge TTS service. Responses are cached for 24 hours in `~/.cache/tts-edge/voices.json` by default.

```bash
tts-edge voices
```

Force a refresh of the cached voice list:

```bash
tts-edge voices --refresh
```

Generate a short audition clip for a voice:

```bash
tts-edge audition --voice en-US-GuyNeural --text "Hello" --out demo.mp3
```

The command saves the generated audio file to the path provided via `--out`.
