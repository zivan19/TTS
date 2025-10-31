"""Synthesis runner with ETA reporting and resumable checkpoints."""

from __future__ import annotations

import signal
import time
from datetime import timedelta
from pathlib import Path
from typing import Callable, List, Sequence

from .checkpoint import CheckpointState, load_checkpoint, save_checkpoint


def _format_duration(seconds: float) -> str:
    """Return a human friendly representation for the ETA."""

    bounded = max(0, int(round(seconds)))
    return str(timedelta(seconds=bounded))


class SynthRunner:
    """Run chunked synthesis jobs with ETA reporting and resume support."""

    def __init__(
        self,
        chunks: Sequence[object],
        synthesizer: Callable[[object], None],
        checkpoint_path: str | Path,
        *,
        resume: bool = False,
        time_func: Callable[[], float] | None = None,
    ) -> None:
        self._chunks: List[object] = list(chunks)
        self._synthesizer = synthesizer
        self._checkpoint_path = Path(checkpoint_path)
        self._resume = resume
        self._time = time_func or time.perf_counter
        self._original_sigint_handler = signal.getsignal(signal.SIGINT)

    def run(self) -> bool:
        """Execute the synthesis job.

        Returns ``True`` when the run completes successfully. Returns ``False``
        when a ``SIGINT``/``KeyboardInterrupt`` was received and a checkpoint was
        written instead.
        """

        if not self._chunks:
            print("No chunks to process.")
            self._clear_checkpoint()
            return True

        checkpoint: CheckpointState | None = load_checkpoint(self._checkpoint_path) if self._resume else None
        start_index = min(checkpoint.next_index, len(self._chunks)) if checkpoint else 0
        durations: List[float] = list(checkpoint.durations) if checkpoint else []
        total_chunks = len(self._chunks)

        if checkpoint and checkpoint.total_chunks != total_chunks:
            print(
                "Checkpoint total chunk count does not match current job; "
                "starting from scratch."
            )
            start_index = 0
            durations = []

        processed = start_index
        total_elapsed = sum(durations)

        if processed:
            print(
                f"Resuming from chunk {processed + 1}/{total_chunks} "
                f"({processed} already complete)."
            )

        current_index = start_index
        last_chunk_start = None
        self._install_sigint_handler()
        try:
            while current_index < total_chunks:
                chunk = self._chunks[current_index]
                last_chunk_start = self._time()
                try:
                    self._synthesizer(chunk)
                except KeyboardInterrupt:
                    # Ensure we restore the original handler before re-raising.
                    raise
                chunk_end = self._time()
                elapsed = chunk_end - last_chunk_start
                durations.append(elapsed)
                processed += 1
                current_index += 1
                total_elapsed += elapsed

                average = total_elapsed / processed if processed else 0.0
                remaining = total_chunks - processed
                eta = average * remaining
                print(
                    f"[{processed}/{total_chunks}] chunk finished in {elapsed:.2f}s - "
                    f"ETA {_format_duration(eta)}"
                )
        except KeyboardInterrupt:
            partial_elapsed = 0.0
            if last_chunk_start is not None:
                partial_elapsed = max(0.0, self._time() - last_chunk_start)
            save_checkpoint(
                self._checkpoint_path,
                next_index=current_index,
                durations=durations,
                total_chunks=total_chunks,
            )
            print(
                "Interrupted. Progress saved to "
                f"{self._checkpoint_path} (partial chunk {partial_elapsed:.2f}s)."
            )
            return False
        finally:
            self._restore_sigint_handler()

        self._clear_checkpoint()
        print("Synthesis complete.")
        return True

    # ------------------------------------------------------------------
    # Signal handling helpers
    def _install_sigint_handler(self) -> None:
        def handler(signum, frame):  # pragma: no cover - thin wrapper
            raise KeyboardInterrupt()

        signal.signal(signal.SIGINT, handler)

    def _restore_sigint_handler(self) -> None:
        signal.signal(signal.SIGINT, self._original_sigint_handler)

    # ------------------------------------------------------------------
    def _clear_checkpoint(self) -> None:
        try:
            self._checkpoint_path.unlink()
        except FileNotFoundError:
            pass
