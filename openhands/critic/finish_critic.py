from __future__ import annotations

from typing import TYPE_CHECKING

from openhands.critic.base import BaseCritic, CriticResult
from openhands.events.action import Action, AgentFinishAction

if TYPE_CHECKING:
    from openhands.events import Event


class AgentFinishedCritic(BaseCritic):
    """This is a simple rule-based critic that checks if the last event is an AgentFinishAction.

    If not, it will return a score of 0 and a message indicating that the agent did not finish.
    If the git patch is provided and is empty, it will return a score of 0 and a message indicating that the git patch is empty.
    """

    def __init__(self) -> None:
        pass

    def evaluate(self, events: list[Event], git_patch: str | None = None) -> CriticResult:
        last_action = next((h for h in reversed(events) if isinstance(h, Action)), None)
        if git_patch is not None and len(git_patch.strip()) == 0:
            return CriticResult(score=0, message="Git patch is empty.")
        if isinstance(last_action, AgentFinishAction):
            return CriticResult(score=1, message="Agent finished.")
        return CriticResult(score=0, message="Agent did not finish.")
