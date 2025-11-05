import logging
import types
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
orig_put = orch.step_cache.put


def wrapped_put(entry):
    logger.info(
        "wrapped_put called with context_hash=%s step_id=%s role=%s total_tokens=%s",
        entry.context_hash,
        entry.step_id,
        entry.role,
        entry.total_tokens,
    )
    try:
        r = orig_put(entry)
        logger.info("wrapped_put result: %s", r)
        return r
    except Exception as e:
        logger.exception("wrapped_put exception: %s", e)
        raise


orch.step_cache.put = wrapped_put
logger.info("run now")
orch.run("req")
logger.info("after run stats: %s", orch.step_cache.stats())
