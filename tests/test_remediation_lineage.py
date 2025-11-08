import json
from pathlib import Path
from types import SimpleNamespace
from forge.metasop.lineage import append_lineage


def test_append_lineage_in_memory():
    ctx = SimpleNamespace(run_id="r1", extra={})
    settings = SimpleNamespace(remediation_lineage_dir=None)
    append_lineage(ctx, "impl", {"phase": "planned", "detail": "x"}, settings=settings)
    key = "failure_lineage::impl"
    assert key in ctx.extra
    rec = ctx.extra[key][0]
    assert rec["phase"] == "planned"
    assert "timestamp" in rec
    assert rec["run_id"] == "r1"


def test_append_lineage_persistence(tmp_path):
    ctx = SimpleNamespace(run_id="runX", extra={})
    settings = SimpleNamespace(remediation_lineage_dir=str(tmp_path))
    append_lineage(ctx, "impl", {"phase": "planned", "detail": "y"}, settings=settings)
    fn = Path(settings.remediation_lineage_dir) / f"{ctx.run_id}_failure_lineage.jsonl"
    assert fn.exists()
    lines = [json.loads(line) for line in fn.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines and lines[0]["phase"] == "planned"
