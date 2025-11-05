import logging
import time
import types
from openhands.metasop.cache import StepCacheEntry
from openhands.metasop.models import Artifact, SopStep, SopTemplate, StepOutputSpec
from openhands.metasop.orchestrator import MetaSOPOrchestrator


class DummyExecutor:

    def execute(self, step, ctx, role_profile, config=None):
        content = {"result": "ok", "value": 42}
        art = Artifact(step_id=step.id, role=step.role, content=content)
        trace = types.SimpleNamespace(total_tokens=20, model_name="dummy-model")
        return types.SimpleNamespace(ok=True, artifact=art, trace=trace, rationale=None, error=None)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="t", outputs=StepOutputSpec(schema_file="dummy.json"))],
    )


metasop_cfg = {"enable_step_cache": True}
config = types.SimpleNamespace(extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace())
orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=config)
orch.template = _make_single_engineer_template()
orch.settings.enabled = True
orch.step_executor = DummyExecutor()
orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
logger = logging.getLogger(__name__)
logger.info("before manual put stats: %s", orch.step_cache.stats())
entry = StepCacheEntry(
    context_hash="manual_ctx",
    step_id="impl",
    role="engineer",
    artifact_content={"x": 1},
    artifact_hash="ah",
    step_hash="sh",
    rationale=None,
    model_name=None,
    total_tokens=20,
    diff_fingerprint=None,
    created_ts=time.time(),
)
ok = orch.step_cache.put(entry)
logger.info("manual put returned: %s", ok)
logger.info("after manual put stats: %s", orch.step_cache.stats())
hit = orch.step_cache.get("manual_ctx", "engineer")
logger.info("get hit: %s", bool(hit))
logger.info("hit entry: %s", getattr(hit, "artifact_content", None))
