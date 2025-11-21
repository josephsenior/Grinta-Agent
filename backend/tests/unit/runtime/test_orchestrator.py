from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.core.config import ForgeConfig
from forge.core.config.runtime_pool_config import RuntimePoolPolicy
from forge.runtime.orchestrator import RuntimeAcquireResult, RuntimeOrchestrator
from forge.runtime.pool import RuntimePool, WarmPoolPolicy, WarmRuntimePool


@pytest.mark.asyncio
async def test_orchestrator_acquire_and_release(monkeypatch):
    runtime = types.SimpleNamespace(
        sid="session-1",
        connect=AsyncMock(),
        disconnect=MagicMock(),
    )

    def fake_create_runtime(*args, **kwargs):
        return runtime

    monkeypatch.setattr("forge.runtime.orchestrator.create_runtime", fake_create_runtime)

    call_async = MagicMock()
    monkeypatch.setattr(
        "forge.runtime.orchestrator.call_async_from_sync",
        call_async,
    )

    orchestrator = RuntimeOrchestrator()
    repo_initializer_called = {}

    def repo_initializer(rt):
        repo_initializer_called["runtime"] = rt
        return "/tmp/repo"

    result = orchestrator.acquire(
        config=MagicMock(),
        llm_registry=MagicMock(),
        session_id="session-1",
        agent=MagicMock(),
        headless_mode=True,
        git_provider_tokens=None,
        repo_initializer=repo_initializer,
    )

    assert result.runtime is runtime
    assert result.repo_directory == "/tmp/repo"
    assert repo_initializer_called["runtime"] is runtime

    orchestrator.release(result, key="local")
    call_async.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_reuses_from_warm_pool(monkeypatch):
    runtime = types.SimpleNamespace(sid="session-1")

    pool = WarmRuntimePool(max_size_per_key=1, ttl_seconds=60)
    telemetry = MagicMock()

    orchestrator = RuntimeOrchestrator(pool=pool, telemetry=telemetry)

    # First acquire should create runtime via create_runtime
    def fake_create_runtime(*args, **kwargs):
        return runtime

    monkeypatch.setattr("forge.runtime.orchestrator.create_runtime", fake_create_runtime)

    result = orchestrator.acquire(
        config=MagicMock(runtime="local"),
        llm_registry=MagicMock(),
        session_id="session-1",
        agent=MagicMock(),
        headless_mode=True,
        git_provider_tokens=None,
    )

    # Release into pool
    orchestrator.release(result, key="local")

    # Second acquire should reuse from pool
    reused = orchestrator.acquire(
        config=MagicMock(runtime="local"),
        llm_registry=MagicMock(),
        session_id="session-2",
        agent=MagicMock(),
        headless_mode=True,
        git_provider_tokens=None,
    )

    assert reused.runtime is runtime
    telemetry.record_acquire.assert_any_call("local", reused=True)


class FakePool(RuntimePool):
    def __init__(self) -> None:
        self.idle_total = 0
        self.eviction_total = 0

    def acquire(self, key: str):
        return None

    def release(self, key: str, runtime):
        self.idle_total += 4
        self.eviction_total += 2

    def stats(self) -> dict[str, int]:
        return {}

    def idle_reclaim_stats(self) -> dict[str, int]:
        return {"local": self.idle_total}

    def eviction_stats(self) -> dict[str, int]:
        return {"local": self.eviction_total}


@pytest.mark.asyncio
async def test_orchestrator_applies_pool_config(monkeypatch):
    runtimes: list[types.SimpleNamespace] = []

    def fake_create_runtime(*args, **kwargs):
        runtime = types.SimpleNamespace(
            sid=f"session-{len(runtimes)}",
            config=types.SimpleNamespace(runtime="local"),
        )
        runtimes.append(runtime)
        return runtime

    monkeypatch.setattr("forge.runtime.orchestrator.create_runtime", fake_create_runtime)
    monkeypatch.setattr(
        "forge.runtime.orchestrator.runtime_watchdog.watch_runtime", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "forge.runtime.orchestrator.runtime_watchdog.unwatch_runtime", lambda *a, **k: None
    )

    disconnected: list[str] = []

    def fake_disconnect(runtime):
        disconnected.append(runtime.sid)

    monkeypatch.setattr("forge.runtime.pool.call_async_disconnect", fake_disconnect)

    pool = WarmRuntimePool(max_size_per_key=2, ttl_seconds=600)
    pool.configure_policies = MagicMock(wraps=pool.configure_policies)
    orchestrator = RuntimeOrchestrator(pool=pool)

    config = ForgeConfig()
    config.runtime = "local"
    config.runtime_pool.overrides["local"] = RuntimePoolPolicy(max_size=0, ttl_seconds=60)

    result1 = orchestrator.acquire(
        config=config,
        llm_registry=MagicMock(),
        session_id="sess-1",
        agent=MagicMock(),
        headless_mode=True,
        git_provider_tokens=None,
    )
    orchestrator.release(result1, key="local")

    result2 = orchestrator.acquire(
        config=config,
        llm_registry=MagicMock(),
        session_id="sess-2",
        agent=MagicMock(),
        headless_mode=True,
        git_provider_tokens=None,
    )

    assert result1.runtime is not result2.runtime
    assert disconnected == ["session-0"]
    pool.configure_policies.assert_called()


@pytest.mark.asyncio
async def test_orchestrator_emits_scaling_signals(monkeypatch):
    pool = FakePool()
    telemetry = MagicMock()
    orchestrator = RuntimeOrchestrator(pool=pool, telemetry=telemetry)
    orchestrator._pool_policy_snapshot = (
        WarmPoolPolicy(max_size=1, ttl_seconds=60),
        {},
    )

    monkeypatch.setattr(
        "forge.runtime.orchestrator.runtime_watchdog.watch_runtime", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "forge.runtime.orchestrator.runtime_watchdog.unwatch_runtime", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "forge.runtime.orchestrator.runtime_watchdog.stats",
        lambda: {"local": 1},
    )

    result = RuntimeAcquireResult(
        runtime=types.SimpleNamespace(config=types.SimpleNamespace(runtime="local")),
        repo_directory=None,
    )

    orchestrator.release(result, key="local")

    signals = {call.args[0] for call in telemetry.record_scaling_signal.call_args_list}
    assert "overprovision|local" in signals
    assert "capacity_exhausted|local" in signals
    assert "saturation|local" in signals


