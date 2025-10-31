# TTS

TTS is a command-line tool for turning long-form text such as books, scripts, and articles into high-quality audio files. The project focuses on reliable offline generation, resumable processing, and flexible output options so you can ship audiobooks and narrated content with minimal friction.

## Quickstart

1. **Install prerequisites.**
   - Python 3.10 or newer.
   - `ffmpeg` available on your system `PATH`.
     ```bash
     # Debian / Ubuntu
     sudo apt-get update && sudo apt-get install ffmpeg

     # macOS (Homebrew)
     brew install ffmpeg
     ```
2. **Create and activate a virtual environment.**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```
3. **Install the project.**
   ```bash
   pip install -e .
   ```
4. **Generate your first clip.**
   ```bash
   tts --text "Hello world, this is your narrator." --voice en_US_narrator --output output/hello-world.wav
   ```
   The command above creates `output/hello-world.wav` and an accompanying `.srt` subtitle file by default.

## Choosing a Voice

Use `tts voices` to list the voices that ship with the model bundle and the remote catalogue.

```bash
# Show the full catalogue
tts voices

# Filter to English female voices
tts voices --language en --gender female
```

When generating audio, pass the identifier to `--voice`:

```bash
tts --text "Chapter One." --voice en_GB_storyteller --output output/chapter-01.wav
```

If you have a local `.onnx` or `.pth` checkpoint, you can point the CLI at it directly:

```bash
tts --text-file chapters/prologue.txt --voice ./voices/custom/checkpoint.onnx --output output/prologue.wav
```

## Handling Very Long Books

Long manuscripts are processed by splitting the text into manageable segments. The CLI accepts plain-text, Markdown, and EPUB input.

```bash
# Process a full book in EPUB format
tts --input-file books/the-lost-expedition.epub --voice en_US_narrator --output output/lost-expedition
```

Tips for smooth long-form runs:

- **Tune the chunk size.** `--chunk-size 1200` (in characters) keeps memory usage predictable while preserving natural pauses.
- **Normalize whitespace.** Run your source through a formatter to remove double spaces and stray control characters.
- **Pre-generate chapter markers.** Place `# Chapter` headers in Markdown to align the audio with the text.

The CLI writes one audio file per chapter and stitches them into a final master track named after the `--output` base.

## Resuming Failed Runs

Every synthesis run writes a `.tts-run.json` manifest beside the output. If a run is interrupted, restart it with `--resume` to skip completed segments:

```bash
tts --input-file books/the-lost-expedition.epub --voice en_US_narrator --output output/lost-expedition --resume
```

You can also resume from a different machine by copying the manifest and partial audio files to the new environment.

## Common Errors

### `ffmpeg` missing

If you see `OSError: ffmpeg not found`, confirm it is installed and visible in `PATH`:

```bash
ffmpeg -version
```

On Windows, download the official build from [gyan.dev](https://www.gyan.dev/ffmpeg/) and add the `bin` folder to your system `PATH`.

### Network hiccups while downloading voices

Transient network failures can interrupt downloads. Re-run the command; the downloader verifies partial artifacts and only fetches missing chunks. For persistent issues, set `HTTP_PROXY` / `HTTPS_PROXY` if you are behind a corporate proxy.

### HTTP 429: Too Many Requests

Voice providers may throttle repeated requests. Use `--cache-dir` so previously downloaded models are reused, and back off for a few minutes before trying again.

## Windows Path Tips

- Always wrap paths containing spaces in quotes: `"C:\\Users\\You\\Documents\\books\\novel.txt"`.
- Prefer forward slashes inside WSL or Git Bash: `books/novel.txt`.
- Use raw string literals in PowerShell: ``tts --input-file "C:\Users\You\books\novel.txt"``.

## Disabling Subtitles

By default the CLI emits `.srt` subtitle files so media players can display captions. Disable subtitle generation with `--disable-subtitles`:

```bash
tts --input-file books/the-lost-expedition.epub \
    --voice en_US_narrator \
    --output output/lost-expedition \
    --disable-subtitles
```

## Changing the Output Format

Set `--format` to control the container and encoding. Supported values include `wav`, `mp3`, and `flac`.

```bash
# Produce MP3 files for each chapter
tts --input-file books/the-lost-expedition.epub --voice en_US_narrator --output output/lost-expedition --format mp3

# Override bitrate when encoding MP3
tts --text-file chapters/afterword.txt --voice en_US_narrator --output output/afterword.mp3 --format mp3 --bitrate 192k
```

When you specify a single output file (e.g., `output/afterword.mp3`), the CLI picks the correct extension automatically.

## Troubleshooting Checklist

1. Run with `--verbose` to surface detailed logs.
2. Remove the `.cache/tts` directory if models become corrupted.
3. Confirm GPU availability with `python -m tts doctor` (falls back to CPU automatically).
4. Share logs and command output when opening an issue.

## License

This project is released under the MIT License. See [LICENSE](LICENSE) for details.
