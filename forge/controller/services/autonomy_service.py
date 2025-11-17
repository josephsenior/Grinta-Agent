from __future__ import annotations

from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.agent_controller import AgentController


class AutonomyService:
    """Encapsulates autonomy, safety, and validation setup for an agent."""

    def __init__(self, controller: "AgentController") -> None:
        self._controller = controller

    def initialize(self, agent: "Agent") -> None:
        """Configure autonomy controller and related validators."""

        from forge.controller.autonomy import AutonomyController
        from forge.core.config.agent_config import AgentConfig as _AgentConfig

        controller = self._controller
        agent_config = getattr(agent, "config", None)

        controller.circuit_breaker_service.reset()

        if agent_config is None or not isinstance(agent_config, _AgentConfig):
            controller.autonomy_controller = None
            controller.safety_validator = None
            controller.task_validator = None
            controller.PENDING_ACTION_TIMEOUT = 120.0
            controller.retry_service.reset_retry_metrics()
            return

        controller.autonomy_controller = AutonomyController(agent_config)
        controller.retry_service.reset_retry_metrics()

        self._initialize_safety_validator(agent)
        self._initialize_task_validator(agent)
        controller.circuit_breaker_service.configure(agent_config)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _initialize_safety_validator(self, agent: "Agent") -> None:
        controller = self._controller
        controller.safety_validator = None

        if (
            hasattr(agent.config, "safety")
            and agent.config.safety.enable_mandatory_validation
        ):
            from forge.controller.safety_validator import SafetyValidator

            controller.safety_validator = SafetyValidator(agent.config.safety)
            logger.info("SafetyValidator enabled for production safety")

    def _initialize_task_validator(self, agent: "Agent") -> None:
        controller = self._controller
        controller.task_validator = None

        if (
            hasattr(agent.config, "enable_completion_validation")
            and agent.config.enable_completion_validation
        ):
            from forge.validation.task_validator import (
                CompositeValidator,
                GitDiffValidator,
                TestPassingValidator,
            )

            validators = [TestPassingValidator(), GitDiffValidator()]
            controller.task_validator = CompositeValidator(
                validators=validators,
                min_confidence=0.7,
                require_all_pass=False,
            )
            logger.info("TaskValidator enabled for completion checking")

        controller.PENDING_ACTION_TIMEOUT = 120.0
        controller._add_system_message()

