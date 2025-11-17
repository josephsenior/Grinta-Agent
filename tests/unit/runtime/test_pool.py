from __future__ import annotations

import time
import types
from unittest.mock import MagicMock

import pytest

from forge.runtime.pool import (
    DelegateForkPool,
    PooledRuntime,
    WarmPoolPolicy,
    WarmRuntimePool,
)


class DummyRuntime:
    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_delegate_pool_passthrough_to_warm_pool(monkeypatch):
    warm_pool = WarmRuntimePool(max_size_per_key=1, ttl_seconds=60)
    runtime = types.SimpleNamespace(sid="session-1")
    warm_pool.release("local", PooledRuntime(runtime=runtime, repo_directory="/repo"))

    def fake_disconnect(rt):
        rt.disconnected = True

    monkeypatch.setattr("forge.runtime.pool.call_async_disconnect", fake_disconnect)

    pool = DelegateForkPool(
        fork_factory=lambda parent: parent,
        warm_pool=warm_pool,
    )

    reused = pool.acquire("local")
    assert reused.runtime is runtime


def test_delegate_pool_forks_runtime_from_parent(monkeypatch):
    warm_pool = WarmRuntimePool(max_size_per_key=1, ttl_seconds=60)
    parent_runtime = types.SimpleNamespace(sid="parent")
    warm_pool.release(
        "local", PooledRuntime(runtime=parent_runtime, repo_directory="/repo")
    )

    forked_runtime = types.SimpleNamespace(sid="delegate-child")
    fork_factory = MagicMock(return_value=forked_runtime)

    pool = DelegateForkPool(fork_factory=fork_factory, warm_pool=warm_pool)
    delegate = pool.acquire("delegate:local")

    assert delegate.runtime is forked_runtime
    assert delegate.repo_directory == "/repo"
    fork_factory.assert_called_once_with(parent_runtime)

    # Parent runtime is returned to warm pool for future acquisitions
    reused = pool.acquire("local")
    assert reused.runtime is parent_runtime


def test_delegate_pool_release_disconnects_delegate():
    warm_pool = WarmRuntimePool(max_size_per_key=1, ttl_seconds=60)
    parent_runtime = DummyRuntime("parent")
    warm_pool.release("local", PooledRuntime(runtime=parent_runtime))

    pool = DelegateForkPool(
        fork_factory=lambda parent: DummyRuntime(f"{parent.sid}-child"),
        warm_pool=warm_pool,
    )
    delegate = pool.acquire("delegate:local")
    pool.release("delegate:local", delegate)

    assert delegate.runtime.closed is True


def test_warm_pool_cleanup_expired():
    pool = WarmRuntimePool(max_size_per_key=2, ttl_seconds=0.01)
    runtime = DummyRuntime("cleanup-test")
    pool.release("docker", PooledRuntime(runtime=runtime))
    time.sleep(0.02)
    removed = pool.cleanup_expired()
    assert removed == 1
    assert runtime.closed is True
    idle = pool.idle_reclaim_stats()
    assert idle.get("docker") == 1


def test_warm_pool_remove_runtime():
    pool = WarmRuntimePool(max_size_per_key=2, ttl_seconds=600)
    runtime = DummyRuntime("remove-test")
    pool.release("docker", PooledRuntime(runtime=runtime))
    removed = pool.remove_runtime("docker", runtime)
    assert removed is True
    assert runtime.closed is True
    assert pool.stats().get("docker", 0) == 0


def test_warm_pool_records_evictions():
    pool = WarmRuntimePool(max_size_per_key=1, ttl_seconds=600)
    first = DummyRuntime("first")
    second = DummyRuntime("second")
    pool.release("docker", PooledRuntime(runtime=first))
    pool.release("docker", PooledRuntime(runtime=second))
    # first should be evicted due to capacity
    assert first.closed is True
    assert second.closed is False
    evictions = pool.eviction_stats()
    assert evictions.get("docker") == 1


def test_warm_pool_policy_overrides_enforced(monkeypatch):
    pool = WarmRuntimePool(max_size_per_key=2, ttl_seconds=600)
    pool.configure_policies(
        WarmPoolPolicy(max_size=2, ttl_seconds=600),
        {"docker": WarmPoolPolicy(max_size=1, ttl_seconds=0.01)},
    )
    first = DummyRuntime("policy-first")
    second = DummyRuntime("policy-second")
    pool.release("docker", PooledRuntime(runtime=first))
    pool.release("docker", PooledRuntime(runtime=second))
    assert first.closed is True  # evicted due to override max_size=1
    time.sleep(0.02)
    removed = pool.cleanup_expired()
    assert removed == 1  # second runtime expired due to short TTL
    idle = pool.idle_reclaim_stats()
    assert idle.get("docker") >= 1


def test_warm_pool_disable_policy_drops_existing(monkeypatch):
    pool = WarmRuntimePool(max_size_per_key=2, ttl_seconds=600)
    first = DummyRuntime("existing")
    pool.release("docker", PooledRuntime(runtime=first))
    pool.configure_policies(
        WarmPoolPolicy(max_size=0, ttl_seconds=600),
        {},
    )
    assert first.closed is True
    assert pool.stats().get("docker") is None

