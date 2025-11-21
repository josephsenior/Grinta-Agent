from forge.metasop.models import (
    Artifact,
    RoleProfile,
    SopStep,
    SopTemplate,
    StepOutputSpec,
    StepResult,
    StepTrace,
)
from forge.metasop.orchestrator import MetaSOPOrchestrator
from forge.metasop.settings import RetrySettings


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, step, ctx, role_profile, config=None):
        self.calls += 1
        if self.calls <= 1:
            return StepResult(ok=False, artifact=None, error="simulated_failure")
        art = Artifact(
            step_id=step.id, role=step.role, content={"content": "remediated"}
        )
        trace = StepTrace(
            step_id=step.id, role=step.role, duration_ms=5, total_tokens=10
        )
        return StepResult(ok=True, artifact=art, trace=trace)


def test_orchestrator_self_remediation_flow():
    orch = MetaSOPOrchestrator(sop_name="dummy")
    out_spec = StepOutputSpec(schema="")
    step = SopStep(id="impl", role="engineer", task="implement", outputs=out_spec)
    orch.template = SopTemplate(name="t", steps=[step])
    rp = RoleProfile(name="engineer", goal="do stuff", capabilities=["write_code"])
    orch.profiles = {"engineer": rp}
    fe = FakeExecutor()
    orch.step_executor = fe
    orch.settings.enable_self_remediation = True
    orch.settings.enable_failure_taxonomy = True
    orch.settings.enabled = True
    orch.settings.retry = RetrySettings(max_attempts=1)
    ok, done = orch.run("please implement", repo_root=None, max_retries=0)
    failed_events = [
        e
        for e in orch.step_events
        if e.get("step_id") == "impl" and e.get("status") in ("failed", "warning")
    ]
    assert failed_events, (
        f"expected failed/warning events for step impl, got: {orch.step_events}"
    )
