import time
import types

from forge.metasop.cache import StepCacheEntry
from forge.metasop.models import Artifact
from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummyQAExecutor:
    def __init__(self):
        self.calls = 0

    def run_qa(self, step, ctx, repo_root, selected_tests=None):
        self.calls += 1
        return Artifact(
            step_id=step.id,
            role=step.role,
            content={"ok": True, "tests": {"passed": 1}},
        )


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
        config=types.SimpleNamespace(
            extended=types.SimpleNamespace(metasop={}), runtime=types.SimpleNamespace()
        ),
    )
    orch.settings.enabled = True
    orch.step_cache = orch.step_cache or None
    if orch.step_cache is None:
        from forge.metasop.cache import StepCache

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
    orch.run(user_request="do qa", repo_root=str(tmp_path))
    assert qa.calls == 0
