"""QA step handling for MetaSOP orchestration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Dict, Tuple

from .models import Artifact, RetryPolicy, SopStep
from .validators import validate_json
from .core.artifacts import extract_qa_outputs, build_qa_verification

if TYPE_CHECKING:
    from .orchestrator import MetaSOPOrchestrator


class QAStepService:
    """Encapsulates QA-specific execution, caching, and telemetry."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    def run(
        self,
        step: SopStep,
        ctx,
        done: dict[str, Artifact],
        pre_context_hash: str | None,
    ) -> Tuple[bool, dict[str, Artifact]]:
        """Main entrypoint for QA roles."""
        cache_hit = self._check_cache(step, done, pre_context_hash)
        if cache_hit is not None:
            return True, cache_hit
        return self._execute_qa_step(step, ctx, done)

    # ------------------------------------------------------------------ #
    # Cache handling
    # ------------------------------------------------------------------ #
    def _check_cache(
        self, step: SopStep, done: dict[str, Artifact], pre_context_hash: str | None
    ) -> dict[str, Artifact] | None:
        cache = self._orch.step_cache
        if not (cache and pre_context_hash):
            return None
        qa_hit = cache.get(pre_context_hash, step.role)
        if not qa_hit:
            return None
        cached_artifact = Artifact(
            step_id=step.id,
            role=step.role,
            content=qa_hit.artifact_content,
        )
        done[step.id] = cached_artifact
        next_hash = qa_hit.step_hash or getattr(self._orch, "_previous_step_hash", None)
        setattr(self._orch, "_previous_step_hash", next_hash)
        self._orch.event_service.emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "executed_cached",
                "duration_ms": 0,
                "retries": 0,
            }
        )
        return {step.id: cached_artifact}

    # ------------------------------------------------------------------ #
    # Execution path
    # ------------------------------------------------------------------ #
    def _execute_qa_step(
        self,
        step: SopStep,
        ctx,
        done: dict[str, Artifact],
    ) -> Tuple[bool, dict[str, Artifact]]:
        qa_result = self._orch.step_executor.execute(step, ctx, self._orch.config)
        if not qa_result or not qa_result.artifact:
            return False, {}

        qa_artifact = qa_result.artifact
        if self._is_qa_timed_out(qa_artifact):
            self._emit_qa_timeout_event(step)
            return False, {}

        validation = self._validate_qa_artifact(step, qa_artifact)
        if validation["success"]:
            return self._handle_successful_qa_execution(
                step, qa_artifact, done, validation["data"]
            )
        return self._handle_failed_qa_execution(step, qa_artifact, validation["error"])

    def _is_qa_timed_out(self, qa_artifact: Artifact) -> bool:
        return (
            isinstance(qa_artifact.content, dict)
            and qa_artifact.content.get("timeout") is True
        )

    def _validate_qa_artifact(
        self, step: SopStep, qa_artifact: Artifact
    ) -> Dict[str, Any]:
        schema_file = getattr(getattr(step, "outputs", None), "schema_file", None)
        schema = self._orch.template_toolkit.load_schema(schema_file) if schema_file else {}
        payload = json.dumps(qa_artifact.content)
        ok, data, err = validate_json(payload, schema)
        return {"success": ok and data is not None, "data": data, "error": err}

    def _handle_successful_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        done: dict[str, Artifact],
        data,
    ) -> Tuple[bool, dict[str, Artifact]]:
        qa_artifact.content = data
        done[step.id] = qa_artifact
        self._orch._ingest_artifact_to_memory(step, qa_artifact)
        self._emit_qa_success_event(step, qa_artifact)
        return True, {step.id: qa_artifact}

    def _handle_failed_qa_execution(
        self,
        step: SopStep,
        qa_artifact: Artifact,
        error: str | None,
    ) -> Tuple[bool, dict[str, Artifact]]:
        stdout, stderr = extract_qa_outputs(qa_artifact)
        self._orch.event_service.emit_event(
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

    # ------------------------------------------------------------------ #
    # Telemetry helpers
    # ------------------------------------------------------------------ #
    def _emit_qa_timeout_event(self, step: SopStep) -> None:
        self._orch.event_service.emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "timeout",
                "reason": "qa_step_timeout",
            }
        )

    def _emit_qa_success_event(self, step: SopStep, qa_artifact: Artifact) -> None:
        event_data = {
            "step_id": step.id,
            "role": step.role,
            "status": "executed",
            "retries": 0,
            "duration_ms": 0,
            "verification_result": build_qa_verification(qa_artifact.content),
        }
        if isinstance(qa_artifact.content, dict):
            coverage = qa_artifact.content.get("coverage")
            coverage_delta = qa_artifact.content.get("coverage_delta")
            if coverage:
                event_data["coverage_overall"] = coverage.get("overall_percent")
            if coverage_delta:
                event_data["coverage_delta_files"] = coverage_delta
        self._orch.event_service.emit_event(event_data)


