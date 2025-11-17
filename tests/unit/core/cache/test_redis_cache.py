import importlib.util
import json
import pathlib
import sys
import types

import pytest

import forge.core.cache.redis_cache as redis_cache


class _FakeRedisClient:
    def __init__(self, connection_pool):  # noqa: ARG001 - signature parity
        self.storage: dict[str, bytes] = {}
        self.closed = False

    def ping(self):
        return True

    def setex(self, key, ttl, data):  # noqa: ARG002 - ttl unused in stub
        self.storage[key] = data
        return True

    def get(self, key):
        return self.storage.get(key)

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if self.storage.pop(key, None) is not None:
                removed += 1
        return removed

    def clear_storage(self):
        self.storage.clear()

    def scan(self, cursor, match=None, count=None):  # noqa: ARG002
        keys = [k for k in self.storage if match is None or k.startswith(match[:-1])]
        return (0, keys) if cursor == 0 else (0, [])

    def scan_iter(self, match=None, count=None):  # noqa: ARG002
        for key in list(self.storage.keys()):
            if match is None or key.startswith(match[:-1]):
                yield key

    def exists(self, key):
        return 1 if key in self.storage else 0

    def info(self, section=None):  # noqa: ARG002
        return {
            "total_commands_processed": 7,
            "keyspace_hits": 3,
            "keyspace_misses": 1,
            "used_memory": 4096,
            "maxmemory": 8192,
        }

    def close(self):
        self.closed = True


def _install_fake_redis(monkeypatch, client_cls=_FakeRedisClient):
    monkeypatch.setattr(redis_cache, "REDIS_AVAILABLE", True, raising=False)
    monkeypatch.setattr(
        redis_cache, "ConnectionPool", lambda **kwargs: kwargs, raising=False
    )
    monkeypatch.setattr(redis_cache, "Redis", client_cls, raising=False)


def test_distributed_cache_local_fallback(monkeypatch):
    monkeypatch.setattr(redis_cache, "REDIS_AVAILABLE", False, raising=False)
    cache = redis_cache.DistributedCache(prefix="local-test")

    assert cache.enabled is False
    assert cache.set("alpha", {"value": 1})
    assert cache.get("alpha") == {"value": 1}
    assert cache.exists("alpha") is True
    assert cache.get("missing") is None
    assert cache.get_size() == 1
    assert cache.delete("alpha") is True
    assert cache.delete("missing") is False
    assert cache.clear() is True
    assert cache.exists("missing") is False

    stats = cache.get_stats()
    assert stats["backend"] == "local"
    assert stats["total_requests"] >= 1


def test_distributed_cache_with_fake_redis(monkeypatch):
    _install_fake_redis(monkeypatch)

    cache = redis_cache.DistributedCache(
        prefix="redis-test", host="localhost", ttl_seconds=30
    )
    assert cache.enabled is True
    assert cache.client is not None

    value = {"json": True}
    assert cache.set("key-json", value)
    assert cache.get("key-json") == value

    complex_value = {"data": {1, 2, 3}}
    assert cache.set("key-pickle", complex_value)
    assert cache.get("key-pickle") == complex_value

    assert cache.exists("key-json") is True
    assert cache.delete("key-json") is True
    assert cache.get("key-json") is None

    assert cache.get_size() == 1  # only pickle entry remains
    assert cache.clear() is True
    assert cache.get_size() == 0

    stats = cache.get_stats()
    assert stats["backend"] == "redis"
    assert stats["redis_total_commands"] == 7

    cache.close()
    assert cache.client.closed is True


def test_distributed_cache_import_without_redis(monkeypatch):
    module_path = pathlib.Path(redis_cache.__file__)
    temp_name = "temp_redis_cache_no_redis"

    spec = importlib.util.spec_from_file_location(temp_name, module_path)
    temp_module = importlib.util.module_from_spec(spec)
    sys.modules[temp_name] = temp_module

    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "redis" or name.startswith("redis"):
            raise ImportError("no redis")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    try:
        assert spec.loader is not None
        spec.loader.exec_module(temp_module)
        assert temp_module.REDIS_AVAILABLE is False
    finally:
        sys.modules.pop(temp_name, None)


def test_distributed_cache_requires_host(monkeypatch):
    monkeypatch.setattr(redis_cache, "REDIS_AVAILABLE", True, raising=False)
    monkeypatch.delenv("REDIS_HOST", raising=False)
    cache = redis_cache.DistributedCache(prefix="missing-host")
    assert cache.enabled is False
    assert cache.client is None


def test_distributed_cache_connection_failure(monkeypatch):
    class _FailingRedis:
        def __init__(self, connection_pool):  # noqa: D401
            pass

        def ping(self):
            raise RuntimeError("down")

    _install_fake_redis(monkeypatch, client_cls=_FailingRedis)
    cache = redis_cache.DistributedCache(prefix="fail", host="localhost")
    assert cache.enabled is False
    assert cache.client is None


class _ErrorRedisBase(_FakeRedisClient):
    def ping(self):
        return True


class _RedisGetError(_ErrorRedisBase):
    def get(self, key):  # noqa: ARG002
        raise RuntimeError("get error")


class _RedisSetError(_ErrorRedisBase):
    def setex(self, key, ttl, data):  # noqa: ARG003
        raise RuntimeError("set error")


class _RedisDeleteError(_ErrorRedisBase):
    def delete(self, key):  # noqa: ARG002
        raise RuntimeError("delete error")


class _RedisClearError(_ErrorRedisBase):
    def scan(self, cursor, match=None, count=None):  # noqa: ARG002
        raise RuntimeError("scan error")


class _RedisExistsError(_ErrorRedisBase):
    def exists(self, key):  # noqa: ARG002
        raise RuntimeError("exists error")


class _RedisStatsError(_ErrorRedisBase):
    def info(self, section=None):  # noqa: ARG002
        raise RuntimeError("info error")


class _RedisSizeError(_ErrorRedisBase):
    def scan_iter(self, match=None, count=None):  # noqa: ARG002
        raise RuntimeError("scan_iter error")


class _RedisCloseError(_ErrorRedisBase):
    def close(self):
        raise RuntimeError("close error")


def _make_cache_with_client(monkeypatch, client_cls):
    _install_fake_redis(monkeypatch, client_cls=client_cls)
    return redis_cache.DistributedCache(prefix="redis-test", host="localhost")


def test_distributed_cache_get_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisGetError)
    assert cache.get("missing") is None
    assert cache.stats["errors"] == 1


def test_distributed_cache_set_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisSetError)
    assert cache.set("key", {"v": 1}) is False
    assert cache.stats["errors"] == 1


def test_distributed_cache_delete_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisDeleteError)
    assert cache.delete("key") is False
    assert cache.stats["errors"] == 1


def test_distributed_cache_clear_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisClearError)
    assert cache.clear() is False
    assert cache.stats["errors"] == 1


def test_distributed_cache_exists_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisExistsError)
    assert cache.exists("key") is False


def test_distributed_cache_stats_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisStatsError)
    stats = cache.get_stats()
    assert stats["backend"] == "redis"
    assert "redis_total_commands" not in stats


def test_distributed_cache_size_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisSizeError)
    assert cache.get_size() == 0


def test_distributed_cache_close_handles_error(monkeypatch):
    cache = _make_cache_with_client(monkeypatch, _RedisCloseError)
    cache.close()  # Should not raise
