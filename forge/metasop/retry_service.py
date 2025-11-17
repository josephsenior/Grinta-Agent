"""Retry and execution result handling for MetaSOP."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

from .models import Artifact, SopStep, StepResult
from .core.artifacts import (
    verify_expected_outcome_if_specified,
    extract_qa_outputs,
)

if TYPE_CHECKING:
    from .orchestrator import MetaSOPOrchestrator


class StepRetryService:
    """Encapsulates success/failure bookkeeping and backoff handling."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    def handle_success(
        self,
        step: SopStep,
        result: StepResult,
        done: dict[str, Artifact],
        retries: int,
    ) -> Tuple[bool, dict[str, Artifact]]:
        artifact = result.artifact
        if artifact is None:
            return False, {}

        self._orch._ensure_artifact_provenance(artifact, step)
        done[step.id] = artifact

        execution_time = getattr(result, "execution_time", 0.0)
        token_cost = getattr(result, "token_cost", 0.0)
        self._orch._track_prompt_performance(step, result, execution_time, token_cost)

        status = self._orch.budget_monitor.record_step_result(step, result)
        self._orch._handle_budget_status(status, step)

        art_hash = self._orch._compute_artifact_hash(artifact)
        setattr(
            self._orch,
            "_previous_step_hash",
            self._orch._compute_step_hash(art_hash, None),
        )

        self._orch._ingest_artifact_to_memory(step, artifact)

        verification = verify_expected_outcome_if_specified(step, artifact)
        self._orch.event_service.emit_success(step, retries, verification)
        self._orch._reflect_and_update_ace(step, result, artifact, verification)
        self._orch.optional_engines.collect_execution_feedback(
            step,
            result.ok,
            {step.id: artifact},
            list(self._orch.active_steps.values()),
        )

        return True, {step.id: artifact}

    def handle_failure(
        self,
        step: SopStep,
        result: StepResult,
        retries: int,
        max_retries: int,
    ) -> Tuple[bool, dict[str, Artifact]]:
        failure_handler = self._orch._get_failure_handler()
        failure_analysis = failure_handler.analyze_step_failure(result, step, retries)

        execution_time = getattr(result, "execution_time", 0.0)
        token_cost = getattr(result, "token_cost", 0.0)
        self._orch._track_prompt_performance(step, result, execution_time, token_cost)

        status = self._orch.budget_monitor.record_step_result(step, result)
        self._orch._handle_budget_status(status, step)

        retry_count = retries + 1
        if retry_count <= max_retries:
            failure_handler.emit_retry_event(step, retry_count, failure_analysis)
        else:
            failure_handler.emit_final_failure_event(step, retry_count, failure_analysis)

        self._orch.event_service.emit_failure(
            step,
            retries,
            result,
            error=None,
        )

        return False, {}

    def handle_exception(
        self,
        step: SopStep,
        exception: Exception,
        retries: int,
        max_retries: int,
    ) -> Tuple[bool, dict[str, Artifact]]:
        retry_count = retries + 1
        self._orch.event_service.emit_failure(
            step,
            retry_count,
            StepResult(ok=False, error=str(exception)),
            error=exception,
        )
        if retry_count > max_retries:
            return False, {}
        return False, {}

