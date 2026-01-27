"""Backward-compatible re-export for command output observations.

Historically, tests and utilities imported command observation helpers from
``forge.events.observation.cmd_output``.  The implementation now lives in
``forge.events.observation.commands``.  This shim preserves the legacy import
path by re-exporting the relevant symbols.
"""

from __future__ import annotations

from .commands import (  # noqa: F401
    CMD_OUTPUT_METADATA_PS1_REGEX,
    CMD_OUTPUT_PS1_BEGIN,
    CMD_OUTPUT_PS1_END,
    CmdOutputMetadata,
    CmdOutputObservation,
)

__all__ = [
    "CMD_OUTPUT_METADATA_PS1_REGEX",
    "CMD_OUTPUT_PS1_BEGIN",
    "CMD_OUTPUT_PS1_END",
    "CmdOutputMetadata",
    "CmdOutputObservation",
]
