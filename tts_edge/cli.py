"""Command line interface for tts-edge."""
from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import edge_tts

from . import __version__
from . import cache


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tts-edge", description="Utilities for Microsoft Edge TTS")
    parser.add_argument("--version", action="version", version=f"tts-edge {__version__}")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    voices_parser = subparsers.add_parser("voices", help="List available voices")
    voices_parser.add_argument("--refresh", action="store_true", help="Refresh the cached voice list")
    voices_parser.set_defaults(handler=handle_voices)

    audition_parser = subparsers.add_parser("audition", help="Create a short audition clip")
    audition_parser.add_argument("--voice", required=True, help="Short name of the voice to use")
    audition_parser.add_argument("--text", required=True, help="Text to read")
    audition_parser.add_argument("--out", required=True, help="Output audio file path")
    audition_parser.set_defaults(handler=handle_audition)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    try:
        result = handler(args)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
    except KeyboardInterrupt:
        return 1
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return int(result) if isinstance(result, int) else 0


def entry_point() -> None:
    sys.exit(main())


def _pick_voice_name(voice: dict[str, str]) -> str:
    for key in ("ShortName", "Shortname", "Name", "name"):
        if key in voice and isinstance(voice[key], str):
            return voice[key]
    return ""


def _format_voice_table(voices: Iterable[dict[str, str]]) -> str:
    rows: List[List[str]] = []
    for voice in voices:
        name = _pick_voice_name(voice)
        locale = voice.get("Locale") or voice.get("locale") or ""
        gender = voice.get("Gender") or voice.get("gender") or ""
        rows.append([name, locale, gender])

    headers = ["Name", "Locale", "Gender"]
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    header_line = "  ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers))
    separator_line = "  ".join("-" * widths[idx] for idx in range(len(headers)))

    if not rows:
        return "\n".join([header_line, separator_line])

    body_lines = [
        "  ".join(value.ljust(widths[idx]) for idx, value in enumerate(row))
        for row in rows
    ]

    return "\n".join([header_line, separator_line, *body_lines])


async def handle_voices(args: argparse.Namespace) -> int:
    voices: List[dict[str, str]] | None = None
    if not args.refresh:
        voices = cache.load_cached_voices()

    if voices is None:
        voices = await _fetch_voices()
        cache.save_cached_voices(voices)

    if not voices:
        print("No voices available.")
        return 0

    voices = sorted(voices, key=_pick_voice_name)
    print(_format_voice_table(voices))
    return 0


async def _fetch_voices() -> List[dict[str, str]]:
    return await edge_tts.list_voices()


async def handle_audition(args: argparse.Namespace) -> int:
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    communicator = edge_tts.Communicate(args.text, voice=args.voice)
    await communicator.save(str(out_path))

    print(f"Saved audition sample to {out_path}")
    return 0
