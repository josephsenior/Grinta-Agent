from __future__ import annotations

import copy
import os
from typing import TYPE_CHECKING

from forge.events import EventSource
from forge.events.observation import Observation
from forge.events.serialization.event import truncate_content
from forge.core.schemas import AgentState
from forge.llm.metrics import Metrics

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext
    from forge.controller.services.action_service import ActionService
    from forge.controller.tool_pipeline import ToolInvocationContext
    from forge.events.action import Action


class ObservationService:
    """Handles observation logging, metrics preparation, and pending-action observation flow."""

    def __init__(
        self,
        context: "ControllerContext",
        action_service: "ActionService | None" = None,
    ) -> None:
        self._context = context
        self._action_service = action_service

    def set_action_service(self, action_service: "ActionService") -> None:
        self._action_service = action_service

    async def handle_observation(self, observation: Observation) -> None:
        controller = self._context.get_controller()
        observation_to_print = self._prepare_observation_for_logging(observation)
        log_level = self._get_log_level()
        controller.log(
            log_level, str(observation_to_print), extra={"msg_type": "OBSERVATION"}
        )
        await self._handle_pending_action_observation(observation)

    def prepare_metrics_for_action(self, action: "Action") -> None:
        controller = self._context.get_controller()
        metrics = controller.conversation_stats.get_combined_metrics()

        clean_metrics = Metrics()
        clean_metrics.accumulated_cost = metrics.accumulated_cost
        clean_metrics._accumulated_token_usage = copy.deepcopy(
            metrics.accumulated_token_usage
        )
        if controller.state.budget_flag:
            clean_metrics.max_budget_per_task = controller.state.budget_flag.max_value
        action.llm_metrics = clean_metrics
        latest_usage = None
        if controller.state.metrics.token_usages:
            latest_usage = controller.state.metrics.token_usages[-1]
        accumulated_usage = controller.state.metrics.accumulated_token_usage
        controller.log(
            "debug",
            f"Action metrics - accumulated_cost: {metrics.accumulated_cost}, max_budget: {metrics.max_budget_per_task}, latest tokens (prompt/completion/cache_read/cache_write): {latest_usage.prompt_tokens if latest_usage else 0}/{latest_usage.completion_tokens if latest_usage else 0}/{latest_usage.cache_read_tokens if latest_usage else 0}/{latest_usage.cache_write_tokens if latest_usage else 0}, accumulated tokens (prompt/completion): {accumulated_usage.prompt_tokens}/{accumulated_usage.completion_tokens}",
            extra={"msg_type": "METRICS"},
        )

    async def _handle_pending_action_observation(
        self, observation: Observation
    ) -> None:
        action_service = self._require_action_service()
        pending_action = action_service.get_pending_action()
        if not (pending_action and pending_action.id == observation.cause):
            return

        controller = self._context.get_controller()
        if controller.state.agent_state == AgentState.AWAITING_USER_CONFIRMATION:
            return

        ctx: "ToolInvocationContext | None" = None
        if observation.cause is not None:
            ctx = self._context.pop_action_context(observation.cause)

        action_service.set_pending_action(None)

        # Delegate confirmation state transitions to confirmation service
        confirmation_service = getattr(controller, "confirmation_service", None)
        if confirmation_service:
            await confirmation_service.handle_observation_for_pending_action(
                observation, ctx
            )
        else:
            # Fallback for backward compatibility
            if controller.state.agent_state == AgentState.USER_CONFIRMED:
                await controller.set_agent_state_to(AgentState.RUNNING)
            elif controller.state.agent_state == AgentState.USER_REJECTED:
                await controller.set_agent_state_to(AgentState.AWAITING_USER_INPUT)

            pipeline = getattr(controller, "tool_pipeline", None)
            if ctx and pipeline:
                await pipeline.run_observe(ctx, observation)
                controller._cleanup_action_context(ctx)

    def _prepare_observation_for_logging(
        self, observation: Observation
    ) -> Observation:
        controller = self._context.get_controller()
        observation_to_print = copy.deepcopy(observation)
        max_chars = controller.agent.llm.config.max_message_chars
        if len(observation_to_print.content) > max_chars:
            observation_to_print.content = truncate_content(
                observation_to_print.content, max_chars
            )
        return observation_to_print

    def _get_log_level(self) -> str:
        return "info" if os.getenv("LOG_ALL_EVENTS") in ("true", "1") else "debug"

    def _require_action_service(self) -> "ActionService":
        if not self._action_service:
            raise RuntimeError("ActionService not bound to ObservationService")
        return self._action_service


