"""Batch synthesis helpers with sensible defaults for throughput."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Iterable, Optional, Sequence

DEFAULT_CONCURRENCY = 2
"""The default level of parallelism for batch synthesis."""

MAX_CONCURRENCY = 6
"""The highest supported concurrency before the client is clamped."""

THROTTLE_WARNING_CONCURRENCY = 5
"""The concurrency where we begin warning about throttling risk."""

FREQUENT_429_THRESHOLD = 3
"""How many 429 responses we consider "frequent" for user messaging."""


class TooManyRequestsError(RuntimeError):
    """Lightweight marker exception for HTTP 429 throttling events."""

    def __init__(self, message: str = "Too many requests", *, status_code: int = 429) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class BatchSynthesizer:
    """Coordinate text-to-speech work across a limited worker pool.

    Parameters
    ----------
    request_fn:
        Coroutine function that performs the synthesis for a single item.
        The callable must accept the job descriptor and the configured
        crossfade duration.
    concurrency:
        Maximum number of simultaneous requests. Values beyond
        :data:`MAX_CONCURRENCY` are automatically clamped and generate a log
        warning to highlight the throttling risk.
    crossfade_seconds:
        Amount of crossfade requested from the service. Lower values reduce
        render quality slightly but can help when disk IO is the bottleneck
        because fewer overlapping samples need to be buffered at once.
    logger:
        Optional logger. When omitted a module level logger is used.
    """

    request_fn: Callable[[object, float], Awaitable[None]]
    concurrency: int = DEFAULT_CONCURRENCY
    crossfade_seconds: float = 0.12
    logger: Optional[logging.Logger] = None
    _429_counter: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.logger = self.logger or logging.getLogger(__name__)
        original_concurrency = self.concurrency
        if self.concurrency < 1:
            raise ValueError("concurrency must be a positive integer")
        if self.concurrency > MAX_CONCURRENCY:
            self.logger.warning(
                "Requested concurrency %s exceeds the supported ceiling of %s. "
                "Clamping to protect against API throttling.",
                self.concurrency,
                MAX_CONCURRENCY,
            )
            self.concurrency = MAX_CONCURRENCY
        elif self.concurrency >= THROTTLE_WARNING_CONCURRENCY:
            self.logger.warning(
                "Running with concurrency=%s may trigger service throttling. "
                "Monitor for HTTP 429 responses and dial it back if needed.",
                self.concurrency,
            )
        if original_concurrency != self.concurrency:
            self.logger.debug("Effective concurrency is %s", self.concurrency)
        self._semaphore = asyncio.Semaphore(self.concurrency)

    async def run(self, jobs: Sequence[object]) -> None:
        """Process a batch of synthesis jobs respecting concurrency limits."""

        async def worker(job: object) -> None:
            async with self._semaphore:
                await self._execute(job)

        await asyncio.gather(*(worker(job) for job in jobs))

    async def iter_run(self, jobs: Iterable[object]) -> None:
        """Process an iterable of jobs lazily, streaming work items."""

        tasks = []
        async for job in _aiter(jobs):  # type: ignore[arg-type]
            tasks.append(asyncio.create_task(self._guarded(job)))
        if tasks:
            await asyncio.gather(*tasks)

    async def _guarded(self, job: object) -> None:
        async with self._semaphore:
            await self._execute(job)

    async def _execute(self, job: object) -> None:
        try:
            await self.request_fn(job, self.crossfade_seconds)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._maybe_note_throttling(exc)
            raise

    def _maybe_note_throttling(self, exc: Exception) -> None:
        status_code = getattr(exc, "status_code", None)
        if status_code == 429 or isinstance(exc, TooManyRequestsError):
            self._429_counter += 1
            if self._429_counter == FREQUENT_429_THRESHOLD:
                self.logger.info(
                    "Seeing repeated 429 responses. If you need to push truly "
                    "massive jobs, consider using Azure Batch to stage the "
                    "workload closer to the service limits."
                )


async def _aiter(iterable: Iterable[object]):
    """Asynchronously yield from a possibly synchronous iterable."""

    if hasattr(iterable, "__aiter__"):
        async for item in iterable:  # type: ignore[union-attr]
            yield item
    else:
        for item in iterable:
            yield item
