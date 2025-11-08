import types
from forge.metasop.models import SopStep, SopTemplate, StepOutputSpec
from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummyExecutor:

    def execute(self, step, ctx, role_profile, config=None):
        iteration = ctx.extra.get("it", 0)
        content = {"content": "alpha"} if iteration == 0 else {"content": "beta"}
        ctx.extra["it"] = iteration + 1
        return types.SimpleNamespace(
            ok=True,
            artifact=types.SimpleNamespace(step_id=step.id, role=step.role, content=content),
            trace=types.SimpleNamespace(total_tokens=0, model_name="dummy"),
        )


def test_micro_iter_summary_event_only():
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="impl task", outputs=StepOutputSpec(schema_file="dummy.json"))],
    )
    orch.settings.enabled = True
    orch.settings.enable_micro_iterations = True
    orch.settings.micro_iteration_max_loops = 5
    orch.settings.micro_iteration_no_change_limit = 2
    orch.step_executor = DummyExecutor()
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    success, _ = orch.run(user_request="test summary")
    events = [e for e in orch.step_events if e.get("step_id") == "impl"]
    summary = [e for e in events if e.get("status") == "micro_iter_summary"]
    assert summary, "Expected a micro_iter_summary event"
    ev = summary[0]
    assert "total_iterations" in ev
    assert "distinct_diffs" in ev
    assert "converged" in ev
    assert ev["converged"] is True
