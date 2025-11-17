from __future__ import annotations

import builtins
import importlib
import os
from datetime import datetime, timedelta
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import forge.agenthub.readonly_agent.tools.file_cache as module
from forge.agenthub.readonly_agent.tools.file_cache import FileCache


def make_cache(tmp_path, **kwargs) -> FileCache:
    return FileCache(
        max_cache_size=kwargs.get("max_cache_size", 2),
        ttl_seconds=kwargs.get("ttl_seconds", 60),
        enable_mtime_check=kwargs.get("enable_mtime_check", True),
        use_distributed=False,
    )


def test_cache_content_and_get_content(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello", encoding="utf-8")

    assert cache.get_content(str(file_path)) is None
    cache.cache_content(str(file_path), "hello")
    assert cache.get_content(str(file_path)) == "hello"


def test_cache_content_handles_missing_file(tmp_path):
    cache = make_cache(tmp_path)
    cache.cache_content(str(tmp_path / "missing.txt"), "data")


def test_local_cache_ttl_expiry(tmp_path, monkeypatch):
    cache = make_cache(tmp_path, ttl_seconds=1)
    file_path = tmp_path / "file.txt"
    file_path.write_text("data", encoding="utf-8")
    cache.cache_content(str(file_path), "data")
    path = str(file_path)
    content, cached_at, mtime = cache.content_cache[path]
    cache.content_cache[path] = (content, cached_at - timedelta(seconds=5), mtime)
    assert cache.get_content(path) is None


def test_local_cache_detects_mtime_change(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("old", encoding="utf-8")
    cache.cache_content(str(file_path), "old")
    original_mtime = file_path.stat().st_mtime
    file_path.write_text("new", encoding="utf-8")
    os.utime(file_path, (original_mtime + 5, original_mtime + 5))
    assert cache.get_content(str(file_path)) is None


def test_local_cache_handles_missing_file(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("old", encoding="utf-8")
    cache.cache_content(str(file_path), "old")
    file_path.unlink()
    assert cache.get_content(str(file_path)) is None


def test_distributed_cache_initialization_success(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class FakeDistributed:
        def __init__(self, *args, **kwargs):
            self.enabled = True

    monkeypatch.setattr(module, "DistributedCache", FakeDistributed)
    cache = FileCache(use_distributed=True)
    assert cache.distributed_cache is not None


def test_distributed_cache_initialization_disabled(monkeypatch):
    monkeypatch.setattr(module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class Disabled:
        def __init__(self, *args, **kwargs):
            self.enabled = False

    monkeypatch.setattr(module, "DistributedCache", Disabled)
    cache = FileCache(use_distributed=True)
    assert cache.distributed_cache is None


def test_distributed_cache_initialization_failure(monkeypatch):
    monkeypatch.setattr(module, "DISTRIBUTED_CACHE_AVAILABLE", True)

    class Failing:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(module, "DistributedCache", Failing)
    cache = FileCache(use_distributed=True)
    assert cache.distributed_cache is None


def test_check_distributed_cache(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    class StubDistributed:
        def __init__(self):
            self.storage = {}

        def get(self, key):
            return self.storage.get(key)

    stub = StubDistributed()
    now = datetime.now().isoformat()
    stub.storage[str(file_path)] = ("content", now, os.path.getmtime(file_path))
    cache.distributed_cache = stub
    assert cache._check_distributed_cache(str(file_path)) == "content"


def test_check_distributed_cache_missing(tmp_path):
    cache = make_cache(tmp_path)

    class Stub:
        def get(self, key):
            return None

    cache.distributed_cache = Stub()
    assert cache._check_distributed_cache("file") is None


def test_check_distributed_cache_error(tmp_path):
    cache = make_cache(tmp_path)

    class Stub:
        def get(self, key):
            raise RuntimeError("boom")

    cache.distributed_cache = Stub()
    assert cache._check_distributed_cache("file") is None


def test_check_distributed_cache_without_mtime_check(tmp_path):
    cache = make_cache(tmp_path, enable_mtime_check=False)

    class Stub:
        def __init__(self):
            self.data = ("content", datetime.now().isoformat(), 0.0)

        def get(self, key):
            return self.data

    cache.distributed_cache = Stub()
    assert cache._check_distributed_cache("file") == "content"


def test_check_distributed_cache_invalid_mtime(tmp_path, monkeypatch):
    cache = make_cache(tmp_path)

    class Stub:
        def __init__(self):
            self.data = ("content", datetime.now().isoformat(), 0.0)

        def get(self, key):
            return self.data

    cache.distributed_cache = Stub()
    monkeypatch.setattr(cache, "_validate_mtime", lambda *a, **k: False)
    assert cache._check_distributed_cache("file") is None


def test_validate_mtime_mismatch(monkeypatch, tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")

    class StubDistributed:
        def delete(self, key):
            pass

    cache.distributed_cache = StubDistributed()
    assert cache._validate_mtime(str(file_path), 0.0) is False


def test_validate_mtime_missing_file(monkeypatch, tmp_path):
    cache = make_cache(tmp_path)
    cache.distributed_cache = SimpleNamespace(delete=lambda key: None)
    assert cache._validate_mtime(str(tmp_path / "missing.txt"), 0.0) is False


def test_check_local_cache_updates_access(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")
    cache.cache_content(str(file_path), "content")
    assert cache._check_local_cache(str(file_path)) == "content"


def test_local_cache_hit_without_mtime_check(tmp_path):
    cache = make_cache(tmp_path, enable_mtime_check=False)
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")
    cache.cache_content(str(file_path), "content")
    assert cache.get_content(str(file_path)) == "content"


def test_cache_symbols_and_structure(tmp_path):
    cache = make_cache(tmp_path)
    cache.cache_symbols("file.py", {"Func": {"line": 1}})
    assert cache.get_symbols("file.py") == {"Func": {"line": 1}}
    assert cache.get_symbols("missing.py") is None

    cache.cache_structure("file.py", {"classes": []})
    assert cache.get_structure("file.py") == {"classes": []}
    assert cache.get_structure("missing.py") is None


def test_eviction_policy(tmp_path):
    cache = make_cache(tmp_path, max_cache_size=1)
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("a", encoding="utf-8")
    file_b.write_text("b", encoding="utf-8")
    cache.cache_content(str(file_a), "a")
    cache.cache_content(str(file_b), "b")
    assert str(file_a) not in cache.content_cache or str(file_b) not in cache.content_cache


def test_evict_lru_no_entries(tmp_path):
    cache = make_cache(tmp_path)
    cache._evict_lru()


def test_clear_resets_state(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.py"
    file_path.write_text("data", encoding="utf-8")
    cache.cache_content(str(file_path), "data")
    cache.clear()
    assert cache.content_cache == {}


def test_stats_report(tmp_path):
    cache = make_cache(tmp_path)
    stats = cache.get_stats()
    assert stats["cached_files"] == 0
    assert stats["hit_rate_percent"] == 0


def test_cache_content_distributed_set_failure(tmp_path):
    cache = make_cache(tmp_path)

    class Setter:
        def set(self, *args, **kwargs):
            raise RuntimeError("boom")

    cache.distributed_cache = Setter()
    cache.cache_content(str(tmp_path / "file.txt"), "data")


def test_get_content_returns_distributed_result(tmp_path):
    cache = make_cache(tmp_path)
    file_path = tmp_path / "file.txt"
    file_path.write_text("content", encoding="utf-8")
    now = datetime.now().isoformat()

    class Stub:
        def get(self, key):
            return ("content", now, os.path.getmtime(file_path))

    cache.distributed_cache = Stub()
    assert cache.get_content(str(file_path)) == "content"


def test_module_import_fallback(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "forge.core.cache":
            raise ImportError("forced")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    mod_name = module.__name__
    reloaded = importlib.reload(sys.modules[mod_name])
    assert reloaded.DISTRIBUTED_CACHE_AVAILABLE is False

    # Restore
    monkeypatch.setattr("builtins.__import__", original_import, raising=False)
    restored = importlib.reload(sys.modules[mod_name])
    globals()["module"] = restored

