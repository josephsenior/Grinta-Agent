from __future__ import annotations

from typing import TYPE_CHECKING

from openhands.controller.state.control_flags import (
    BudgetControlFlag,
    IterationControlFlag,
)
from openhands.controller.state.state import State
from openhands.core.logger import openhands_logger as logger
from openhands.events.action.agent import AgentDelegateAction, ChangeAgentStateAction
from openhands.events.action.empty import NullAction
from openhands.events.event_filter import EventFilter
from openhands.events.observation.agent import AgentStateChangedObservation
from openhands.events.observation.delegate import AgentDelegateObservation
from openhands.events.observation.empty import NullObservation
from openhands.events.serialization.event import event_to_trajectory

if TYPE_CHECKING:
    from openhands.events.event import Event
    from openhands.events.stream import EventStream
    from openhands.server.services.conversation_stats import ConversationStats
    from openhands.storage.files import FileStore


class StateTracker:
    """Manages and synchronizes the state of an agent throughout its lifecycle.

    It is responsible for:
    1. Maintaining agent state persistence across sessions
    2. Managing agent history by filtering and tracking relevant events (previously done in the agent controller)
    3. Synchronizing metrics between the controller and LLM components
    4. Updating control flags for budget and iteration limits

    """

    def __init__(self, sid: str | None, file_store: FileStore | None, user_id: str | None) -> None:
        self.sid = sid
        self.file_store = file_store
        self.user_id = user_id
        self.agent_history_filter = EventFilter(
            exclude_types=(NullAction, NullObservation, ChangeAgentStateAction, AgentStateChangedObservation),
            exclude_hidden=True,
        )

    def set_initial_state(
        self,
        id: str,
        state: State | None,
        conversation_stats: ConversationStats,
        max_iterations: int,
        max_budget_per_task: float | None,
        confirmation_mode: bool = False,
    ) -> None:
        """Sets the initial state for the agent, either from the previous session, or from a parent agent, or by creating a new one.

        Args:
            id: The session ID for the agent.
            state: The state to initialize with, or None to create a new state.
            conversation_stats: Statistics for the conversation.
            max_iterations: The maximum number of iterations allowed for the task.
            max_budget_per_task: The maximum budget allowed for the task.
            confirmation_mode: Whether to enable confirmation mode.
        """
        if state is None:
            self.state = State(
                session_id=id.removesuffix("-delegate"),
                user_id=self.user_id,
                inputs={},
                conversation_stats=conversation_stats,
                iteration_flag=IterationControlFlag(
                    limit_increase_amount=max_iterations,
                    current_value=0,
                    max_value=max_iterations,
                ),
                budget_flag=(
                    BudgetControlFlag(
                        limit_increase_amount=max_budget_per_task,
                        current_value=0,
                        max_value=max_budget_per_task,
                    )
                    if max_budget_per_task
                    else None
                ),
                confirmation_mode=confirmation_mode,
            )
            self.state.start_id = 0
            logger.info("AgentController %s - created new state. start_id: %s", id, self.state.start_id)
        else:
            self.state = state
            if self.state.start_id <= -1:
                self.state.start_id = 0
            state.conversation_stats = conversation_stats

    def _init_history(self, event_stream: EventStream) -> None:
        """Initializes the agent's history from the event stream.

        The history is a list of events that:
        - Excludes events of types listed in self.filter_out
        - Excludes events with hidden=True attribute
        - For delegate events (between AgentDelegateAction and AgentDelegateObservation):
            - Excludes all events between the action and observation
            - Includes the delegate action and observation themselves
        """
        start_id, end_id = self._get_history_range(event_stream)

        if not self._validate_history_range(start_id, end_id):
            return

        events = self._fetch_events_from_stream(event_stream, start_id, end_id)
        if delegate_ranges := self._find_delegate_ranges(events):
            self.state.history = self._filter_events_with_delegates(events, delegate_ranges)
        else:
            self.state.history = events

        self.state.start_id = start_id

    def _get_history_range(self, event_stream: EventStream) -> tuple[int, int]:
        """Get the start and end ID range for history."""
        start_id = max(self.state.start_id, 0)
        end_id = self.state.end_id if self.state.end_id >= 0 else event_stream.get_latest_event_id()
        return start_id, end_id

    def _validate_history_range(self, start_id: int, end_id: int) -> bool:
        """Validate the history range and set empty history if invalid."""
        if start_id > end_id + 1:
            logger.warning("start_id %s is greater than end_id + 1 (%s). History will be empty.", start_id, end_id + 1)
            self.state.history = []
            return False
        return True

    def _fetch_events_from_stream(self, event_stream: EventStream, start_id: int, end_id: int) -> list[Event]:
        """Fetch events from the event stream."""
        return list(
            event_stream.search_events(
                start_id=start_id,
                end_id=end_id,
                reverse=False,
                filter=self.agent_history_filter,
            ),
        )

    def _find_delegate_ranges(self, events: list[Event]) -> list[tuple[int, int]]:
        """Find delegate action-observation ranges in events."""
        delegate_ranges: list[tuple[int, int]] = []
        delegate_action_ids: list[int] = []

        for event in events:
            if isinstance(event, AgentDelegateAction):
                delegate_action_ids.append(event.id)
            elif isinstance(event, AgentDelegateObservation):
                if not delegate_action_ids:
                    logger.warning("Found AgentDelegateObservation without matching action at id=%s", event.id)
                    continue
                action_id = delegate_action_ids.pop()
                delegate_ranges.append((action_id, event.id))

        return delegate_ranges

    def _filter_events_with_delegates(self, events: list[Event], delegate_ranges: list[tuple[int, int]]) -> list[Event]:
        """Filter events to exclude those within delegate ranges."""
        filtered_events: list[Event] = []
        current_idx = 0

        for start_id, end_id in sorted(delegate_ranges):
            # Add events before the delegate range
            filtered_events.extend(event for event in events[current_idx:] if event.id < start_id)

            # Add only the delegate action and observation
            filtered_events.extend(event for event in events if event.id in (start_id, end_id))

            # Update current index to after this delegate range
            current_idx = next((i for i, e in enumerate(events) if e.id > end_id), len(events))

        # Add remaining events after the last delegate range
        filtered_events.extend(events[current_idx:])
        return filtered_events

    def close(self, event_stream: EventStream) -> None:
        start_id = max(self.state.start_id, 0)
        end_id = self.state.end_id if self.state.end_id >= 0 else event_stream.get_latest_event_id()
        self.state.history = list(
            event_stream.search_events(
                start_id=start_id,
                end_id=end_id,
                reverse=False,
                filter=self.agent_history_filter,
            ),
        )

    def add_history(self, event: Event) -> None:
        if self.agent_history_filter.include(event):
            self.state.history.append(event)

    def get_trajectory(self, include_screenshots: bool = False) -> list[dict]:
        return [event_to_trajectory(event, include_screenshots) for event in self.state.history]

    def maybe_increase_control_flags_limits(self, headless_mode: bool) -> None:
        self.state.iteration_flag.increase_limit(headless_mode)
        if self.state.budget_flag:
            self.state.budget_flag.increase_limit(headless_mode)

    def get_metrics_snapshot(self):
        """Deep copy of metrics.

        This serves as a snapshot for the parent's metrics at the time a delegate is created
        It will be stored and used to compute local metrics for the delegate
        (since delegates now accumulate metrics from where its parent left off).
        """
        return self.state.metrics.copy()

    def save_state(self) -> None:
        """Save's current state to persistent store."""
        if self.sid and self.file_store:
            self.state.save_to_session(self.sid, self.file_store, self.user_id)
        if self.state.conversation_stats:
            self.state.conversation_stats.save_metrics()

    def run_control_flags(self) -> None:
        """Performs one step of the control flags."""
        self.state.iteration_flag.step()
        if self.state.budget_flag:
            self.state.budget_flag.step()

    def sync_budget_flag_with_metrics(self) -> None:
        """Ensures that budget flag is up to date with accumulated costs from llm completions.

        Budget flag will monitor for when budget is exceeded.
        """
        if self.state.budget_flag and self.state.conversation_stats:
            self.state.budget_flag.current_value = self.state.conversation_stats.get_combined_metrics().accumulated_cost
