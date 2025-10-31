"""Utilities for working with Edge TTS."""

from .synth import (
    DEFAULT_PITCH,
    DEFAULT_RATE,
    DEFAULT_VOICE,
    DEFAULT_VOLUME,
    synth_all,
    synth_chunk,
)

__all__ = [
    "DEFAULT_VOICE",
    "DEFAULT_RATE",
    "DEFAULT_PITCH",
    "DEFAULT_VOLUME",
    "synth_chunk",
    "synth_all",
]
