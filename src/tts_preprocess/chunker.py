"""Paragraph and chunk utilities."""
from __future__ import annotations

import re
from typing import Iterable, List

CHAPTER_PATTERN = re.compile(
    r"^\s*(?:chapter|book|section)\s+(?:[0-9]+|[ivxlcdm]+|[a-z]+)\b.*",
    re.IGNORECASE,
)
MAX_CHARS_PER_CHUNK = 1200


def _flush(buffer: List[str], chunks: List[str]) -> None:
    if buffer:
        chunk = "\n\n".join(buffer).strip()
        if chunk:
            chunks.append(chunk)
        buffer.clear()


def is_chapter_heading(text: str) -> bool:
    return bool(CHAPTER_PATTERN.match(text.strip()))


def iter_paragraphs(text: str) -> Iterable[str]:
    """Split text into logical paragraphs while preserving special blocks."""
    lines = text.splitlines()
    buffer: List[str] = []
    in_code_fence = False
    in_quote_block = False

    def append_buffer_line(line: str) -> None:
        buffer.append(line.rstrip())

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        # Handle fenced code blocks (```)
        if stripped.startswith("```"):
            if not in_code_fence:
                if buffer:
                    yield "\n".join(buffer).strip()
                    buffer.clear()
                in_code_fence = True
                buffer.append(line)
                continue
            else:
                buffer.append(line)
                yield "\n".join(buffer).strip()
                buffer.clear()
                in_code_fence = False
                continue

        if in_code_fence:
            buffer.append(line)
            continue

        # Handle Markdown style block quotes (> ...)
        if stripped.startswith(">"):
            if not in_quote_block:
                if buffer:
                    yield "\n".join(buffer).strip()
                    buffer.clear()
                in_quote_block = True
            buffer.append(line)
            continue
        else:
            if in_quote_block:
                yield "\n".join(buffer).strip()
                buffer.clear()
                in_quote_block = False

        if not stripped:
            if buffer:
                yield "\n".join(buffer).strip()
                buffer.clear()
            continue

        append_buffer_line(line)

    if buffer:
        yield "\n".join(buffer).strip()


def chunk_paragraphs(paragraphs: Iterable[str], keep_chapters: bool = True) -> List[str]:
    chunks: List[str] = []
    buffer: List[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        chapter_heading = is_chapter_heading(paragraph)
        if keep_chapters and chapter_heading:
            _flush(buffer, chunks)
            buffer.append(paragraph.strip())
            current_len = len(buffer[-1])
            continue

        paragraph_len = len(paragraph)
        if buffer and current_len + 2 + paragraph_len > MAX_CHARS_PER_CHUNK:
            _flush(buffer, chunks)
            buffer.append(paragraph.strip())
            current_len = len(buffer[-1])
            continue

        if not buffer:
            buffer.append(paragraph.strip())
            current_len = len(buffer[-1])
        else:
            buffer.append(paragraph.strip())
            current_len += 2 + paragraph_len

    _flush(buffer, chunks)
    return chunks

