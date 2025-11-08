"""Run MetaSOP with a mocked StepExecutor to produce a deterministic successful run.

This helps debug orchestration logic without requiring an LLM or external agent.
The script writes a persisted run summary to logs/metasop_last_run_mock.json.
"""

import json
import logging
from pathlib import Path
from forge.core.config.utils import load_FORGE_config
from forge.metasop.models import Artifact, StepResult, StepTrace
from forge.metasop.orchestrator import MetaSOPOrchestrator


class MockStepExecutor:
    """A minimal executor that returns canned successful artifacts for common step ids."""

    def execute(self, step, ctx, role_profile, config=None):
        sid = getattr(step, "id", None)
        role = getattr(step, "role", "unknown")
        if sid == "pm_spec":
            content = {
                "user_stories": ["As a user, I can say hello so that I get a greeting."],
                "acceptance_criteria": ["Greeting is returned"],
                "ui_multi_section": True,
            }
        elif sid == "ui_design":
            content = {
                "layout_plan": "single-column full-width sections",
                "design_tokens": {"contrast": "high", "spacing": "8px"},
                "accessibility": [],
            }
        elif sid == "arch_design":
            content = {"decisions": ["keep simple server flow", "no heavy-weight runtime"]}
        elif sid == "engineer_impl":
            content = {"tests_added": True}
        elif sid in ["qa_verify", "qa"]:
            content = {"ok": True, "tests": {"passed": 3, "failed": 0}}
        elif sid == "engineer_fix":
            content = {"fixed": True}
        elif sid == "pm_approve":
            content = {"approved": True}
        else:
            content = {"ok": True, "note": f"mock for {sid}"}
        art = Artifact(step_id=sid or "unknown", role=role, content=content)
        trace = StepTrace(step_id=sid or "unknown", role=role, total_tokens=10, duration_ms=20, retries=0)
        return StepResult(ok=True, artifact=art, trace=trace)


def main():
    logging.basicConfig(level=logging.DEBUG)
    cfg = load_FORGE_config(set_logging_levels=False)
    try:
        ext = (
            cfg.extended.model_dump()
            if hasattr(cfg.extended, "model_dump")
            else dict(cfg.extended) if cfg.extended else {}
        )
        ext["metasop"] = ext.get("metasop", {}) or {}
        ext["metasop"]["enabled"] = True
        ext["metasop"]["default_sop"] = "feature_delivery_with_ui"
        cfg.extended = type(cfg.extended)(ext) if hasattr(cfg.extended, "__class__") else cfg.extended
    except Exception:
        pass
    orch = MetaSOPOrchestrator(sop_name="feature_delivery_with_ui", config=cfg)
    orch.step_executor = MockStepExecutor()
    ok, artifacts = orch.run("Simulated SOP run for debug: please produce feature delivery with UI", repo_root=None)
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
