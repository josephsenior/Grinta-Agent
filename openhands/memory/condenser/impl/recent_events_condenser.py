from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.core.config.condenser_config import RecentEventsCondenserConfig
    from openhands.llm.llm_registry import LLMRegistry

from openhands.memory.condenser.condenser import Condensation, Condenser
from openhands.memory.view import View


class RecentEventsCondenser(Condenser):
    """A condenser that only keeps a certain number of the most recent events."""

    def __init__(self, keep_first: int = 1, max_events: int = 10) -> None:
        self.keep_first = keep_first
        self.max_events = max_events
        super().__init__()

    def condense(self, view: View) -> View | Condensation:
        """Keep only the most recent events (up to `max_events`)."""
        head = view[: self.keep_first]
        tail_length = max(0, self.max_events - len(head))
        tail = view[-tail_length:]
        return View(events=head + tail)

    @classmethod
    def from_config(cls, config: "RecentEventsCondenserConfig", llm_registry: "LLMRegistry") -> "RecentEventsCondenser":
        from openhands.core.pydantic_compat import model_dump_with_options

        return RecentEventsCondenser(**model_dump_with_options(config, exclude={"type"}))


# Lazy registration to avoid circular imports
def _register_config():
    from openhands.core.config.condenser_config import RecentEventsCondenserConfig
    RecentEventsCondenser.register_config(RecentEventsCondenserConfig)

_register_config()
