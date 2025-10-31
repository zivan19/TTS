"""FFmpeg discovery utilities.

This module is imported on package load so that the CLI and downstream modules
can depend on an eagerly validated FFmpeg installation.  Discovery follows a
few heuristics so that common platform specific locations work out of the box.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, Optional

__all__ = [
    "FFMPEG_EXECUTABLE",
    "FFmpegNotFoundError",
    "get_ffmpeg_executable",
]


class FFmpegNotFoundError(RuntimeError):
    """Raised when an FFmpeg executable cannot be discovered."""


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def _ffmpeg_python_default() -> Optional[str]:
    """Return the path discovered by ffmpeg-python's default lookup."""

    ffmpeg_binary = os.environ.get("FFMPEG_BINARY", "ffmpeg")
    resolved = shutil.which(ffmpeg_binary)
    if resolved:
        return resolved
    return None


def _common_install_paths() -> Iterable[Path]:
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", r"C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")
        local_appdata = os.environ.get("LocalAppData", r"C:\\Users\\Public")
        return [
            Path(program_files) / "ffmpeg" / "bin" / "ffmpeg.exe",
            Path(program_files_x86) / "ffmpeg" / "bin" / "ffmpeg.exe",
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path(local_appdata) / "Microsoft" / "WindowsApps" / "ffmpeg.exe",
            Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
            Path("C:/scoop/apps/ffmpeg/current/ffmpeg.exe"),
        ]
    possible = [
        Path("/usr/local/bin/ffmpeg"),
        Path("/usr/bin/ffmpeg"),
        Path("/snap/bin/ffmpeg"),
        Path("/opt/homebrew/bin/ffmpeg"),
        Path("/opt/local/bin/ffmpeg"),
    ]
    return possible


def _from_env_var() -> Optional[str]:
    candidate = os.environ.get("FFMPEG_BIN")
    if not candidate:
        return None

    path = Path(candidate).expanduser()
    if path.is_dir():
        executable_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        path = path / executable_name

    if _is_executable(path):
        return str(path)
    return None


def _discover_ffmpeg() -> str:
    """Discover the FFmpeg executable using a few heuristics."""

    strategies = (
        _ffmpeg_python_default,
        lambda: next((str(path) for path in _common_install_paths() if _is_executable(path)), None),
        _from_env_var,
    )

    for strategy in strategies:
        resolved = strategy()
        if resolved:
            return resolved

    env_hint = os.environ.get("FFMPEG_BIN")
    message_parts = [
        "Unable to locate an FFmpeg executable.",
        "Install FFmpeg and ensure it is on your PATH,",
        "or set the FFMPEG_BIN environment variable to the full path.",
    ]
    if env_hint:
        message_parts.append(f"FFMPEG_BIN is set to '{env_hint}', but no executable was found there.")
    raise FFmpegNotFoundError(" ".join(message_parts))


def get_ffmpeg_executable() -> str:
    """Return the cached FFmpeg executable path."""

    return FFMPEG_EXECUTABLE


FFMPEG_EXECUTABLE = _discover_ffmpeg()
os.environ.setdefault("FFMPEG_BINARY", FFMPEG_EXECUTABLE)
