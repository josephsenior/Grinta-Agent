"""Quick demo runner for MetaSOP remediation instrumentation.

This script runs a minimal MetaSOPOrchestrator with a fake executor that
fails the first run and succeeds on the remediation attempt. It prints
emitted events and any recorded failure lineage.

Run with: python Forge/metasop/demo_remediation_run.py
"""

from typing import Any

from forge.metasop.models import (
    Artifact,
    OrchestrationContext,
    RoleProfile,
    SopStep,
    SopTemplate,
    StepOutputSpec,
    StepResult,
    StepTrace,
)
from forge.metasop.orchestrator import MetaSOPOrchestrator
from forge.metasop.settings import RetrySettings
from forge.metasop.strategies import BaseStepExecutor


class DemoExecutor(BaseStepExecutor):
    """Toy executor that fails once then succeeds to demonstrate remediation."""

    def __init__(self) -> None:
        """Initialize with call counter used to simulate failure/success."""
        self.calls = 0

    def execute(
        self,
        step: SopStep,
        ctx: OrchestrationContext,
        role_profile: dict[str, Any],
        config: Any = None,
    ) -> StepResult:
        """Simulate single failure followed by success with canned artifact."""
        self.calls += 1
        if self.calls == 1:
            return StepResult(ok=False, artifact=None, error="simulated_failure")
        art = Artifact(step_id=step.id, role=step.role, content={"content": "remediated"})
        trace = StepTrace(step_id=step.id, role=step.role, duration_ms=10, total_tokens=5)
        return StepResult(ok=True, artifact=art, trace=trace)


def main() -> None:
    """Run demo orchestrator showcasing remediation pipeline."""
    orch = MetaSOPOrchestrator("demo")
    orch.settings.enabled = True
    orch.settings.enable_self_remediation = True
    orch.settings.enable_failure_taxonomy = True
    orch.settings.retry = RetrySettings(max_attempts=1)
    out = StepOutputSpec(schema="")
    step = SopStep(id="impl", role="engineer", task="implement", outputs=out)
    orch.template = SopTemplate(name="demo", steps=[step])
    orch.profiles = {"engineer": RoleProfile(name="engineer", goal="implement", capabilities=["write_code"])}
    orch.step_executor = DemoExecutor()
    _ok, _done = orch.run("please implement", repo_root=None)
    for _e in orch.step_events:
        pass
    key = "failure_lineage::impl"
    ctx = getattr(orch, "_ctx", None)
    if ctx is not None:
        extra = ctx.extra
        if key in extra:
            for _r in extra[key]:
                pass


if __name__ == "__main__":
    main()
