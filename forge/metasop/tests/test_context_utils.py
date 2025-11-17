"""Tests for standalone MetaSOP utilities."""

from forge.metasop.context_hash import compute_context_hash, trunc
from forge.metasop.diff_utils import compute_diff_fingerprint


def test_compute_context_hash_is_deterministic_and_sorted():
    """Context hash should be stable regardless of dictionary input order."""
    retrieval_hits = [
        {
            "id": "r2",
            "score": 0.42,
            "excerpt": "Relevant details B that need truncation",
        },
        {
            "id": "r1",
            "score": 0.99,
            "excerpt": "Relevant details A that need truncation",
        },
    ]
    prior_artifacts = [
        {"artifact_hash": "abc123", "kind": "log"},
        {"hash": "def456", "kind": "report"},
    ]

    role_capabilities = ["testing", "deployment"]
    env_signature = {"os": "linux"}
    hash_one = compute_context_hash(
        step_id="step-001",
        role="engineer",
        retrieval_hits=retrieval_hits,
        prior_artifacts=prior_artifacts,
        role_capabilities=role_capabilities,
        env_signature=env_signature,
        model_name="gpt-4",
        executor_name="default",
        truncate_bytes=16,
    )

    reordered_hits = [
        {"score": hit["score"], "excerpt": hit["excerpt"], "id": hit["id"]}
        for hit in retrieval_hits
    ]
    hash_two = compute_context_hash(
        step_id="step-001",
        role="engineer",
        retrieval_hits=reordered_hits,
        prior_artifacts=prior_artifacts,
        role_capabilities=list(reversed(role_capabilities)),
        env_signature=env_signature,
        model_name="gpt-4",
        executor_name="default",
        truncate_bytes=16,
    )

    assert hash_one == hash_two


def test_compute_context_hash_detects_meaningful_changes():
    """Changing key fields should result in a different hash."""
    base_hash = compute_context_hash(
        step_id="step-001",
        role="engineer",
        retrieval_hits=[],
        prior_artifacts=[],
        role_capabilities=["analysis"],
        env_signature=None,
        model_name="gpt-4",
        executor_name="default",
    )

    changed_hash = compute_context_hash(
        step_id="step-001",
        role="engineer",
        retrieval_hits=[],
        prior_artifacts=[],
        role_capabilities=["analysis"],
        env_signature=None,
        model_name="gpt-4",
        executor_name="specialized",
    )

    assert base_hash != changed_hash


def test_compute_context_hash_truncation_variants():
    """Truncation helper inside compute_context_hash should handle limits."""
    long_hit = [{"id": "x", "score": 0.5, "excerpt": "x" * 50}]

    truncated = compute_context_hash(
        step_id="step-456",
        role="pm",
        retrieval_hits=long_hit,
        prior_artifacts=[],
        role_capabilities=[],
        env_signature=None,
        model_name=None,
        executor_name=None,
        truncate_bytes=8,
    )

    no_limit = compute_context_hash(
        step_id="step-456",
        role="pm",
        retrieval_hits=long_hit,
        prior_artifacts=[],
        role_capabilities=[],
        env_signature=None,
        model_name=None,
        executor_name=None,
        truncate_bytes=0,
    )

    assert truncated != no_limit


def test_compute_diff_fingerprint_normalises_headers_and_ranges():
    """Diff fingerprint should ignore path differences and range metadata."""
    diff_one = """--- a/src/example.py
+++ b/src/example.py
@@ -10,5 +10,5 @@
-print("hello")
+print("hello world")
"""
    diff_two = """--- C:/workspace/project/src/example.py
+++ /tmp/tmp123/src/example.py
@@ -99,3 +42,3 @@
-print("hello")
+print("hello world")
"""

    fingerprint_one = compute_diff_fingerprint(diff_one)
    fingerprint_two = compute_diff_fingerprint(diff_two)

    assert fingerprint_one == fingerprint_two


def test_compute_diff_fingerprint_handles_empty_input():
    """Empty diff inputs should still produce a deterministic hash."""
    assert compute_diff_fingerprint("") == compute_diff_fingerprint("")


def test_truncation_helper_adds_ellipsis():
    """The standalone trunc helper should append an ellipsis when shortened."""
    assert trunc("abcdefgh", 5) == "abcd…"
