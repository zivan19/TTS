"""Deterministic helpers that model a tiny speech pipeline.

The real project relies on an asynchronous Edge TTS client.  For tests we only
need a deterministic representation of the key pieces so that we can stitch the
waveform returned for each chunk and merge the subtitle segments that belong to
those chunks.  The helpers below are intentionally straightforward and avoid
external dependencies so that golden tests can exercise them without requiring
network access.
"""

from __future__ import annotations

from array import array
from dataclasses import dataclass
from typing import Callable, Iterable, List, Sequence, Tuple


@dataclass
class RelativeSegment:
    """Segment whose timestamps are relative to the start of a chunk."""

    start: float
    end: float
    text: str


@dataclass
class SrtSegment:
    """Subtitle segment with absolute timestamps."""

    index: int
    start: float
    end: float
    text: str


@dataclass
class SynthesizedChunk:
    """Result of synthesising a single chunk of text."""

    text: str
    sample_rate: int
    waveform: array
    segments: List[RelativeSegment]

    def __post_init__(self) -> None:
        if not isinstance(self.waveform, array):
            # Normalise to 16-bit signed integers to match typical PCM data.
            self.waveform = array("h", self.waveform)
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be a positive integer")
        if any(seg.end < seg.start for seg in self.segments):
            raise ValueError("segment end must not be before its start")

    @property
    def duration(self) -> float:
        """Duration of the waveform in seconds."""

        if not self.waveform:
            return 0.0
        return len(self.waveform) / float(self.sample_rate)


def synthesize_chunks(
    chunks: Sequence[str],
    synthesizer: Callable[[str], SynthesizedChunk],
) -> List[SynthesizedChunk]:
    """Synchronously synthesise a list of text chunks."""

    results: List[SynthesizedChunk] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        result = synthesizer(chunk)
        if not isinstance(result, SynthesizedChunk):
            raise TypeError("synthesizer must return SynthesizedChunk instances")
        results.append(result)
    return results


def stitch_waveforms(chunks: Sequence[SynthesizedChunk]) -> Tuple[array, int]:
    """Combine multiple waveforms into a single PCM buffer."""

    if not chunks:
        return array("h"), 0

    sample_rate = chunks[0].sample_rate
    stitched = array("h")
    for chunk in chunks:
        if chunk.sample_rate != sample_rate:
            raise ValueError("all chunks must use the same sample rate")
        stitched.extend(chunk.waveform)
    return stitched, sample_rate


def merge_srt_segments(chunks: Sequence[SynthesizedChunk]) -> List[SrtSegment]:
    """Merge relative subtitle segments into a single ordered list."""

    merged: List[SrtSegment] = []
    offset = 0.0
    index = 1
    for chunk in chunks:
        for segment in chunk.segments:
            merged.append(
                SrtSegment(
                    index=index,
                    start=round(segment.start + offset, 3),
                    end=round(segment.end + offset, 3),
                    text=segment.text,
                )
            )
            index += 1
        offset += chunk.duration
    return merged


def format_timestamp(seconds: float) -> str:
    """Convert a number of seconds into the SRT hh:mm:ss,mmm format."""

    total_milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def render_srt(segments: Iterable[SrtSegment]) -> str:
    """Render merged subtitle segments to a single SRT string."""

    lines: List[str] = []
    for segment in segments:
        lines.append(str(segment.index))
        lines.append(
            f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}"
        )
        lines.append(segment.text)
        lines.append("")
    # Ensure a trailing newline so that tools expecting POSIX text files are happy.
    return "\n".join(lines).rstrip() + "\n"
