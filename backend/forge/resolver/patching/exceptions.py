"""Exception hierarchy for resolver diff parsing and application."""

from __future__ import annotations


class PatchingException(Exception):
    """Base exception for all patch parsing/apply errors."""


class HunkException(PatchingException):
    """Base exception for errors tied to a specific diff hunk."""

    def __init__(self, msg: str, hunk: int | None = None) -> None:
        """Attach optional hunk number to error message."""
        self.hunk = hunk
        if hunk is not None:
            super().__init__(f"{msg}, in hunk #{hunk}")
        else:
            super().__init__(msg)


class ApplyException(PatchingException):
    """Raised when applying a patch to working tree fails."""


class SubprocessException(ApplyException):
    """Raised when an external patch subprocess exits with non-zero status."""

    def __init__(self, msg: str, code: int) -> None:
        """Capture exit code from failing subprocess."""
        super().__init__(msg)
        self.code = code


class HunkApplyException(HunkException, ApplyException, ValueError):
    """Raised when applying an individual hunk fails."""


class ParseException(HunkException, ValueError):
    """Raised when a diff cannot be parsed into the expected structure."""
