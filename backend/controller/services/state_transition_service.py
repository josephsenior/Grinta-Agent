from __future__ import annotations

from typing import TYPE_CHECKING

from backend.core.logger import forge_logger as logger
from backend.core.schemas import AgentState
from backend.events import EventSource
from backend.events.action import ActionConfirmationStatus
from backend.events.observation import AgentStateChangedObservation

if TYPE_CHECKING:
    from backend.controller.services.controller_context import ControllerContext


# ── Valid state transitions ─────────────────────────────────────────────
# Maps ``from_state`` → frozenset of valid ``to_state`` values.
# Any transition NOT listed here is logged as a warning but still allowed
# (to avoid breaking existing edge-cases in the short term).  Over time the
# warning should be upgraded to a hard rejection.
VALID_TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    AgentState.LOADING: frozenset({
        AgentState.RUNNING,
        AgentState.ERROR,
        AgentState.STOPPED,
    }),
    AgentState.RUNNING: frozenset({
        AgentState.PAUSED,
        AgentState.STOPPED,
        AgentState.FINISHED,
        AgentState.ERROR,
        AgentState.RATE_LIMITED,
        AgentState.AWAITING_USER_INPUT,
        AgentState.AWAITING_USER_CONFIRMATION,
        AgentState.REJECTED,
    }),
    AgentState.PAUSED: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
    AgentState.STOPPED: frozenset({
        AgentState.LOADING,
        AgentState.RUNNING,
    }),
    AgentState.FINISHED: frozenset({
        AgentState.RUNNING,
        AgentState.LOADING,
        AgentState.STOPPED,
    }),
    AgentState.REJECTED: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
    AgentState.ERROR: frozenset({
        AgentState.RUNNING,
        AgentState.LOADING,
        AgentState.STOPPED,
    }),
    AgentState.AWAITING_USER_INPUT: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
    AgentState.AWAITING_USER_CONFIRMATION: frozenset({
        AgentState.USER_CONFIRMED,
        AgentState.USER_REJECTED,
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
    AgentState.USER_CONFIRMED: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
    AgentState.USER_REJECTED: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
        AgentState.REJECTED,
    }),
    AgentState.RATE_LIMITED: frozenset({
        AgentState.RUNNING,
        AgentState.STOPPED,
        AgentState.ERROR,
    }),
}


class StateTransitionService:
    """Owns agent state transitions and related side effects."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    async def set_agent_state(self, new_state: AgentState) -> None:
        controller = self._context.get_controller()
        old_state = controller.state.agent_state
        logger.info(
            "Setting agent(%s) state from %s to %s",
            controller.agent.name,
            old_state,
            new_state,
        )

        if new_state == old_state:
            return

        # ── Transition validation ──────────────────────────────────────
        allowed = VALID_TRANSITIONS.get(old_state)
        if allowed is not None and new_state not in allowed:
            logger.warning(
                "Unexpected state transition %s → %s for agent %s. "
                "Allowing for now but this should be investigated.",
                old_state,
                new_state,
                controller.agent.name,
            )

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


