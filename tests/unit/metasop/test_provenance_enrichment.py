from forge.core.config import ForgeConfig
from forge.metasop.models import Artifact
from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummySettings:
    pass


def make_orchestrator():
    return MetaSOPOrchestrator(sop_name="test_sop")


def test_ensure_provenance_populates_missing(tmp_path):
    orch = make_orchestrator()
    art = Artifact(step_id="s1", role="engineer", content={"content": "print('hi')"})
    art_hash, fp = orch._ensure_artifact_provenance(art)
    assert isinstance(art.content, dict)
    prov = art.content.get("_provenance")
    assert prov is not None, "_provenance should have been added"
    assert "artifact_hash" in prov and "diff_fingerprint" in prov
    assert art_hash == prov.get("artifact_hash")
    assert fp == prov.get("diff_fingerprint")


def test_ensure_provenance_preserves_existing(tmp_path):
    orch = make_orchestrator()
    existing = {"artifact_hash": "agenthash", "diff_fingerprint": "agentfp"}
    art = Artifact(
        step_id="s2",
        role="engineer",
        content={"content": "x=1", "_provenance": existing.copy()},
    )
    art_hash, fp = orch._ensure_artifact_provenance(art)
    prov = art.content.get("_provenance")
    assert prov == existing, "existing provenance must not be overwritten"
    assert art.content.get("_provenance") == existing
    assert isinstance(art_hash, (str, type(None)))
    assert isinstance(fp, (str, type(None)))


def test_ensure_provenance_with_prev_text(tmp_path):
    orch = make_orchestrator()
    art = Artifact(step_id="s3", role="engineer", content={"content": "print('hi')"})
    prev = "print('bye')"
    art_hash, fp = orch._ensure_artifact_provenance(art, prev_text=prev)
    assert art_hash is not None
    assert fp is not None
    assert art.content.get("_provenance", {}).get("prev_text_hash") is None


def test_ensure_provenance_with_config_preserves_agent_values():
    cfg = ForgeConfig()
    orch = MetaSOPOrchestrator(sop_name="cfg_sop", config=cfg)
    existing = {"artifact_hash": "preset-hash", "diff_fingerprint": "preset-fp"}
    art = Artifact(
        step_id="cfg",
        role="engineer",
        content={"content": "x", "_provenance": existing.copy()},
    )
    art_hash, fp = orch._ensure_artifact_provenance(art, prev_text=None)
    assert art.content["_provenance"] == existing
    assert isinstance(art_hash, (str, type(None)))
    assert isinstance(fp, (str, type(None)))
