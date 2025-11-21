from __future__ import annotations

import os
from datetime import datetime, timedelta
import importlib
import builtins
import json
from pathlib import Path
from typing import Set
from types import SimpleNamespace

import pytest

from forge.agenthub.loc_agent.graph_cache import GraphCache
from forge.agenthub.loc_agent import graph_cache as graph_cache_module


def make_cache(tmp_path, **kwargs) -> GraphCache:
    cache_dir = tmp_path / "cache"
    return GraphCache(
        cache_dir=str(cache_dir),
        ttl_seconds=kwargs.get("ttl_seconds", 3600),
        enable_persistence=kwargs.get("enable_persistence", False),
        use_distributed=False,
    )


def test_cache_graph_and_get_graph_hit(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-A"
    assert cache.get_graph(repo) is None

    cache.cache_graph(repo, {"nodes": 1})
    assert cache.get_graph(repo) == {"nodes": 1}

    stats = cache.get_stats()
    assert stats["cached_repos"] == 1
    assert stats["hits"] >= 1


def test_ttl_invalidation(tmp_path):
    cache = make_cache(tmp_path, ttl_seconds=1)
    repo = "repo-ttl"
    cache.cache_graph(repo, {"graph": True})
    cache.graph_metadata[repo]["cached_at"] = datetime.now() - timedelta(seconds=5)

    assert cache.get_graph(repo) is None
    assert repo not in cache.graph_cache


def test_detects_file_modifications(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-mod"
    tracked_file = tmp_path / "module.py"
    tracked_file.write_text("print('hi')", encoding="utf-8")

    cache.cache_graph(repo, {"graph": []}, tracked_files={str(tracked_file)})
    original_mtime = tracked_file.stat().st_mtime
    tracked_file.write_text("print('bye')", encoding="utf-8")
    os.utime(tracked_file, (original_mtime + 10, original_mtime + 10))

    assert cache.get_graph(repo) is None
    assert cache.stats["partial_updates"] == 1


def test_persistence_round_trip(tmp_path):
    cache_dir = tmp_path / "persist"
    cache = GraphCache(
        cache_dir=str(cache_dir),
        ttl_seconds=3600,
        enable_persistence=True,
        use_distributed=False,
    )
    repo = "repo-persist"
    cache.cache_graph(repo, {"foo": "bar"})

    cache2 = GraphCache(
        cache_dir=str(cache_dir),
        ttl_seconds=3600,
        enable_persistence=True,
        use_distributed=False,
    )
    assert cache2.get_graph(repo) == {"foo": "bar"}


def test_clear_removes_all_entries(tmp_path):
    cache = make_cache(tmp_path)
    cache.cache_graph("repo", {"data": 1})
    cache.clear()

    stats = cache.get_stats()
    assert stats["cached_repos"] == 0
    assert cache.graph_cache == {}


def test_cache_graph_tracks_files(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-files"
    tracked_file = tmp_path / "tracked.py"
    tracked_file.write_text("x = 1", encoding="utf-8")
    tracked: Set[str] = {str(tracked_file)}

    cache.cache_graph(repo, {"graph": {}}, tracked_files=tracked)
    assert repo in cache.file_mtimes
    assert str(tracked_file) in cache.file_mtimes[repo]
    assert cache.stats["files_tracked"] == 1


def test_distributed_cache_initialization_success(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_cache_module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class FakeDistributedCache:
        def __init__(self, *args, **kwargs):
            self.enabled = True

    monkeypatch.setattr(graph_cache_module, "DistributedCache", FakeDistributedCache)
    cache = GraphCache(
        cache_dir=str(tmp_path / "cache"),
        ttl_seconds=10,
        enable_persistence=False,
        use_distributed=True,
    )
    assert cache.distributed_cache is not None


def test_distributed_cache_initialization_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_cache_module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class FailingDistributed:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(graph_cache_module, "DistributedCache", FailingDistributed)
    cache = GraphCache(
        cache_dir=str(tmp_path / "cache"),
        ttl_seconds=10,
        enable_persistence=False,
        use_distributed=True,
    )
    assert cache.distributed_cache is None


def test_distributed_cache_disabled_when_not_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(graph_cache_module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class DisabledDistributed:
        def __init__(self, *args, **kwargs):
            self.enabled = False

    monkeypatch.setattr(graph_cache_module, "DistributedCache", DisabledDistributed)
    cache = GraphCache(
        cache_dir=str(tmp_path / "cache"),
        ttl_seconds=10,
        enable_persistence=False,
        use_distributed=True,
    )
    assert cache.distributed_cache is None


def test_load_from_distributed_cache(tmp_path):
    cache = make_cache(tmp_path)

    class StubDistributed:
        def __init__(self):
            self.storage = {}

        def get(self, key):
            return self.storage.get(key)

    repo = "repo-distributed"
    stub = StubDistributed()
    stub.storage[repo] = {
        "graph": {"value": 42},
        "metadata": {"cached_at": datetime.now()},
        "file_mtimes": {},
    }
    cache.distributed_cache = stub
    assert cache._load_from_distributed_cache(repo) is True
    assert cache.graph_cache[repo]["value"] == 42


def test_get_graph_uses_distributed_cache(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-l2"

    class StubDistributed:
        def __init__(self):
            self.result = {
                "graph": {"value": 99},
                "metadata": {"cached_at": datetime.now()},
                "file_mtimes": {},
            }

        def get(self, key):
            return self.result if key == repo else None

    cache.distributed_cache = StubDistributed()
    assert cache.get_graph(repo)["value"] == 99


def test_load_from_distributed_cache_handles_error(tmp_path):
    cache = make_cache(tmp_path)

    class BadDistributed:
        def get(self, key):
            raise RuntimeError("boom")

    cache.distributed_cache = BadDistributed()
    assert cache._load_from_distributed_cache("repo-error") is False


def test_load_from_distributed_cache_miss(tmp_path):
    cache = make_cache(tmp_path)
    cache.distributed_cache = SimpleNamespace(get=lambda key: None)
    assert cache._load_from_distributed_cache("repo-miss") is False
    assert cache.stats["distributed_misses"] >= 1


def test_cache_graph_writes_to_distributed(tmp_path):
    cache = make_cache(tmp_path)

    class Setter:
        def __init__(self):
            self.saved = {}

        def set(self, repo, data):
            self.saved[repo] = data

    setter = Setter()
    cache.distributed_cache = setter
    cache.cache_graph("repo-dist", {"foo": "bar"})
    assert "repo-dist" in setter.saved


def test_deleted_file_invalidates_cache(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-delete"
    tracked_file = tmp_path / "deleted.py"
    tracked_file.write_text("print('hi')", encoding="utf-8")
    cache.cache_graph(repo, {"graph": []}, tracked_files={str(tracked_file)})
    tracked_file.unlink()
    assert cache.get_graph(repo) is None


def test_save_to_disk_handles_errors(monkeypatch, tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )

    def boom(*args, **kwargs):
        raise RuntimeError("dump failed")

    monkeypatch.setattr(graph_cache_module.json, "dump", boom)
    cache.cache_graph("repo", {"x": 1})


def test_load_from_disk_handles_corrupt_file(tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )
    repo = "repo-corrupt"
    cache_file = cache._get_cache_file_path(repo)
    Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    Path(cache_file).write_text("{invalid json}", encoding="utf-8")
    cache._load_from_persistence(repo)


def test_cache_graph_handles_missing_tracked_file(tmp_path):
    cache = make_cache(tmp_path)
    missing = tmp_path / "missing.py"
    cache.cache_graph("repo-missing", {"g": 1}, tracked_files={str(missing)})
    assert cache.file_mtimes["repo-missing"] == {}


def test_distributed_set_failure_is_handled(tmp_path):
    cache = make_cache(tmp_path)

    class FailingSetter:
        def set(self, repo, data):
            raise RuntimeError("boom")

    cache.distributed_cache = FailingSetter()
    cache.cache_graph("repo-fail", {"data": 1})


def test_save_and_load_disk_roundtrip_direct(tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )
    repo = "repo-direct"
    cache.graph_cache[repo] = {"value": 1}
    cache.graph_metadata[repo] = {"cached_at": datetime.now()}
    cache.file_mtimes[repo] = {}
    cache._save_to_disk(repo)
    cache.graph_cache.clear()
    cache.graph_metadata.clear()
    cache._load_from_disk(repo)
    assert isinstance(cache.graph_metadata[repo]["cached_at"], datetime)


def test_save_to_disk_without_cached_at(tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )
    repo = "repo-no-meta"
    cache.graph_cache[repo] = {"value": 0}
    cache.graph_metadata[repo] = {}
    cache.file_mtimes[repo] = {}
    cache._save_to_disk(repo)


def test_load_from_disk_missing_file(tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )
    cache._load_from_disk("does-not-exist")


def test_load_from_disk_without_cached_at(tmp_path):
    cache = GraphCache(
        cache_dir=str(tmp_path / "persist"),
        ttl_seconds=10,
        enable_persistence=True,
        use_distributed=False,
    )
    repo = "repo-no-cached-at"
    cache_file = cache._get_cache_file_path(repo)
    Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    Path(cache_file).write_text(
        json.dumps({"graph": {}, "metadata": {}, "file_mtimes": {}}),
        encoding="utf-8",
    )
    cache._load_from_disk(repo)


def test_has_modifications_false(tmp_path):
    cache = make_cache(tmp_path)
    repo = "repo-clean"
    tracked_file = tmp_path / "clean.py"
    tracked_file.write_text("x = 1", encoding="utf-8")
    cache.cache_graph(repo, {"data": 1}, tracked_files={str(tracked_file)})
    assert cache._has_modifications(repo) is False


def test_module_import_fallback(monkeypatch):
    import forge.agenthub.loc_agent.graph_cache as gc

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "forge.core.cache":
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    reloaded = importlib.reload(gc)
    assert reloaded.DISTRIBUTED_CACHE_AVAILABLE is False
    globals()["GraphCache"] = reloaded.GraphCache
    globals()["graph_cache_module"] = reloaded

    # Restore original module state for other tests
    monkeypatch.setattr("builtins.__import__", original_import, raising=False)
    restored = importlib.reload(gc)
    globals()["GraphCache"] = restored.GraphCache
    globals()["graph_cache_module"] = restored

