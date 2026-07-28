"""Transcript display tiers for TUI tool rendering.

The live TUI renders tool activity in two tiers:

- **Orient** — a flat single-line :class:`OrientLine` row (no body, no
  expansion). Used for lightweight reads / lookups. See
  :data:`ORIENT_TOOL_NAMES`.
- **Action** — a :class:`ScanLineCard` with a state-colored headline and a
  curated inline payload preview. Diffs, commands, task progress, and bounded
  output are readable without leaving the transcript. A ``⤢`` affordance can
  still open a full-screen ``DetailScreen`` for overflow. Used for everything
  heavier than an orient read. See :data:`ACTION_TOOL_NAMES`.

Inline bodies are intentionally bounded so the transcript remains scannable.
Expansion means opening the complete payload on the screen stack (Enter/Space
on a focused card, the ``⤢`` button, or a click).

These name sets are a reference for which tier a tool belongs to. They are not
imported by the render pipeline (which keys off event/observation types in
``renderer/handlers``); keep them in sync as a documentation aid.
"""

from __future__ import annotations

from typing import Final

# Orient: read / lookup / lightweight workspace actions → OrientLine
ORIENT_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        'grep',
        'glob',
        'find_symbols',
        'read_file',
        'read_symbol',
        'lsp',
        'analyze_project_structure',
        'web_search',
        'web_fetch',
        'docs_resolve',
        'docs_query',
        'checkpoint',
    }
)

# Action: everything heavier → ScanLineCard (1-line summary) + DetailScreen
ACTION_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        'shell',
        'terminal',
        'debugger',
        'browser',
        'mcp',
        'workers',
        'condensation',
        'acceptance_criteria',
    }
)
