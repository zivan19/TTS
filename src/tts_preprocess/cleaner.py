"""Utilities for cleaning scanned book and transcript text."""
from __future__ import annotations

import re
from typing import Iterable, List

from rapidfuzz import fuzz

PAGE_NUMBER_RE = re.compile(r"^\s*(?:page\s+)?\d+(?:\s*/\s*\d+)?\s*$", re.IGNORECASE)
HEADER_FOOTER_WINDOW = 3
FUZZ_THRESHOLD = 92


def _cluster_repeated_lines(lines: Iterable[str]) -> List[str]:
    """Return canonical representations of lines that repeat across pages.

    Lines are compared using :func:`rapidfuzz.fuzz.ratio` to allow for
    small OCR variations (e.g. ``Page 12`` vs ``PAGE 13``)."""

    clusters: List[dict[str, object]] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for cluster in clusters:
            canonical = cluster["repr"]  # type: ignore[index]
            if fuzz.ratio(canonical, line) >= FUZZ_THRESHOLD:
                cluster["count"] = int(cluster["count"]) + 1  # type: ignore[index]
                # Prefer the shorter representation to avoid trailing noise
                if len(line) < len(canonical):
                    cluster["repr"] = line
                matched = True
                break
        if not matched:
            clusters.append({"repr": line, "count": 1})
    return [cluster["repr"] for cluster in clusters if int(cluster["count"]) > 1]


def _matches_any(line: str, candidates: Iterable[str]) -> bool:
    return any(fuzz.ratio(line, candidate) >= FUZZ_THRESHOLD for candidate in candidates)


def _strip_page_numbers(line: str) -> bool:
    return bool(PAGE_NUMBER_RE.match(line))


def _clean_page_lines(lines: List[str], headers: List[str], footers: List[str]) -> List[str]:
    cleaned: List[str] = []
    total = len(lines)
    for idx, raw_line in enumerate(lines):
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        if _strip_page_numbers(stripped):
            continue
        if idx < HEADER_FOOTER_WINDOW and _matches_any(stripped, headers):
            continue
        if idx >= total - HEADER_FOOTER_WINDOW and _matches_any(stripped, footers):
            continue
        cleaned.append(line)
    return cleaned


def remove_page_artifacts(text: str) -> str:
    """Remove headers, footers and page numbers from paginated text.

    The implementation assumes pages are separated by form-feed characters.
    If no form-feed is present the entire input is treated as a single page,
    so no content is removed.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    pages = normalized.split("\f")
    page_lines: List[List[str]] = [page.splitlines() for page in pages]

    header_candidates = _cluster_repeated_lines(
        line
        for lines in page_lines
        for line in lines[:HEADER_FOOTER_WINDOW]
    )
    footer_candidates = _cluster_repeated_lines(
        line
        for lines in page_lines
        for line in lines[-HEADER_FOOTER_WINDOW:]
    )

    cleaned_pages: List[str] = []
    for lines in page_lines:
        cleaned_lines = _clean_page_lines(lines, header_candidates, footer_candidates)
        cleaned_page = "\n".join(line for line in cleaned_lines if line.strip())
        if cleaned_page:
            cleaned_pages.append(cleaned_page)
    return "\n\n".join(cleaned_pages)


def clean_text(text: str) -> str:
    """High level cleanup for downstream chunking."""
    return remove_page_artifacts(text)

