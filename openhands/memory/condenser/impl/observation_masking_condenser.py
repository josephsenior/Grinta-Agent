from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.core.config.condenser_config import ObservationMaskingCondenserConfig
from openhands.events.observation import Observation
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.memory.condenser.condenser import Condensation, Condenser
from openhands.memory.view import View

if TYPE_CHECKING:
    from openhands.events.event import Event
    from openhands.llm.llm_registry import LLMRegistry


class ObservationMaskingCondenser(Condenser):
    """A condenser that masks the values of observations outside of a recent attention window."""

    def __init__(self, attention_window: int = 5) -> None:
        self.attention_window = attention_window
        super().__init__()

    def condense(self, view: View) -> View | Condensation:
        """Replace the content of observations outside of the attention window with a placeholder."""
        results: list[Event] = []
        for i, event in enumerate(view):
            if isinstance(event, Observation) and i < len(view) - self.attention_window:
                results.append(AgentCondensationObservation("<MASKED>"))
            else:
                results.append(event)
        return View(events=results)

    @classmethod
    def from_config(
        cls,
        config: "ObservationMaskingCondenserConfig",
        llm_registry: LLMRegistry,
    ) -> ObservationMaskingCondenser:
        from openhands.core.pydantic_compat import model_dump_with_options

        return ObservationMaskingCondenser(**model_dump_with_options(config, exclude={"type"}))


# Lazy registration to avoid circular imports
def _register_config():
    from openhands.core.config.condenser_config import ObservationMaskingCondenserConfig
    ObservationMaskingCondenser.register_config(ObservationMaskingCondenserConfig)

_register_config()
