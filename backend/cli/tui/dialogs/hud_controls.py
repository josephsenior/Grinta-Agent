"""Compact HUD controls drawer for narrow terminals."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, Select, Static

from backend.cli.tui.widgets.dialogs import ModalDialog


class GrintaHUDControlsDialog(ModalDialog[dict[str, str] | None]):
    """Expose all session controls without requiring horizontal HUD space."""

    DEFAULT_CSS = """
    GrintaHUDControlsDialog > #dialog-container {
        width: 48;
        min-width: 0;
        max-width: 94%;
        padding: 1 2;
    }
    GrintaHUDControlsDialog Select { margin-bottom: 1; }
    """

    def __init__(
        self,
        *,
        mode: str,
        autonomy: str,
        reasoning: str,
        mode_options: list[tuple[str, str]],
        autonomy_options: list[tuple[str, str]],
        reasoning_options: list[tuple[str, str]],
    ) -> None:
        super().__init__()
        self._mode = mode
        self._autonomy = autonomy
        self._reasoning = reasoning
        self._mode_options = mode_options

        self._autonomy_options = autonomy_options
        self._reasoning_options = reasoning_options or [('Default', '')]

    def compose(self) -> ComposeResult:
        with Vertical(id='dialog-container'):
            yield Label('Session controls', id='dialog-title')
            yield Static('Controls normally shown in the HUD.', id='dialog-subtitle')
            yield Label('Mode', classes='field-label')
            yield Select(
                self._mode_options,
                value=self._mode,
                allow_blank=False,
                id='hud-drawer-mode',
            )
            yield Label('Autonomy', classes='field-label')
            yield Select(
                self._autonomy_options,
                value=self._autonomy,
                allow_blank=False,
                id='hud-drawer-autonomy',
            )
            yield Label('Reasoning', classes='field-label')
            yield Select(
                self._reasoning_options,
                value=self._reasoning,
                allow_blank=False,
                id='hud-drawer-reasoning',
            )
            with Horizontal(id='dialog-buttons'):
                yield Button('Apply', id='hud-drawer-apply', variant='primary')
                yield Button('Cancel', id='hud-drawer-cancel')

    def on_mount(self) -> None:
        self.query_one('#hud-drawer-mode', Select).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'hud-drawer-cancel':
            self.dismiss(None)
        elif event.button.id == 'hud-drawer-apply':
            self.dismiss(
                {
                    'mode': str(self.query_one('#hud-drawer-mode', Select).value),
                    'autonomy': str(
                        self.query_one('#hud-drawer-autonomy', Select).value
                    ),
                    'reasoning': str(
                        self.query_one('#hud-drawer-reasoning', Select).value
                    ),
                }
            )
