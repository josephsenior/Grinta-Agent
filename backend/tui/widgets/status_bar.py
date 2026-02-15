"""Agent status bar — shows agent state, model name, and accumulated cost."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Label

# Map agent states to display indicators
_STATE_DISPLAY: dict[str, tuple[str, str]] = {
    "loading": ("⏳", "Loading"),
    "running": ("🔄", "Running"),
    "awaiting_user_input": ("💬", "Awaiting Input"),
    "awaiting_user_confirmation": ("⚠️", "Needs Confirmation"),
    "paused": ("⏸", "Paused"),
    "stopped": ("⏹", "Stopped"),
    "finished": ("✅", "Finished"),
    "rejected": ("❌", "Rejected"),
    "error": ("💥", "Error"),
    "rate_limited": ("🕐", "Rate Limited"),
}


class AgentStatusBar(Widget):
    """Persistent footer showing agent state, model, and cost."""

    DEFAULT_CSS = """
    AgentStatusBar {
        height: 1;
        dock: bottom;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    #state-label {
        width: auto;
        text-style: bold;
    }
    #model-label {
        width: 1fr;
        text-align: center;
        color: $text-muted;
    }
    #cost-label {
        width: auto;
        text-align: right;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("⏳ Loading", id="state-label")
            yield Label("—", id="model-label")
            yield Label("$0.00", id="cost-label")

    def update_state(self, state: str) -> None:
        icon, text = _STATE_DISPLAY.get(state, ("❓", state))
        self.query_one("#state-label", Label).update(f"{icon} {text}")

    def update_model(self, model: str) -> None:
        self.query_one("#model-label", Label).update(model)

    def update_cost(self, cost: float) -> None:
        self.query_one("#cost-label", Label).update(f"${cost:.4f}")
