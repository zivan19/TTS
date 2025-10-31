"""Utilities for splitting text into manageable chunks."""

from __future__ import annotations

from functools import lru_cache
import os
import re
from typing import Callable, Iterable, List

SentenceSplitter = Callable[[str], List[str]]


_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_EXTRA_SPACE_RE = re.compile(r"[^\S\n]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")

_SENTENCE_SPLIT_FALLBACK_RE = re.compile(
    r"(?<!\b[A-Z]\.)"  # Initials such as "T."
    r"(?<!\b[A-Z][a-z]\.)"  # Abbreviations like "Dr."
    r"(?<!\b[A-Z][a-z][a-z]\.)"  # Slightly longer abbreviations
    r"(?<!\b[A-Z][a-z][a-z][a-z]\.)"
    r"(?<!\bvs\.)"  # specific lower-case abbreviations
    r"(?<!\betc\.)"
    r"(?<!\bInc\.)"
    r"(?<!\bLtd\.)"
    r"(?<=[.!?])\s+(?=[A-Z0-9\"'\(])"
)


def load_text(path: os.PathLike[str] | str) -> str:
    """Read UTF-8 encoded text from *path*.

    Parameters
    ----------
    path:
        File system path to read from.

    Returns
    -------
    str
        File contents as a string.
    """

    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


@lru_cache(maxsize=1)
def _get_sentence_splitter() -> SentenceSplitter:
    """Return a sentence splitter function using available backends."""

    try:  # Prefer NLTK punkt when available.
        import nltk
        from nltk.tokenize import sent_tokenize

        try:
            # Trigger a quick check to confirm the tokenizer resources exist.
            sent_tokenize("Test.")
            return lambda text: [s for s in sent_tokenize(text) if s.strip()]
        except LookupError:
            pass
    except Exception:
        pass

    try:  # Fallback to spaCy if available.
        import spacy

        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            nlp = spacy.blank("en")
            if "sentencizer" not in nlp.pipe_names:
                nlp.add_pipe("sentencizer")

        def spacy_split(text: str) -> List[str]:
            return [sent.text for sent in nlp(text).sents if sent.text.strip()]

        # Ensure the pipeline works before returning it.
        spacy_split("Test.")
        return spacy_split
    except Exception:
        pass

    def regex_split(text: str) -> List[str]:
        sentences = _SENTENCE_SPLIT_FALLBACK_RE.split(text)
        return [sentence for sentence in sentences if sentence.strip()]

    return regex_split


def _normalize_text(text: str) -> str:
    text = _CONTROL_CHARS_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _EXTRA_SPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def _normalize_sentence(sentence: str) -> str:
    sentence = sentence.replace("\n", " ")
    sentence = _EXTRA_SPACE_RE.sub(" ", sentence)
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip()


def _iter_sentences_by_paragraph(text: str) -> Iterable[tuple[str, bool]]:
    splitter = _get_sentence_splitter()
    for paragraph in filter(None, _PARAGRAPH_SPLIT_RE.split(text)):
        sentences = splitter(paragraph)
        normalized = [_normalize_sentence(sentence) for sentence in sentences]
        normalized = [sentence for sentence in normalized if sentence]
        for index, sentence in enumerate(normalized):
            yield sentence, index == 0


def chunk_text(text: str, max_len: int = 2500) -> list[str]:
    """Split *text* into sentence-aware chunks.

    Parameters
    ----------
    text:
        The text to chunk.
    max_len:
        Target maximum length per chunk. The implementation allows a ±10% tolerance
        so that sentences remain intact.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if max_len <= 0:
        raise ValueError("max_len must be a positive integer")

    text = _normalize_text(text)
    if not text:
        return []

    tolerance = max(1, int(max_len * 0.1))
    min_len = max_len - tolerance
    max_with_tol = max_len + tolerance

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_parts, current_len
        if current_parts:
            chunk = "".join(current_parts).strip()
            if chunk:
                chunks.append(chunk)
            current_parts = []
            current_len = 0

    for sentence, paragraph_start in _iter_sentences_by_paragraph(text):
        prefix = ""
        if current_parts:
            prefix = "\n\n" if paragraph_start else " "
        addition = prefix + sentence if current_parts else sentence
        addition_len = len(addition)
        potential_len = current_len + addition_len

        if current_parts and potential_len > max_with_tol:
            flush()
            addition = sentence
            addition_len = len(addition)
            potential_len = addition_len
        elif current_parts and potential_len > max_len and current_len >= min_len:
            flush()
            addition = sentence
            addition_len = len(addition)
            potential_len = addition_len

        if not current_parts and addition_len > max_with_tol:
            current_parts.append(sentence)
            current_len = len(sentence)
            flush()
            continue

        if current_parts:
            current_parts.append(prefix + sentence)
            current_len += len(prefix + sentence)
        else:
            current_parts.append(sentence)
            current_len += len(sentence)

    flush()
    return chunks
