"""Utility functions powering the :mod:`tts_edge` command line interface."""
from __future__ import annotations

import math
import re
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Sequence

SAMPLE_RATE = 22_050
BIT_DEPTH = 2  # bytes per sample for 16-bit audio


@dataclass(slots=True)
class TextChunk:
    """Represents a slice of text ready for synthesis."""

    index: int
    text: str

    @property
    def key(self) -> str:
        return f"chunk-{self.index:04d}"


@dataclass(slots=True)
class AudioChunk:
    """Represents synthesized audio for a text chunk."""

    chunk: TextChunk
    samples: array
    duration: float
    path: Path


@dataclass(slots=True)
class SRTEntry:
    """Represents a subtitle entry."""

    index: int
    start: float
    end: float
    text: str


def load_text(path: Path) -> str:
    """Read a UTF-8 encoded text file."""

    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text("utf-8").strip()


def chunk_text(text: str, max_len: int) -> List[TextChunk]:
    """Split a block of text into manageable chunks.

    Chunks are produced sentence-by-sentence while respecting the ``max_len``
    constraint. Fallback logic ensures that extremely long sentences are still
    split cleanly.
    """

    if max_len < 1:
        raise ValueError("max_len must be positive")

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: List[TextChunk] = []
    buffer: List[str] = []

    def flush_buffer() -> None:
        if buffer:
            chunk_text = " ".join(buffer).strip()
            if chunk_text:
                chunks.append(TextChunk(index=len(chunks), text=chunk_text))
            buffer.clear()

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_len:
            flush_buffer()
            for piece in _split_long_sentence(sentence, max_len):
                chunks.append(TextChunk(index=len(chunks), text=piece))
        else:
            tentative = " ".join(buffer + [sentence]).strip()
            if len(tentative) > max_len:
                flush_buffer()
                buffer.append(sentence)
            else:
                buffer.append(sentence)
    flush_buffer()
    return chunks


def _split_long_sentence(sentence: str, max_len: int) -> Iterator[str]:
    words = sentence.split(" ")
    buff: List[str] = []
    for word in words:
        buff.append(word)
        tentative = " ".join(buff)
        if len(tentative) >= max_len:
            yield tentative
            buff.clear()
    if buff:
        yield " ".join(buff)


def synth_all(
    chunks: Sequence[TextChunk],
    out_dir: Path,
    voice: str,
    rate: float,
    pitch: float,
    volume: float,
    concurrency: int,
    resume: bool,
    progress_callback: callable | None = None,
) -> tuple[List[AudioChunk], List[SRTEntry]]:
    """Synthesize all chunks concurrently.

    The speech generation is a lightweight deterministic synthesizer that turns
    text into sine-wave audio. It is intentionally simple so that the pipeline
    can run in a self-contained environment without external services.
    """

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")

    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    completed: List[AudioChunk] = []
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def synth_chunk(chunk: TextChunk) -> AudioChunk:
        target = chunks_dir / f"{chunk.index:04d}.wav"
        if resume and target.exists():
            samples, duration = _read_wave(target)
        else:
            samples, duration = _sine_speech(chunk.text, voice, rate, pitch, volume)
            _write_wave(target, samples)
        return AudioChunk(chunk=chunk, samples=samples, duration=duration, path=target)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {executor.submit(synth_chunk, chunk): chunk for chunk in chunks}
        for future in as_completed(future_map):
            audio_chunk = future.result()
            completed.append(audio_chunk)
            if progress_callback:
                progress_callback(1)

    completed.sort(key=lambda a: a.chunk.index)
    srt_entries = _build_srt_entries(completed)
    return completed, srt_entries


def stitch_audio(
    audio_chunks: Sequence[AudioChunk],
    out_dir: Path,
    crossfade_ms: int,
    progress_callback: callable | None = None,
) -> Path:
    """Merge all audio chunks into a single WAV file with optional crossfades."""

    if not audio_chunks:
        raise ValueError("No audio chunks were provided")

    final_path = out_dir / "synthesized.wav"
    crossfade_samples = max(0, int(SAMPLE_RATE * crossfade_ms / 1000))
    output = array("h")

    for index, chunk in enumerate(audio_chunks):
        data = array("h", chunk.samples)
        if index == 0 or crossfade_samples == 0:
            output.extend(data)
        else:
            overlap = min(crossfade_samples, len(data), len(output))
            if overlap:
                start_idx = len(output) - overlap
                for i in range(overlap):
                    fade_out = 1.0 - (i / overlap)
                    fade_in = i / overlap
                    mixed = int(output[start_idx + i] * fade_out + data[i] * fade_in)
                    output[start_idx + i] = max(-32768, min(32767, mixed))
                output.extend(data[overlap:])
            else:
                output.extend(data)
        if progress_callback:
            progress_callback(1)

    _write_wave(final_path, output)
    return final_path


def merge_srts(
    entries: Sequence[SRTEntry],
    out_dir: Path,
    progress_callback: callable | None = None,
) -> Path:
    """Combine individual SRT entries into a single file."""

    if not entries:
        raise ValueError("No subtitle entries to merge")

    final_path = out_dir / "synthesized.srt"
    lines: List[str] = []
    for entry in entries:
        lines.append(str(entry.index))
        lines.append(f"{_format_ts(entry.start)} --> {_format_ts(entry.end)}")
        lines.append(entry.text)
        lines.append("")
        if progress_callback:
            progress_callback(1)

    final_path.write_text("\n".join(lines), encoding="utf-8")
    return final_path


def _format_ts(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _build_srt_entries(audio_chunks: Sequence[AudioChunk]) -> List[SRTEntry]:
    entries: List[SRTEntry] = []
    cursor = 0.0
    for chunk in audio_chunks:
        start = cursor
        end = cursor + chunk.duration
        entries.append(
            SRTEntry(
                index=len(entries) + 1,
                start=start,
                end=end,
                text=chunk.chunk.text,
            )
        )
        cursor = end
    return entries


def _sine_speech(
    text: str,
    voice: str,
    rate: float,
    pitch: float,
    volume: float,
) -> tuple[array, float]:
    """Generate a deterministic sine-wave representation for ``text``."""

    sanitized = text.strip()
    if not sanitized:
        return array("h"), 0.0

    base_duration = 0.35
    per_char = max(0.02, 0.06 / max(rate, 0.1))
    duration = base_duration + len(sanitized) * per_char

    base_freq = 200 + (hash(voice) % 200)
    freq = base_freq * (2 ** (pitch / 12.0))
    amplitude = max(0.0, min(1.0, volume)) * 32767

    total_samples = int(duration * SAMPLE_RATE)
    data = array("h")
    for n in range(total_samples):
        t = n / SAMPLE_RATE
        value = int(amplitude * math.sin(2 * math.pi * freq * t))
        data.append(value)
    return data, total_samples / SAMPLE_RATE


def _write_wave(path: Path, samples: array) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(BIT_DEPTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(samples.tobytes())


def _read_wave(path: Path) -> tuple[array, float]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        data = array("h")
        data.frombytes(handle.readframes(frames))
        duration = frames / handle.getframerate()
    return data, duration
