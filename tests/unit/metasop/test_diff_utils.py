import difflib

from forge.metasop.diff_utils import compute_diff_fingerprint


def make_unified(a: str, b: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            a.splitlines(),
            b.splitlines(),
            fromfile="a/file.txt",
            tofile="b/file.txt",
            lineterm="",
        )
    )


def test_fingerprint_stable():
    sample_a = "line1\nline2\nline3\n"
    sample_b = "line1\nLINE2_changed\nline3\n"
    diff1 = make_unified(sample_a, sample_b)
    diff2 = make_unified(sample_a, sample_b)
    f1 = compute_diff_fingerprint(diff1)
    f2 = compute_diff_fingerprint(diff2)
    assert f1 == f2, (
        "Fingerprint should be stable across regenerated diffs with same semantic change"
    )


def test_fingerprint_differs_on_semantic_change():
    sample_a = "line1\nline2\nline3\n"
    sample_b = "line1\nLINE2_changed\nline3\n"
    sample_c = "line1\nLINE2_other\nline3\n"
    diff1 = make_unified(sample_a, sample_b)
    diff2 = make_unified(sample_a, sample_c)
    f1 = compute_diff_fingerprint(diff1)
    f2 = compute_diff_fingerprint(diff2)
    assert f1 != f2, "Different modifications should yield different fingerprints"


def test_diff_fingerprint_empty_diff():
    f = compute_diff_fingerprint("")
    f2 = compute_diff_fingerprint("")
    assert f == f2 and len(f) == 64
