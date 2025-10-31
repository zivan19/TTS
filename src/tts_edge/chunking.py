"""Utilities for splitting long bodies of text into synthesis-friendly chunks."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional


_TOKENIZER_UNAVAILABLE = object()
_SENTENCE_TOKENIZER: Any = None


def load_text(path: str | Path) -> str:
    """Read a UTF-8 encoded text file and return its contents."""

    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return handle.read()


def chunk_text(text: str, max_len: int = 2500) -> list[str]:
    """Split ``text`` into paragraph-aware chunks close to ``max_len`` characters.

    The function keeps sentence boundaries intact, avoids splitting inside numbers
    or URLs where possible, and tolerates chunks roughly +/-10% of ``max_len``.
    """

    if max_len <= 0:
        raise ValueError("max_len must be a positive integer")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    tolerance = int(max_len * 1.1)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if current:
            chunk = "".join(current).strip()
            if chunk:
                chunks.append(chunk)
        current = []
        current_len = 0

    paragraphs = _split_paragraphs(normalized)

    for paragraph in paragraphs:
        sentences = _split_sentences(paragraph)
        if not sentences:
            continue

        first_in_paragraph = True
        for sentence in sentences:
            separator = "\n\n" if (current and first_in_paragraph) else (" " if current else "")
            addition = f"{separator}{sentence.strip()}"
            if not current and separator:
                addition = addition.lstrip()

            if current and current_len + len(addition) > tolerance:
                flush()
                addition = sentence.strip()

            if len(addition) > tolerance and not current:
                # Sentence exceeds tolerance by itself. Accept as-is rather than
                # attempting to split inside the sentence.
                current.append(addition)
                current_len += len(addition)
                flush()
                first_in_paragraph = False
                continue

            current.append(addition)
            current_len += len(addition)
            first_in_paragraph = False

    flush()
    return chunks


def _normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _split_paragraphs(text: str) -> list[str]:
    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]


def _split_sentences(paragraph: str) -> list[str]:
    tokenizer = _get_sentence_tokenizer()
    if tokenizer is not None:
        try:
            sentences = tokenizer.tokenize(paragraph)  # type: ignore[attr-defined]
            normalized = [s.strip() for s in sentences if s.strip()]
            if normalized:
                return normalized
        except Exception:
            pass
    return _fallback_sentence_split(paragraph)


def _get_sentence_tokenizer() -> Optional[object]:
    global _SENTENCE_TOKENIZER
    if _SENTENCE_TOKENIZER is _TOKENIZER_UNAVAILABLE:
        return None
    if _SENTENCE_TOKENIZER is not None:
        return _SENTENCE_TOKENIZER

    try:
        import nltk

        try:
            tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
        except LookupError:
            nltk.download("punkt", quiet=True)
            tokenizer = nltk.data.load("tokenizers/punkt/english.pickle")
        _SENTENCE_TOKENIZER = tokenizer
    except Exception:
        _SENTENCE_TOKENIZER = _TOKENIZER_UNAVAILABLE
    return None if _SENTENCE_TOKENIZER is _TOKENIZER_UNAVAILABLE else _SENTENCE_TOKENIZER


def _fallback_sentence_split(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    length = len(paragraph)

    while start < length and paragraph[start].isspace():
        start += 1

    i = start
    while i < length:
        char = paragraph[i]
        if char in ".!?":
            end = i + 1
            while end < length and paragraph[end] in "\"')]}":
                end += 1
            j = end
            while j < length and paragraph[j].isspace():
                j += 1

            boundary = j >= length
            if not boundary and paragraph[j] in "\"'()":
                boundary = True
            if not boundary and paragraph[j].isalnum():
                boundary = True
            if boundary and _is_valid_boundary(paragraph, i, j):
                sentence = paragraph[start:j].strip()
                if sentence:
                    sentences.append(sentence)
                start = j
                i = j
                continue
        i += 1

    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


_ABBREVIATION_RE = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|Fig|Eq|No|Inc|Ltd|Dept|Rev|St|Mt|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.$",
    re.IGNORECASE,
)


def _is_valid_boundary(text: str, punct_index: int, next_index: int) -> bool:
    prev_char = text[punct_index - 1] if punct_index > 0 else ""
    next_char = text[punct_index + 1] if punct_index + 1 < len(text) else ""

    if text[punct_index] == "." and prev_char.isdigit() and (next_char.isdigit() or next_char == "."):
        return False

    window_start = max(0, punct_index - 32)
    window = text[window_start: punct_index + 1]
    if "://" in window:
        return False

    trimmed_prev = text[: punct_index + 1].strip()
    lower_prev = trimmed_prev.lower()
    if lower_prev.endswith("a.m.") or lower_prev.endswith("p.m."):
        return False
    if _ABBREVIATION_RE.search(trimmed_prev):
        return False
    if re.search(r"\b[A-Z]\.$", trimmed_prev):
        return False

    if next_index < len(text):
        following = text[next_index]
        if (
            following
            and not following.isupper()
            and not following.isdigit()
            and following not in "\"'()[]{}\n"
        ):
            return False

    return True


__all__ = ["chunk_text", "load_text"]

