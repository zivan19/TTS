from __future__ import annotations

import re
from datetime import timedelta
from pathlib import Path
from typing import List

from pydub import AudioSegment

from .subtitles import read_srt, write_srt


_PART_PATTERN = re.compile(r"^part_(\d+)\.[^.]+$")


def _ordered_part_files(parts_dir: Path, suffix: str | None = None) -> List[Path]:
    if not parts_dir.exists():
        raise ValueError(f"Parts directory does not exist: {parts_dir}")

    files = [p for p in parts_dir.iterdir() if p.is_file()]
    if suffix is not None:
        suffix = suffix.lower()
        files = [p for p in files if p.suffix.lower() == suffix]

    numbered: List[tuple[int, Path, int]] = []
    for path in files:
        match = _PART_PATTERN.match(path.name)
        if not match:
            continue
        index_text = match.group(1)
        numbered.append((int(index_text), path, len(index_text)))

    if not numbered:
        raise ValueError(f"No part files found in {parts_dir}")

    widths = {width for _, _, width in numbered}
    if len(widths) != 1:
        raise ValueError("Part filenames must share the same zero-padding width")

    ordered = sorted(numbered, key=lambda item: item[0])
    expected = ordered[0][0]
    width = ordered[0][2]
    for number, _path, _ in ordered:
        if number != expected:
            raise ValueError(
                f"Missing part file for index {expected:0{width}d} in {parts_dir}"
            )
        expected += 1

    return [path for _, path, _ in ordered]


def stitch_audio(parts_dir: Path, out_path: Path, crossfade_ms: int = 20) -> None:
    """Concatenate audio segments from ``parts_dir`` into a single file."""

    if crossfade_ms < 0:
        raise ValueError("crossfade_ms must be non-negative")

    audio_files = _ordered_part_files(parts_dir)
    audio_iter = iter(audio_files)

    try:
        first_path = next(audio_iter)
    except StopIteration as exc:  # pragma: no cover - guarded by _ordered_part_files
        raise ValueError("No audio segments found to stitch") from exc

    merged = AudioSegment.from_file(first_path)
    for audio_path in audio_iter:
        segment = AudioSegment.from_file(audio_path)
        crossfade = min(crossfade_ms, len(merged), len(segment))
        merged = merged.append(segment, crossfade=crossfade)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    export_format = out_path.suffix.lstrip(".") or "wav"
    merged.export(out_path, format=export_format)


def merge_srts(subs_dir: Path, out_path: Path) -> None:
    """Merge sequential subtitle parts into a single SRT file."""

    subtitle_files = _ordered_part_files(subs_dir, suffix=".srt")

    merged_subs = []
    offset = timedelta()

    for srt_path in subtitle_files:
        subtitles = read_srt(srt_path)
        if not subtitles:
            continue

        for subtitle in subtitles:
            shifted = subtitle.__class__(
                index=subtitle.index,
                start=subtitle.start + offset,
                end=subtitle.end + offset,
                content=subtitle.content,
                proprietary=subtitle.proprietary,
            )
            merged_subs.append(shifted)

        offset += subtitles[-1].end

    write_srt(merged_subs, out_path)
