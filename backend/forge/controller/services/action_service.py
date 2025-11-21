from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import LOG_ALL_EVENTS
from forge.events import EventSource
from forge.events.action import Action, NullAction
from forge.events.observation import ErrorObservation

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext
    from forge.controller.services.observation_service import ObservationService
    from forge.controller.services.confirmation_service import ConfirmationService
    from forge.controller.tool_pipeline import ToolInvocationContext


class ActionService:
    """Coordinates tool pipeline verification/execute and pending action lifecycle."""

    def __init__(
        self,
        context: "ControllerContext",
        observation_service: "ObservationService",
        pending_action_service,
        confirmation_service: "ConfirmationService",
    ) -> None:
        self._context = context
        self._observation_service = observation_service
        self._pending_service = pending_action_service
        self._confirmation_service = confirmation_service

    async def run(
        self, action: Action, ctx: "ToolInvocationContext | None"
    ) -> None:
        """Entry point used by AgentController to process an action end-to-end."""

        if not isinstance(action, Action):
            raise TypeError("_process_action requires an Action instance")

        if action.runnable:
            await self._handle_runnable_action(action, ctx)

        controller = self._context.get_controller()
        if ctx and ctx.blocked:
            controller.telemetry_service.handle_blocked_invocation(action, ctx)
            return

        if not isinstance(action, NullAction):
            await self._finalize_action(action, ctx)

    async def _handle_runnable_action(
        self, action: Action, ctx: "ToolInvocationContext | None"
    ) -> None:
        controller = self._context.get_controller()
        pipeline = getattr(controller, "tool_pipeline", None)

        if ctx and pipeline:
            await pipeline.run_verify(ctx)
            if ctx.blocked:
                return

        await self._confirmation_service.evaluate_action(action)

        self.set_pending_action(action)

    async def _finalize_action(
        self, action: Action, ctx: "ToolInvocationContext | None"
    ) -> None:
        controller = self._context.get_controller()

        await self._confirmation_service.handle_pending_confirmation(action)

        pipeline = getattr(controller, "tool_pipeline", None)
        if ctx and pipeline:
            await pipeline.run_execute(ctx)
            if ctx.blocked:
                controller.telemetry_service.handle_blocked_invocation(action, ctx)
                return

        self._observation_service.prepare_metrics_for_action(action)
        controller.event_stream.add_event(action, action.source or EventSource.AGENT)

        if ctx:
            ctx.action_id = action.id
            controller._bind_action_context(action, ctx)

        log_level = "info" if LOG_ALL_EVENTS else "debug"
        controller.log(log_level, str(action), extra={"msg_type": "ACTION"})

    def set_pending_action(self, action: Action | None) -> None:
        """Track pending action with timestamp; emit logging changes."""

        self._pending_service.set(action)

    def get_pending_action(self) -> Action | None:
        """Expose the pending action, auto-clearing when it times out."""

        return self._pending_service.get()

    def get_pending_action_info(self) -> tuple[Action, float] | None:
        return self._pending_service.info()


