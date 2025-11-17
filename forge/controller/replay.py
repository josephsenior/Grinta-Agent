"""Utilities for replaying previously captured agent trajectories."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from forge.core.logger import forge_logger as logger
from forge.events.action.action import Action
from forge.events.action.message import MessageAction
from forge.events.event import Event, EventSource
from forge.events.observation.empty import NullObservation
from forge.events.serialization.event import event_from_dict


class ReplayManager:
    """ReplayManager manages the lifecycle of a replay session of a given trajectory.

    Replay manager keeps track of a list of events, replays actions, and ignore
    messages and observations.

    Note that unexpected or even errorneous results could happen if
    1) any action is non-deterministic, OR
    2) if the initial state before the replay session is different from the
    initial state of the trajectory.
    """

    def __init__(self, events: list[Event] | None) -> None:
        """Normalise the supplied events and prime replay mode state."""
        replay_events = []
        for event in events or []:
            if event.source == EventSource.ENVIRONMENT:
                continue
            if isinstance(event, NullObservation):
                continue
            replay_events.append(event)
        if replay_events:
            logger.info("Replay events loaded, events length = %s", len(replay_events))
            for index in range(len(replay_events) - 1):
                event = replay_events[index]
                if isinstance(event, MessageAction) and event.wait_for_response:
                    logger.info(
                        "Replay events contains wait_for_response message action, ignoring wait_for_response"
                    )
                    event.wait_for_response = False
        self.replay_events = replay_events
        self.replay_mode = bool(replay_events)
        self.replay_index = 0

    def _replayable(self) -> bool:
        return (
            self.replay_events is not None
            and self.replay_index < len(self.replay_events)
            and isinstance(self.replay_events[self.replay_index], Action)
        )

    def should_replay(self) -> bool:
        """Whether the controller is in trajectory replay mode, and the replay.

        hasn't finished. Note: after the replay is finished, the user and
        the agent could continue to message/act.

        This method also moves "replay_index" to the next action, if applicable.
        """
        if not self.replay_mode:
            return False
        assert self.replay_events is not None
        while self.replay_index < len(self.replay_events) and (not self._replayable()):
            self.replay_index += 1
        return self._replayable()

    def step(self) -> Action:
        """Get next action from replay trajectory.

        Returns:
            Next action to replay

        """
        assert self.replay_events is not None
        event = self.replay_events[self.replay_index]
        if not isinstance(event, Action):
            raise RuntimeError(
                f"Unexpected non-action event in replay at index {self.replay_index}: {type(event).__name__}"
            )
        self.replay_index += 1
        return event

    @staticmethod
    def get_replay_events(trajectory: Iterable[Mapping[str, Any]]) -> list[Event]:
        """Convert trajectory list to event objects for replay.

        Args:
            trajectory: List of event dictionaries

        Returns:
            List of event objects

        Raises:
            ValueError: If trajectory format is invalid

        """
        replay_events: list[Event] = []
        for item in trajectory:
            event = event_from_dict(dict(item))
            if event.source == EventSource.ENVIRONMENT:
                continue
            event._id = None
            replay_events.append(event)
        return replay_events
