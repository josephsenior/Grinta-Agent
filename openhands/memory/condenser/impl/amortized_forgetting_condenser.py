from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.core.config.condenser_config import AmortizedForgettingCondenserConfig
from openhands.events.action.agent import CondensationAction
from openhands.memory.condenser.condenser import Condensation, RollingCondenser
from openhands.memory.view import View

if TYPE_CHECKING:
    from openhands.llm.llm_registry import LLMRegistry


class AmortizedForgettingCondenser(RollingCondenser):
    """A condenser that maintains a condensed history and forgets old events when it grows too large."""

    def __init__(self, max_size: int = 100, keep_first: int = 0) -> None:
        """Initialize the condenser.

        Args:
            max_size: Maximum size of history before forgetting.
            keep_first: Number of initial events to always keep.

        Raises:
            ValueError: If keep_first is greater than max_size, keep_first is negative, or max_size is non-positive.
        """
        if keep_first >= max_size // 2:
            msg = f"keep_first ({keep_first}) must be less than half of max_size ({max_size})"
            raise ValueError(msg)
        if keep_first < 0:
            msg = f"keep_first ({keep_first}) cannot be negative"
            raise ValueError(msg)
        if max_size < 1:
            msg = f"max_size ({keep_first}) cannot be non-positive"
            raise ValueError(msg)
        self.max_size = max_size
        self.keep_first = keep_first
        super().__init__()

    def get_condensation(self, view: View) -> Condensation:
        target_size = self.max_size // 2
        head = view[: self.keep_first]
        events_from_tail = target_size - len(head)
        tail = view[-events_from_tail:]
        event_ids_to_keep = {event.id for event in head + tail}
        event_ids_to_forget = {event.id for event in view} - event_ids_to_keep
        event = CondensationAction(
            forgotten_events_start_id=min(event_ids_to_forget),
            forgotten_events_end_id=max(event_ids_to_forget),
        )
        return Condensation(action=event)

    def should_condense(self, view: View) -> bool:
        return len(view) > self.max_size

    @classmethod
    def from_config(
        cls,
        config: "AmortizedForgettingCondenserConfig",
        llm_registry: LLMRegistry,
    ) -> AmortizedForgettingCondenser:
        from openhands.core.pydantic_compat import model_dump_with_options

        return AmortizedForgettingCondenser(**model_dump_with_options(config, exclude={"type"}))


# Lazy registration to avoid circular imports
def _register_config():
    from openhands.core.config.condenser_config import AmortizedForgettingCondenserConfig
    AmortizedForgettingCondenser.register_config(AmortizedForgettingCondenserConfig)

_register_config()
