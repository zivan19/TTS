from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from tts_edge.stitch import merge_srts, stitch_audio
from tts_edge.subtitles import read_srt


@pytest.fixture()
def tone_segments(tmp_path: Path) -> Path:
    parts_dir = tmp_path / "audio_parts"
    parts_dir.mkdir()

    durations = [500, 500, 500]
    frequencies = [440, 554, 660]

    for index, (duration, frequency) in enumerate(zip(durations, frequencies), start=1):
        segment = Sine(frequency).to_audio_segment(duration=duration)
        file_path = parts_dir / f"part_{index:04d}.wav"
        segment.export(file_path, format="wav")

    return parts_dir


def test_stitch_audio_crossfade(tmp_path: Path, tone_segments: Path) -> None:
    out_path = tmp_path / "stitched.wav"
    crossfade = 20

    stitch_audio(tone_segments, out_path, crossfade_ms=crossfade)

    result = AudioSegment.from_file(out_path)
    expected_length = (3 * 500) - crossfade * 2
    assert abs(len(result) - expected_length) <= 1


def test_merge_srts(tmp_path: Path) -> None:
    subs_dir = tmp_path / "subs"
    subs_dir.mkdir()

    part_1 = """1\n00:00:00,000 --> 00:00:01,000\nHello there  \n\n2\n00:00:01,200 --> 00:00:02,000\nGeneral Kenobi\n"""
    part_2 = """1\n00:00:00,000 --> 00:00:01,500\nAnother line\n"""
    part_3 = """1\n00:00:00,500 --> 00:00:01,000\nFinal bit\n"""

    (subs_dir / "part_0001.srt").write_text(part_1, encoding="utf-8")
    (subs_dir / "part_0002.srt").write_text(part_2, encoding="utf-8")
    (subs_dir / "part_0003.srt").write_text(part_3, encoding="utf-8")

    out_path = tmp_path / "final.srt"
    merge_srts(subs_dir, out_path)

    merged = read_srt(out_path)
    assert len(merged) == 4
    assert merged[0].start == timedelta(seconds=0)
    assert merged[0].content == "Hello there"
    assert merged[1].start == timedelta(milliseconds=1200)
    assert merged[2].start == timedelta(seconds=2)
    assert merged[3].start == timedelta(seconds=4)
    assert merged[-1].end == timedelta(milliseconds=4500)


def test_invalid_part_names(tmp_path: Path) -> None:
    parts_dir = tmp_path / "bad_parts"
    parts_dir.mkdir()

    (parts_dir / "part_1.wav").write_bytes(b"")
    (parts_dir / "part_0002.wav").write_bytes(b"")

    with pytest.raises(ValueError):
        stitch_audio(parts_dir, tmp_path / "out.wav")
