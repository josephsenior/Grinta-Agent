from openhands.metasop.models import Artifact
from openhands.metasop.orchestrator import MetaSOPOrchestrator


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
    art = Artifact(step_id="s2", role="engineer", content={"content": "x=1", "_provenance": existing.copy()})
    art_hash, fp = orch._ensure_artifact_provenance(art)
    prov = art.content.get("_provenance")
    assert prov == existing, "existing provenance must not be overwritten"
    assert art.content.get("_provenance") == existing
    assert isinstance(art_hash, (str, type(None)))
    assert isinstance(fp, (str, type(None)))
