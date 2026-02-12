"""Handles action retrieval and execution steps for AgentController."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from backend.core.logger import forge_logger as logger
from backend.events import EventSource
from backend.events.observation import ErrorObservation
from backend.events.action.agent import CondensationRequestAction
from backend.core.exceptions import (
    LLMMalformedActionError,
    LLMNoActionError,
    LLMResponseError,
    LLMContextWindowExceedError,
    FunctionCallValidationError,
    FunctionCallNotExistsError,
)

from backend.models.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    InternalServerError,
    OpenAIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    is_context_window_error,
)

if TYPE_CHECKING:
    from backend.controller.services.controller_context import ControllerContext
    from backend.events.action import Action
    from backend.controller.tool_pipeline import ToolInvocationContext


class ActionExecutionService:
    """Encapsulates action acquisition, planning, and execution orchestration."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    async def get_next_action(self) -> "Action | None":
        controller = self._context.get_controller()
        try:
            confirmation = getattr(controller, "confirmation_service", None)
            if confirmation:
                return confirmation.get_next_action()
            action = controller.agent.step(controller.state)
            action.source = EventSource.AGENT
            return action
        except (
            LLMMalformedActionError,
            LLMNoActionError,
            LLMResponseError,
            FunctionCallValidationError,
            FunctionCallNotExistsError,
        ) as exc:
            controller.event_stream.add_event(
                ErrorObservation(content=str(exc)), EventSource.AGENT
            )
            return None
        except (ContextWindowExceededError, BadRequestError, OpenAIError) as exc:
            return await self._handle_context_window_error(exc)
        except (
            APIConnectionError,
            AuthenticationError,
            RateLimitError,
            ServiceUnavailableError,
            APIError,
            InternalServerError,
            Timeout,
        ):
            raise

    async def execute_action(self, action: "Action") -> None:
        # Plugin hook: action_pre
        try:
            from backend.core.plugin import get_plugin_registry
            action = await get_plugin_registry().dispatch_action_pre(action)
        except Exception:  # noqa: BLE001 — plugins must not break the pipeline
            pass

        controller = self._context.get_controller()
        ctx: ToolInvocationContext | None = None
        pipeline = getattr(controller, "tool_pipeline", None)
        if action.runnable and pipeline:
            ctx = pipeline.create_context(action, controller.state)
            controller._register_action_context(action, ctx)
            await pipeline.run_plan(ctx)
            await controller.iteration_service.apply_dynamic_iterations(ctx)
            if ctx.blocked:
                controller.telemetry_service.handle_blocked_invocation(action, ctx)
                return
        await controller.action_service.run(action, ctx)

    async def _handle_context_window_error(self, exc: Exception) -> "Action | None":
        controller = self._context.get_controller()
        error_str = str(exc).lower()
        if not is_context_window_error(error_str, exc):
            raise exc
        if not controller.agent.config.enable_history_truncation:
            raise LLMContextWindowExceedError from exc
        controller.event_stream.add_event(
            CondensationRequestAction(), EventSource.AGENT
        )
        return None


