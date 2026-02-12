"""Canonical error types for boundary normalization.

These are intentionally small and generic. Layers (server/runtime/storage) can
wrap arbitrary exceptions into one of these for consistent handling.
"""

from __future__ import annotations


class ForgeError(RuntimeError):
    """Base class for normalized Forge errors."""


class RetryableError(ForgeError):
    """Operation may succeed if retried."""


class UserActionRequiredError(ForgeError):
    """User must change config/inputs before retrying."""


class InvariantBrokenError(ForgeError):
    """A system invariant was violated; continuing may be unsafe."""


def classify_error(exc: Exception) -> type[ForgeError]:
    """Best-effort classification helper."""
    if isinstance(exc, (ValueError,)):  # narrow by default
        return UserActionRequiredError
    return ForgeError
