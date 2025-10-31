"""Synthesis pipeline integrations with edge-tts."""

from __future__ import annotations


def synthesize_text(text: str) -> bytes:
    """Placeholder synthesis routine.

    Returns raw audio bytes.
    """

    if not text:
        raise ValueError("Text must not be empty")
    return text.encode("utf-8")
