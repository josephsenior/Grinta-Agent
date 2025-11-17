from __future__ import annotations

import logging
import types
from typing import Any, TYPE_CHECKING, cast

from forge.metasop.cache import StepCache, StepCacheEntry
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

orig_put = StepCache.put


def class_put(self: StepCache, entry: StepCacheEntry) -> bool:
    logger = logging.getLogger(__name__)
    logger.info(
        "CLASS PUT CALLED for context_hash=%s", getattr(entry, "context_hash", None)
    )
    return orig_put(self, entry)


StepCache.put = class_put  # type: ignore[method-assign]


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
            step_id=step.id, role=step.role, total_tokens=20, model_name="dummy-model"
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl",
                role="engineer",
                task="t",
                outputs=StepOutputSpec(schema="dummy.json"),
            )
        ],
    )


metasop_cfg = {"enable_step_cache": True}
config: Any = types.SimpleNamespace(
    extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace()
)
orch = MetaSOPOrchestrator(
    sop_name="feature_delivery", config=cast("ForgeConfig | None", config)
)
orch.template = _make_single_engineer_template()
orch.settings.enabled = True
orch.step_executor = DummyExecutor()
if orch.profiles is None:
    orch.profiles = {}
orch.profiles["engineer"] = RoleProfile(
    name="engineer",
    goal="Implement task",
    capabilities=["implement"],
)
logger = logging.getLogger(__name__)
step_cache = orch.step_cache
if step_cache is None:
    raise RuntimeError("Step cache is not initialized on the orchestrator")
logger.info("step_cache present: %s", step_cache is not None)
logger.info("initial stats: %s", step_cache.stats())
orch.run("req")
logger.info("after stats: %s", step_cache.stats())
