"""Utilities for chunking text for synthesis."""

from __future__ import annotations


def chunk_text(text: str, max_length: int = 4000) -> list[str]:
    """Placeholder chunking implementation.

    Args:
        text: Source text to chunk.
        max_length: Maximum characters per chunk.

    Returns:
        A list containing the original text as a single chunk.
    """

    if not text:
        return []
    return [text[:max_length]]
