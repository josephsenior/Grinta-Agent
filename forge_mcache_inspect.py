import logging
import types
from forge.metasop.models import Artifact, SopStep, SopTemplate, StepOutputSpec
from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummyExecutor:

    def execute(self, step, ctx, role_profile, config=None):
        content = {"result": "ok", "value": 42}
        art = Artifact(step_id=step.id, role=step.role, content=content)
        trace = types.SimpleNamespace(
            total_tokens=20,
            model_name="dummy-model",
            prompt_tokens=10,
            completion_tokens=10,
            duration_ms=0,
            retries=0,
            step_id=step.id,
            role=step.role,
        )
        return types.SimpleNamespace(ok=True, artifact=art, trace=trace, rationale=None, error=None)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl", role="engineer", task="implement feature", outputs=StepOutputSpec(schema_file="dummy.json")
            )
        ],
    )


metasop_cfg = {"enable_step_cache": True}
config = types.SimpleNamespace(extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace())
orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=config)
orch.template = _make_single_engineer_template()
orch.settings.enabled = True
orch.step_executor = DummyExecutor()
logger = logging.getLogger(__name__)
orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
logger.info("step_cache present: %s", orch.step_cache is not None)
if orch.step_cache:
    logger.info("initial stats: %s", orch.step_cache.stats())
logger.info("\n-- First run --")
ok1, _ = orch.run(user_request="do something")
logger.info("after run ok1: %s", ok1)
if orch.step_cache:
    logger.info("stats after run1: %s", orch.step_cache.stats())
logger.info("\n-- Second run --")
ok2, _ = orch.run(user_request="do something")
logger.info("after run ok2: %s", ok2)
if orch.step_cache:
    logger.info("stats after run2: %s", orch.step_cache.stats())
logger.info("\n-- Events emitted (last 10) --")
for e in orch.step_events[-10:]:
    logger.info("%s", e)
