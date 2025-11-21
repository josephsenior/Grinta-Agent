from __future__ import annotations

import types
from typing import Any, TYPE_CHECKING, cast

import pytest

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
        iteration = ctx.extra.get("it", 0)
        content = {"content": "alpha"} if iteration == 0 else {"content": "beta"}
        ctx.extra["it"] = iteration + 1
        artifact = Artifact(step_id=step.id, role=step.role, content=content)
        trace = StepTrace(
            step_id=step.id, role=step.role, total_tokens=0, model_name="dummy"
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)


@pytest.mark.skip(reason="Requires stabilized micro-iteration summary pipeline")
def test_micro_iter_summary_event_only():
    orch = MetaSOPOrchestrator(
        sop_name="feature_delivery",
        config=cast(
            "ForgeConfig | None",
            types.SimpleNamespace(
                extended=types.SimpleNamespace(metasop={}),
                runtime=types.SimpleNamespace(),
            ),
        ),
    )
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
    orch.settings.enabled = True
    orch.settings.enable_micro_iterations = True
    orch.settings.micro_iteration_max_loops = 5
    orch.settings.micro_iteration_no_change_limit = 2
    orch.step_executor = DummyExecutor()
    orch.profiles["engineer"] = RoleProfile(
        name="engineer",
        goal="Implement micro iteration task",
        capabilities=["implement"],
    )
    success, _ = orch.run(user_request="test summary")
    assert success
    events = [e for e in orch.step_events if e.get("step_id") == "impl"]
    summary = [e for e in events if e.get("status") == "micro_iter_summary"]
    assert summary, "Expected a micro_iter_summary event"
    ev = summary[0]
    assert "total_iterations" in ev
    assert "distinct_diffs" in ev
    assert "converged" in ev
    assert ev["converged"] is True
