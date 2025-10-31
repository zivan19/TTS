from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import srt


def _normalize_whitespace(text: str) -> str:
    normalized_lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        collapsed = " ".join(line.strip().split())
        normalized_lines.append(collapsed)
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    return "\n".join(normalized_lines)


def read_srt(path: Path) -> List[srt.Subtitle]:
    """Read and parse subtitles from ``path`` ensuring UTF-8 encoding."""

    text = path.read_text(encoding="utf-8-sig")
    subtitles = [
        srt.Subtitle(
            index=subtitle.index,
            start=subtitle.start,
            end=subtitle.end,
            content=_normalize_whitespace(subtitle.content),
            proprietary=subtitle.proprietary,
        )
        for subtitle in srt.parse(text)
    ]
    return subtitles


def write_srt(subtitles: Iterable[srt.Subtitle], path: Path) -> None:
    """Write subtitles to ``path`` in UTF-8 encoding."""

    normalised = []
    for index, subtitle in enumerate(subtitles, start=1):
        normalised.append(
            srt.Subtitle(
                index=index,
                start=subtitle.start,
                end=subtitle.end,
                content=_normalize_whitespace(subtitle.content),
                proprietary=subtitle.proprietary,
            )
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(srt.compose(normalised), encoding="utf-8")
