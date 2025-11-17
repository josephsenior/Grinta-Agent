import types
import fnmatch
import importlib.util
import pathlib
import sys
from typing import TYPE_CHECKING, Any, cast

import pytest

import forge.core.cache.async_smart_cache as async_cache

if TYPE_CHECKING:
    from forge.core.config.forge_config import ForgeConfig as ForgeConfigType
    from forge.storage.data_models.settings import Settings as SettingsType
    from forge.storage.settings.settings_store import SettingsStore as SettingsStoreType
else:  # pragma: no cover - typing fallbacks
    ForgeConfigType = Any
    SettingsType = Any
    SettingsStoreType = Any


class _DummySettings:
    def __init__(self):
        self.merge_calls = 0

    def merge_with_config_settings(self) -> SettingsType:
        self.merge_calls += 1
        return cast(SettingsType, types.SimpleNamespace(merged=True))


class _AsyncStore:
    def __init__(self, result: Any):
        self._result: Any = result
        self.calls = 0

    async def load(self) -> Any:
        self.calls += 1
        return self._result


def _as_store(store: _AsyncStore) -> SettingsStoreType:
    return cast(SettingsStoreType, store)


class _StubAsyncRedis:
    def __init__(self):
        self.storage: dict[str, bytes] = {}
        self.closed = False
        self.pings = 0

    async def ping(self):
        self.pings += 1
        return True

    async def get(self, key):
        return self.storage.get(key)

    async def setex(self, key, ttl, value):  # noqa: ARG002 - ttl unused in stub
        self.storage[key] = value
        return True

    async def delete(self, key):
        self.storage.pop(key, None)
        return True

    async def info(self):
        return {
            "used_memory": 2048,
            "total_commands_processed": 42,
            "keyspace_hits": 5,
            "keyspace_misses": 1,
        }

    async def keys(self, pattern):
        return [k for k in self.storage if fnmatch.fnmatch(k, pattern)]

    async def close(self):
        self.closed = True
        return True


class _ErroringRedis(_StubAsyncRedis):
    async def get(self, key):  # noqa: ARG002
        raise RuntimeError("boom")


class _DeleteErrorRedis(_StubAsyncRedis):
    async def delete(self, key):  # noqa: ARG002
        raise RuntimeError("cannot delete")


@pytest.mark.asyncio
async def test_global_config_memory_cache(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", False, raising=False)
    cache = async_cache.AsyncSmartCache()

    calls = {"count": 0}

    def fake_load_config():
        calls["count"] += 1
        return {"value": "memory"}

    monkeypatch.setattr("forge.core.config.utils.load_FORGE_config", fake_load_config)

    first = await cache.get_global_config()
    second = await cache.get_global_config()

    assert first == second == {"value": "memory"}
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_user_settings_memory_cache(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", False, raising=False)
    cache = async_cache.AsyncSmartCache()

    settings = _DummySettings()
    store = _AsyncStore(settings)

    async def fake_global_config():
        return {"cfg": True}

    monkeypatch.setattr("forge.core.config.utils.load_FORGE_config", fake_global_config)

    merged_first = cast(Any, await cache.get_user_settings("user", _as_store(store)))
    merged_second = cast(Any, await cache.get_user_settings("user", _as_store(store)))

    assert merged_first is merged_second
    assert store.calls == 1
    assert settings.merge_calls == 1
    assert merged_first.merged is True

    await cache.invalidate_user_cache("user")
    assert "user" not in cache._user_settings_cache


@pytest.mark.asyncio
async def test_memory_cache_stats_and_invalidation(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", False, raising=False)
    cache = async_cache.AsyncSmartCache()

    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"cfg": True}
    )

    await cache.get_global_config()

    stats = await cache.get_cache_stats()
    assert stats["cache_type"] == "memory"
    assert stats["global_config_cached"] is True
    assert stats["cached_users"] == 0

    await cache.invalidate_global_cache()
    stats_after = await cache.get_cache_stats()
    assert stats_after["global_config_cached"] is False


@pytest.mark.asyncio
async def test_async_cache_redis_flow(monkeypatch):
    stub_client = _StubAsyncRedis()

    async def fake_from_url(*_args, **_kwargs):
        return stub_client

    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", True, raising=False)
    monkeypatch.setattr(
        async_cache,
        "aioredis",
        types.SimpleNamespace(from_url=fake_from_url),
        raising=False,
    )

    cache = async_cache.AsyncSmartCache(
        redis_host="localhost", redis_port=1234, redis_password="secret"
    )

    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"value": "redis"}
    )

    config = await cache.get_global_config()
    assert config == {"value": "redis"}
    assert "smart_cache:global_config" in stub_client.storage

    settings = _DummySettings()
    store = _AsyncStore(settings)

    merged = cast(Any, await cache.get_user_settings("uid-1", _as_store(store)))
    assert store.calls == 1
    assert merged.merged is True

    merged_again = cast(Any, await cache.get_user_settings("uid-1", _as_store(store)))
    assert store.calls == 1  # cached
    assert merged_again.merged is True

    stats = await cache.get_cache_stats()
    assert stats["cache_type"] == "redis"
    assert stats["global_config_cached"] is True
    assert stats["cached_users"] == 1

    await cache.invalidate_user_cache("uid-1")
    assert "smart_cache:user_settings:uid-1" not in stub_client.storage

    await cache.invalidate_global_cache()
    assert "smart_cache:global_config" not in stub_client.storage

    await cache.close()
    assert stub_client.closed is True


def test_async_cache_import_without_aioredis(monkeypatch):
    module_path = pathlib.Path(async_cache.__file__)
    temp_name = "temp_async_cache_no_redis"

    spec = importlib.util.spec_from_file_location(temp_name, module_path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    temp_module = importlib.util.module_from_spec(spec)
    sys.modules[temp_name] = temp_module
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "redis.asyncio":
            raise ImportError("no redis asyncio")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    try:
        loader.exec_module(temp_module)
        assert temp_module.REDIS_AVAILABLE is False
    finally:
        sys.modules.pop(temp_name, None)


@pytest.mark.asyncio
async def test_async_cache_connection_failure_falls_back(monkeypatch):
    async def failing_from_url(*_args, **_kwargs):
        raise RuntimeError("connect fail")

    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", True, raising=False)
    monkeypatch.setattr(
        async_cache,
        "aioredis",
        types.SimpleNamespace(from_url=failing_from_url),
        raising=False,
    )

    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    success = await cache._ensure_connection()
    assert success is False

    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"v": "memory"}
    )
    result = await cache.get_global_config()
    assert result == {"v": "memory"}


@pytest.mark.asyncio
async def test_async_cache_ping_failure_triggers_reconnect(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", True, raising=False)

    class _FailingPing:
        def __init__(self):
            self.calls = 0

        async def ping(self):
            self.calls += 1
            raise RuntimeError("ping fail")

    async def returning_client(*_args, **_kwargs):
        return _StubAsyncRedis()

    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    first = _FailingPing()
    second = _FailingPing()
    cache.redis_available = True
    cache.redis_client = cast(Any, first)

    class _InjectingLock:
        def __init__(self, cache_ref):
            self.cache_ref = cache_ref

        async def __aenter__(self):
            self.cache_ref.redis_client = cast(Any, second)
            return None

        async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
            return False

    setattr(cache, "_connection_lock", cast(Any, _InjectingLock(cache)))
    monkeypatch.setattr(
        async_cache,
        "aioredis",
        types.SimpleNamespace(from_url=returning_client),
        raising=False,
    )

    assert await cache._ensure_connection() is True
    assert isinstance(cache.redis_client, _StubAsyncRedis)


@pytest.mark.asyncio
async def test_async_cache_redis_global_config_error_fallback(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", True, raising=False)
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_client = cast(Any, _ErroringRedis())
    cache.redis_available = True

    monkeypatch.setattr(
        "forge.core.config.utils.load_FORGE_config", lambda: {"fallback": True}
    )
    config = await cache.get_global_config()
    assert config == {"fallback": True}


@pytest.mark.asyncio
async def test_async_cache_redis_user_settings_none(monkeypatch):
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_client = cast(Any, _StubAsyncRedis())
    cache.redis_available = True

    store = _AsyncStore(None)
    result = await cache._get_user_settings_redis("missing", _as_store(store))
    assert result is None


@pytest.mark.asyncio
async def test_async_cache_redis_user_settings_without_global_config(monkeypatch):
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    client = _StubAsyncRedis()
    cache.redis_client = cast(Any, client)
    cache.redis_available = True

    settings = _DummySettings()
    store = _AsyncStore(settings)

    async def no_global_config():
        return None

    setattr(cache, "get_global_config", cast(Any, no_global_config))

    merged = await cache._get_user_settings_redis("user", _as_store(store))
    assert merged is settings
    assert settings.merge_calls == 0


@pytest.mark.asyncio
async def test_async_cache_redis_user_settings_error_fallback(monkeypatch):
    cache = async_cache.AsyncSmartCache(redis_host="localhost")

    class _BrokenRedis(_StubAsyncRedis):
        async def get(self, key):  # noqa: ARG002
            raise RuntimeError("boom")

    cache.redis_client = cast(Any, _BrokenRedis())
    cache.redis_available = True

    settings = _DummySettings()
    store = _AsyncStore(settings)

    async def fake_memory(user_id, settings_store):  # noqa: ARG001
        return "memory-result"

    setattr(cache, "_get_user_settings_memory", cast(Any, fake_memory))

    result = await cache._get_user_settings_redis("user", _as_store(store))
    assert result == "memory-result"


@pytest.mark.asyncio
async def test_async_cache_memory_user_settings_none(monkeypatch):
    cache = async_cache.AsyncSmartCache()

    store = _AsyncStore(None)
    result = await cache._get_user_settings_memory("user", _as_store(store))
    assert result is None


@pytest.mark.asyncio
async def test_async_cache_memory_user_settings_without_global_config(monkeypatch):
    cache = async_cache.AsyncSmartCache()
    settings = _DummySettings()
    store = _AsyncStore(settings)

    async def no_global_config():
        return None

    setattr(cache, "get_global_config", cast(Any, no_global_config))

    merged = await cache._get_user_settings_memory("user", _as_store(store))
    assert merged is settings
    assert settings.merge_calls == 0


@pytest.mark.asyncio
async def test_async_cache_invalidate_user_cache_error(monkeypatch):
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_available = True
    cache.redis_client = cast(Any, _DeleteErrorRedis())
    cache._user_settings_cache["user"] = cast(Any, (types.SimpleNamespace(), 0.0))

    await cache.invalidate_user_cache("user")
    assert "user" not in cache._user_settings_cache


@pytest.mark.asyncio
async def test_async_cache_invalidate_global_cache_error(monkeypatch):
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_available = True
    cache.redis_client = cast(Any, _DeleteErrorRedis())
    cache._global_config_cache = cast(ForgeConfigType, {"exists": True})

    await cache.invalidate_global_cache()
    assert cache._global_config_cache is None


@pytest.mark.asyncio
async def test_async_cache_stats_error(monkeypatch):
    class _StatsRedis(_StubAsyncRedis):
        async def keys(self, pattern):  # noqa: ARG002
            raise RuntimeError("bad keys")

    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_available = True
    cache.redis_client = cast(Any, _StatsRedis())

    stats = await cache.get_cache_stats()
    assert stats["cache_type"] == "redis"
    assert "redis_error" in stats


@pytest.mark.asyncio
async def test_async_cache_close_error(monkeypatch):
    class _ClosingRedis(_StubAsyncRedis):
        async def close(self):
            raise RuntimeError("cannot close")

    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_available = True
    cache.redis_client = cast(Any, _ClosingRedis())

    await cache.close()  # Should not raise


@pytest.mark.asyncio
async def test_get_async_smart_cache_singleton(monkeypatch):
    monkeypatch.setattr(async_cache, "_async_smart_cache", None, raising=False)
    monkeypatch.setenv("REDIS_HOST", "redis-host")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD", "pwd")

    cache_first = await async_cache.get_async_smart_cache()
    cache_second = await async_cache.get_async_smart_cache()

    assert cache_first is cache_second


@pytest.mark.asyncio
async def test_async_cache_lock_returns_existing_connection(monkeypatch):
    monkeypatch.setattr(async_cache, "REDIS_AVAILABLE", True, raising=False)
    cache = async_cache.AsyncSmartCache(redis_host="localhost")
    cache.redis_available = True
    cache.redis_client = None

    class _AssigningLock:
        def __init__(self, cache_ref):
            self.cache_ref = cache_ref
            self.client = None

        async def __aenter__(self):
            self.client = _StubAsyncRedis()
            self.cache_ref.redis_client = cast(Any, self.client)
            return None

        async def __aexit__(self, exc_type, exc, tb):  # noqa: D401
            return False

    setattr(cache, "_connection_lock", cast(Any, _AssigningLock(cache)))

    assert await cache._ensure_connection() is True
    assert isinstance(cache.redis_client, _StubAsyncRedis)
