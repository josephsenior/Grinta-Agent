"""Handles action retrieval and execution steps for AgentController."""

from __future__ import annotations

from typing import TYPE_CHECKING, Type

from forge.core.logger import forge_logger as logger
from forge.events import EventSource
from forge.events.observation import ErrorObservation
from forge.events.action.agent import CondensationRequestAction
from forge.core.exceptions import (
    LLMMalformedActionError,
    LLMNoActionError,
    LLMResponseError,
    LLMContextWindowExceedError,
    FunctionCallValidationError,
    FunctionCallNotExistsError,
)

try:
    import litellm
except ImportError:  # pragma: no cover - litellm should be installed in most envs
    litellm = None  # type: ignore[assignment]


def _litellm_exc(name: str) -> Type[Exception]:
    """Return litellm exception class when available, fallback to Exception."""

    if litellm and hasattr(litellm, name):
        return getattr(litellm, name)

    class _FallbackLitellmException(Exception):
        ...

    _FallbackLitellmException.__name__ = f"MissingLitellm{name}"
    return _FallbackLitellmException


APIConnectionError = _litellm_exc("APIConnectionError")
AuthenticationError = _litellm_exc("AuthenticationError")
RateLimitError = _litellm_exc("RateLimitError")
ServiceUnavailableError = _litellm_exc("ServiceUnavailableError")
APIError = _litellm_exc("APIError")
InternalServerError = _litellm_exc("InternalServerError")
Timeout = _litellm_exc("Timeout")
BadRequestError = _litellm_exc("BadRequestError")
OpenAIError = _litellm_exc("OpenAIError")
ContextWindowExceededError = _litellm_exc("ContextWindowExceededError")

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext
    from forge.events.action import Action
    from forge.controller.tool_pipeline import ToolInvocationContext


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
        if self._is_context_window_error(error_str, exc):
            raise exc
        if not controller.agent.config.enable_history_truncation:
            raise LLMContextWindowExceedError from exc
        controller.event_stream.add_event(
            CondensationRequestAction(), EventSource.AGENT
        )
        return None

    def _is_context_window_error(self, error_str: str, exc: Exception) -> bool:
        return (
            "contextwindowexceedederror" not in error_str
            and "prompt is too long" not in error_str
            and ("input length and `max_tokens` exceed context limit" not in error_str)
            and ("please reduce the length of either one" not in error_str)
            and ("the request exceeds the available context size" not in error_str)
            and ("context length exceeded" not in error_str)
            and (
                "sambanovaexception" not in error_str
                or "maximum context length" not in error_str
            )
            and (not isinstance(exc, ContextWindowExceededError))
        )


