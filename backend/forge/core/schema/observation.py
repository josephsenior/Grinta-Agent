"""Deprecated shim for legacy imports."""

from __future__ import annotations

import warnings

warnings.warn(
    "Importing ObservationType from 'forge.core.schema.observation' is deprecated. "
    "Import from 'forge.core.schemas.enums' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forge.core.schemas.enums import ObservationType

__all__ = ["ObservationType"]
