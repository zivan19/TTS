# TTS

Asynchronous helpers for producing MP3 audio and SRT subtitle chunks using
[edge-tts](https://github.com/rany2/edge-tts).

## Configuration defaults

| Option | Default | Description |
| --- | --- | --- |
| `DEFAULT_VOICE` | `af-ZA-AdriNeural` | Azure voice used by default. |
| `DEFAULT_RATE` | `+0%` | Speaking rate relative to the default speed. |
| `DEFAULT_PITCH` | `+0Hz` | Pitch adjustment relative to the default tone. |
| `DEFAULT_VOLUME` | `+0%` | Volume gain relative to the default loudness. |

Each modifier follows the standard edge-tts format:

- **Voice** is a string identifier from the available Azure neural voices.
- **Rate/Volume** are percentages, e.g. `-10%`, `+20%`.
- **Pitch** is expressed in Hertz, e.g. `-4Hz`, `+3Hz`.

## Synthesizing chunks

Use `tts_edge.synth.synth_all` to process a list of text chunks. The helper will
create `parts/part_XXXX.mp3` audio files (one per chunk) and matching subtitle
files under `subs/part_XXXX.srt` by default.

Key behaviours:

- **Concurrency** – limit simultaneous requests with the `concurrency` argument
  (default: `2`).
- **Resume support** – when `resume=True`, existing MP3 and SRT outputs are left
  untouched so interrupted runs can restart without re-synthesising completed
  chunks.
- **Retry & backoff** – transient HTTP `429`/`500` responses trigger exponential
  backoff delays of `0.5`, `1`, `2`, then `4` seconds before ultimately raising
  the error if the synthesis keeps failing.
- **Subtitles toggle** – set `srt=False` to skip subtitle generation entirely.

For single chunks you can call `tts_edge.synth.synth_chunk` directly, which uses
identical file naming, voice configuration, and retry semantics.
