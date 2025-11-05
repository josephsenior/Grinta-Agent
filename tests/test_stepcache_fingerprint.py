import time
from openhands.metasop.cache import StepCache, StepCacheEntry


def test_get_by_fingerprint_hit_and_miss(tmp_path):
    cache_dir = str(tmp_path)
    sc = StepCache(max_entries=10, cache_dir=cache_dir, ttl_seconds=None)
    entry = StepCacheEntry(
        context_hash="ctx1",
        step_id="s1",
        role="engineer",
        artifact_content={"content": "x"},
        artifact_hash="ah",
        step_hash="sh",
        rationale=None,
        model_name="m",
        total_tokens=10,
        diff_fingerprint="fp123",
        created_ts=time.time(),
    )
    assert sc.put(entry) is True
    found = sc.get_by_fingerprint("fp123", "engineer")
    assert found is not None
    assert found.context_hash == "ctx1"
    miss = sc.get_by_fingerprint("doesnotexist", "engineer")
    assert miss is None


def test_get_by_fingerprint_ttl_expiry(tmp_path):
    sc = StepCache(max_entries=10, cache_dir=None, ttl_seconds=1)
    entry = StepCacheEntry(
        context_hash="ctx2",
        step_id="s2",
        role="engineer",
        artifact_content={"content": "y"},
        artifact_hash="ah2",
        step_hash="sh2",
        rationale=None,
        model_name="m2",
        total_tokens=5,
        diff_fingerprint="fp_exp",
        created_ts=time.time() - 2,
    )
    sc._store[entry.context_hash] = entry
    got = sc.get_by_fingerprint("fp_exp", "engineer")
    assert got is None
