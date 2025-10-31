"""Asynchronous synthesis helpers using edge-tts."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from pathlib import Path
from typing import Any

try:
    import edge_tts as _edge_tts  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover - handled in tests
    _edge_tts = None

edge_tts = _edge_tts


def _require_edge_tts():
    if edge_tts is None:
        raise ModuleNotFoundError("edge-tts is required for synthesis. Install the 'edge-tts' package or provide a stub.")
    return edge_tts


DEFAULT_VOICE = "af-ZA-AdriNeural"
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"
DEFAULT_VOLUME = "+0%"

_AUDIO_TEMPLATE = "part_{index:04d}.mp3"
_SUBTITLE_TEMPLATE = "part_{index:04d}.srt"
_BACKOFF_DELAYS = (0.5, 1.0, 2.0, 4.0)
_TRANSIENT_STATUSES = {429, 500}


async def synth_chunk(
    text: str,
    index: int,
    out_dir: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
    srt: bool = True,
) -> tuple[Path, Path | None]:
    """Synthesize a single chunk of text to audio (and optional subtitles).

    Args:
        text: Text to synthesize.
        index: The sequential index of the chunk (1-based).
        out_dir: Base directory for output files.
        voice: The voice identifier supported by ``edge-tts``.
        rate: Speaking rate modifier (e.g. ``"+0%"``).
        pitch: Pitch modifier (e.g. ``"+0Hz"``).
        volume: Volume modifier (e.g. ``"+0%"``).
        srt: Whether to emit an accompanying subtitle file.

    Returns:
        Tuple containing the path to the MP3 file and, if ``srt`` is ``True``,
        the generated subtitle path. When ``srt`` is ``False`` the subtitle path
        will be ``None``.
    """

    parts_dir = out_dir / "parts"
    subs_dir = out_dir / "subs"
    parts_dir.mkdir(parents=True, exist_ok=True)
    if srt:
        subs_dir.mkdir(parents=True, exist_ok=True)

    audio_path = parts_dir / _AUDIO_TEMPLATE.format(index=index)
    subtitle_path = subs_dir / _SUBTITLE_TEMPLATE.format(index=index) if srt else None

    module = _require_edge_tts()

    communicate = module.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )

    submaker = module.SubMaker() if srt else None

    with audio_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            chunk_type = chunk.get("type")
            if chunk_type == "audio":
                audio_file.write(chunk["data"])
            elif srt and chunk_type == "WordBoundary" and submaker is not None:
                submaker.create_subtitle(chunk)

    if srt and subtitle_path is not None and submaker is not None:
        subtitle_path.write_text(submaker.generate_subs(kind="srt"), encoding="utf-8")

    return audio_path, subtitle_path


def _is_transient_error(exc: BaseException) -> bool:
    """Determine if an exception is a transient HTTP failure."""

    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int) and value in _TRANSIENT_STATUSES:
            return True

    messages: Iterable[Any]
    if isinstance(exc.args, tuple):
        messages = exc.args
    else:
        messages = (exc.args,)

    for message in messages:
        if isinstance(message, str):
            for status in _TRANSIENT_STATUSES:
                if str(status) in message:
                    return True

    return False


async def synth_all(
    chunks: list[str],
    out_dir: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
    volume: str = DEFAULT_VOLUME,
    *,
    concurrency: int = 2,
    resume: bool = True,
    srt: bool = True,
) -> list[tuple[Path, Path | None]]:
    """Synthesize a series of chunks concurrently with retry support."""

    out_dir = Path(out_dir)
    parts_dir = out_dir / "parts"
    subs_dir = out_dir / "subs"
    parts_dir.mkdir(parents=True, exist_ok=True)
    if srt:
        subs_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(max(concurrency, 1))

    async def process(index: int, text: str) -> tuple[Path, Path | None]:
        audio_path = parts_dir / _AUDIO_TEMPLATE.format(index=index)
        subtitle_path = subs_dir / _SUBTITLE_TEMPLATE.format(index=index) if srt else None

        if resume and audio_path.exists() and (not srt or (subtitle_path and subtitle_path.exists())):
            return audio_path, subtitle_path

        attempt = 0
        while True:
            try:
                async with semaphore:
                    return await synth_chunk(
                        text=text,
                        index=index,
                        out_dir=out_dir,
                        voice=voice,
                        rate=rate,
                        pitch=pitch,
                        volume=volume,
                        srt=srt,
                    )
            except Exception as exc:  # noqa: BLE001 - we need to inspect the exception
                if attempt < len(_BACKOFF_DELAYS) and _is_transient_error(exc):
                    delay = _BACKOFF_DELAYS[attempt]
                    attempt += 1
                    await asyncio.sleep(delay)
                    continue
                raise

    tasks = [process(idx, chunk) for idx, chunk in enumerate(chunks, start=1)]
    if not tasks:
        return []

    return await asyncio.gather(*tasks)
