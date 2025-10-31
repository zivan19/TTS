from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tts_edge import cache, cli


@pytest.fixture(autouse=True)
def restore_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("TTS_EDGE_CACHE_DIR", str(tmp_path))
    yield


def test_voices_command_uses_cache_when_fresh(monkeypatch, capsys):
    cached_voices = [
        {"ShortName": "en-US-AnaNeural", "Locale": "en-US", "Gender": "Female"}
    ]
    cache.save_cached_voices(cached_voices)

    async def _should_not_run():  # pragma: no cover - defensive
        raise AssertionError("list_voices should not be called when cache is fresh")

    monkeypatch.setattr(cli.edge_tts, "list_voices", _should_not_run)

    exit_code = cli.main(["voices"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "Name" in output
    assert "en-US-AnaNeural" in output
    assert "en-US" in output


def test_voices_command_refreshes_expired_cache(monkeypatch, capsys, tmp_path):
    path = cache.get_voices_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    stale_payload = {
        "timestamp": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "voices": [{"ShortName": "old", "Locale": "en-US", "Gender": "Female"}],
    }
    path.write_text(json.dumps(stale_payload))

    calls: list[list[str]] = []
    fresh_voices = [{"ShortName": "new", "Locale": "en-GB", "Gender": "Male"}]

    async def _fake_list_voices():
        calls.append(["called"])
        return fresh_voices

    monkeypatch.setattr(cli.edge_tts, "list_voices", _fake_list_voices)

    exit_code = cli.main(["voices"])
    assert exit_code == 0
    assert calls

    output = capsys.readouterr().out
    assert "new" in output
    assert "en-GB" in output

    updated_payload = json.loads(path.read_text())
    assert updated_payload["voices"] == fresh_voices


def test_voices_command_refresh_flag_forces_fetch(monkeypatch, capsys):
    cache.save_cached_voices([
        {"ShortName": "cached", "Locale": "en-US", "Gender": "Female"}
    ])

    fresh_voices = [{"ShortName": "fresh", "Locale": "fr-FR", "Gender": "Male"}]
    calls: list[list[str]] = []

    async def _fake_list_voices():
        calls.append(["called"])
        return fresh_voices

    monkeypatch.setattr(cli.edge_tts, "list_voices", _fake_list_voices)

    exit_code = cli.main(["voices", "--refresh"])
    assert exit_code == 0
    assert calls

    output = capsys.readouterr().out
    assert "fresh" in output
    assert "fr-FR" in output


def test_audition_command_writes_file(monkeypatch, tmp_path, capsys):
    calls: list[tuple[str, str]] = []

    class DummyCommunicate:
        def __init__(self, text: str, voice: str) -> None:
            calls.append((text, voice))

        async def save(self, path: str) -> None:
            Path(path).write_bytes(b"demo")

    monkeypatch.setattr(cli.edge_tts, "Communicate", DummyCommunicate)

    output_path = tmp_path / "demo.mp3"
    exit_code = cli.main([
        "audition",
        "--voice",
        "en-US-GuyNeural",
        "--text",
        "Hello world",
        "--out",
        str(output_path),
    ])

    assert exit_code == 0
    assert calls == [("Hello world", "en-US-GuyNeural")]
    assert output_path.exists()
    assert output_path.read_bytes() == b"demo"

    output = capsys.readouterr().out
    assert "Saved audition sample" in output
