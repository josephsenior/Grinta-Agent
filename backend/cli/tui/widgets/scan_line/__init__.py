"""Transcript action cards with inline payload previews and overflow detail.

Each card mirrors OrientLine/ThinkingIndicator chrome (background #090d18,
left pipe, padding). Useful payload is visible in the feed; a ``⤢`` button may
push a :class:`DetailScreen` for full overflow content.

Subclasses override ``_line_text()`` and ``build_detail_screen()``.
"""

from __future__ import annotations

from backend.cli.tui.widgets.scan_line.card import ScanLineCard
from backend.cli.tui.widgets.scan_line.cards import (
    AcceptanceCriteriaCard,
    AgentMessageCard,
    BrowserCard,
    CompactionCard,
    DebuggerCard,
    DelegateCard,
    EditCard,
    MCPCard,
    PayloadCard,
    ShellCard,
    TaskStateCard,
    TerminalCard,
    _compact_path,
    _extract_syntax_error,
    _format_diff_delta,
    _parse_syntax_badge,
    _truncate,
)

__all__ = [
    'ScanLineCard',
    'AcceptanceCriteriaCard',
    'AgentMessageCard',
    'DelegateCard',
    'EditCard',
    'MCPCard',
    'PayloadCard',
    'ShellCard',
    'TaskStateCard',
    'TerminalCard',
    'BrowserCard',
    'CompactionCard',
    'DebuggerCard',
    '_parse_syntax_badge',
    '_extract_syntax_error',
    '_format_diff_delta',
    '_compact_path',
    '_truncate',
]
