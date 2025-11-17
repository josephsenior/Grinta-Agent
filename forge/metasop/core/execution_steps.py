from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional, Tuple

from forge.core.pydantic_compat import model_dump_with_options
from forge.metasop import patch_scoring
from forge.metasop.diff_utils import compute_diff_fingerprint
from forge.metasop.models import Artifact, OrchestrationContext, RetryPolicy, SopStep, StepResult
from forge.metasop.core.artifacts import (
    build_qa_verification,
    extract_qa_outputs,
    verify_expected_outcome_if_specified,
)
from forge.metasop.validators import validate_json
from forge.metasop.registry import load_schema
from forge.structural import available as structural_available

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class StepExecutionManager:
    """Encapsulates step execution flow for the MetaSOP orchestrator."""

    def __init__(self, orchestrator: MetaSOPOrchestrator) -> None:
        self._orch = orchestrator
        self._memory = getattr(orchestrator, "memory_cache")
        self._optional = getattr(orchestrator, "optional_engines")
        self._profiles = getattr(orchestrator, "profile_manager")
        self._log_step_entry = getattr(orchestrator, "_log_step_entry")
        self._check_capability_matrix = getattr(
            orchestrator, "_check_capability_matrix"
        )
        self._check_dependencies_and_conditions = getattr(
            orchestrator, "_check_dependencies_and_conditions"
        )
        self._emit_event = getattr(orchestrator, "_emit_event")
        self._add_active_step = getattr(orchestrator, "_add_active_step")
        self._remove_active_step = getattr(orchestrator, "_remove_active_step")
        self._track_prompt_performance = getattr(
            orchestrator, "_track_prompt_performance"
        )
        self._apply_prompt_optimization = getattr(
            orchestrator, "_apply_prompt_optimization"
        )
        self._get_failure_handler = getattr(orchestrator, "_get_failure_handler")
        self._reflect_and_update_ace = getattr(
            orchestrator, "_reflect_and_update_ace"
        )

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - simple delegator
        return getattr(self._orch, name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def execute_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        """Execute a single orchestration step synchronously."""
        self._log_step_entry(step)

        if not self._check_capability_matrix(step, done):
            return True, {}

        if not self._check_dependencies_and_conditions(step, done):
            return True, {}

        self._memory.perform_memory_retrieval(step, ctx)

        role_profile = self._profiles.resolve_role_profile(step)
        if role_profile is None:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "no_role_profile",
                }
            )
            return True, {}

        self._add_active_step(step)
        success = False
        artifacts: Dict[str, Artifact] = {}
        try:
            success, artifacts = self._execute_step_with_retry(
                step,
                ctx,
                done,
                role_profile,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )
            active_steps_at_execution = list(self._orch.active_steps.values())
            self._optional.collect_execution_feedback(
                step, success, artifacts, active_steps_at_execution
            )
            return success, artifacts
        finally:
            self._remove_active_step(step.id, success=success)

    async def execute_step_async(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        """Execute a single orchestration step asynchronously."""
        self._log_step_entry(step)

        if not self._check_capability_matrix(step, done):
            return True, {}

        if not self._check_dependencies_and_conditions(step, done):
            return True, {}

        self._memory.perform_memory_retrieval(step, ctx)

        role_profile = self._profiles.resolve_role_profile(step)
        if role_profile is None:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "no_role_profile",
                }
            )
            return True, {}

        self._add_active_step(step)
        success = False
        artifacts: Dict[str, Artifact] = {}
        try:
            success, artifacts = await self._execute_step_with_retry_async(
                step,
                ctx,
                done,
                role_profile,
                soft_budget,
                hard_budget,
                consumed_tokens,
                taxonomy_enabled,
                retry_policy,
                max_retries,
            )
            active_steps_at_execution = list(self._orch.active_steps.values())
            self._optional.collect_execution_feedback(
                step, success, artifacts, active_steps_at_execution
            )
            return success, artifacts
        finally:
            self._remove_active_step(step.id, success=success)

    # ------------------------------------------------------------------
    # Internal execution helpers
    # ------------------------------------------------------------------
    async def _execute_step_with_retry_async(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        role_profile,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._execute_step_with_retry,
            step,
            ctx,
            done,
            role_profile,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
            retry_policy,
            max_retries,
        )

    def _execute_step_with_retry(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        role_profile,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
        retry_policy: RetryPolicy,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        pre_context_hash = self._memory.compute_pre_context_hash(step, ctx, done)
        cached_result = self._memory.check_step_cache(step, pre_context_hash)
        if cached_result is not None:
            return True, cached_result

        if step.role.strip().lower() == "qa":
            return self._handle_qa_step(step, ctx, done, pre_context_hash)

        success, artifacts = self._execute_step_with_retries(
            step,
            ctx,
            done,
            role_profile,
            retry_policy,
            max_retries,
            soft_budget,
            hard_budget,
            consumed_tokens,
            taxonomy_enabled,
        )

        if success and artifacts and pre_context_hash:
            self._memory.store_step_in_cache(step, artifacts, pre_context_hash)

        return success, artifacts

    def _store_step_in_cache(
        self, step: SopStep, artifacts: Dict[str, Artifact], pre_context_hash: str
    ) -> None:
        self._memory.store_step_in_cache(step, artifacts, pre_context_hash)

    def _handle_qa_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        pre_context_hash: Optional[str],
    ) -> Tuple[bool, Dict[str, Artifact]]:
        if pre_context_hash:
            cached = self._memory.check_step_cache(step, pre_context_hash)
            if cached is not None:
                done.update(cached)
                return True, cached

        return self._execute_qa_step(step, ctx, done)

    def _execute_qa_step(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
    ) -> Tuple[bool, Dict[str, Artifact]]:
        try:
            selected_tests, _selection_reason = self._perform_selective_tests(step, ctx)
            qa_artifact = self._orch.qa_executor.run_qa(
                step,
                ctx,
                getattr(ctx, "repo_root", None),
                selected_tests=selected_tests,
            )

            if self._is_qa_timed_out(qa_artifact):
                self._emit_qa_timeout_event(step)
                return False, {}

            validation_result = self._validate_qa_artifact(step, qa_artifact)
            if validation_result["success"]:
                return self._handle_successful_qa_execution(
                    step, qa_artifact, done, validation_result["data"]
                )
            return self._handle_failed_qa_execution(
                step, qa_artifact, validation_result["error"]
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "error",
                    "reason": "qa_execution_failed",
                    "error": str(exc)[:300],
                }
            )
            return False, {}

    @staticmethod
    def _is_qa_timed_out(qa_artifact: Artifact) -> bool:
        return bool(
            isinstance(qa_artifact.content, dict) and qa_artifact.content.get("timeout")
        )

    def _emit_qa_timeout_event(self, step: SopStep) -> None:
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "timeout",
                "reason": "qa_step_timeout",
            }
        )

    def _validate_qa_artifact(
        self, step: SopStep, qa_artifact: Artifact
    ) -> Dict[str, Any]:
        schema_file = getattr(getattr(step, "outputs", None), "schema_file", None)
        schema = load_schema(schema_file) if schema_file else {}
        payload = json.dumps(qa_artifact.content)
        ok, data, err = validate_json(payload, schema)
        return {"success": ok and data is not None, "data": data, "error": err}

    def _handle_successful_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        done: Dict[str, Artifact],
        data,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        qa_artifact.content = data
        done[step.id] = qa_artifact
        self._memory.ingest_artifact_to_memory(step, qa_artifact)
        self._emit_qa_success_event(step, qa_artifact)
        return True, {step.id: qa_artifact}

    def _emit_qa_success_event(self, step: SopStep, qa_artifact: Artifact) -> None:
        event_data: Dict[str, Any] = {
            "step_id": step.id,
            "role": step.role,
            "status": "executed",
            "retries": 0,
            "duration_ms": 0,
            "verification_result": build_qa_verification(qa_artifact.content),
        }
        if isinstance(qa_artifact.content, dict):
            coverage = qa_artifact.content.get("coverage", {})
            if coverage:
                event_data["coverage_overall"] = coverage.get("overall_percent")
            if qa_artifact.content.get("coverage_delta"):
                event_data["coverage_delta_files"] = qa_artifact.content.get(
                    "coverage_delta"
                )
        self._emit_event(event_data)

    def _handle_failed_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        error: str,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        stdout, stderr = extract_qa_outputs(qa_artifact)
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "failed",
                "reason": "qa_validation_failed",
                "error": error or "Unknown validation error",
                "stdout": stdout[:500],
                "stderr": stderr[:500],
            }
        )
        return False, {}

    def _execute_step_with_retries(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        done: Dict[str, Artifact],
        role_profile,
        retry_policy: RetryPolicy,
        max_retries: int,
        soft_budget: int,
        hard_budget: int,
        consumed_tokens: int,
        taxonomy_enabled: bool,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        retries = 0
        micro_iteration_config = self._get_micro_iteration_config()

        while retries <= max_retries:
            try:
                result = self._execute_step_attempt(
                    step, ctx, role_profile, retry_policy, micro_iteration_config
                )
                if self._is_step_execution_successful(result):
                    return self._handle_successful_execution(step, result, done, retries)
                return self._handle_failed_execution(step, result, retries, max_retries)
            except Exception as exc:
                return self._handle_execution_exception(step, exc, retries, max_retries)

        return False, {}

    def _get_micro_iteration_config(self) -> Dict[str, Any]:
        settings = self._orch.settings
        return {
            "candidate_count": getattr(settings, "micro_iteration_candidate_count", 1)
            or 1,
            "speculative_enabled": getattr(
                settings, "speculative_execution_enable", False
            ),
            "patch_scoring_enabled": getattr(settings, "patch_scoring_enable", False),
        }

    def _execute_step_attempt(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: RetryPolicy,
        config: Dict[str, Any],
    ) -> StepResult:
        if config["candidate_count"] > 1 and (
            config["speculative_enabled"] or config["patch_scoring_enabled"]
        ):
            return self._execute_with_micro_iterations(
                step, ctx, role_profile, retry_policy, config["candidate_count"]
            )
        return self._attempt_execute_with_retry(step, ctx, role_profile, retry_policy)

    @staticmethod
    def _is_step_execution_successful(result: StepResult) -> bool:
        return bool(result and result.ok and result.artifact is not None)

    def _handle_successful_execution(
        self,
        step: SopStep,
        result: StepResult,
        done: Dict[str, Artifact],
        retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        artifact = result.artifact
        if artifact is None:
            return False, {}

        self._memory.ensure_artifact_provenance(artifact, step)
        done[step.id] = artifact

        execution_time = getattr(result, "execution_time", 0.0)
        token_cost = getattr(result, "token_cost", 0.0)
        self._track_prompt_performance(step, result, execution_time, token_cost)

        art_hash = self._memory.compute_artifact_hash(artifact)
        setattr(
            self._orch,
            "_previous_step_hash",
            self._memory.compute_step_hash(art_hash, None),
        )

        self._memory.ingest_artifact_to_memory(step, artifact)
        verification = verify_expected_outcome_if_specified(step, artifact)
        self._emit_success_event(step, retries, verification)
        self._reflect_and_update_ace(step, result, artifact, verification)

        return True, {step.id: artifact}

    def _emit_success_event(
        self, step: SopStep, retries: int, verification: Optional[Dict[str, Any]]
    ) -> None:
        event_data: Dict[str, Any] = {
            "step_id": step.id,
            "role": step.role,
            "status": "executed",
            "retries": retries,
            "duration_ms": 0,
        }
        if verification:
            event_data["verification"] = verification
        self._emit_event(event_data)

    def _handle_failed_execution(
        self,
        step: SopStep,
        result: StepResult,
        retries: int,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        failure_handler = self._get_failure_handler()
        failure_analysis = failure_handler.analyze_step_failure(result, step, retries)
        retries += 1

        execution_time = getattr(result, "execution_time", 0.0)
        token_cost = getattr(result, "token_cost", 0.0)
        self._track_prompt_performance(step, result, execution_time, token_cost)

        if retries <= max_retries:
            failure_handler.emit_retry_event(step, retries, failure_analysis)
        else:
            failure_handler.emit_final_failure_event(step, retries, failure_analysis)
            return False, {}
        return False, {}

    def _handle_execution_exception(
        self,
        step: SopStep,
        exception: Exception,
        retries: int,
        max_retries: int,
    ) -> Tuple[bool, Dict[str, Artifact]]:
        retries += 1
        if retries <= max_retries:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "retry",
                    "retries": retries,
                    "reason": "step_execution_exception",
                    "error": str(exception)[:300],
                }
            )
        else:
            self._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "failed",
                    "retries": retries,
                    "reason": "max_retries_exceeded",
                    "error": str(exception)[:300],
                }
            )
            return False, {}
        return False, {}

    def _execute_with_micro_iterations(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: RetryPolicy,
        candidate_count: int,
    ) -> StepResult:
        try:
            candidates = self._generate_candidates(step, ctx, role_profile, candidate_count)
            if not candidates:
                return StepResult(ok=False, error="no_valid_candidates")

            if getattr(self._orch.settings, "patch_scoring_enable", False):
                best_candidate = self._select_best_candidate_with_scoring(candidates, step)
                if best_candidate:
                    return best_candidate

            return self._create_step_result_from_candidate(candidates[0], step)
        except Exception as exc:  # pragma: no cover - defensive
            return StepResult(ok=False, error=f"micro_iteration_error: {exc!s}")

    def _generate_candidates(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        candidate_count: int,
    ) -> list:
        candidates = []
        for _ in range(candidate_count):
            try:
                if self._orch.llm_registry and not hasattr(ctx, "llm_registry"):
                    ctx.llm_registry = self._orch.llm_registry
                candidate = self._orch.step_executor.execute(
                    step,
                    ctx,
                    model_dump_with_options(role_profile),
                    config=self._orch.config,
                )
                if candidate and candidate.ok and candidate.artifact:
                    patch_candidate = self._create_patch_candidate(candidate.artifact, step)
                    candidates.append(patch_candidate)
            except (RuntimeError, ValueError, TypeError, AttributeError):
                continue
        return candidates

    def _select_best_candidate_with_scoring(
        self, candidates: list, step: SopStep
    ) -> Optional[StepResult]:
        try:
            scores = patch_scoring.score_candidates(candidates, self._orch.settings)
            if not scores:
                return None
            best_idx = max(range(len(scores)), key=lambda idx: scores[idx].composite)
            best_candidate = candidates[best_idx]
            return self._create_step_result_from_candidate(best_candidate, step)
        except (TypeError, ValueError, AttributeError, RuntimeError):
            return None

    def _create_step_result_from_candidate(self, candidate, step: SopStep) -> StepResult:
        artifact = Artifact(step_id=step.id, role=step.role, content=candidate.content)
        return StepResult(ok=True, artifact=artifact)

    def _create_patch_candidate(self, artifact: Artifact, step: SopStep):
        try:
            content = artifact.content
            diff = self._extract_diff_from_artifact(artifact, content)
            meta = self._build_patch_candidate_metadata(artifact, diff)
            return patch_scoring.PatchCandidate(
                content=str(content) if content else "",
                diff=diff,
                meta=meta,
            )
        except (TypeError, ValueError, AttributeError) as exc:
            return self._create_error_patch_candidate(artifact, exc)

    @staticmethod
    def _extract_diff_from_artifact(artifact: Artifact, content: Any) -> str:
        if isinstance(content, dict) and "diff" in content:
            return content["diff"]
        if hasattr(artifact, "diff"):
            return artifact.diff
        return ""

    @staticmethod
    def _build_patch_candidate_metadata(artifact: Artifact, diff: str) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if structural_available() and diff:
            try:
                meta["diff_fingerprint"] = compute_diff_fingerprint(diff)
            except (TypeError, ValueError, AttributeError):
                pass
        if hasattr(artifact, "provenance"):
            meta["provenance"] = artifact.provenance
        return meta

    @staticmethod
    def _create_error_patch_candidate(artifact: Artifact, error: Exception):
        return patch_scoring.PatchCandidate(
            content=str(artifact.content) if artifact.content else "",
            diff="",
            meta={"error": str(error)},
        )

    # ------------------------------------------------------------------
    # Retry helpers
    # ------------------------------------------------------------------
    def _should_retry_step(
        self,
        step: SopStep,
        error: str,
        retries: int,
        max_retries: int,
        retry_policy: RetryPolicy,
    ) -> bool:
        if retries >= max_retries:
            return False
        if hasattr(retry_policy, "should_retry"):
            return retry_policy.should_retry(error, retries)
        return retries < max_retries

    @staticmethod
    def _get_retry_delay(retries: int, retry_policy: RetryPolicy) -> float:
        if hasattr(retry_policy, "get_delay"):
            return retry_policy.get_delay(retries)
        return min(2**retries, 60)

    def _attempt_execute_with_retry(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile,
        retry_policy: Optional[RetryPolicy],
    ) -> StepResult:
        attempts = self._get_max_attempts(retry_policy)
        result = StepResult(ok=False, artifact=None)
        for attempt in range(attempts):
            self._log_execution_attempt(step, attempt, attempts)
            result = self._execute_single_attempt(step, ctx, role_profile)
            if self._is_execution_successful(result, step, ctx, attempt):
                return result
            if not self._handle_retry_backoff(step, attempt, attempts, retry_policy):
                break
        return result

    @staticmethod
    def _get_max_attempts(retry_policy: Optional[RetryPolicy]) -> int:
        if retry_policy and getattr(retry_policy, "max_attempts", None):
            return retry_policy.max_attempts
        return 1

    def _log_execution_attempt(self, step: SopStep, attempt: int, attempts: int) -> None:
        message = (
            "metasop: executing step_id=%s role=%s attempt=%s of %s"
            % (step.id, step.role, attempt, attempts)
        )
        try:
            self._orch._logger.info(message)
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(message)

    def _execute_single_attempt(
        self, step: SopStep, ctx: OrchestrationContext, role_profile
    ) -> StepResult:
        try:
            if self._orch.llm_registry and not hasattr(ctx, "llm_registry"):
                ctx.llm_registry = self._orch.llm_registry
            optimized_role_profile = self._apply_prompt_optimization(
                step,
                role_profile,
            )
            return self._orch.step_executor.execute(
                step,
                ctx,
                model_dump_with_options(optimized_role_profile),
                config=self._orch.config,
            )
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            return StepResult(ok=False, artifact=None, error=str(exc))

    def _is_execution_successful(
        self,
        result: StepResult,
        step: SopStep,
        ctx: OrchestrationContext,
        attempt: int,
    ) -> bool:
        if getattr(result, "ok", False) and getattr(result, "artifact", None):
            self._record_successful_attempt(step, ctx, attempt)
            return True
        return False

    @staticmethod
    def _record_successful_attempt(
        step: SopStep, ctx: OrchestrationContext, attempt: int
    ) -> None:
        with contextlib.suppress(AttributeError, TypeError):
            ctx.extra[f"successful_attempt::{step.id}"] = attempt

    def _handle_retry_backoff(
        self,
        step: SopStep,
        attempt: int,
        attempts: int,
        retry_policy: Optional[RetryPolicy],
    ) -> bool:
        if attempt >= (attempts - 1):
            return False
        delay = self._compute_retry_delay(retry_policy, attempt)
        self._log_retry_attempt(step, attempt, delay)
        if delay > 0:
            time.sleep(delay)
        return True

    @staticmethod
    def _compute_retry_delay(
        retry_policy: Optional[RetryPolicy], attempt: int
    ) -> float:
        try:
            return retry_policy.compute_sleep(attempt) if retry_policy else 0
        except (AttributeError, TypeError, ValueError):
            return 0

    def _log_retry_attempt(self, step: SopStep, attempt: int, delay: float) -> None:
        message = (
            "metasop: retrying step_id=%s after failure attempt=%s delay=%s"
            % (step.id, attempt, delay)
        )
        try:
            self._orch._logger.info(message)
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(message)

    def _perform_selective_tests(
        self, step: SopStep, ctx: OrchestrationContext
    ) -> Tuple[Optional[list[str]], Optional[str]]:
        return self._memory.perform_selective_tests(step, ctx)
