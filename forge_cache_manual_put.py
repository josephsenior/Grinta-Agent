from __future__ import annotations

import logging
import time
import types
from typing import Any, TYPE_CHECKING, cast

from forge.metasop.cache import StepCacheEntry
from forge.metasop.models import Artifact, RoleProfile, SopStep, SopTemplate, StepOutputSpec, StepResult, StepTrace
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
        trace = StepTrace(step_id=step.id, role=step.role, total_tokens=20, model_name="dummy-model")
        return StepResult(ok=True, artifact=artifact, trace=trace)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[SopStep(id="impl", role="engineer", task="t", outputs=StepOutputSpec(schema="dummy.json"))],
    )


metasop_cfg = {"enable_step_cache": True}
config: Any = types.SimpleNamespace(extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace())
orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=cast("ForgeConfig | None", config))
orch.template = _make_single_engineer_template()
orch.settings.enabled = True
orch.step_executor = DummyExecutor()
orch.profiles["engineer"] = RoleProfile(
    name="engineer",
    goal="Implement task",
    capabilities=["implement"],
)
logger = logging.getLogger(__name__)

step_cache = orch.step_cache
if step_cache is None:
    raise RuntimeError("Step cache is not initialized on the orchestrator")
logger.info("before manual put stats: %s", step_cache.stats())
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
ok = step_cache.put(entry)
logger.info("manual put returned: %s", ok)
logger.info("after manual put stats: %s", step_cache.stats())
hit = step_cache.get("manual_ctx", "engineer")
logger.info("get hit: %s", bool(hit))
logger.info("hit entry: %s", getattr(hit, "artifact_content", None))
