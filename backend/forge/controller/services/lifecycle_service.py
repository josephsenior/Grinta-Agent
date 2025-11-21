from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from forge.controller.replay import ReplayManager
from forge.controller.state.state_tracker import StateTracker
from forge.events import EventStreamSubscriber

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.agent_controller import AgentController
    from forge.core.config import AgentConfig, LLMConfig
    from forge.events.event import Event
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore


class LifecycleService:
    """Manages AgentController lifecycle wiring and state bookkeeping."""

    def __init__(self, controller: "AgentController") -> None:
        self._controller = controller

    def initialize_core_attributes(
        self,
        sid: str | None,
        event_stream,
        agent: "Agent",
        user_id: str | None,
        file_store: "FileStore | None",
        headless_mode: bool,
        is_delegate: bool,
        conversation_stats: "ConversationStats",
        status_callback: Callable | None,
        security_analyzer,
    ) -> None:
        """Initialize identifiers, event subscriptions, and shared references."""

        controller = self._controller
        controller.id = sid or event_stream.sid
        controller.user_id = user_id
        controller.file_store = file_store
        controller.agent = agent
        controller.headless_mode = headless_mode
        controller.is_delegate = is_delegate
        controller.conversation_stats = conversation_stats
        controller.event_stream = event_stream
        controller.status_callback = status_callback
        controller.security_analyzer = security_analyzer

        if not controller.is_delegate:
            event_stream.subscribe(
                EventStreamSubscriber.AGENT_CONTROLLER, controller.on_event, controller.id
            )

        controller._closed = False

    def initialize_state_and_tracking(
        self,
        sid: str | None,
        file_store: "FileStore | None",
        user_id: str | None,
        initial_state,
        conversation_stats: "ConversationStats",
        iteration_delta: int,
        budget_per_task_delta: float | None,
        confirmation_mode: bool,
        replay_events: list["Event"] | None,
    ) -> None:
        """Prepare state tracker, stuck detector, and replay manager."""

        controller = self._controller
        controller.state_tracker = StateTracker(sid, file_store, user_id)
        controller.set_initial_state(
            state=initial_state,
            conversation_stats=conversation_stats,
            max_iterations=iteration_delta,
            max_budget_per_task=budget_per_task_delta,
            confirmation_mode=confirmation_mode,
        )
        controller.state = controller.state_tracker.state
        controller.confirmation_mode = confirmation_mode
        controller._replay_manager = ReplayManager(replay_events)

    def initialize_agent_configs(
        self,
        agent_to_llm_config: dict[str, "LLMConfig"] | None,
        agent_configs: dict[str, "AgentConfig"] | None,
        iteration_delta: int,
        budget_per_task_delta: float | None,
    ) -> None:
        """Record controller-level config overrides."""

        controller = self._controller
        controller.agent_to_llm_config = agent_to_llm_config or {}
        controller.agent_configs = agent_configs or {}
        controller._initial_max_iterations = iteration_delta
        controller._initial_max_budget_per_task = budget_per_task_delta

