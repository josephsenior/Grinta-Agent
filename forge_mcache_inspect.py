from __future__ import annotations

import logging
import types
from typing import Any, TYPE_CHECKING, cast

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
from forge.metasop.strategies import BaseStepExecutor

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig


class DummyExecutor(BaseStepExecutor):
    def execute(
        self,
        step: SopStep,
        ctx: Any,
        role_profile: dict[str, Any],
        config: "ForgeConfig | None" = None,
    ) -> StepResult:
        content = {"result": "ok", "value": 42}
        artifact = Artifact(step_id=step.id, role=step.role, content=content)
        trace = StepTrace(
            step_id=step.id,
            role=step.role,
            total_tokens=20,
            model_name="dummy-model",
            prompt_tokens=10,
            completion_tokens=10,
            duration_ms=0,
            retries=0,
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl",
                role="engineer",
                task="implement feature",
                outputs=StepOutputSpec(schema="dummy.json"),
            )
        ],
    )


metasop_cfg = {"enable_step_cache": True}
config: Any = types.SimpleNamespace(extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace())
orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=cast("ForgeConfig | None", config))
orch.template = _make_single_engineer_template()
orch.settings.enabled = True
orch.step_executor = DummyExecutor()
logger = logging.getLogger(__name__)
orch.profiles["engineer"] = RoleProfile(
    name="engineer",
    goal="Implement feature",
    capabilities=["implement"],
)
step_cache = orch.step_cache
logger.info("step_cache present: %s", step_cache is not None)
if step_cache:
    logger.info("initial stats: %s", step_cache.stats())
logger.info("\n-- First run --")
ok1, _ = orch.run(user_request="do something")
logger.info("after run ok1: %s", ok1)
if step_cache:
    logger.info("stats after run1: %s", step_cache.stats())
logger.info("\n-- Second run --")
ok2, _ = orch.run(user_request="do something")
logger.info("after run ok2: %s", ok2)
if step_cache:
    logger.info("stats after run2: %s", step_cache.stats())
logger.info("\n-- Events emitted (last 10) --")
for e in orch.step_events[-10:]:
    logger.info("%s", e)
