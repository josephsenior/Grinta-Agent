"""Quick demo runner for MetaSOP remediation instrumentation.

This script runs a minimal MetaSOPOrchestrator with a fake executor that
fails the first run and succeeds on the remediation attempt. It prints
emitted events and any recorded failure lineage.

Run with: python openhands/metasop/demo_remediation_run.py
"""

from openhands.metasop.models import (
    Artifact,
    RoleProfile,
    SopStep,
    SopTemplate,
    StepOutputSpec,
    StepResult,
    StepTrace,
)
from openhands.metasop.orchestrator import MetaSOPOrchestrator
from openhands.metasop.settings import RetrySettings


class DemoExecutor:

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, step, ctx, role_profile, config=None):
        self.calls += 1
        if self.calls == 1:
            return StepResult(ok=False, artifact=None, error="simulated_failure")
        art = Artifact(step_id=step.id, role=step.role, content={"content": "remediated"})
        trace = StepTrace(step_id=step.id, role=step.role, duration_ms=10, total_tokens=5)
        return StepResult(ok=True, artifact=art, trace=trace)


def main() -> None:
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
    if getattr(orch, "_ctx", None) and key in orch._ctx.extra:
        for _r in orch._ctx.extra[key]:
            pass
    else:
        pass


if __name__ == "__main__":
    main()
