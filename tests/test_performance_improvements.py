import time
import types
from openhands.metasop.cache import StepCacheEntry
from openhands.metasop.models import Artifact
from openhands.metasop.orchestrator import MetaSOPOrchestrator


class DummyQAExecutor:

    def __init__(self):
        self.calls = 0

    def run_qa(self, step, ctx, repo_root, selected_tests=None):
        self.calls += 1
        return Artifact(step_id=step.id, role=step.role, content={"ok": True, "tests": {"passed": 1}})


class DummyExec:

    def __init__(self, return_artifact):
        self.calls = 0
        self.return_artifact = return_artifact

    def execute(self, step, ctx, role_profile, config=None):
        self.calls += 1
        return self.return_artifact


class StepStub:

    def __init__(self, id_, role):
        self.id = id_
        self.role = role
        self.depends_on = []
        self.task = "task"
        self.condition = None
        self.outputs = types.SimpleNamespace(schema_file=None)


class TemplateStub:

    def __init__(self, steps):
        self.name = "test"
        self.steps = steps


def test_qa_cache_short_circuits(tmp_path):
    """Test that QA cache short-circuits correctly for performance."""
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch.settings.enabled = True
    orch.step_cache = orch.step_cache or None
    if orch.step_cache is None:
        from openhands.metasop.cache import StepCache

        orch.step_cache = StepCache(max_entries=10)
    step = StepStub("qa1", "qa")
    orch.template = TemplateStub([step])
    ctx = types.SimpleNamespace(run_id="r", user_request="u", extra={})
    orch._ctx = ctx
    pre_hash = "ctx_hash_qa"
    ctx.extra = {"retrieval::qa1": []}
    entry = StepCacheEntry(
        context_hash=pre_hash,
        step_id="qa1",
        role="qa",
        artifact_content={"ok": True},
        artifact_hash="ah",
        step_hash="sh",
        rationale=None,
        model_name=None,
        total_tokens=None,
        diff_fingerprint=None,
        created_ts=time.time(),
    )
    orch.step_cache.put(entry)
    orch._compute_context_hash = lambda *a, **k: pre_hash
    qa = DummyQAExecutor()
    orch.qa_executor = qa
    success, done = orch.run("req", repo_root=str(tmp_path))
    assert qa.calls == 0


def test_speculative_execution_short_circuits():
    """Test that speculative execution short-circuits correctly for performance."""
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=types.SimpleNamespace(extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()),
    )
    orch.settings.enabled = True
    step = StepStub("impl", "engineer")
    orch.template = TemplateStub([step])
    orch.settings.enable_micro_iterations = True
    orch.settings.speculative_execution_enable = True
    orch.settings.speculative_candidate_count = 3
    fast = DummyExec(
        return_artifact=types.SimpleNamespace(
            ok=True,
            artifact=types.SimpleNamespace(step_id="impl", role="engineer", content={"content": "fast"}),
            trace=types.SimpleNamespace(total_tokens=10, model_name="m"),
        )
    )
    slow = DummyExec(
        return_artifact=types.SimpleNamespace(
            ok=True,
            artifact=types.SimpleNamespace(step_id="impl", role="engineer", content={"content": "slow"}),
            trace=types.SimpleNamespace(total_tokens=20, model_name="m"),
        )
    )

    def executor_factory():
        calls = {"n": 0}

        def _exec(step_, ctx_, role_profile_, config=None):
            calls["n"] += 1
            if calls["n"] == 1:
                return fast.execute(step_, ctx_, role_profile_, config)
            time.sleep(0.1)
            return slow.execute(step_, ctx_, role_profile_, config)

        return _exec

    orch.step_executor = types.SimpleNamespace(execute=executor_factory())
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    success, done = orch.run("req")
    assert success is True
    assert "impl" in done
