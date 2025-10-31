import os
from pathlib import Path

import pytest

from tts_edge.chunking import chunk_text, load_text


@pytest.fixture()
def sample_text() -> str:
    return (
        "First sentence in the opening paragraph. Another sentence follows.\n\n"
        "The second paragraph starts here. It continues the discussion with more text."
    )


def test_chunk_text_preserves_paragraphs(sample_text: str) -> None:
    chunks = chunk_text(sample_text, max_len=80)
    assert len(chunks) == 2
    assert "First sentence" in chunks[0]
    assert chunks[0].endswith("Another sentence follows.")
    assert chunks[1].startswith("The second paragraph")


def test_chunk_text_handles_long_sentence() -> None:
    long_sentence = "This sentence is exceedingly long " * 20 + "and should remain intact."
    chunks = chunk_text(long_sentence, max_len=120)
    assert len(chunks) == 1
    assert len(chunks[0]) >= len(long_sentence.strip())
    assert chunks[0].startswith("This sentence")


def test_chunk_text_balances_within_tolerance(sample_text: str) -> None:
    extended = " ".join([f"Sentence number {i}." for i in range(1, 21)])
    text = sample_text + "\n\n" + extended
    max_len = 120
    chunks = chunk_text(text, max_len=max_len)
    assert chunks, "Expected at least one chunk"
    tolerance = int(max_len * 0.1)
    assert any(len(chunk) >= max_len - tolerance for chunk in chunks)
    for chunk in chunks:
        assert len(chunk) <= max_len + tolerance


def test_chunk_text_preserves_urls_and_numbers() -> None:
    text = (
        "The value is 3.14159 and should remain together. "
        "Visit https://example.com/path/to/page?query=1 for more info. "
        "Another sentence appears afterwards."
    )
    chunks = chunk_text(text, max_len=80)
    assert any("3.14159" in chunk for chunk in chunks)
    assert any("https://example.com/path/to/page?query=1" in chunk for chunk in chunks)
    rebuilt = " ".join(chunks)
    assert "The value is 3.14159" in rebuilt
    assert "https://example.com/path/to/page?query=1" in rebuilt


def test_chunk_text_empty_input() -> None:
    assert chunk_text("   \n\n", max_len=50) == []


def test_chunk_text_invalid_max_len(sample_text: str) -> None:
    with pytest.raises(ValueError):
        chunk_text(sample_text, max_len=0)


def test_load_text(tmp_path: Path) -> None:
    path = tmp_path / "example.txt"
    path.write_text("content", encoding="utf-8")
    assert load_text(path) == "content"
