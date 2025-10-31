"""Command line interface for preprocessing text."""
from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import preprocess_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preprocess books and transcripts")
    parser.add_argument("input", type=Path, help="Path to the input text file")
    parser.add_argument("output", type=Path, help="Path to write the cleaned output")

    keep_group = parser.add_mutually_exclusive_group()
    keep_group.add_argument(
        "--keep-chapters",
        dest="keep_chapters",
        action="store_true",
        default=True,
        help="Start new chunks at detected chapter headings (default)",
    )
    keep_group.add_argument(
        "--no-keep-chapters",
        dest="keep_chapters",
        action="store_false",
        help="Disable chapter-aware chunking",
    )
    return parser


def run_cli(args: argparse.Namespace | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(args=args)

    text = namespace.input.read_text(encoding="utf-8")
    chunks = preprocess_text(text, keep_chapters=namespace.keep_chapters)
    output_text = "\n\n".join(chunks)
    namespace.output.write_text(output_text, encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_cli())

