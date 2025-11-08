"""Observation emitted after updating the task tracking list."""

from dataclasses import dataclass, field
from typing import Any

from forge.core.schema import ObservationType
from forge.events.observation.observation import Observation


@dataclass
class TaskTrackingObservation(Observation):
    """This data class represents the result of a task tracking operation."""

    observation: str = ObservationType.TASK_TRACKING
    command: str = ""
    task_list: list[dict[str, Any]] = field(default_factory=list)

    @property
    def message(self) -> str:
        """Get task tracking operation result."""
        return self.content

    __test__ = False
