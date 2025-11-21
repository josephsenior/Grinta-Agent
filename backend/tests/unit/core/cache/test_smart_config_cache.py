import importlib.util
import pathlib
import sys
import types

import pytest

import forge.core.cache.smart_config_cache as smart_cache


class _BaseRedis:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        self.storage: dict[str, bytes] = {}

    def ping(self):
        return True

    def get(self, key):
        return self.storage.get(key)

    def setex(self, key, ttl, value):  # noqa: ARG002 - ttl unused in stub
        self.storage[key] = value
        return True

    def delete(self, key):
        self.storage.pop(key, None)
        return 1

    def info(self):
        return {
            "used_memory": 1024,
            "total_commands_processed": 12,
            "keyspace_hits": 2,
            "keyspace_misses": 1,
        }

    def keys(self, pattern):
        prefix = pattern.replace("*", "")
        return [k for k in self.storage if k.startswith(prefix)]


class _RedisPingError(_BaseRedis):
    def ping(self):
        raise RuntimeError("ping fail")


class _RedisGetError(_BaseRedis):
    def get(self, key):  # noqa: ARG002
        raise RuntimeError("get error")


class _RedisSetError(_BaseRedis):
    def setex(self, key, ttl, value):  # noqa: ARG003
        raise RuntimeError("set error")


class _RedisDeleteError(_BaseRedis):
    def delete(self, key):  # noqa: ARG002
        raise RuntimeError("delete error")


class _RedisKeysError(_BaseRedis):
    def keys(self, pattern):  # noqa: ARG002
        raise RuntimeError("keys error")


class _RedisInfoError(_BaseRedis):
    def info(self, section=None):  # noqa: ARG002
        raise RuntimeError("info error")


def _install_sync_redis(monkeypatch, client_cls):
    monkeypatch.setattr(smart_cache, "REDIS_AVAILABLE", True, raising=False)
    fake_module = types.SimpleNamespace(Redis=client_cls)
    monkeypatch.setattr(smart_cache, "redis", fake_module)


class _SyncSettings:
    def __init__(self):
        self.merge_calls = 0

    def merge_with_config_settings(self):
        self.merge_calls += 1
        return types.SimpleNamespace(merged=True)


class _SyncStore:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def load(self):
        self.calls += 1
        return self.result


def test_smart_config_cache_memory(monkeypatch):
    monkeypatch.setattr(smart_cache, "REDIS_AVAILABLE", False, raising=False)
    cache = smart_cache.SmartConfigCache()

    calls = {"count": 0}

    def fake_load_config():
        calls["count"] += 1
        return {"value": "memory"}

    monkeypatch.setattr("forge.core.config.utils.load_FORGE_config", fake_load_config)

    cfg1 = cache.get_global_config()
    cfg2 = cache.get_global_config()
    assert cfg1 == cfg2 == {"value": "memory"}
    assert calls["count"] == 1

    settings = _SyncSettings()
    store = _SyncStore(settings)
    merged1 = cache.get_user_settings("user", store, None)
    merged2 = cache.get_user_settings("user", store, None)

    assert merged1 is merged2
    assert store.calls == 1
    assert settings.merge_calls == 1

    cache.invalidate_user_cache("user")
    assert "user" not in cache._user_settings_cache

    stats = cache.get_cache_stats()
    assert stats["cache_type"] == "memory"
    assert stats["global_config_cached"] is True

    cache.invalidate_global_cache()
    stats_after = cache.get_cache_stats()
    assert stats_after["global_config_cached"] is False


def test_smart_config_cache_with_fake_redis(monkeypatch):
    _install_sync_redis(monkeypatch, _BaseRedis)
    cache = smart_cache.SmartConfigCache(
        redis_host="localhost", redis_port=6379, redis_password="secret"
    )

    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"value": "redis"}
    )

    cfg = cache.get_global_config()
    assert cfg == {"value": "redis"}
    assert "smart_cache:global_config" in cache.redis.storage

    settings = _SyncSettings()
    store = _SyncStore(settings)
    merged = cache.get_user_settings("uid", store, None)
    cached = cache.get_user_settings("uid", store, None)
    assert merged.merged is True
    assert cached.merged is True
    assert store.calls == 1

    stats = cache.get_cache_stats()
    assert stats["cache_type"] == "redis"
    assert stats["global_config_cached"] is True
    assert stats["cached_users"] == 1

    cache.invalidate_user_cache("uid")
    assert "smart_cache:user_settings:uid" not in cache.redis.storage

    cache.invalidate_global_cache()
    assert "smart_cache:global_config" not in cache.redis.storage


def test_smart_config_cache_import_without_redis(monkeypatch):
    module_path = pathlib.Path(smart_cache.__file__)
    temp_name = "temp_smart_cache_no_redis"

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


def test_smart_config_cache_connection_failure(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisPingError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    assert cache.redis_available is False
    assert hasattr(cache, "_global_config_cache")


def test_smart_config_cache_global_config_error(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisGetError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"fallback": True}
    )
    cfg = cache.get_global_config()
    assert cfg == {"fallback": True}


def test_smart_config_cache_user_settings_none(monkeypatch):
    _install_sync_redis(monkeypatch, _BaseRedis)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    store = _SyncStore(None)
    assert cache.get_user_settings("missing", store, None) is None


def test_smart_config_cache_user_settings_without_global_config(monkeypatch):
    _install_sync_redis(monkeypatch, _BaseRedis)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    settings = _SyncSettings()
    store = _SyncStore(settings)

    monkeypatch.setattr(cache, "get_global_config", lambda: None)
    merged = cache.get_user_settings("user", store, None)
    assert merged is settings
    assert settings.merge_calls == 0


def test_smart_config_cache_user_settings_error_fallback(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisSetError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    settings = _SyncSettings()
    store = _SyncStore(settings)
    result = cache.get_user_settings("user", store, None)
    assert isinstance(result, types.SimpleNamespace)
    assert store.calls == 2  # initial load + fallback load


def test_smart_config_cache_user_settings_error_no_settings(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisSetError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    settings = _SyncSettings()

    class _FlakyStore:
        def __init__(self, first):
            self.first = first
            self.calls = 0

        def load(self):
            self.calls += 1
            if self.calls == 1:
                return self.first
            return None

    store = _FlakyStore(settings)
    assert cache.get_user_settings("user", store, None) is None
    assert store.calls == 2


def test_smart_config_cache_memory_user_settings_none(monkeypatch):
    cache = smart_cache.SmartConfigCache()
    store = _SyncStore(None)
    assert cache.get_user_settings("user", store, None) is None


def test_smart_config_cache_memory_user_settings_without_global(monkeypatch):
    cache = smart_cache.SmartConfigCache()
    settings = _SyncSettings()
    store = _SyncStore(settings)
    monkeypatch.setattr(cache, "get_global_config", lambda: None)
    merged = cache.get_user_settings("user", store, None)
    assert merged is settings
    assert settings.merge_calls == 0


def test_smart_config_cache_invalidate_user_cache_error(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisDeleteError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    cache.invalidate_user_cache("user")  # Should not raise


def test_smart_config_cache_invalidate_global_cache_error(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisDeleteError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    cache._global_config_cache = {"exists": True}
    cache.invalidate_global_cache()
    assert cache._global_config_cache == {"exists": True}


def test_smart_config_cache_stats_with_error(monkeypatch):
    _install_sync_redis(monkeypatch, _RedisKeysError)
    cache = smart_cache.SmartConfigCache(redis_host="localhost")
    stats = cache.get_cache_stats()
    assert stats["cache_type"] == "redis"
    assert "redis_error" in stats


def test_smart_config_cache_stats_memory(monkeypatch):
    cache = smart_cache.SmartConfigCache()
    stats = cache.get_cache_stats()
    assert stats["cache_type"] == "memory"


def test_get_smart_config_cache_singleton(monkeypatch):
    monkeypatch.setattr(smart_cache, "_smart_cache", None, raising=False)
    monkeypatch.setattr(smart_cache, "REDIS_AVAILABLE", False, raising=False)
    cache_first = smart_cache.get_smart_cache()
    cache_second = smart_cache.get_smart_cache()
    assert cache_first is cache_second
