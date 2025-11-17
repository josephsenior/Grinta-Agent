from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, cast

from forge.metasop.models import Artifact, SopStep, SopTemplate, StepTrace


def build_qa_verification(qa_content: Any) -> dict[str, Any]:
    """Compile a normalized QA verification payload."""
    if qa_content is None:
        return {}
    if not isinstance(qa_content, Mapping):
        return {}

    typed_qa = cast(Mapping[str, Any], qa_content)
    tests_value = typed_qa.get("tests")
    tests_data: Mapping[str, Any] = (
        cast(Mapping[str, Any], tests_value) if isinstance(tests_value, Mapping) else {}
    )
    coverage_value = typed_qa.get("coverage")
    coverage_data: Mapping[str, Any] = (
        cast(Mapping[str, Any], coverage_value)
        if isinstance(coverage_value, Mapping)
        else {}
    )

    verification: dict[str, Any] = {
        "ok": bool(typed_qa.get("ok", False)),
        "tests_passed": tests_data.get("passed", 0),
        "tests_failed": tests_data.get("failed", 0),
        "coverage": dict(coverage_data),
        "timeout": bool(typed_qa.get("timeout", False)),
        "error": typed_qa.get("error"),
    }

    if "stdout" in typed_qa:
        verification["stdout"] = typed_qa["stdout"]
    if "stderr" in typed_qa:
        verification["stderr"] = typed_qa["stderr"]
    return verification


def verify_expected_outcome(
    expected_outcome: Optional[str],
    artifact_content: Mapping[str, Any] | str | None,
) -> dict[str, Any]:
    """Validate whether an artifact matches an expected outcome."""
    if not expected_outcome or not artifact_content:
        return {"verified": False, "reason": "missing_expected_outcome_or_content"}

    if isinstance(artifact_content, Mapping):
        content_text = (
            artifact_content.get("content")
            or artifact_content.get("text")
            or str(artifact_content)
        )
    else:
        content_text = str(artifact_content)

    expected_lower = expected_outcome.lower()
    actual_lower = content_text.lower()
    verified = expected_lower in actual_lower
    actual_preview = content_text[:500] if len(content_text) > 500 else content_text

    return {
        "verified": verified,
        "expected": expected_outcome,
        "actual": actual_preview,
        "reason": "expected_outcome_found" if verified else "expected_outcome_not_found",
    }


def verify_expected_outcome_if_specified(step: SopStep, artifact: Artifact) -> Optional[dict[str, Any]]:
    """Check expected outcome configuration on a step and verify when present."""
    expected_outcome = getattr(step, "expected_outcome", None)
    if expected_outcome:
        return verify_expected_outcome(expected_outcome, artifact.content)
    return None


def extract_qa_outputs(qa_artifact: Artifact) -> tuple[str, str]:
    """Extract stdout/stderr strings from a QA artifact."""
    content: Any = qa_artifact.content
    if isinstance(content, Mapping):
        stdout = content.get("stdout", "")
        stderr = content.get("stderr", "")
    else:
        stdout = ""
        stderr = ""
    return str(stdout), str(stderr)


def build_verification_report(
    traces: Sequence[StepTrace],
    step_events: Sequence[dict[str, Any]],
    template: SopTemplate | None,
) -> dict[str, Any]:
    """Construct a verification report summary for the orchestrator."""
    executed_steps = get_executed_steps(traces)
    all_steps = get_all_steps(template)
    skipped_steps = get_skipped_steps(step_events)
    efficiency = calculate_efficiency_metrics(traces, step_events)

    return {
        "executed_steps": list(executed_steps),
        "all_steps": all_steps,
        "skipped_steps": skipped_steps,
        "efficiency": efficiency,
        "total_traces": len(traces),
        "total_events": len(step_events),
        "events": list(step_events),
    }


def get_executed_steps(traces: Sequence[StepTrace]) -> set[str]:
    """Return set of step IDs that produced traces."""
    return {t.step_id for t in traces if getattr(t, "step_id", None)}


def get_all_steps(template: SopTemplate | None) -> list[str]:
    """Return ordered list of all template step IDs."""
    if template and getattr(template, "steps", None):
        return [s.id for s in template.steps if getattr(s, "id", None)]
    return []


def get_skipped_steps(step_events: Sequence[dict[str, Any]]) -> list[str]:
    """Return list of skipped step IDs recorded in step events."""
    skipped = [e for e in step_events if e.get("status") == "skipped"]
    result = []
    for event in skipped:
        step_id = event.get("step_id")
        if isinstance(step_id, str):
            result.append(step_id)
    return result


def calculate_efficiency_metrics(
    traces: Sequence[StepTrace], step_events: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    """Compute simple efficiency statistics from trace and event data."""
    total_tokens = calculate_total_tokens(traces)
    successful_steps = get_successful_steps(step_events)
    tokens_per_success = calculate_tokens_per_success(successful_steps)

    return {
        "total_tokens": total_tokens or None,
        "executed_steps": len(successful_steps),
        "tokens_per_successful_step": round(tokens_per_success, 2) if tokens_per_success else None,
    }


def calculate_total_tokens(traces: Sequence[StepTrace]) -> int:
    """Aggregate total tokens across traces."""
    total = 0
    for trace in traces:
        tokens = getattr(trace, "total_tokens", 0) or 0
        total += tokens
    return total


def get_successful_steps(step_events: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return step events marked as executed."""
    return [e for e in step_events if e.get("status") == "executed"]


def calculate_tokens_per_success(successful_steps: Sequence[dict[str, Any]]) -> Optional[float]:
    """Compute average tokens per successful step event."""
    if not successful_steps:
        return None
    total_tokens = sum(event.get("total_tokens") or 0 for event in successful_steps)
    return total_tokens / len(successful_steps) if successful_steps else None


__all__ = [
    "build_qa_verification",
    "verify_expected_outcome",
    "verify_expected_outcome_if_specified",
    "extract_qa_outputs",
    "build_verification_report",
    "calculate_efficiency_metrics",
]


