"""Deprecated shim for legacy imports."""

from __future__ import annotations

import warnings

warnings.warn(
    "Importing AgentState from 'forge.core.schema.agent' is deprecated. "
    "Import from 'forge.core.schemas.enums' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forge.core.schemas.enums import AgentState

__all__ = ["AgentState"]
