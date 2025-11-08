import logging
import types
from forge.metasop.cache import StepCache
from forge.metasop.models import Artifact, SopStep, SopTemplate, StepOutputSpec
from forge.metasop.orchestrator import MetaSOPOrchestrator

orig_put = StepCache.put


def class_put(self, entry):
    logger = logging.getLogger(__name__)
    logger.info("CLASS PUT CALLED for context_hash=%s", getattr(entry, "context_hash", None))
    return orig_put(self, entry)


StepCache.put = class_put


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
logger.info("step_cache present: %s", orch.step_cache is not None)
logger.info("initial stats: %s", orch.step_cache.stats())
orch.run("req")
logger.info("after stats: %s", orch.step_cache.stats())
