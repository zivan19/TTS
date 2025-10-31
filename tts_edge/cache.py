"""Utilities for caching voice metadata."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterable, List, Optional

CACHE_TTL = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_cache_dir() -> Path:
    """Return the directory used to store cache files."""

    custom = os.environ.get("TTS_EDGE_CACHE_DIR")
    if custom:
        return Path(custom)
    return Path.home() / ".cache" / "tts-edge"


def get_voices_cache_path() -> Path:
    return get_cache_dir() / "voices.json"


def load_cached_voices(ttl: timedelta = CACHE_TTL) -> Optional[List[dict[str, Any]]]:
    """Load cached voices if they have not expired."""

    path = get_voices_cache_path()
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        timestamp_raw = payload["timestamp"]
        voices = payload["voices"]
    except (OSError, ValueError, KeyError, TypeError):
        return None

    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except ValueError:
        return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)

    if _now() - timestamp > ttl:
        return None

    if not isinstance(voices, list):
        return None

    return voices  # type: ignore[return-value]


def save_cached_voices(voices: Iterable[dict[str, Any]]) -> None:
    """Persist the voices metadata to disk."""

    path = get_voices_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": _now().isoformat(),
        "voices": list(voices),
    }

    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
