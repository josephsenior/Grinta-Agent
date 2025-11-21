"""Deprecated shim for legacy imports.

The canonical enums now live in ``forge.core.schemas.enums``. Import from
``forge.core.schemas`` instead. This module will be removed in a future release.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Importing from 'forge.core.schema' is deprecated. "
    "Use 'forge.core.schemas' (or 'forge.core.schemas.enums') instead.",
    DeprecationWarning,
    stacklevel=2,
)

from forge.core.schemas import ActionType, AgentState, ObservationType

__all__ = ["ActionType", "AgentState", "ObservationType"]
