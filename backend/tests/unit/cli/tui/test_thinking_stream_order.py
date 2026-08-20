from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, PropertyMock

import pytest
from rich.console import Console as RichConsole
from textual.widgets import Static

from backend.cli.display.hud import HUDBar
from backend.cli.display.reasoning_display import ReasoningDisplay
from backend.cli.tui.app import GrintaScreen, TUIRenderer
from backend.cli.tui.main import GrintaTUIApp
from backend.cli.tui.widgets.activity_card import ThinkingIndicator
from backend.cli.tui.widgets.scan_line import ShellCard
from backend.ledger.action import CmdRunAction, StreamingChunkAction
from backend.ledger.observation import CmdOutputObservation


@pytest.fixture
def mock_config():
    config = MagicMock()
    type(config).project_root = PropertyMock(return_value=None)

    llm_config = MagicMock()
    llm_config.model = 'openai/gpt-4o'
    llm_config.base_url = None
    config.get_llm_config.return_value = llm_config
    config.get_llm_config_from_agent.return_value = llm_config
    return config


def _plain_text(widget: ThinkingIndicator) -> str:
    body = widget.query_one('#thinking-content', Static)
    rendered = body.content
    if hasattr(rendered, 'plain'):
        return str(rendered.plain)
    console = RichConsole()
    with console.capture() as capture:
        console.print(rendered)
    return capture.get()


@pytest.mark.asyncio
async def test_thinking_stream_freezes_before_later_activity(
    mock_config,
    monkeypatch,
) -> None:
    monkeypatch.setattr(GrintaScreen, '_start_background_bootstrap', lambda self: None)
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        screen = app.screen
        renderer = TUIRenderer(
            console=console,
            hud=HUDBar(),
            reasoning=ReasoningDisplay(),
            tui=screen,  # type: ignore[arg-type]
            loop=loop,
        )
        screen._renderer = renderer  # type: ignore[attr-defined]

        renderer._process_event(
            StreamingChunkAction(thinking_accumulated='First thought.')
        )
        await pilot.pause()
        renderer._process_event(
            StreamingChunkAction(thinking_accumulated='First thought.\nStill thinking.')
        )
        await pilot.pause()
        renderer._process_event(CmdRunAction(command='pytest -q'))
        renderer._process_event(
            CmdOutputObservation('2 passed', command='pytest -q', exit_code=0)
        )
        await pilot.pause()
        renderer._process_event(
            StreamingChunkAction(thinking_accumulated='Second thought.')
        )

        display = screen.query_one('#main-display')

        # Streaming chunks are paint-throttled through a ``call_later`` timer
        # and appended widgets mount asynchronously, so a single
        # ``pilot.pause()`` can race the mount. Poll until the transcript has
        # settled before asserting.
        async def _transcript_settled() -> list[Any]:
            def _thinking_plain(widget: ThinkingIndicator) -> str:
                try:
                    return _plain_text(widget)
                except Exception:
                    return ''

            for _ in range(200):
                visible = [
                    child
                    for child in display.children
                    if isinstance(child, (ThinkingIndicator, ShellCard))
                ]
                if (
                    len(visible) == 3
                    and 'Still thinking.' in _thinking_plain(visible[0])
                    and 'Second thought.' in _thinking_plain(visible[2])
                ):
                    return visible
                await pilot.pause()
            return [
                child
                for child in display.children
                if isinstance(child, (ThinkingIndicator, ShellCard))
            ]

        visible = await _transcript_settled()

        assert [type(child) for child in visible] == [
            ThinkingIndicator,
            ShellCard,
            ThinkingIndicator,
        ]
        assert 'Still thinking.' in _plain_text(visible[0])
        assert 'pytest -q' in getattr(visible[1], 'command', '')
        assert 'Second thought.' in _plain_text(visible[2])
