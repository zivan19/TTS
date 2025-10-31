from __future__ import annotations

from pathlib import Path

import pytest

from tts_edge.chunking import chunk_text, load_text


def test_chunk_text_preserves_paragraphs_and_limits_length():
    text = (
        "Paragraph one sentence one. Paragraph one sentence two? Paragraph one sentence three!\n\n"
        "Paragraph two has numbers like 3.14 and 42.0 that should stay together. "
        "Paragraph two also mentions https://example.com/path. Another sentence follows.\n\n"
        "A short final paragraph."
    )

    chunks = chunk_text(text, max_len=180)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= int(180 * 1.1)
        assert "  " not in chunk

    joined = "\n\n".join(chunks)
    assert "Paragraph one sentence one." in joined
    assert "Paragraph two has numbers like 3.14" in joined
    assert "\n\nParagraph two has numbers like" in chunks[0]
    assert chunks[-1].endswith("A short final paragraph.")


def test_chunk_text_avoids_decimal_and_url_splits():
    text = (
        "The constant is 3.14159 which is important."
        " Visit https://contoso.example/path/index.html for more info."
        " More context follows in subsequent sentences."
    )

    chunks = chunk_text(text, max_len=120)

    assert any("3.14159" in chunk for chunk in chunks)
    for chunk in chunks:
        if "3." in chunk:
            assert "3.14159" in chunk

    if not any("https://contoso.example/path/index.html" in chunk for chunk in chunks):
        pytest.fail("URL was split across chunks")


def test_chunk_text_fallback_splitter(monkeypatch):
    from tts_edge import chunking

    monkeypatch.setattr(chunking, "_SENTENCE_TOKENIZER", chunking._TOKENIZER_UNAVAILABLE)

    paragraph = "Dr. Smith met Mr. Jones at 4.30 p.m. They discussed plans."
    chunks = chunking.chunk_text(paragraph, max_len=80)

    assert any("Dr. Smith met Mr. Jones" in chunk for chunk in chunks)
    assert any("They discussed plans" in chunk for chunk in chunks)


def test_load_text(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    content = "Line one\nLine two with unicode café."
    sample.write_text(content, encoding="utf-8")

    assert load_text(sample) == content
