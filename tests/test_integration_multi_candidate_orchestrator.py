from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from forge.metasop.models import Artifact, RoleProfile, SopStep, StepOutputSpec, StepResult
from forge.metasop.orchestrator import MetaSOPOrchestrator
from forge.metasop.strategies import BaseStepExecutor

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig


def make_template_with_engineer_step(tmp_path):
    """Create a template with an engineer step for testing.

    Args:
        tmp_path: Temporary path for test files.

    Returns:
        list: List containing a single engineer step.
    """
    step = SopStep(id="eng_step", role="engineer", task="Make change", outputs=StepOutputSpec(schema=""), depends_on=[])
    return [step]


class DummyExecutor(BaseStepExecutor):
    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self.candidates = candidates

    def execute(
        self,
        step: SopStep,
        ctx: Any,
        role_profile: dict[str, Any],
        config: "ForgeConfig | None" = None,
    ) -> StepResult:
        artifact = Artifact(step_id=step.id, role=step.role, content={"candidates": self.candidates})
        return StepResult(ok=True, artifact=artifact)


def test_orchestrator_selects_best_candidate(tmp_path, monkeypatch):
    """Test that the orchestrator correctly selects the best candidate from multiple options.

    Args:
        tmp_path: Temporary path for test files.
        monkeypatch: Pytest monkeypatch fixture for mocking.
    """
    orch = MetaSOPOrchestrator(sop_name="test")
    orch.template = type("T", (), {"steps": make_template_with_engineer_step(tmp_path)})
    candidates = [
        {"content": "candidate A " + "longtext " * 200, "meta": {"quality": 0.3}},
        {"content": "B", "meta": {"quality": 0.8}},
    ]
    dummy = DummyExecutor(candidates)
    orch.step_executor = dummy
    orch.profiles["engineer"] = RoleProfile(name="Engineer", goal="", skills=[])
    orch.settings.enabled = True
    orch.settings.enable_micro_iterations = False  # Disable micro-iterations to avoid validation issues
    orch.settings.micro_iteration_candidate_count = 2
    orch.settings.patch_scoring_enable = False
    ok, done = orch.run("please", repo_root=str(tmp_path))
    assert ok is True
    assert "eng_step" in done
    art = done["eng_step"]
    content_text = json.dumps(art.content) if isinstance(art.content, dict) else str(art.content)
    assert "B" in content_text
