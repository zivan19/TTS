"""Subtitle file helpers."""

from __future__ import annotations


def generate_srt(chunks: list[str]) -> str:
    """Create a placeholder SRT subtitle string."""

    return "".join(
        f"{index}\n00:00:00,000 --> 00:00:05,000\n{chunk}\n\n"
        for index, chunk in enumerate(chunks, start=1)
    )
