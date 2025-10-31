"""High level preprocessing pipeline."""
from __future__ import annotations

from typing import List

from .cleaner import clean_text
from .chunker import chunk_paragraphs, iter_paragraphs


def preprocess_text(text: str, *, keep_chapters: bool = True) -> List[str]:
    """Clean and chunk raw text from books and transcripts.

    Parameters
    ----------
    text:
        Raw text input.
    keep_chapters:
        When ``True`` (default) each detected chapter heading starts a new
        chunk. When ``False`` the text is chunked purely by size.
    """

    cleaned = clean_text(text)
    paragraphs = iter_paragraphs(cleaned)
    chunks = chunk_paragraphs(paragraphs, keep_chapters=keep_chapters)
    return chunks

