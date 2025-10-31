"""Utilities for working with the Edge TTS pipeline."""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "FFMPEG_EXECUTABLE",
    "FFmpegNotFoundError",
    "get_ffmpeg_executable",
]


def get_ffmpeg_executable() -> str:
    """Return the discovered FFmpeg executable path."""

    module = import_module("tts_edge.ffmpeg")
    return module.get_ffmpeg_executable()


def __getattr__(name: str) -> Any:  # pragma: no cover - thin wrapper
    if name in {"FFMPEG_EXECUTABLE", "FFmpegNotFoundError"}:
        module = import_module("tts_edge.ffmpeg")
        return getattr(module, name)
    raise AttributeError(name)
