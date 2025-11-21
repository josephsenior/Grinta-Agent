"""Step execution and retry handling for MetaSOP."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Tuple

from .models import Artifact, OrchestrationContext, RetryPolicy, SopStep, StepResult


if TYPE_CHECKING:
    from .orchestrator import MetaSOPOrchestrator


class StepExecutionService:
    """Encapsulates MetaSOP step execution, retries, and micro-iteration logic."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # Public API ---------------------------------------------------------
    def execute_with_retries(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: dict[str, Artifact],
        role_profile: Dict[str, Any],
        retry_policy: RetryPolicy,
        max_retries: int,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
    ) -> Tuple[bool, dict[str, Artifact]]:
        """Run a step with retries."""
        retries = 0
        micro_iteration_config = self._orch._get_micro_iteration_config()

        while retries <= max_retries:
            try:
                result = self._execute_step_attempt(
                    step,
                    ctx,
                    role_profile,
                    retry_policy,
                    micro_iteration_config,
                )

                if self._orch._is_step_execution_successful(result):
                    return self._orch.retry_service.handle_success(
                        step, result, done, retries
                    )
                return self._orch.retry_service.handle_failure(
                    step, result, retries, max_retries
                )
            except Exception as exc:  # pragma: no cover - orchestrator handles logging
                return self._orch.retry_service.handle_exception(
                    step, exc, retries, max_retries
                )

        return False, {}

    # Internal helpers ---------------------------------------------------
    def _execute_step_attempt(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile: Dict[str, Any],
        retry_policy: RetryPolicy,
        config: dict,
    ) -> StepResult:
        if config["candidate_count"] > 1 and (
            config["speculative_enabled"] or config["patch_scoring_enabled"]
        ):
            return self._orch.candidate_service.generate_and_select(
                step,
                ctx,
                role_profile,
                retry_policy,
                config["candidate_count"],
            )
        return self._orch._attempt_execute_with_retry(
            step,
            ctx,
            role_profile,
            retry_policy,
        )



