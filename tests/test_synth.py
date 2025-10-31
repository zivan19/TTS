from __future__ import annotations

import asyncio
import types

import pytest

import tts_edge.synth as synth


class DummyCommunicate:
    """A stub ``edge_tts.Communicate`` implementation for testing."""

    def __init__(self, text: str, voice: str, rate: str, pitch: str, volume: str) -> None:
        self.text = text
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = volume

    async def stream(self):
        yield {"type": "audio", "data": b"audio-bytes"}
        yield {"type": "WordBoundary", "offset": 0, "duration": 1, "text": self.text}


class DummySubMaker:
    def __init__(self) -> None:
        self.chunks: list[dict[str, object]] = []

    def create_subtitle(self, chunk: dict[str, object]) -> None:
        self.chunks.append(chunk)

    def generate_subs(self, *, kind: str = "srt") -> str:
        return f"{kind}:{len(self.chunks)}"


@pytest.fixture(autouse=True)
def stub_edge_tts(monkeypatch):
    module = types.SimpleNamespace(Communicate=DummyCommunicate, SubMaker=DummySubMaker)
    monkeypatch.setattr(synth, "edge_tts", module)
    return module


def test_synth_chunk_creates_audio_and_subtitles(tmp_path):
    audio_path, subtitle_path = asyncio.run(
        synth.synth_chunk(
            text="Hello world",
            index=1,
            out_dir=tmp_path,
            voice="en-US-Example",
            rate="+10%",
            pitch="+2Hz",
            volume="+5%",
            srt=True,
        )
    )

    assert audio_path == tmp_path / "parts" / "part_0001.mp3"
    assert subtitle_path == tmp_path / "subs" / "part_0001.srt"
    assert audio_path.read_bytes() == b"audio-bytes"
    assert subtitle_path.read_text(encoding="utf-8") == "srt:1"


def test_synth_chunk_without_subtitles(tmp_path):
    audio_path, subtitle_path = asyncio.run(
        synth.synth_chunk(
            text="No subs",
            index=2,
            out_dir=tmp_path,
            voice="voice",
            rate="+0%",
            pitch="+0Hz",
            volume="+0%",
            srt=False,
        )
    )

    assert audio_path == tmp_path / "parts" / "part_0002.mp3"
    assert subtitle_path is None
    assert not (tmp_path / "subs" / "part_0002.srt").exists()


def test_synth_all_respects_resume(monkeypatch, tmp_path):
    parts_dir = tmp_path / "parts"
    subs_dir = tmp_path / "subs"
    parts_dir.mkdir()
    subs_dir.mkdir()

    existing_audio = parts_dir / "part_0001.mp3"
    existing_audio.write_bytes(b"old")
    existing_srt = subs_dir / "part_0001.srt"
    existing_srt.write_text("old", encoding="utf-8")

    calls: list[int] = []

    async def fake_synth_chunk(**kwargs):
        calls.append(kwargs["index"])
        return tmp_path / "parts" / f"part_{kwargs['index']:04d}.mp3", tmp_path / "subs" / f"part_{kwargs['index']:04d}.srt"

    monkeypatch.setattr(synth, "synth_chunk", fake_synth_chunk)

    results = asyncio.run(
        synth.synth_all(
            ["skip", "run"],
            out_dir=tmp_path,
            voice="voice",
            rate="+0%",
            pitch="+0Hz",
            volume="+0%",
            concurrency=2,
            resume=True,
        )
    )

    assert calls == [2]
    assert results[0] == (existing_audio, existing_srt)


class TransientError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class FlakyCommunicate:
    attempts = 0

    def __init__(self, text: str, voice: str, rate: str, pitch: str, volume: str) -> None:
        self.text = text

    async def stream(self):
        FlakyCommunicate.attempts += 1
        if FlakyCommunicate.attempts < 3:
            raise TransientError(429)
        yield {"type": "audio", "data": b"final"}
        yield {"type": "WordBoundary", "offset": 0, "duration": 1, "text": self.text}


def test_synth_all_retries_with_backoff(monkeypatch, tmp_path, stub_edge_tts):
    FlakyCommunicate.attempts = 0
    stub_edge_tts.Communicate = FlakyCommunicate

    sleep_calls: list[float] = []

    async def fake_sleep(duration: float):  # noqa: D401 - simple stub
        sleep_calls.append(duration)

    monkeypatch.setattr(synth.asyncio, "sleep", fake_sleep)

    results = asyncio.run(
        synth.synth_all(
            ["retry"],
            out_dir=tmp_path,
            voice="voice",
            rate="+0%",
            pitch="+0Hz",
            volume="+0%",
            concurrency=1,
            resume=False,
        )
    )

    audio_path, subtitle_path = results[0]
    assert audio_path.read_bytes() == b"final"
    assert subtitle_path.read_text(encoding="utf-8") == "srt:1"
    assert sleep_calls == [0.5, 1.0]
