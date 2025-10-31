"""Utility functions powering the :mod:`tts_edge` command line interface."""
from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterator, List, MutableMapping, Sequence

from .errors import PermanentSynthesisError, RateLimitedError, TransientSynthesisError

SAMPLE_RATE = 22_050
BIT_DEPTH = 2  # bytes per sample for 16-bit audio
_CHECKPOINT_FILENAME = "checkpoints.json"
_STATUS_PENDING = "pending"
_STATUS_DONE = "done"
_STATUS_FAILED = "failed"
_VALID_STATUSES = {_STATUS_PENDING, _STATUS_DONE, _STATUS_FAILED}


def _load_checkpoint(path: Path) -> Dict[str, Dict[str, int | str]]:
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    checkpoint: Dict[str, Dict[str, int | str]] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, dict):
            continue
        status = value.get("status")
        if status not in _VALID_STATUSES:
            status = _STATUS_PENDING
        attempts_raw = value.get("attempts", 0)
        try:
            attempts = int(attempts_raw)
        except (TypeError, ValueError):
            attempts = 0
        if attempts < 0:
            attempts = 0
        checkpoint[key] = {"status": status, "attempts": attempts}
    return checkpoint


def _write_checkpoint(
    path: Path, data: MutableMapping[str, Dict[str, int | str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(serialized, encoding="utf-8")
    tmp_path.replace(path)


def _compute_backoff_delay(
    attempt_no: int, base: float, cap: float, rng: random.Random
) -> float:
    exponent = max(attempt_no - 1, 0)
    delay = base * (2**exponent)
    delay = min(delay, cap)
    if delay <= 0:
        return 0.0
    return rng.uniform(0, delay)


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
    max_attempts: int,
    backoff_base: float,
    backoff_cap: float,
    progress_callback: Callable[[int], None] | None = None,
    *,
    sleep_func: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> tuple[List[AudioChunk], List[SRTEntry]]:
    """Synthesize all chunks concurrently.

    The speech generation is a lightweight deterministic synthesizer that turns
    text into sine-wave audio. It is intentionally simple so that the pipeline
    can run in a self-contained environment without external services.
    """

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if backoff_base <= 0:
        raise ValueError("backoff_base must be positive")
    if backoff_cap <= 0:
        raise ValueError("backoff_cap must be positive")

    chunks_dir = out_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / _CHECKPOINT_FILENAME

    checkpoint: Dict[str, Dict[str, int | str]]
    if resume:
        checkpoint = _load_checkpoint(checkpoint_path)
    else:
        checkpoint = {}

    completed_map: Dict[str, AudioChunk] = {}
    failures: List[tuple[TextChunk, str]] = []
    status_lock = threading.Lock()
    rng_lock = threading.Lock()
    rng = rng or random.Random()

    to_process: List[TextChunk] = []
    checkpoint_modified = False

    for chunk in chunks:
        key = chunk.key
        entry = checkpoint.get(key)
        if entry is None:
            entry = {"status": _STATUS_PENDING, "attempts": 0}
            checkpoint[key] = entry
            checkpoint_modified = True
        else:
            status = entry.get("status")
            if status not in _VALID_STATUSES:
                entry["status"] = _STATUS_PENDING
                checkpoint_modified = True
            attempts = entry.get("attempts")
            if not isinstance(attempts, int) or attempts < 0:
                entry["attempts"] = 0
                checkpoint_modified = True

        target = chunks_dir / f"{chunk.index:04d}.wav"
        status = entry["status"]  # type: ignore[index]

        if resume and status == _STATUS_DONE and target.exists():
            samples, duration = _read_wave(target)
            audio_chunk = AudioChunk(chunk=chunk, samples=samples, duration=duration, path=target)
            completed_map[key] = audio_chunk
            if progress_callback:
                progress_callback(1)
        else:
            if status == _STATUS_DONE and not target.exists():
                entry["status"] = _STATUS_PENDING
                checkpoint_modified = True
            to_process.append(chunk)

    if checkpoint_modified or not checkpoint_path.exists():
        with status_lock:
            _write_checkpoint(checkpoint_path, checkpoint)

    if not to_process:
        completed = sorted(completed_map.values(), key=lambda c: c.chunk.index)
        srt_entries = _build_srt_entries(completed)
        return completed, srt_entries

    def _delay_for(attempt_no: int) -> float:
        with rng_lock:
            return _compute_backoff_delay(attempt_no, backoff_base, backoff_cap, rng)

    from concurrent.futures import ThreadPoolExecutor, wait

    def process_chunk(chunk: TextChunk) -> None:
        key = chunk.key
        target = chunks_dir / f"{chunk.index:04d}.wav"
        entry = checkpoint[key]
        attempts = int(entry.get("attempts", 0))

        if attempts >= max_attempts and entry.get("status") != _STATUS_DONE:
            with status_lock:
                checkpoint[key]["status"] = _STATUS_FAILED
                _write_checkpoint(checkpoint_path, checkpoint)
                failures.append((chunk, "attempts exhausted"))
            return

        while attempts < max_attempts:
            attempt_no = attempts + 1
            try:
                samples, duration = _sine_speech(chunk.text, voice, rate, pitch, volume)
                _write_wave(target, samples)
                audio_chunk = AudioChunk(chunk=chunk, samples=samples, duration=duration, path=target)
                with status_lock:
                    checkpoint[key] = {"status": _STATUS_DONE, "attempts": attempt_no}
                    completed_map[key] = audio_chunk
                    _write_checkpoint(checkpoint_path, checkpoint)
                if progress_callback:
                    progress_callback(1)
                return
            except KeyboardInterrupt:
                raise
            except (RateLimitedError, TransientSynthesisError) as exc:
                attempts = attempt_no
                with status_lock:
                    checkpoint[key] = {"status": _STATUS_PENDING, "attempts": attempts}
                    _write_checkpoint(checkpoint_path, checkpoint)
                if attempts >= max_attempts:
                    with status_lock:
                        checkpoint[key] = {"status": _STATUS_FAILED, "attempts": attempts}
                        _write_checkpoint(checkpoint_path, checkpoint)
                        failures.append((chunk, str(exc)))
                    return
                delay = _delay_for(attempt_no)
                if delay > 0:
                    sleep_func(delay)
            except PermanentSynthesisError as exc:
                attempts = attempt_no
                with status_lock:
                    checkpoint[key] = {"status": _STATUS_FAILED, "attempts": attempts}
                    _write_checkpoint(checkpoint_path, checkpoint)
                    failures.append((chunk, str(exc)))
                return
            except Exception as exc:  # pragma: no cover - safety net
                attempts = attempt_no
                with status_lock:
                    checkpoint[key] = {"status": _STATUS_FAILED, "attempts": attempts}
                    _write_checkpoint(checkpoint_path, checkpoint)
                    failures.append((chunk, str(exc)))
                return
        with status_lock:
            checkpoint[key] = {"status": _STATUS_FAILED, "attempts": attempts}
            _write_checkpoint(checkpoint_path, checkpoint)
            failures.append((chunk, "attempts exhausted"))

    def sort_priority(chunk: TextChunk) -> tuple[int, int]:
        entry = checkpoint.get(chunk.key, {})
        status = entry.get("status", _STATUS_PENDING)
        priority = 1
        if status == _STATUS_FAILED:
            priority = 0
        elif status != _STATUS_PENDING:
            priority = 2
        return (priority, chunk.index)

    ordered = sorted(to_process, key=sort_priority)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(process_chunk, chunk) for chunk in ordered]
        wait(futures)

    with status_lock:
        _write_checkpoint(checkpoint_path, checkpoint)

    if failures:
        failed_keys = ", ".join(sorted({chunk.key for chunk, _ in failures}))
        raise RuntimeError(f"Failed to synthesize chunks: {failed_keys}")

    completed = [
        completed_map[ch.key]
        for ch in sorted(chunks, key=lambda chunk: chunk.index)
        if ch.key in completed_map
    ]
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
