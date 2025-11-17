from __future__ import annotations

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


class RotatingExecutor(BaseStepExecutor):
    def __init__(self) -> None:
        self.calls = 0

    def execute(
        self,
        step: SopStep,
        ctx: Any,
        role_profile: dict[str, Any],
        config: "ForgeConfig | None" = None,
    ) -> StepResult:
        ctx.extra.get(f"micro_prev_artifact::{step.id}")
        variants = [
            "func a()\nprint('A')",
            "func b()\nprint('B B B B')",
            "func c()\nprint('C')",
        ]
        content_variant = variants[self.calls % len(variants)]
        ctx.extra["last_variant"] = content_variant
        self.calls += 1
        artifact = Artifact(
            step_id=step.id, role=step.role, content={"content": content_variant}
        )
        trace = StepTrace(
            step_id=step.id, role=step.role, total_tokens=0, model_name="dummy"
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)


def _make_orchestrator():
    return MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=cast(
            "ForgeConfig | None",
            types.SimpleNamespace(
                extended=types.SimpleNamespace(metasop={}),
                runtime=types.SimpleNamespace(),
            ),
        ),
    )


def test_patch_scoring_events():
    """Test patch scoring events in the MetaSOP orchestrator."""
    orch = _make_orchestrator()
    orch.template = SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl",
                role="engineer",
                task="impl task",
                outputs=StepOutputSpec(schema="dummy.json"),
            )
        ],
    )
    settings = orch.settings
    settings.metrics_prometheus_port = None
    settings.enabled = True
    settings.enable_micro_iterations = False
    settings.micro_iteration_max_loops = 1
    settings.micro_iteration_no_change_limit = 2
    settings.patch_scoring_enable = False
    settings.micro_iteration_candidate_count = 3
    orch.step_executor = RotatingExecutor()
    orch.profiles["engineer"] = RoleProfile(
        name="engineer",
        goal="Implement patch scoring task",
        capabilities=["implement"],
    )
    success, _ = orch.run(user_request="try scoring")
    assert success
    events = [e for e in orch.step_events if e.get("step_id") == "impl"]
    executed_events = [e for e in events if e.get("status") == "executed"]
    assert executed_events, "Expected step to execute successfully"
