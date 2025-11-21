from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from forge.metasop.failure_taxonomy import corrective_hint
from forge.metasop.models import SopStep, StepResult
from forge.metasop.remediation import get_remediation_plan, summarize_remediation


class FailureHandler:
    """Encapsulates failure analysis and event emission for MetaSOP orchestration."""

    def __init__(
        self,
        settings: Any,
        failure_classifier: Any,
        emit_event: Callable[[dict[str, Any]], None],
    ) -> None:
        self.settings = settings
        self.failure_classifier = failure_classifier
        self._emit_event = emit_event

    def update_failure_classifier(self, failure_classifier: Any) -> None:
        """Update the underlying failure classifier."""
        self.failure_classifier = failure_classifier

    def analyze_step_failure(
        self, result: StepResult, step: SopStep, retries: int
    ) -> dict[str, Any]:
        """Analyse a failed step and return structured failure metadata."""
        try:
            if not result or not hasattr(result, "error"):
                return {
                    "failure_type": "unknown",
                    "reason": "no_error_info",
                    "retries": retries,
                    "step_id": step.id,
                    "role": step.role,
                }

            error = getattr(result, "error", None) or "unknown_error"

            if self.failure_classifier:
                try:
                    failure_type, failure_meta = self.failure_classifier.classify(
                        step.id,
                        step.role,
                        stderr=error,
                        retries_exhausted=retries > 0,
                    )
                    if failure_type:
                        hint = corrective_hint(failure_type)
                        payload: dict[str, Any] = {
                            "failure_type": failure_type,
                            "error": error,
                            "metadata": failure_meta,
                            "retries": retries,
                            "step_id": step.id,
                            "role": step.role,
                        }
                        if hint:
                            payload["corrective_hint"] = hint
                        return payload
                except (AttributeError, TypeError, ValueError):
                    pass

            return {
                "failure_type": "execution_error",
                "error": error,
                "retries": retries,
                "step_id": step.id,
                "role": step.role,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "failure_type": "analysis_error",
                "error": str(exc),
                "retries": retries,
                "step_id": step.id,
                "role": step.role,
            }

    def get_remediation_plan(
        self, failure_analysis: Optional[dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Return remediation plan summary for a failure analysis."""
        try:
            if not failure_analysis:
                return None
            failure_type = failure_analysis.get("failure_type")
            if not isinstance(failure_type, str):
                return None

            if remediation_plan := get_remediation_plan(failure_type):
                return {
                    "plan": remediation_plan,
                    "summary": summarize_remediation(remediation_plan),
                    "failure_type": failure_type,
                }
        except (AttributeError, TypeError, ValueError, ImportError):
            return None
        return None

    def emit_retry_event(
        self, step: SopStep, retries: int, failure_analysis: dict[str, Any]
    ) -> None:
        """Emit an orchestration event signaling a retry for a failed step."""
        remediation = self.get_remediation_plan(failure_analysis)
        event_data: dict[str, Any] = {
            "step_id": step.id,
            "role": step.role,
            "status": "retry",
            "retries": retries,
            "reason": "step_execution_failed",
            "failure_analysis": failure_analysis,
        }
        if remediation:
            event_data["remediation"] = remediation
        self._emit_event(event_data)

    def emit_final_failure_event(
        self, step: SopStep, retries: int, failure_analysis: dict[str, Any]
    ) -> None:
        """Emit final failure event when retries are exhausted."""
        self._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "failed",
                "retries": retries,
                "reason": "max_retries_exceeded",
                "failure_analysis": failure_analysis,
            }
        )

    def handle_step_failure(
        self,
        step: SopStep,
        error: str,
        retries: int,
        max_retries: int,
    ) -> dict[str, Any]:
        """Build structured failure info including taxonomy hints where possible."""
        failure_info: dict[str, Any] = {
            "step_id": step.id,
            "role": step.role,
            "error": error,
            "retries": retries,
            "max_retries": max_retries,
        }

        if getattr(self.settings, "enable_failure_taxonomy", False) and self.failure_classifier:
            try:
                failure_type, failure_meta = self.failure_classifier.classify(
                    step.id,
                    step.role,
                    stderr=error,
                    retries_exhausted=retries >= max_retries,
                )
                if failure_type:
                    failure_info["failure_type"] = failure_type
                    if failure_meta:
                        failure_info["taxonomy_meta"] = failure_meta
                    if hint := corrective_hint(failure_type):
                        failure_info["corrective_hint"] = hint
                    if remediation := get_remediation_plan(failure_type):
                        failure_info["remediation"] = remediation
            except (AttributeError, TypeError, ValueError, RuntimeError):
                failure_info["taxonomy_error"] = "classification_failed"

        return failure_info

    def emit_failure_event(self, step: SopStep, failure_info: dict[str, Any]) -> None:
        """Emit failure event enriched with taxonomy metadata."""
        event_data: dict[str, Any] = {
            "step_id": step.id,
            "role": step.role,
            "status": "failed",
            "retries": failure_info.get("retries", 0),
            "reason": "step_execution_failed",
            "error": failure_info.get("error", "Unknown error"),
        }
        if "failure_type" in failure_info:
            event_data["failure_type"] = failure_info["failure_type"]
        if "corrective_hint" in failure_info:
            event_data["corrective_hint"] = failure_info["corrective_hint"]
        if "remediation" in failure_info:
            event_data["remediation"] = failure_info["remediation"]

        try:
            self._emit_event(event_data)
        except Exception:  # pragma: no cover - defensive
            logging.exception("Failed to emit failure event")


