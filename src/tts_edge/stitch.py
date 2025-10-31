"""Audio stitching helpers."""

from __future__ import annotations


def stitch_segments(segments: list[bytes]) -> bytes:
    """Concatenate audio segments in-memory.

    Args:
        segments: Iterable of audio byte sequences.

    Returns:
        Concatenated bytes.
    """

    return b"".join(segments)
