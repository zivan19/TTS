"""Command line entry points for the batch synthesizer."""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Iterable, List

from .batch import (
    BatchSynthesizer,
    DEFAULT_CONCURRENCY,
    MAX_CONCURRENCY,
    THROTTLE_WARNING_CONCURRENCY,
    TooManyRequestsError,
)

_LOGGER = logging.getLogger("tts.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch text-to-speech helper")
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Text snippets to synthesize. When omitted, the command runs a dry configuration check.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=(
            "How many requests to issue in parallel. The default of %d keeps throughput steady "
            "while respecting shared service limits. Values between %d and %d may hit rate limits." 
            % (DEFAULT_CONCURRENCY, THROTTLE_WARNING_CONCURRENCY, MAX_CONCURRENCY)
        ),
    )
    parser.add_argument(
        "--crossfade",
        type=float,
        default=0.12,
        help=(
            "Seconds of crossfade to request from the service. Lower this when disk IO becomes a bottleneck."
        ),
    )
    return parser


def _select_concurrency(requested: int) -> int:
    if requested < 1:
        raise argparse.ArgumentTypeError("--concurrency must be a positive integer")
    if requested > MAX_CONCURRENCY:
        _LOGGER.warning(
            "Concurrency %s is beyond the supported ceiling of %s; limiting to prevent throttling.",
            requested,
            MAX_CONCURRENCY,
        )
        return MAX_CONCURRENCY
    if requested >= THROTTLE_WARNING_CONCURRENCY:
        _LOGGER.warning(
            "Concurrency %s pushes close to the service rate limits. Watch for HTTP 429 throttling.",
            requested,
        )
    return requested


def _setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main(argv: Iterable[str] | None = None) -> int:
    _setup_logging()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    concurrency = _select_concurrency(args.concurrency)

    async def fake_request(job: str, crossfade: float) -> None:
        del crossfade
        await asyncio.sleep(0.01)
        if job == "429":
            raise TooManyRequestsError()

    synthesizer = BatchSynthesizer(
        fake_request,
        concurrency=concurrency,
        crossfade_seconds=args.crossfade,
        logger=_LOGGER,
    )

    if not args.inputs:
        _LOGGER.info(
            "Configured batch synthesizer with concurrency=%s and crossfade=%s", concurrency, args.crossfade
        )
        return 0

    async def runner(items: List[str]) -> None:
        try:
            await synthesizer.run(items)
        except TooManyRequestsError:
            # Already handled in BatchSynthesizer; ensure exit code remains non-zero.
            raise

    try:
        asyncio.run(runner(args.inputs))
    except TooManyRequestsError:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
