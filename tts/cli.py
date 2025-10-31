"""Command line interface for the sample TTS runner."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .runner import SynthRunner


def _default_chunks(text: str, chunk_size: int) -> list[str]:
    if chunk_size <= 0:
        return [text]
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [text]


def _default_synthesizer(_: object) -> None:
    # Simulate a small amount of work per chunk.
    time.sleep(0.1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a resumable synthesis job")
    parser.add_argument("text", nargs="*", help="Text to synthesise")
    parser.add_argument("--chunk-size", type=int, default=40, help="Characters per chunk")
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoint.json"))
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    text = " ".join(args.text) or "Hello, world!"
    chunks = _default_chunks(text, args.chunk_size)

    runner = SynthRunner(chunks, _default_synthesizer, args.checkpoint, resume=args.resume)
    completed = runner.run()
    return 0 if completed else 130


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
