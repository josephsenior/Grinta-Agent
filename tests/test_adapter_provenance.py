from openhands.core.config import OpenHandsConfig
from openhands.metasop.models import Artifact, SopStep
from openhands.metasop.orchestrator import MetaSOPOrchestrator


def _make_orch():
    cfg = OpenHandsConfig()
    return MetaSOPOrchestrator("example_sop", config=cfg)


def test_enrich_provenance_for_agent_artifact():
    """If an adapter returns an artifact without _provenance, orchestrator should compute and attach artifact_hash and diff_fingerprint."""
    orch = _make_orch()
    step = SopStep(id="s1", role="engineer", task="make change", outputs={"schema": ""})
    art = Artifact(step_id="s1", role="engineer", content={"content": 'print("hello world")'})
    assert isinstance(art.content, dict)
    assert "_provenance" not in art.content
    ah, fp = orch._ensure_artifact_provenance(art, step=step, prev_text=None)
    assert ah is not None
    assert fp is not None
    assert "_provenance" in art.content
    prov = art.content["_provenance"]
    assert prov.get("artifact_hash") == ah
    assert prov.get("diff_fingerprint") == fp


def test_preserve_agent_provided_provenance():
    """If an agent provides _provenance values, orchestrator should not overwrite them."""
    orch = _make_orch()
    step = SopStep(id="s2", role="engineer", task="do nothing", outputs={"schema": ""})
    art = Artifact(
        step_id="s2",
        role="engineer",
        content={"content": "x = 1", "_provenance": {"artifact_hash": "agenthash", "diff_fingerprint": "agentfp"}},
    )
    ah_before = art.content["_provenance"]["artifact_hash"]
    fp_before = art.content["_provenance"]["diff_fingerprint"]
    ah, fp = orch._ensure_artifact_provenance(art, step=step, prev_text=None)
    assert art.content["_provenance"]["artifact_hash"] == ah_before
    assert art.content["_provenance"]["diff_fingerprint"] == fp_before
    assert art.content["_provenance"]["artifact_hash"] == ah_before
    assert art.content["_provenance"]["diff_fingerprint"] == fp_before
    if ah is not None:
        assert isinstance(ah, str)
    if fp is not None:
        assert isinstance(fp, str)
