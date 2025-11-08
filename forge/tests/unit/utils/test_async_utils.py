from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from forge.utils import async_utils


def test_call_async_from_sync_validation() -> None:
    with pytest.raises(ValueError):
        async_utils.call_async_from_sync(None)

    def not_coro():
        return 1

    with pytest.raises(ValueError):
        async_utils.call_async_from_sync(not_coro)  # type: ignore[arg-type]


def test_call_async_from_sync_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    async def sample(x):
        return x + 1

    assert async_utils.call_async_from_sync(sample, 1, 1) == 2

    # Force branch where executor is shut down.
    stub = SimpleNamespace(_shutdown=True)
    monkeypatch.setattr(async_utils, "EXECUTOR", stub)
    assert async_utils.call_async_from_sync(sample, 1, 1) == 2


@pytest.mark.asyncio
async def test_call_sync_from_async_and_coro_in_bg_thread():
    def multiply(x, y):
        return x * y

    result = await async_utils.call_sync_from_async(multiply, 3, 7)
    assert result == 21

    async def sample_async(val):
        await asyncio.sleep(0)
        return val * 2

    await async_utils.call_coro_in_bg_thread(sample_async, 1, 5)


@pytest.mark.asyncio
async def test_wait_all_success_and_errors():
    async def ok(val):
        return val

    async def fail():
        raise RuntimeError("boom")

    results = await async_utils.wait_all([ok(1), ok(2)])
    assert results == [1, 2]

    with pytest.raises(asyncio.TimeoutError):
        await async_utils.wait_all([asyncio.sleep(0.2)], timeout=0.01)

    with pytest.raises(async_utils.AsyncException) as exc:
        await async_utils.wait_all([fail(), fail()])
    assert "boom" in str(exc.value)

    with pytest.raises(RuntimeError):
        await async_utils.wait_all([fail()])

    assert await async_utils.wait_all([]) == []


@pytest.mark.asyncio
async def test_run_in_loop_same_and_different_loops():
    async def sample(value):
        return value + 1

    loop = asyncio.get_running_loop()
    same = await async_utils.run_in_loop(sample(1), loop)
    assert same == 2

    other_loop = asyncio.new_event_loop()
    try:
        def run_loop():
            asyncio.set_event_loop(other_loop)
            other_loop.run_forever()

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        try:
            result = await async_utils.run_in_loop(sample(2), other_loop)
            assert result == 3
        finally:
            other_loop.call_soon_threadsafe(other_loop.stop)
            thread.join()
    finally:
        other_loop.close()


def test_async_exception_str() -> None:
    exc = async_utils.AsyncException([RuntimeError("one"), RuntimeError("two")])
    assert "one" in str(exc)
    assert "two" in str(exc)

