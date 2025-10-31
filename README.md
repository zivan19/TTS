# TTS

This repository contains a small, testable example of a resumable text to speech
(TTS) synthesis pipeline. The included runner keeps track of synthesis speeds to
estimate the remaining time and writes a checkpoint when interrupted so that a
future run can resume seamlessly.

## Running the demo

```bash
python -m tts.cli "This is a demo phrase" --checkpoint synth.json
```

Re-run the command with ``--resume`` to continue from the last saved chunk if a
``SIGINT`` (``Ctrl+C``) interrupted the synthesis.

## Testing

```bash
pytest
```
