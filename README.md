# TTS

## Stitching utilities

This project bundles helpers that combine audio snippets and subtitle fragments
into finalized deliverables:

- **Audio stitching** – `tts_edge.stitch.stitch_audio` concatenates sequential
  `part_XXXX.*` clips stored in a directory. The implementation uses
  [`pydub`](https://github.com/jiaaro/pydub) and supports configurable
  crossfades (20 ms by default) to smooth the seams between clips.
- **Subtitle merging** – `tts_edge.stitch.merge_srts` loads sequential
  `part_XXXX.srt` files, offsets each cue by the cumulative duration, and writes
  a clean UTF-8 SRT file.

See the tests in `tests/test_stitch.py` for end-to-end samples that produce
stitched audio and merged subtitles.
