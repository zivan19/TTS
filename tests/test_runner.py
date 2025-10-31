from __future__ import annotations

from pathlib import Path

import pytest

from tts.checkpoint import load_checkpoint
from tts.runner import SynthRunner


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self._now += seconds


class DeterministicSynth:
    def __init__(self, clock: FakeClock, durations: list[float], *, interrupt_after: int | None = None, start_index: int = 0) -> None:
        self._clock = clock
        self._durations = durations
        self._next = start_index
        self._interrupt_after = interrupt_after

    def __call__(self, chunk: object) -> None:
        if self._interrupt_after is not None and self._next == self._interrupt_after:
            raise KeyboardInterrupt()
        duration = self._durations[self._next]
        self._clock.sleep(duration)
        self._next += 1


@pytest.fixture()
def checkpoint_path(tmp_path: Path) -> Path:
    return tmp_path / "progress.json"


def test_eta_output_updates_each_chunk(checkpoint_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock()
    durations = [1.0, 1.0, 1.0]
    synth = DeterministicSynth(clock, durations)
    chunks = ["a", "b", "c"]
    runner = SynthRunner(chunks, synth, checkpoint_path, time_func=clock.time)

    assert runner.run() is True

    out = capsys.readouterr().out
    assert "[1/3] chunk finished in 1.00s - ETA 0:00:02" in out
    assert "[2/3] chunk finished in 1.00s - ETA 0:00:01" in out
    assert "Synthesis complete." in out


def test_resume_after_interrupt(checkpoint_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clock = FakeClock()
    durations = [1.0, 1.0, 1.0, 1.0]
    chunks = ["w", "x", "y", "z"]

    interrupting_synth = DeterministicSynth(clock, durations, interrupt_after=2)
    runner = SynthRunner(chunks, interrupting_synth, checkpoint_path, time_func=clock.time)

    assert runner.run() is False

    state = load_checkpoint(checkpoint_path)
    assert state is not None
    assert state.next_index == 2
    assert state.durations == pytest.approx([1.0, 1.0])

    resume_synth = DeterministicSynth(clock, durations, start_index=2)
    resume_runner = SynthRunner(chunks, resume_synth, checkpoint_path, resume=True, time_func=clock.time)

    assert resume_runner.run() is True

    out = capsys.readouterr().out
    assert "Resuming from chunk 3/4" in out
    assert "[3/4] chunk finished in 1.00s - ETA 0:00:01" in out
    assert "Synthesis complete." in out
    assert load_checkpoint(checkpoint_path) is None
