from __future__ import annotations

import logging
import types
from typing import Any, Callable, TYPE_CHECKING, cast

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
orig_put = step_cache.put


def _bind_put(cache: StepCache, func: Callable[[StepCacheEntry], bool]) -> None:
    def _wrapped(self: StepCache, entry: StepCacheEntry) -> bool:
        return func(entry)

    cache.put = types.MethodType(_wrapped, cache)  # type: ignore[assignment]


def wrapped_put(entry: StepCacheEntry) -> bool:
    logger.info("wrapped_put called")
    try:
        r = orig_put(entry)
        logger.info("wrapped_put result: %s", r)
        return r
    except Exception:
        logger.exception("wrapped_put exception")
        raise


_bind_put(step_cache, wrapped_put)
logger.info("run now")
orch.run("req")
logger.info("after run stats: %s", step_cache.stats())
