from __future__ import annotations

import hashlib
from array import array
from pathlib import Path
from typing import Callable, List
from unittest.mock import Mock

import pytest

from tts import (
    RelativeSegment,
    SynthesizedChunk,
    merge_srt_segments,
    render_srt,
    stitch_waveforms,
    synthesize_chunks,
)


SAMPLE_RATE = 16_000
EXPECTED_WAVE_DIGEST = "c3fe43154f013cc0d78e18b077c121727249c236b8134e63adf646a1c20a1109"
EXPECTED_SRT_DIGEST = "f12cfe320694f8918012e9d8d662b8e9a2299692addbe3a580acdf2d1ae82171"


def _mock_edge_tts() -> Callable[[str], SynthesizedChunk]:
    def _generate(text: str) -> SynthesizedChunk:
        base = sum(ord(char) for char in text)
        waveform = array(
            "h",
            ((base + (index * 31)) % 32768 - 16384 for index in range(len(text) * 12)),
        )
        duration = len(waveform) / SAMPLE_RATE
        words = text.split() or [text]
        step = duration / len(words)
        segments: List[RelativeSegment] = []
        for idx, word in enumerate(words):
            start = idx * step
            end = duration if idx == len(words) - 1 else (idx + 1) * step
            segments.append(RelativeSegment(start=start, end=end, text=word))
        return SynthesizedChunk(
            text=text,
            sample_rate=SAMPLE_RATE,
            waveform=waveform,
            segments=segments,
        )

    return Mock(side_effect=_generate, name="edge_tts_mock")


@pytest.mark.parametrize("chunk_count", [3])
def test_small_sample_pipeline_golden(chunk_count: int) -> None:
    root = Path(__file__).resolve().parents[1]
    text_path = root / "samples" / "alice_excerpt.txt"
    lines = [line.strip() for line in text_path.read_text(encoding="utf8").splitlines()]
    chunks = [line for line in lines if line][:chunk_count]
    assert len(chunks) == chunk_count, "sample must provide enough lines"

    mocked_edge_tts = _mock_edge_tts()
    synthesized = synthesize_chunks(chunks, mocked_edge_tts)
    assert mocked_edge_tts.call_count == chunk_count

    stitched, sample_rate = stitch_waveforms(synthesized)
    assert sample_rate == SAMPLE_RATE
    digest = hashlib.sha256(stitched.tobytes()).hexdigest()
    assert digest == EXPECTED_WAVE_DIGEST

    merged_segments = merge_srt_segments(synthesized)
    srt_output = render_srt(merged_segments)
    srt_digest = hashlib.sha256(srt_output.encode("utf8")).hexdigest()
    assert srt_digest == EXPECTED_SRT_DIGEST

    # Spot-check the merged subtitles for sanity to make debugging easier.
    assert merged_segments[0].text == "Alice"
    assert merged_segments[-1].text == 'conversations?"'
    assert merged_segments[-1].end == pytest.approx(0.225, rel=1e-6)

    # Ensure the merge keeps a stable number of subtitle rows.
    assert len(merged_segments) == sum(len(chunk.segments) for chunk in synthesized)
