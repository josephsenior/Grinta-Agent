from forge.metasop import patch_scoring
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))


def make_candidates():
    c1 = patch_scoring.PatchCandidate(
        content="def foo():\n    return 1\n", diff="+def foo():\n+    return 1\n", meta={}
    )
    c2 = patch_scoring.PatchCandidate(
        content="def foo():\n    return 2\n", diff="+def foo():\n+    return 2\n", meta={}
    )
    return [c1, c2]


def test_with_diff_match_patch():
    candidates = make_candidates()

    class S:
        patch_score_weight_complexity = 0.25
        patch_score_weight_lint = 0.25
        patch_score_weight_diffsize = 0.25
        patch_score_weight_length = 0.25

    res = patch_scoring.score_candidates(candidates, S())
    assert len(res) == 2
    for r in res:
        assert hasattr(r, "composite")
        assert "diff_fingerprint" in r.raw


def test_without_diff_match_patch(monkeypatch):
    monkeypatch.setattr(patch_scoring, "dmp_module", None)
    candidates = make_candidates()

    class S:
        patch_score_weight_complexity = 0.25
        patch_score_weight_lint = 0.25
        patch_score_weight_diffsize = 0.25
        patch_score_weight_length = 0.25

    res = patch_scoring.score_candidates(candidates, S())
    assert len(res) == 2
    for r in res:
        assert "diff_fingerprint" in r.raw
