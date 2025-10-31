"""Command line interface for the tts-edge pipeline."""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from . import pipeline

app = typer.Typer(name="tts-edge", no_args_is_help=True)
console = Console()


def _progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )


@app.command()
def synth(
    text_file: Path = typer.Argument(..., exists=True, readable=True, dir_okay=False, help="Path to the input text file."),
    out: Path = typer.Option(..., "--out", help="Directory where artifacts will be written."),
    voice: str = typer.Option("standard", "--voice", help="Logical voice identifier."),
    rate: float = typer.Option(1.0, "--rate", min=0.1, help="Playback rate multiplier."),
    pitch: float = typer.Option(0.0, "--pitch", help="Pitch adjustment in semitones."),
    volume: float = typer.Option(1.0, "--volume", min=0.0, max=1.0, help="Output volume multiplier."),
    max_len: int = typer.Option(2500, "--max-len", min=1, help="Maximum characters per chunk."),
    concurrency: int = typer.Option(2, "--concurrency", min=1, help="Number of concurrent synthesis workers."),
    crossfade_ms: int = typer.Option(20, "--crossfade-ms", min=0, help="Crossfade duration between chunks."),
    no_srt: bool = typer.Option(False, "--no-srt", help="Disable subtitle generation."),
    resume: bool = typer.Option(False, "--resume/--no-resume", help="Reuse previously synthesized chunks if available."),
    max_attempts: int = typer.Option(5, "--max-attempts", min=1, help="Maximum retry attempts per chunk."),
    backoff_base: float = typer.Option(0.5, "--backoff-base", min=0.0, help="Base delay in seconds for retry backoff."),
    backoff_cap: float = typer.Option(8.0, "--backoff-cap", min=0.0, help="Maximum delay in seconds for retry backoff."),
) -> None:
    """Run the full text-to-speech pipeline for ``TEXT_FILE``."""

    out.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Loading:[/] {text_file}")
    text = pipeline.load_text(text_file)

    with _progress() as progress:
        chunk_task = progress.add_task("Chunking text", total=max(len(text), 1))
        chunks: List[pipeline.TextChunk] = []
        processed_chars = 0
        for chunk in pipeline.chunk_text(text, max_len):
            chunks.append(chunk)
            processed_chars += len(chunk.text)
            progress.update(chunk_task, completed=processed_chars)
        progress.update(chunk_task, completed=max(len(text), processed_chars))

        if not chunks:
            console.print("[yellow]No text chunks were generated. Nothing to synthesize.[/]")
            return

        synth_task = progress.add_task(f"Synthesizing audio (x{concurrency})", total=len(chunks) or 1)

        def synth_progress(step: int) -> None:
            progress.advance(synth_task, step)

        audio_chunks, srt_entries = pipeline.synth_all(
            chunks,
            out,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
            concurrency=concurrency,
            resume=resume,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
            backoff_cap=backoff_cap,
            progress_callback=synth_progress,
        )
        progress.update(synth_task, completed=len(chunks) or 1)

        stitch_task = progress.add_task("Stitching audio", total=len(audio_chunks) or 1)

        def stitch_progress(step: int) -> None:
            progress.advance(stitch_task, step)

        final_audio = pipeline.stitch_audio(
            audio_chunks,
            out,
            crossfade_ms=crossfade_ms,
            progress_callback=stitch_progress,
        )
        progress.update(stitch_task, completed=len(audio_chunks) or 1)

        final_srt: Optional[Path] = None
        if not no_srt:
            merge_task = progress.add_task("Merging subtitles", total=len(srt_entries) or 1)

            def merge_progress(step: int) -> None:
                progress.advance(merge_task, step)

            final_srt = pipeline.merge_srts(
                srt_entries,
                out,
                progress_callback=merge_progress,
            )
            progress.update(merge_task, completed=len(srt_entries) or 1)

    total_duration = sum(chunk.duration for chunk in audio_chunks)
    duration_td = timedelta(seconds=total_duration)
    summary_lines = [
        f"Chunks generated: {len(chunks)}",
        f"Total duration: {duration_td}",
        f"Audio file: {final_audio}",
    ]
    if final_srt:
        summary_lines.append(f"Subtitle file: {final_srt}")

    console.print(Panel("\n".join(summary_lines), title="tts-edge summary", expand=False))


__all__ = ["app", "synth"]


if __name__ == "__main__":
    app()
