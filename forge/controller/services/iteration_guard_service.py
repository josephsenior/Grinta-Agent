"""Iteration and graceful shutdown guardrails for AgentController."""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger
from forge.events import EventSource
from forge.events.action import AgentFinishAction, MessageAction
from forge.core.schemas import AgentState

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext


class IterationGuardService:
    """Handles control flag execution, graceful shutdown, and forced completion."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    async def run_control_flags(self) -> None:
        """Run controller control flags with limit/error handling."""
        controller = self._context.get_controller()
        try:
            logger.debug(
                "AGENT_CTRL: before run_control_flags, iteration=%s",
                controller.state.iteration_flag.current_value,
            )
            controller.state_tracker.run_control_flags()
            logger.debug(
                "AGENT_CTRL: after run_control_flags, iteration=%s",
                controller.state.iteration_flag.current_value,
            )
        except Exception as exc:
            error_str = str(exc).lower()
            if self._is_limit_error(error_str):
                logger.warning("Control flag limit hit: %s", type(exc).__name__)
                if self._graceful_shutdown_enabled():
                    self._schedule_graceful_shutdown(reason=str(exc))
            else:
                logger.warning("Control flag error (non-limit)")
            raise

    def _is_limit_error(self, error_str: str) -> bool:
        return any(
            key in error_str
            for key in ("limit", "maximum", "budget", "iteration")
        )

    def _graceful_shutdown_enabled(self) -> bool:
        graceful_env = os.getenv("FORGE_GRACEFUL_SHUTDOWN", "0").strip().lower()
        return graceful_env in ("1", "true", "yes")

    def _schedule_graceful_shutdown(self, reason: str) -> None:
        asyncio.create_task(self._graceful_shutdown(reason=reason))

    async def _graceful_shutdown(self, reason: str) -> None:
        """Give agent one final turn to save work and summarize progress."""
        controller = self._context.get_controller()

        logger.info("Initiating graceful shutdown: %s", reason)
        if not hasattr(controller.state, "graceful_shutdown_mode"):
            setattr(controller.state, "graceful_shutdown_mode", True)

        summary_msg = MessageAction(
            content=(
                f"SYSTEM NOTICE: {reason}\n\n"
                f"You have ONE FINAL TURN to:\n"
                "1. Save all important work and progress\n"
                "2. Create a summary of what you accomplished\n"
                "3. List any remaining work or next steps\n"
                "4. Use the finish tool with your final summary\n\n"
                "Please be concise and focus on preserving critical information."
            ),
        )
        summary_msg.source = EventSource.ENVIRONMENT
        controller.event_stream.add_event(summary_msg, EventSource.ENVIRONMENT)

        original_max = None
        try:
            iteration_flag = getattr(controller.state, "iteration_flag", None)
            if iteration_flag and hasattr(iteration_flag, "current_value"):
                original_max = getattr(iteration_flag, "max_value", None)
                iteration_flag.max_value = iteration_flag.current_value + 1

            await controller._step()
            await asyncio.sleep(2)

            if iteration_flag and original_max is not None:
                iteration_flag.max_value = original_max
        except Exception as exc:  # pragma: no cover - defensive log
            logger.error("Error during graceful shutdown step: %s", exc)

        if controller.state.agent_state not in (AgentState.FINISHED, AgentState.ERROR):
            await self._force_partial_completion(reason)

    async def _force_partial_completion(self, reason: str) -> None:
        """Force partial completion when agent doesn't finish gracefully."""
        controller = self._context.get_controller()

        logger.info("Forcing partial completion: %s", reason)
        finish_action = AgentFinishAction(
            outputs={
                "status": "partial",
                "reason": reason,
                "message": (
                    "Task partially completed. Stopped due to: "
                    f"{reason}\n\nProgress: "
                    f"{controller.state.iteration_flag.current_value} iterations "
                    "completed.\nPlease review the conversation history for "
                    "completed work."
                ),
            },
            final_thought=f"Task stopped: {reason}",
            force_finish=True,
        )
        finish_action.force_finish = True
        await controller._handle_finish_action(finish_action)


