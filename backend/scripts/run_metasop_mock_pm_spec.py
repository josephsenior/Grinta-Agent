"""Run MetaSOP with a mocked StepExecutor to produce a deterministic successful run.

This helps debug orchestration logic without requiring an LLM or external agent.
The script writes a persisted run summary to logs/metasop_last_run_mock.json.
"""

import json
import logging
from pathlib import Path
from typing import Any

from forge.core.config.utils import load_FORGE_config
from forge.metasop.models import Artifact, SopStep, StepResult, StepTrace
from forge.metasop.orchestrator import MetaSOPOrchestrator
from forge.metasop.strategies import BaseStepExecutor


class MockStepExecutor(BaseStepExecutor):
    """A minimal executor that returns canned successful artifacts for common step ids."""

    def execute(
        self,
        step: SopStep,
        ctx: Any,
        role_profile: dict[str, Any],
        config: Any = None,
    ) -> StepResult:
        step_id = getattr(step, "id", None) or "unknown"
        role = getattr(step, "role", "unknown")
        content = self._build_content(step_id)
        return self._build_result(step_id, role, content)

    def _build_content(self, step_id: str) -> dict[str, Any]:
        builders = {
            "pm_spec": self._pm_spec_content,
            "ui_design": self._ui_design_content,
            "arch_design": self._arch_design_content,
            "engineer_impl": lambda: {"tests_added": True},
            "engineer_fix": lambda: {"fixed": True},
            "pm_approve": lambda: {"approved": True},
        }
        if step_id in {"qa_verify", "qa"}:
            return {"ok": True, "tests": {"passed": 3, "failed": 0}}
        builder = builders.get(step_id)
        if builder:
            return builder()
        return {"ok": True, "note": f"mock for {step_id}"}

    @staticmethod
    def _pm_spec_content() -> dict[str, Any]:
        return {
            "user_stories": ["As a user, I can say hello so that I get a greeting."],
            "acceptance_criteria": ["Greeting is returned"],
            "ui_multi_section": True,
        }

    @staticmethod
    def _ui_design_content() -> dict[str, Any]:
        return {
            "layout_plan": "single-column full-width sections",
            "design_tokens": {"contrast": "high", "spacing": "8px"},
            "accessibility": [],
        }

    @staticmethod
    def _arch_design_content() -> dict[str, Any]:
        return {"decisions": ["keep simple server flow", "no heavy-weight runtime"]}

    @staticmethod
    def _build_result(step_id: str, role: str, content: dict[str, Any]) -> StepResult:
        artifact = Artifact(step_id=step_id, role=role, content=content)
        trace = StepTrace(
            step_id=step_id,
            role=role,
            total_tokens=10,
            duration_ms=20,
            retries=0,
        )
        return StepResult(ok=True, artifact=artifact, trace=trace)


def main():
    logging.basicConfig(level=logging.DEBUG)
    cfg = load_FORGE_config(set_logging_levels=False)
    try:
        ext = (
            cfg.extended.model_dump()
            if hasattr(cfg.extended, "model_dump")
            else dict(cfg.extended)
            if cfg.extended
            else {}
        )
        ext["metasop"] = ext.get("metasop", {}) or {}
        ext["metasop"]["enabled"] = True
        ext["metasop"]["default_sop"] = "feature_delivery_with_ui"
        cfg.extended = (
            type(cfg.extended)(ext)
            if hasattr(cfg.extended, "__class__")
            else cfg.extended
        )
    except Exception:
        pass
    orch = MetaSOPOrchestrator(sop_name="feature_delivery_with_ui", config=cfg)
    orch.step_executor = MockStepExecutor()
    ok, artifacts = orch.run(
        "Simulated SOP run for debug: please produce feature delivery with UI",
        repo_root=None,
    )
    report = orch.get_verification_report()
    payload = {
        "ok": ok,
        "summary": "mock run",
        "report": report,
        "artifacts": {k: getattr(v, "content", {}) for k, v in artifacts.items()},
    }
    out = Path("logs")
    out.mkdir(exist_ok=True)
    p = out / "metasop_last_run_mock.json"
    p.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.getLogger(__name__).info("Wrote mock run: %s", p)


if __name__ == "__main__":
    main()
