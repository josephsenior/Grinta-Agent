"""State models and helpers for tracking agent conversations."""

from __future__ import annotations

import base64
import contextlib
import os
import pickle  # nosec B403 - Used only for internal state serialization
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import forge
from forge.controller.state.control_flags import (
    BudgetControlFlag,
    IterationControlFlag,
)
from forge.core.logger import forge_logger as logger
from forge.core.schema import AgentState
from forge.events.action import MessageAction
from forge.events.action.agent import AgentFinishAction
from forge.events.event import Event, EventSource
from forge.llm.metrics import Metrics
from forge.memory.view import View
from forge.storage.locations import get_conversation_agent_state_filename

if TYPE_CHECKING:
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore

RESUMABLE_STATES = [
    AgentState.RUNNING,
    AgentState.PAUSED,
    AgentState.AWAITING_USER_INPUT,
    AgentState.FINISHED,
]


class TrafficControlState:
    """Track pause/resume state for agent loops and manage iteration counters."""

    NORMAL = "normal"
    THROTTLING = "throttling"
    PAUSED = "paused"


@dataclass
class State:
    """Represents the running state of an agent in the Forge system, saving data of its operation and memory.

    - Multi-agent/delegate state:
      - store the task (conversation between the agent and the user)
      - the subtask (conversation between an agent and the user or another agent)
      - global and local iterations
      - delegate levels for multi-agent interactions
      - almost stuck state

    - Running state of an agent:
      - current agent state (e.g., LOADING, RUNNING, PAUSED)
      - traffic control state for rate limiting
      - confirmation mode
      - the last error encountered

    - Data for saving and restoring the agent:
      - save to and restore from a session
      - serialize with pickle and base64

    - Save / restore data about message history
      - start and end IDs for events in agent's history
      - summaries and delegate summaries

    - Metrics:
      - global metrics for the current task
      - local metrics for the current subtask

    - Extra data:
      - additional task-specific data
    """

    session_id: str = ""
    user_id: str | None = None
    iteration_flag: IterationControlFlag = field(
        default_factory=lambda: IterationControlFlag(
            limit_increase_amount=100,
            current_value=0,
            max_value=100,
        ),
    )
    conversation_stats: ConversationStats | None = None
    budget_flag: BudgetControlFlag | None = None
    confirmation_mode: bool = False
    history: list[Event] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    agent_state: AgentState = AgentState.LOADING
    resume_state: AgentState | None = None
    delegate_level: int = 0
    start_id: int = -1
    end_id: int = -1
    parent_metrics_snapshot: Metrics | None = None
    parent_iteration: int = 100
    extra_data: dict[str, Any] = field(default_factory=dict)
    last_error: str = ""
    iteration: int | None = None
    local_iteration: int | None = None
    max_iterations: int | None = None
    traffic_control_state: TrafficControlState | None = None
    local_metrics: Metrics | None = None
    delegates: dict[tuple[int, int], tuple[str, str]] | None = None
    metrics: Metrics = field(default_factory=Metrics)

    def save_to_session(
        self,
        sid: str,
        file_store: FileStore,
        user_id: str | None,
    ) -> None:
        """Save agent state to persistent storage.
        
        Serializes state with pickle/base64 for session resumption.
        
        Args:
            sid: Session ID
            file_store: File storage backend
            user_id: Optional user ID for scoping

        """
        conversation_stats = self.conversation_stats
        self.conversation_stats = None
        # nosec B301 - Controlled serialization of internal application state
        pickled = pickle.dumps(self)
        logger.debug("Saving state to session %s:%s", sid, self.agent_state)
        encoded = base64.b64encode(pickled).decode("utf-8")
        try:
            file_store.write(
                get_conversation_agent_state_filename(sid, user_id),
                encoded,
            )
            if user_id:
                filename = get_conversation_agent_state_filename(sid)
                with contextlib.suppress(Exception):
                    file_store.delete(filename)
        except Exception as e:
            logger.error("Failed to save state to session: %s", e)
            raise
        self.conversation_stats = conversation_stats

    @staticmethod
    def restore_from_session(
        sid: str,
        file_store: FileStore,
        user_id: str | None = None,
    ) -> State:
        """Restores the state from the previously saved session."""
        state: State
        try:
            encoded = file_store.read(
                get_conversation_agent_state_filename(sid, user_id),
            )
            pickled = base64.b64decode(encoded)
            state = pickle.loads(
                pickled,
            )  # nosec B301 - Safe: loading from trusted application state file
        except FileNotFoundError as e:
            if not user_id:
                msg = f"Could not restore state from session file for sid: {sid}"
                raise FileNotFoundError(
                    msg,
                ) from e
            filename = get_conversation_agent_state_filename(sid)
            encoded = file_store.read(filename)
            pickled = base64.b64decode(encoded)
            state = pickle.loads(
                pickled,
            )  # nosec B301 - Safe: loading from trusted application state file
        except Exception as e:
            logger.debug("Could not restore state from session: %s", e)
            raise
        if state.agent_state in RESUMABLE_STATES:
            state.resume_state = state.agent_state
        else:
            state.resume_state = None
        state.agent_state = AgentState.LOADING
        return state

    def __getstate__(self) -> dict:
        """Return the picklable state while omitting large transient history."""
        state = self.__dict__.copy()
        state["history"] = []
        state.pop("_history_checksum", None)
        state.pop("_view", None)
        state.pop("iteration", None)
        state.pop("local_iteration", None)
        state.pop("max_iterations", None)
        state.pop("traffic_control_state", None)
        state.pop("local_metrics", None)
        state.pop("delegates", None)
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore state from pickled data and rebuild control flags."""
        is_old_version = "iteration" in state
        if is_old_version:
            max_iterations = state.get("max_iterations", 100)
            current_iteration = state.get("iteration", 0)
            state["iteration_flag"] = IterationControlFlag(
                limit_increase_amount=max_iterations,
                current_value=current_iteration,
                max_value=max_iterations,
            )
        self.__dict__.update(state)
        if not hasattr(self, "history"):
            self.history = []
        if not hasattr(self, "iteration_flag"):
            self.iteration_flag = IterationControlFlag(
                limit_increase_amount=100,
                current_value=0,
                max_value=100,
            )
        if not hasattr(self, "budget_flag"):
            self.budget_flag = None

    def _process_user_message_event(
        self,
        event: MessageAction,
    ) -> tuple[str, list[str] | None]:
        """Process a user message event and extract content and image URLs."""
        return event.content, event.image_urls

    def _check_for_finish_action(
        self,
        event: Event,
        last_user_message: str | None,
    ) -> tuple[str | None, list[str] | None] | None:
        """Check if event is a finish action and return appropriate result."""
        if isinstance(event, AgentFinishAction) and last_user_message is not None:
            return (last_user_message, None)
        return None

    def _find_user_intent_from_events(self) -> tuple[str | None, list[str] | None]:
        """Find user intent by processing events in reverse order."""
        last_user_message = None
        last_user_message_image_urls: list[str] | None = []

        for event in reversed(self.view):
            if isinstance(event, MessageAction) and event.source == "user":
                last_user_message, last_user_message_image_urls = self._process_user_message_event(event)
            elif isinstance(event, AgentFinishAction):
                finish_result = self._check_for_finish_action(event, last_user_message)
                if finish_result is not None:
                    return finish_result

        return (last_user_message, last_user_message_image_urls)

    def get_current_user_intent(self) -> tuple[str | None, list[str] | None]:
        """Returns the latest user message and image(if provided) that appears after a FinishAction, or the first (the task) if nothing was finished yet."""
        return self._find_user_intent_from_events()

    def get_last_agent_message(self) -> MessageAction | None:
        """Get most recent message from agent in conversation history.
        
        Returns:
            Last agent message, or None if no agent messages

        """
        return next(
            (
                event
                for event in reversed(self.view)
                if isinstance(event, MessageAction) and event.source == EventSource.AGENT
            ),
            None,
        )

    def get_last_user_message(self) -> MessageAction | None:
        """Get most recent message from user in conversation history.
        
        Returns:
            Last user message, or None if no user messages

        """
        return next(
            (
                event
                for event in reversed(self.view)
                if isinstance(event, MessageAction) and event.source == EventSource.USER
            ),
            None,
        )

    def to_llm_metadata(self, model_name: str, agent_name: str) -> dict:
        """Convert state to metadata dict for LLM tracing/logging.
        
        Args:
            model_name: Name of LLM model being used
            agent_name: Name of agent being traced
            
        Returns:
            Dictionary with session, version, and tag metadata

        """
        return {
            "session_id": self.session_id,
            "trace_version": forge.__version__,
            "trace_user_id": self.user_id,
            "tags": [
                f"model:{model_name}",
                f"agent:{agent_name}",
                f"web_host:{
                    os.environ.get(
                        'WEB_HOST',
                        'unspecified')}",
                f"FORGE_version:{
                    forge.__version__}",
            ],
        }

    def get_local_step(self):
        """Get iteration count for current subtask (delegate).
        
        Returns:
            Local step count relative to parent, or global count if no parent

        """
        if not self.parent_iteration:
            return self.iteration_flag.current_value
        return self.iteration_flag.current_value - self.parent_iteration

    def get_local_metrics(self):
        """Get metrics for current subtask (delegate).
        
        Returns:
            Local metrics relative to parent snapshot, or global if no parent

        """
        if not self.parent_metrics_snapshot:
            return self.metrics
        return self.metrics.diff(self.parent_metrics_snapshot)

    @property
    def view(self) -> View:
        """Get filtered view of conversation history for agent.
        
        Returns:
            View object containing relevant events for agent context

        """
        history_checksum = len(self.history)
        old_history_checksum = getattr(self, "_history_checksum", -1)
        if history_checksum != old_history_checksum:
            self._history_checksum = history_checksum
            self._view = View.from_events(self.history)
        return self._view
