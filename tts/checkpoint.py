"""Checkpoint helpers for resumable synthesis runs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class CheckpointState:
    """Represents saved progress for a synthesis run."""

    next_index: int
    durations: List[float]
    total_chunks: int


def load_checkpoint(path: os.PathLike[str] | str) -> Optional[CheckpointState]:
    """Load checkpoint data if it exists.

    Args:
        path: File path where the checkpoint is stored.

    Returns:
        A :class:`CheckpointState` instance if the checkpoint exists and is
        valid, otherwise ``None``.
    """

    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        return None

    try:
        with checkpoint_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):  # pragma: no cover - defensive
        return None

    try:
        next_index = int(payload["next_index"])
        durations = [float(value) for value in payload["durations"]]
        total_chunks = int(payload["total_chunks"])
    except (KeyError, TypeError, ValueError):  # pragma: no cover - defensive
        return None

    return CheckpointState(next_index=next_index, durations=durations, total_chunks=total_chunks)


def save_checkpoint(
    path: os.PathLike[str] | str,
    next_index: int,
    durations: Iterable[float],
    total_chunks: int,
) -> None:
    """Persist checkpoint information atomically.

    Args:
        path: Destination file path for the checkpoint.
        next_index: Index of the next chunk to be processed.
        durations: Iterable containing previously recorded chunk durations.
        total_chunks: Total number of chunks for the synthesis run.
    """

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "next_index": int(next_index),
        "durations": [float(value) for value in durations],
        "total_chunks": int(total_chunks),
    }

    tmp_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())

    tmp_path.replace(checkpoint_path)
