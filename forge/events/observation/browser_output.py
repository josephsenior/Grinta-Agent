"""Backward-compatible re-export for browser output observations.

Older code referenced ``forge.events.observation.browser_output`` whereas the
implementation now lives in ``forge.events.observation.browse``.  This shim
preserves the legacy import path.
"""

from __future__ import annotations

from .browse import BrowserOutputObservation  # noqa: F401

__all__ = ["BrowserOutputObservation"]


