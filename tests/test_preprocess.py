from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import pytest

from tts_preprocess import preprocess_text

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_remove_headers_and_page_numbers() -> None:
    text = read_fixture("sample_book.txt")
    chunks = preprocess_text(text)
    output = "\n\n".join(chunks)

    assert "My Book Title" not in output
    assert "--- Page Footer ---" not in output
    assert "\n1\n" not in output
    assert "\n2\n" not in output


def test_keep_chapters_starts_new_chunks() -> None:
    text = read_fixture("sample_book.txt")
    chunks = preprocess_text(text, keep_chapters=True)
    assert chunks
    assert chunks[0].startswith("Chapter 1")
    assert any(chunk.startswith("Chapter 2") for chunk in chunks)


def test_no_keep_chapters_merges_sections() -> None:
    text = read_fixture("sample_book.txt")
    chunks = preprocess_text(text, keep_chapters=False)
    combined = "\n\n".join(chunks)
    assert "Chapter 1" in combined and "Chapter 2" in combined
    assert any("Chapter 1" in chunk and "Chapter 2" in chunk for chunk in chunks)


def test_quotes_and_code_blocks_preserved() -> None:
    text = read_fixture("sample_book.txt")
    chunks = preprocess_text(text)
    block_quote_chunk = next(chunk for chunk in chunks if "> A block quote" in chunk)
    assert "Second line of the same quote." in block_quote_chunk
    code_chunk = next(chunk for chunk in chunks if "def hello()" in chunk)
    assert 'return "world"' in code_chunk


def test_transcript_header_removal() -> None:
    text = read_fixture("sample_transcript.txt")
    chunks = preprocess_text(text)
    joined = "\n\n".join(chunks)
    assert "Interview Series" not in joined
    assert "--- Transcript Footer ---" not in joined


@pytest.mark.parametrize("flag,keep", [("--keep-chapters", True), ("--no-keep-chapters", False)])
def test_cli(tmp_path: Path, flag: str, keep: bool) -> None:
    text = read_fixture("sample_book.txt")
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    input_path.write_text(text, encoding="utf-8")

    env = dict(**os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    cmd = [sys.executable, "-m", "tts_preprocess.cli", str(input_path), str(output_path), flag]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    assert proc.returncode == 0

    output = output_path.read_text(encoding="utf-8")
    assert "Chapter 1" in output
    if keep:
        assert output.startswith("Chapter 1")
    else:
        assert "Chapter 2" in output

