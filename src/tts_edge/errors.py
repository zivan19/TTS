"""Error types used by the synthesis pipeline."""
from __future__ import annotations


class SynthesisError(Exception):
    """Base class for synthesis-related exceptions."""


class TransientSynthesisError(SynthesisError):
    """Recoverable error raised when the request can be retried."""


class RateLimitedError(TransientSynthesisError):
    """The upstream service is throttling requests."""


class PermanentSynthesisError(SynthesisError):
    """Unrecoverable error that should not be retried."""


__all__ = [
    "SynthesisError",
    "TransientSynthesisError",
    "RateLimitedError",
    "PermanentSynthesisError",
]
