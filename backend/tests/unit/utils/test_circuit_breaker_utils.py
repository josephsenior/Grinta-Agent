from __future__ import annotations

import asyncio
import pytest

from forge.utils.circuit_breaker import (
    get_circuit_breaker_manager,
    get_circuit_breaker_metrics_snapshot,
)


@pytest.mark.asyncio
async def test_circuit_breaker_transitions(monkeypatch):
    cb = get_circuit_breaker_manager()

    # Make a failing async function
    call_count = {"n": 0}

    async def failing():
        call_count["n"] += 1
        raise RuntimeError("boom")

    # Trigger failures to open the breaker
    for _ in range(4):  # default threshold is 3
        try:
            await cb.async_call("test:op", failing)
        except RuntimeError:
            pass
    snap = get_circuit_breaker_metrics_snapshot()
    assert snap["opens_total"] >= 1
    assert snap["open_count"] >= 1

    # Calls should be blocked while open
    blocked_before = snap["blocked_total"]
    with pytest.raises(RuntimeError):
        await cb.async_call("test:op", failing)
    snap2 = get_circuit_breaker_metrics_snapshot()
    assert snap2["blocked_total"] >= blocked_before


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_success(monkeypatch):
    # Configure small window and single failure threshold for fast transition
    monkeypatch.setenv("FORGE_CB_FAILURE_THRESHOLD", "1")
    monkeypatch.setenv("FORGE_CB_BASE_OPEN_SECONDS", "0.05")
    monkeypatch.setenv("FORGE_CB_HALF_OPEN_PROBES", "1")

    cb = get_circuit_breaker_manager()
    key = "halfopen:op:success"

    # First call fails and opens the breaker (threshold=1)
    async def failing():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cb.async_call(key, failing)

    snap_open = get_circuit_breaker_metrics_snapshot()
    assert key in snap_open["open_keys"]

    # Wait long enough for half-open transition
    await asyncio.sleep(0.06)

    # Successful probe should close the breaker
    async def succeed():
        return 42

    probes_before = snap_open.get("half_open_probes_total", 0)
    closes_before = snap_open.get("close_success_total", 0)

    result = await cb.async_call(key, succeed)
    assert result == 42

    snap_after = get_circuit_breaker_metrics_snapshot()
    assert snap_after.get("half_open_probes_total", 0) >= probes_before + 1
    assert snap_after.get("close_success_total", 0) >= closes_before + 1
    assert key not in snap_after["open_keys"]
