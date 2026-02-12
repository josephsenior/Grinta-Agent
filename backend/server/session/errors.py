"""Session-layer error types.

These are used at server boundaries (routes/services) so failures can be
classified consistently without leaking low-level storage/runtime exceptions.
"""

from __future__ import annotations


class SessionError(RuntimeError):
    """Base class for session-related errors."""


class SessionInvariantError(SessionError):
    """Raised when a session invariant is violated (ordering, IDs, etc.)."""


class PersistenceError(SessionError):
    """Raised when event persistence is unavailable or corrupted."""


class ReplayError(SessionError):
    """Raised when trajectory replay/export fails."""
