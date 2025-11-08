import json
from forge.core.config import ForgeConfig
from forge.metasop.adapters.engineer_codeact import ENGINEER_SUMMARY_PATH, run_engineer_with_codeact
from forge.metasop.models import OrchestrationContext, SopStep, StepOutputSpec


def make_step():
    return SopStep(
        id="eng_test", role="engineer", task="Make a tiny change", outputs=StepOutputSpec(schema_file=""), depends_on=[]
    )


def make_ctx(tmp_path):
    return OrchestrationContext(run_id="test", user_request="please", repo_root=str(tmp_path))


def test_adapter_reads_candidates(tmp_path, monkeypatch):

    async def _dummy_run_controller(*a, **k):
        return None

    monkeypatch.setattr("forge.metasop.adapters.engineer_codeact.run_controller", _dummy_run_controller)
    meta_dir = tmp_path / ".metasop"
    meta_dir.mkdir()
    summary = {
        "artifact_path": str(ENGINEER_SUMMARY_PATH),
        "candidates": [{"content": "candidate one", "diff": "diff1"}, {"content": "candidate two", "diff": "diff2"}],
    }
    summary_path = meta_dir / "engineer_step.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    step = make_step()
    ctx = make_ctx(tmp_path)
    res = run_engineer_with_codeact(step, ctx, role_profile={}, config=ForgeConfig())
    assert res.ok
    assert getattr(res, "artifact", None) is not None
    art = res.artifact
    assert isinstance(art.content, dict)
    assert "candidates" in art.content
    assert len(art.content["candidates"]) == 2
    assert art.content["candidates"][0]["content"] == "candidate one"
