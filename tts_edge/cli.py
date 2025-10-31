"""Command line interface for the Edge TTS utilities."""
from __future__ import annotations

import argparse
import importlib
import sys
import textwrap
from pathlib import Path
from typing import List, Optional


def _check_python_version(min_version: tuple[int, int] = (3, 8)) -> tuple[bool, str]:
    current = sys.version_info
    meets_requirement = current >= (*min_version, 0)
    version_text = f"{current.major}.{current.minor}.{current.micro}"
    message = f"Python {version_text} (>= {min_version[0]}.{min_version[1]})"
    return meets_requirement, message


def _check_ffmpeg() -> tuple[bool, str]:
    try:
        ffmpeg_module = importlib.import_module("tts_edge.ffmpeg")
        executable = ffmpeg_module.get_ffmpeg_executable()
        message = f"FFmpeg available at: {executable}"
        return True, message
    except Exception as exc:  # pragma: no cover - exercised in runtime environments
        message = str(exc) or "FFmpeg could not be located."
        return False, message


def _check_write_permissions(target_dir: Optional[Path] = None) -> tuple[bool, str]:
    directory = target_dir or Path.cwd()
    test_file = directory / ".tts_edge_write_test"

    try:
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        test_file.unlink()
        return True, f"Write permission confirmed for: {directory}"
    except OSError as exc:
        return False, f"Cannot write to {directory}: {exc}"


def _format_result(ok: bool, message: str) -> str:
    icon = "✓" if ok else "✗"
    return f"{icon} {message}"


def doctor_command(_: argparse.Namespace) -> int:
    checks = [
        ("Python", *_check_python_version()),
        ("FFmpeg", *_check_ffmpeg()),
        ("File system", *_check_write_permissions()),
    ]

    print("Environment diagnostics:\n")
    exit_code = 0
    for label, ok, message in checks:
        if not ok:
            exit_code = 1
        print(_format_result(ok, f"{label}: {message}"))

    if exit_code:
        print(
            "\nOne or more checks failed. Install missing dependencies or adjust "
            "permissions, then re-run `tts-edge doctor`."
        )
    else:
        print("\nAll checks passed. You're ready to use tts-edge!")

    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tts-edge",
        description="Utilities for working with the Edge TTS pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            Additional help:
              • Ensure FFmpeg is installed and discoverable. See the README for platform-specific instructions.
              • Override the detected FFmpeg binary by setting the FFMPEG_BIN environment variable.
            """
        ),
    )

    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser(
        "doctor", help="Run diagnostic checks for the local environment."
    )
    doctor_parser.set_defaults(func=doctor_command)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
