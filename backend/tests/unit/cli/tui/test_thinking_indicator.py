"""Unit tests for ThinkingIndicator lightweight highlighting."""

from __future__ import annotations

import pytest
from rich.console import Console, Group
from rich.syntax import Syntax
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Static

from backend.cli.tui.widgets.activity_card import ThinkingIndicator


class _ThinkingHost(App):
    def compose(self) -> ComposeResult:
        yield ThinkingIndicator(id='thinking')


@pytest.mark.asyncio
async def test_thinking_indicator_finalized_inline_code_uses_lightweight_highlight() -> (
    None
):
    app = _ThinkingHost()

    async with app.run_test():
        widget = app.query_one('#thinking', ThinkingIndicator)
        widget.start()
        widget.set_thoughts(
            'Inspect `backend/main.py` before editing.', streaming=False
        )

        content = widget.query_one('#thinking-content', Static)
        renderable = content.renderable
        assert isinstance(renderable, Text)
        assert renderable.plain.startswith('Thinking: Inspect')
        assert 'backend/main.py' in renderable.plain


@pytest.mark.asyncio
async def test_thinking_indicator_finalized_fenced_code_uses_syntax() -> None:
    app = _ThinkingHost()

    async with app.run_test():
        widget = app.query_one('#thinking', ThinkingIndicator)
        widget.start()
        widget.set_thoughts('Plan:\n```python\nprint("hi")\n```', streaming=False)

        content = widget.query_one('#thinking-content', Static)
        renderable = content.renderable
        assert isinstance(renderable, Group)
        assert isinstance(renderable.renderables[0], Text)
        assert renderable.renderables[0].plain.startswith('Thinking: Plan:')
        tail = renderable.renderables[1:]
        assert any(isinstance(part, Syntax) for part in tail) or any(
            isinstance(part, Group)
            and any(isinstance(sub, Syntax) for sub in part.renderables)
            for part in tail
            if isinstance(part, Group)
        )


@pytest.mark.asyncio
async def test_thinking_indicator_plain_prose_stays_flat() -> None:
    app = _ThinkingHost()

    async with app.run_test():
        widget = app.query_one('#thinking', ThinkingIndicator)
        widget.start()
        widget.set_thoughts('Plotting the next move.', streaming=False)

        content = widget.query_one('#thinking-content', Static)
        assert content.styles.opacity == 0.68
        renderable = content.renderable
        assert isinstance(renderable, Text)
        assert renderable.plain == 'Thinking: Plotting the next move.'


@pytest.mark.asyncio
async def test_thinking_indicator_highlights_reasoning_structure_and_paths() -> None:
    app = _ThinkingHost()

    async with app.run_test():
        widget = app.query_one('#thinking', ThinkingIndicator)
        widget.start()
        widget.set_thoughts(
            '**Plan:** Inspect backend/cli/tui/app.py\n- Verify the renderer.',
            streaming=True,
        )

        content = widget.query_one('#thinking-content', Static)
        renderable = content.renderable
        assert isinstance(renderable, Text)
        assert renderable.plain.startswith('Thinking: Plan: Inspect')
        assert '**' not in renderable.plain

        console = Console(force_terminal=True, color_system='truecolor', width=100)
        rendered = list(console.render(renderable, console.options.update_width(100)))
        path_styles = [
            style
            for value, style, _ in rendered
            if value.strip() == 'backend/cli/tui/app.py'
        ]
        bullet_styles = [
            style for value, style, _ in rendered if value.strip() == '-'
        ]
        assert path_styles and any('101829' in str(style) for style in path_styles)
        assert bullet_styles and any('42a394' in str(style.color) for style in bullet_styles)
