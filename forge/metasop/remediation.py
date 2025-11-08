"""Structured remediation plans for MetaSOP failure types."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class RemediationAction:
    """Single remediation recommendation.

    kind: classification for future automation (e.g., 'add_tests', 'adjust_dependency', 'retry_with_hint').
    description: human-readable guidance.
    priority: lower number = higher priority.
    params: optional structured parameters (e.g., files, thresholds).
    """

    kind: str
    description: str
    priority: int = 100
    params: dict[str, object] = field(default_factory=dict)
    __test__ = False


@dataclass
class RemediationPlan:
    """Collection of remediation actions plus metadata for a failure type."""

    failure_type: str
    summary: str
    actions: list[RemediationAction]
    references: list[str] = field(default_factory=list)
    confidence: str = "low"
    __test__ = False


REMEDIATION_MAP: dict[str, RemediationPlan] = {
    "retries_exhausted": RemediationPlan(
        failure_type="retries_exhausted",
        summary="All retries consumed without producing a valid artifact.",
        actions=[
            RemediationAction(
                kind="retry_with_validation_hint",
                description="Inject validation error messages directly into the next prompt and reduce scope.",
                priority=10,
            ),
            RemediationAction(
                kind="narrow_task",
                description="Split the step's task into smaller sub-steps to isolate failing portion.",
                priority=20,
            ),
        ],
        references=["validation hints", "step schema"],
        confidence="medium",
    ),
    "qa_validation_failed": RemediationPlan(
        failure_type="qa_validation_failed",
        summary="QA output could not be validated or tests failing.",
        actions=[
            RemediationAction(
                kind="inspect_failures",
                description="Surface first failing test traceback and capture stdout/stderr snippet.",
                priority=5,
            ),
            RemediationAction(
                kind="add_or_update_tests",
                description="Add missing test coverage for new functionality or update brittle assertions.",
                priority=15,
            ),
            RemediationAction(
                kind="rerun_with_focus",
                description="Run only failing test modules to speed iteration.",
                priority=25,
            ),
        ],
        references=["pytest report"],
    ),
    "budget_exceeded": RemediationPlan(
        failure_type="budget_exceeded",
        summary="Hard token budget exceeded; run aborted.",
        actions=[
            RemediationAction(
                kind="reduce_context",
                description="Prune retrieval results and collapse previous step details into concise summaries.",
                priority=5,
            ),
            RemediationAction(
                kind="switch_model",
                description="Fallback to cheaper model for exploratory roles (PM/Architect).",
                priority=15,
            ),
        ],
        references=["token efficiency metrics"],
        confidence="high",
    ),
    "soft_token_budget_exceeded": RemediationPlan(
        failure_type="soft_token_budget_exceeded",
        summary="Soft token budget exceeded advisory.",
        actions=[
            RemediationAction(
                kind="context_compaction",
                description="Summarize previous artifacts with abstraction cues (interfaces, file list only).",
                priority=30,
            ),
        ],
        references=["token efficiency metrics"],
        confidence="medium",
    ),
    "failed": RemediationPlan(
        failure_type="failed",
        summary="Generic failure without explicit taxonomy mapping.",
        actions=[
            RemediationAction(
                kind="review_logs",
                description="Capture stderr/stdout and highlight first error line.",
                priority=10,
            ),
        ],
    ),
    "verification_failed": RemediationPlan(
        failure_type="verification_failed",
        summary="Expected outcome criteria not satisfied.",
        actions=[
            RemediationAction(
                kind="compare_expected_observed",
                description="Generate diff table of success_criteria vs observed_metrics.",
                priority=5,
            ),
            RemediationAction(
                kind="targeted_adjustment",
                description="Plan a micro-step to lift the weakest metric (lowest ratio observed/target).",
                priority=15,
            ),
        ],
        references=["verification_result"],
        confidence="medium",
    ),
}


def get_remediation_plan(failure_type: str) -> RemediationPlan | None:
    """Return remediation playbook for given failure type, if available."""
    return REMEDIATION_MAP.get(failure_type)


def summarize_remediation(plan: RemediationPlan | None) -> dict | None:
    """Convert remediation plan into sorted dict form for telemetry/rendering."""
    if not plan:
        return None
    return {
        "failure_type": plan.failure_type,
        "summary": plan.summary,
        "actions": [
            {"kind": a.kind, "description": a.description, "priority": a.priority, "params": a.params}
            for a in sorted(plan.actions, key=lambda x: x.priority)
        ],
        "references": plan.references,
        "confidence": plan.confidence,
    }
