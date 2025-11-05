from openhands.metasop.context_hash import compute_context_hash


def test_context_hash_stable():
    h1 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": "Alpha"}],
        prior_artifacts=[{"step_id": "s0", "artifact_hash": "H123", "role": "planner"}],
        role_capabilities=["plan"],
        env_signature={"os": "linux", "py": "3.11"},
        model_name="gemini-2.5-pro",
        executor_name="DefaultExecutor",
        truncate_bytes=256,
    )
    h2 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": "Alpha"}],
        prior_artifacts=[{"step_id": "s0", "artifact_hash": "H123", "role": "planner"}],
        role_capabilities=["plan"],
        env_signature={"os": "linux", "py": "3.11"},
        model_name="gemini-2.5-pro",
        executor_name="DefaultExecutor",
        truncate_bytes=256,
    )
    assert h1 == h2, "Context hash must be deterministic for identical inputs"


def test_context_hash_changes_with_retrieval_variation():
    h1 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": "Alpha"}],
        prior_artifacts=[],
        role_capabilities=[],
        env_signature={},
        model_name=None,
        executor_name="DefaultExecutor",
        truncate_bytes=256,
    )
    h2 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": "AlphaX"}],
        prior_artifacts=[],
        role_capabilities=[],
        env_signature={},
        model_name=None,
        executor_name="DefaultExecutor",
        truncate_bytes=256,
    )
    assert h1 != h2, "Context hash should change when retrieval content changes"


def test_context_hash_truncation():
    long_content = "A" * 5000
    h1 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": long_content}],
        prior_artifacts=[],
        role_capabilities=[],
        env_signature={},
        model_name=None,
        executor_name="DefaultExecutor",
        truncate_bytes=1024,
    )
    modified = "A" * 1024 + "B" * 3000
    h2 = compute_context_hash(
        step_id="s1",
        role="planner",
        retrieval_hits=[{"id": "r1", "score": 0.9, "content": modified}],
        prior_artifacts=[],
        role_capabilities=[],
        env_signature={},
        model_name=None,
        executor_name="DefaultExecutor",
        truncate_bytes=1024,
    )
    assert h1 == h2, "Hash should be stable when only truncated-away content differs"
