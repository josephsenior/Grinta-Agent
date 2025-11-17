from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger
from forge.core.schemas import AgentState
from forge.events import EventSource
from forge.events.action import ActionConfirmationStatus
from forge.events.observation import AgentStateChangedObservation

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext


class StateTransitionService:
    """Owns agent state transitions and related side effects."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    async def set_agent_state(self, new_state: AgentState) -> None:
        controller = self._context.get_controller()
        logger.info(
            "Setting agent(%s) state from %s to %s",
            controller.agent.name,
            controller.state.agent_state,
            new_state,
        )

        if new_state == controller.state.agent_state:
            return

        old_state = controller.state.agent_state
        controller.state.agent_state = new_state

        self._handle_state_reset(new_state)
        self._handle_error_recovery(old_state, new_state)
        self._handle_pending_action_confirmation(new_state)

        reason = controller.state.last_error if new_state == AgentState.ERROR else ""
        controller.event_stream.add_event(
            AgentStateChangedObservation("", controller.state.agent_state, reason),
            EventSource.ENVIRONMENT,
        )
        controller.save_state()

    def _handle_state_reset(self, new_state: AgentState) -> None:
        controller = self._context.get_controller()
        if new_state in (AgentState.STOPPED, AgentState.ERROR):
            controller._reset()

    def _handle_error_recovery(self, old_state: AgentState, new_state: AgentState) -> None:
        state_tracker = self._context.state_tracker
        controller = self._context.get_controller()
        if (
            state_tracker
            and old_state == AgentState.ERROR
            and new_state == AgentState.RUNNING
        ):
            state_tracker.maybe_increase_control_flags_limits(controller.headless_mode)

    def _handle_pending_action_confirmation(self, new_state: AgentState) -> None:
        pending_action = self._context.pending_action
        if pending_action is None or new_state not in (
            AgentState.USER_CONFIRMED,
            AgentState.USER_REJECTED,
        ):
            return

        if hasattr(pending_action, "thought"):
            pending_action.thought = ""

        pending_action.confirmation_state = (
            ActionConfirmationStatus.CONFIRMED
            if new_state == AgentState.USER_CONFIRMED
            else ActionConfirmationStatus.REJECTED
        )
        pending_action._id = None
        self._context.emit_event(pending_action, EventSource.AGENT)
        self._context.clear_pending_action()


