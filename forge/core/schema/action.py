"""Deprecated shim for legacy imports."""

from __future__ import annotations

import warnings

warnings.warn(
    "Importing ActionType from 'forge.core.schema.action' is deprecated. "
    "Import from 'forge.core.schemas.enums' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forge.core.schemas.enums import ActionType

__all__ = ["ActionType"]
