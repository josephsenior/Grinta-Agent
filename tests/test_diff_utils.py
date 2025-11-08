from forge.metasop.diff_utils import compute_diff_fingerprint

SAMPLE_A = "line1\nline2\nline3\n"
SAMPLE_B = "line1\nLINE2_changed\nline3\n"


def make_unified(a: str, b: str) -> str:
    import difflib

    return "\n".join(
        difflib.unified_diff(a.splitlines(), b.splitlines(), fromfile="a/file.txt", tofile="b/file.txt", lineterm="")
    )


def test_fingerprint_stable():
    diff1 = make_unified(SAMPLE_A, SAMPLE_B)
    diff2 = make_unified(SAMPLE_A, SAMPLE_B)
    f1 = compute_diff_fingerprint(diff1)
    f2 = compute_diff_fingerprint(diff2)
    assert f1 == f2, "Fingerprint should be stable across regenerated diffs with same semantic change"


def test_fingerprint_differs_on_semantic_change():
    diff1 = make_unified(SAMPLE_A, SAMPLE_B)
    SAMPLE_C = "line1\nLINE2_other\nline3\n"
    diff2 = make_unified(SAMPLE_A, SAMPLE_C)
    f1 = compute_diff_fingerprint(diff1)
    f2 = compute_diff_fingerprint(diff2)
    assert f1 != f2, "Different modifications should yield different fingerprints"


def test_empty_diff():
    f = compute_diff_fingerprint("")
    f2 = compute_diff_fingerprint("")
    assert f == f2 and len(f) == 64
