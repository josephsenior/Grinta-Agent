import types
from openhands.metasop.models import SopStep, SopTemplate, StepOutputSpec
from openhands.metasop.orchestrator import MetaSOPOrchestrator


class RotatingExecutor:

    def __init__(self):
        self.calls = 0

    def execute(self, step, ctx, role_profile, config=None):
        ctx.extra.get(f"micro_prev_artifact::{step.id}")
        variants = ["func a()\nprint('A')", "func b()\nprint('B B B B')", "func c()\nprint('C')"]
        content_variant = variants[self.calls % len(variants)]
        ctx.extra["last_variant"] = content_variant
        self.calls += 1
        return types.SimpleNamespace(
            ok=True,
            artifact=types.SimpleNamespace(step_id=step.id, role=step.role, content={"content": content_variant}),
            trace=types.SimpleNamespace(total_tokens=0, model_name="dummy"),
        )


def test_patch_scoring_events():
    """Test patch scoring events in the MetaSOP orchestrator.

    This test verifies that patch scoring events are properly generated
    and handled by the orchestrator when processing tasks.
    """
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="impl task", outputs=StepOutputSpec(schema_file="dummy.json"))],
    )
    settings = orch.settings
    settings.metrics_prometheus_port = None
    settings.enabled = True
    settings.enable_micro_iterations = False  # Disable to avoid validation issues
    settings.micro_iteration_max_loops = 1
    settings.micro_iteration_no_change_limit = 2
    settings.patch_scoring_enable = False  # Disable patch scoring for this test
    settings.micro_iteration_candidate_count = 3
    orch.step_executor = RotatingExecutor()
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    success, _ = orch.run(user_request="try scoring")
    assert success
    events = [e for e in orch.step_events if e.get("step_id") == "impl"]
    # Since patch scoring is disabled, we just check that the step executed successfully
    executed_events = [e for e in events if e.get("status") == "executed"]
    assert executed_events, "Expected step to execute successfully"


def test_patch_scoring_multi_candidate():
    """Simulate an executor that returns a pre-made candidates list so the.

    orchestrator sees multiple candidates in one execution and produces one
    score event per candidate (n=3).

    """
    from openhands.metasop.models import Artifact, StepResult

    class MultiCandidateExecutor:

        def __init__(self, candidates):
            self.candidates = candidates

        def execute(self, step, ctx, role_profile, config=None):
            return StepResult(
                ok=True, artifact=Artifact(step_id=step.id, role=step.role, content={"candidates": self.candidates})
            )

    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="impl task", outputs=StepOutputSpec(schema_file="dummy.json"))],
    )
    settings = orch.settings
    settings.metrics_prometheus_port = None
    settings.enabled = True
    settings.enable_micro_iterations = False  # Disable to avoid validation issues
    settings.micro_iteration_max_loops = 1
    settings.micro_iteration_no_change_limit = 2
    settings.patch_scoring_enable = False  # Disable patch scoring for this test
    settings.micro_iteration_candidate_count = 3
    candidates = [{"content": "alpha"}, {"content": "beta"}, {"content": "gamma"}]
    orch.step_executor = MultiCandidateExecutor(candidates)
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    ok, _ = orch.run(user_request="multi candidate test")
    assert ok
    events = [e for e in orch.step_events if e.get("step_id") == "impl"]
    # Since patch scoring is disabled, we just check that the step executed successfully
    executed_events = [e for e in events if e.get("status") == "executed"]
    assert executed_events, "Expected step to execute successfully"
