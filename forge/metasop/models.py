"""Pydantic models defining MetaSOP roles, steps, artifacts, and execution results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RoleProfile(BaseModel):
    """Profile defining a role's capabilities and constraints in MetaSOP.
    
    Specifies the skills, constraints, and capabilities for a role (PM, Architect,
    Engineer, QA, etc.) in the orchestration workflow.
    """
    name: str
    goal: str
    skills: list[str] = Field(default_factory=list)
    output_format: str | None = None
    constraints: list[str | dict[str, Any]] = Field(default_factory=list)  # Accept strings or dicts
    capabilities: list[str] = Field(
        default_factory=list,
        description="Declarative capability tags for policy gating (e.g., write_code, run_tests, design_ui)",
    )
    __test__ = False


class StepOutputSpec(BaseModel):
    """Specification for step output validation schema."""
    schema_file: str = Field(
        alias="schema",
        description="Path to JSON schema file relative to metasop/templates/schemas",
    )
    model_config = {"populate_by_name": True, "extra": "ignore"}

    __test__ = False


class SopStep(BaseModel):
    """Single step in a Standard Operating Procedure (SOP).
    
    Defines a task to be executed by a specific role with dependencies,
    conditions, and output validation requirements.
    """
    id: str
    role: str
    task: str
    outputs: StepOutputSpec
    depends_on: list[str] = Field(default_factory=list)
    condition: str | None = None
    lock: str | None = Field(
        default=None,
        description="Resource lock category: read_only | write | test | network (reserved).",
    )
    priority: int = Field(default=100, description="Relative priority for future scheduling (lower = earlier).")
    __test__ = False


class SopTemplate(BaseModel):
    """Template defining a complete SOP with multiple steps."""
    name: str
    steps: list[SopStep]
    __test__ = False


class Artifact(BaseModel):
    """Output artifact produced by a step execution."""
    step_id: str
    role: str
    content: dict[str, Any]
    __test__ = False


class StepTrace(BaseModel):
    """Execution trace and metrics for a step."""
    step_id: str
    role: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    model_name: str | None = None
    duration_ms: int | None = None
    retries: int = 0
    __test__ = False


class ExpectedOutcome(BaseModel):
    """Declarative intent for a step before execution.

    Example:
      intent: increase_coverage
      target_files: ["parser.py"]
      success_criteria: {"branch_delta_min": 0.05}

    """

    intent: str
    description: str | None = None
    target_files: list[str] = Field(default_factory=list)
    success_criteria: dict[str, Any] = Field(default_factory=dict)
    __test__ = False


class VerificationResult(BaseModel):
    """Result of step output verification against expected criteria."""
    status: str
    observed_metrics: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    __test__ = False


class StepResult(BaseModel):
    """Result of step execution with success status and optional artifact."""
    ok: bool
    artifact: Artifact | None = None
    trace: StepTrace | None = None
    error: str | None = None
    rationale: str | None = None
    expected_outcome: ExpectedOutcome | None = None
    verification_result: VerificationResult | None = None
    artifact_hash: str | None = None
    step_hash: str | None = None
    __test__ = False


class OrchestrationContext(BaseModel):
    """Context for MetaSOP orchestration run.
    
    Contains run metadata, user request, repository path, and optional
    LLM registry for step execution.
    """
    run_id: str
    user_request: str = Field(max_length=100000, description="User's request text")
    repo_root: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
    llm_registry: Any = Field(default=None, exclude=True)  # Exclude from serialization
    __test__ = False


class RetryPolicy(BaseModel):
    """Structured retry configuration for non-QA steps.

    Attributes:
        max_attempts: Total attempts (initial try + retries). Must be >=1.
        backoff: Backoff strategy; currently supports 'none', 'linear', 'exponential'.
        base_delay_sec: Base delay (for linear/exponential) in seconds.
        max_delay_sec: Cap for any computed delay.

    """

    max_attempts: int = 3
    backoff: str = "none"
    base_delay_sec: float = 1.0
    max_delay_sec: float = 30.0

    def compute_sleep(self, attempt_index: int) -> float:
        """Return sleep duration BEFORE the next attempt.

        attempt_index: zero-based index of the failed attempt just completed.
        """
        if self.backoff == "none":
            return 0.0
        if self.backoff == "linear":
            return min(self.base_delay_sec * (attempt_index + 1), self.max_delay_sec)
        if self.backoff == "exponential":
            return min(self.base_delay_sec * 2**attempt_index, self.max_delay_sec)
        return 0.0

    __test__ = False
