"""Tests for checkpoint-driven resume logic."""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from tts_edge import pipeline
from tts_edge.errors import PermanentSynthesisError


def _synth_kwargs():
    return dict(
        voice="standard",
        rate=1.0,
        pitch=0.0,
        volume=1.0,
        concurrency=1,
        max_attempts=3,
        backoff_base=0.1,
        backoff_cap=0.5,
        sleep_func=lambda _: None,
        rng=random.Random(0),
    )


def test_resume_retries_failed_chunk_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = "First chunk. Second chunk."
    chunks = pipeline.chunk_text(text, max_len=12)
    assert len(chunks) == 2

    first_text = chunks[0].text
    second_text = chunks[1].text
    first_key = chunks[0].key
    second_key = chunks[1].key

    original_sine = pipeline._sine_speech  # type: ignore[attr-defined]

    def failing_sine(text: str, *args, **kwargs):
        if text == first_text:
            raise PermanentSynthesisError("forced failure")
        return original_sine(text, *args, **kwargs)

    monkeypatch.setattr(pipeline, "_sine_speech", failing_sine)

    with pytest.raises(RuntimeError):
        pipeline.synth_all(
            chunks,
            tmp_path,
            resume=False,
            progress_callback=None,
            **_synth_kwargs(),
        )

    checkpoint_path = tmp_path / "checkpoints.json"
    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert data[first_key]["status"] == "failed"
    assert data[first_key]["attempts"] == 1
    assert data[second_key]["status"] == "done"

    call_order: list[str] = []

    def resumed_sine(text: str, *args, **kwargs):
        if text == first_text:
            call_order.append(first_key)
        elif text == second_text:
            call_order.append(second_key)
        return original_sine(text, *args, **kwargs)

    monkeypatch.setattr(pipeline, "_sine_speech", resumed_sine)

    audio_chunks, _ = pipeline.synth_all(
        chunks,
        tmp_path,
        resume=True,
        progress_callback=None,
        **_synth_kwargs(),
    )

    assert call_order == [first_key]

    updated = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert updated[first_key]["status"] == "done"
    assert updated[first_key]["attempts"] == 2
    assert len(audio_chunks) == 2


def test_resume_prioritises_failed_then_pending_then_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "One. Two. Three. Four."
    chunks = pipeline.chunk_text(text, max_len=6)
    assert len(chunks) == 4

    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_data = {
        chunks[0].key: {"status": "done", "attempts": 1},
        chunks[1].key: {"status": "failed", "attempts": 2},
        chunks[2].key: {"status": "pending", "attempts": 1},
    }

    samples, _ = pipeline._sine_speech(chunks[0].text, "standard", 1.0, 0.0, 1.0)  # type: ignore[attr-defined]
    pipeline._write_wave(chunks_dir / f"{chunks[0].index:04d}.wav", samples)  # type: ignore[attr-defined]

    checkpoint_path = tmp_path / "checkpoints.json"
    checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2), encoding="utf-8")

    text_to_key = {chunk.text: chunk.key for chunk in chunks}
    call_order: list[str] = []
    original_sine = pipeline._sine_speech  # type: ignore[attr-defined]

    def tracking_sine(text: str, *args, **kwargs):
        key = text_to_key.get(text)
        if key:
            call_order.append(key)
        return original_sine(text, *args, **kwargs)

    monkeypatch.setattr(pipeline, "_sine_speech", tracking_sine)

    audio_chunks, _ = pipeline.synth_all(
        chunks,
        tmp_path,
        resume=True,
        progress_callback=None,
        **_synth_kwargs(),
    )

    assert call_order == [chunks[1].key, chunks[2].key, chunks[3].key]
    assert len(audio_chunks) == 4

    updated = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    for chunk in chunks:
        assert updated[chunk.key]["status"] == "done"
        assert updated[chunk.key]["attempts"] >= 1
