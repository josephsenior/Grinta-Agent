import types

import pytest

from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummyResult:
    def __init__(self, ok: bool, artifact: str):
        self.ok = ok
        self.artifact = artifact
        self.error = None
        self.trace = types.SimpleNamespace(total_tokens=10, model_name="dummy-model")
        self.artifact_hash = None
        self.step_hash = None


class DummyExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, step, ctx, role_profile, config=None):
        self.calls += 1
        if self.calls == 1:
            return DummyResult(True, "line1\nalpha\n")
        else:
            return DummyResult(True, "line1\nbeta\n")


class Step:
    def __init__(self, id_, role):
        self.id = id_
        self.role = role
        self.depends_on = []
        self.extras = {}
        self.condition = None
        self.shape_output = None
        self.validation_schema = None
        self.max_retries = 0
        self.timeout_seconds = None
        self.task = "Implement minimal change"
        self.outputs = types.SimpleNamespace(schema_file=None)


class Template:
    def __init__(self):
        self.name = "feature_delivery"
        self.steps = [Step("impl", "engineer")]


class Ctx:
    def __init__(self):
        self.extra = {}
        self.run_id = "run-test"
        self.user_request = "test"


@pytest.mark.skip(
    reason="Temporarily skipped pending stabilization of micro-iteration artifact validation path"
)
def test_micro_iteration_basic():
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(
            extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()
        ),
    )
    orch.template = Template()
    orch.settings.enable_micro_iterations = True
    orch.settings.micro_iteration_max_loops = 5
    orch.settings.micro_iteration_no_change_limit = 2
    orch.step_executor = DummyExecutor()
    orch.profiles["engineer"] = types.SimpleNamespace(
        model_dump=lambda: {}, capabilities=["implement"]
    )
    ctx = Ctx()
    orch._ctx = ctx
    orch.settings.enabled = True
    success, _ = orch.run(user_request="test micro iteration")
    micro_events = [e for e in orch.step_events if e.get("status") == "micro_iter"]
    assert micro_events, "Expected micro_iter events emitted"
    assert any((e.get("no_change_stop") for e in micro_events)), (
        "Expected a no_change_stop termination event"
    )
