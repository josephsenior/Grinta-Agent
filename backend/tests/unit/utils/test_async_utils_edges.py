"""Edge-path tests for backend.utils.async_helpers.async_utils.

Targets the branches not exercised by test_async_utils.py /
test_async_utils_unit.py: env-var fallbacks, executor shutdown, loop
finalization, run_or_schedule dispatch paths, and drain helpers.
"""

from __future__ import annotations

import asyncio
import atexit
import sys
import threading

import pytest

from backend.utils.async_helpers import async_utils
from backend.utils.async_helpers.async_utils import (
    _cancel_pending_tasks_bounded,
    _debugger_sync_pool_workers,
    _get_max_workers,
    _get_sync_from_async_workers,
    _run_in_loop,
    _schedule_on_main_loop,
    _shutdown_executor_atexit,
    _warn_if_on_loop_thread,
    call_async_from_sync,
    create_tracked_task,
    drain_background_tasks,
    drain_step_barrier,
    get_main_event_loop,
    run_in_loop,
    run_or_schedule,
    set_main_event_loop,
    wait_all,
)

# ── pool-size env-var fallbacks ──────────────────────────────────────


class TestPoolSizeFallbacks:
    def test_max_workers_invalid_value(self, monkeypatch):
        monkeypatch.setenv('APP_THREAD_POOL_MAX_WORKERS', 'not-a-number')
        assert _get_max_workers() == 32

    def test_max_workers_non_positive(self, monkeypatch):
        monkeypatch.setenv('APP_THREAD_POOL_MAX_WORKERS', '-3')
        assert _get_max_workers() == 32

    def test_sync_from_async_workers_invalid(self, monkeypatch):
        monkeypatch.setenv('GRINTA_SYNC_FROM_ASYNC_POOL_WORKERS', 'abc')
        default = max(4, min(_get_max_workers(), 16))
        assert _get_sync_from_async_workers() == default

    def test_sync_from_async_workers_clamped(self, monkeypatch):
        monkeypatch.setenv('GRINTA_SYNC_FROM_ASYNC_POOL_WORKERS', '9999')
        assert _get_sync_from_async_workers() == 64

    def test_debugger_sync_pool_workers_invalid(self, monkeypatch):
        monkeypatch.setenv('GRINTA_DEBUGGER_SYNC_POOL_WORKERS', 'nope')
        assert _debugger_sync_pool_workers() == 6


# ── executor shutdown ────────────────────────────────────────────────


class TestShutdownExecutorAtexit:
    def test_shuts_down_all_executors(self, monkeypatch):
        seen = {}

        class FakeExecutor:
            def __init__(self, name):
                self.name = name

            def shutdown(self, *, wait=True, cancel_futures=True):
                seen[self.name] = (wait, cancel_futures)

        executors = {
            'EXECUTOR': FakeExecutor('main'),
            'SYNC_FROM_ASYNC_EXECUTOR': FakeExecutor('sync-from-async'),
            'DEBUGGER_SYNC_EXECUTOR': FakeExecutor('debugger'),
        }
        for name, fake in executors.items():
            monkeypatch.setattr(async_utils, name, fake)

        _shutdown_executor_atexit()
        assert seen == {fake.name: (True, True) for fake in executors.values()}

    def test_shutdown_exceptions_swallowed(self, monkeypatch):
        class BoomExecutor:
            def shutdown(self, *, wait=True, cancel_futures=True):
                raise RuntimeError('shutdown boom')

        monkeypatch.setattr(async_utils, 'EXECUTOR', BoomExecutor())
        monkeypatch.setattr(async_utils, 'SYNC_FROM_ASYNC_EXECUTOR', BoomExecutor())
        monkeypatch.setattr(async_utils, 'DEBUGGER_SYNC_EXECUTOR', BoomExecutor())
        _shutdown_executor_atexit()  # must not raise


# ── on-loop bridge tripwire ──────────────────────────────────────────


class TestWarnIfOnLoopThread:
    @pytest.mark.asyncio
    async def test_unknown_call_site(self, monkeypatch, caplog):
        real_getframe = sys._getframe

        def selective(*args):
            if args == (2,):
                raise RuntimeError('no frame')
            return real_getframe(*args)

        monkeypatch.setattr(sys, '_getframe', selective)

        async def probe():
            _warn_if_on_loop_thread(probe)

        with caplog.at_level('WARNING', logger='backend.utils.async_helpers.async_utils'):
            await probe()
        assert any('BRIDGE_ON_LOOP' in r.message for r in caplog.records)
        assert any('<unknown>' in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_real_call_site(self, caplog):
        async def probe():
            _warn_if_on_loop_thread(probe)

        with caplog.at_level('WARNING', logger='backend.utils.async_helpers.async_utils'):
            await probe()
        assert any('BRIDGE_ON_LOOP' in r.message for r in caplog.records)
        assert any('.py:' in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_strict_mode_raises(self, monkeypatch):
        monkeypatch.setattr(async_utils, '_STRICT_LOOP_BRIDGE', True)

        async def probe():
            _warn_if_on_loop_thread(probe)

        with pytest.raises(RuntimeError):
            await probe()


# ── bounded task cancellation ────────────────────────────────────────


class TestCancelPendingTasksBounded:
    def test_timeout_logs_undone_tasks(self, caplog):
        # Regression test: a task that swallows CancelledError used to hang
        # _cancel_pending_tasks_bounded forever on Windows Proactor (wait_for's
        # timeout cancellation is delegated to the stubborn child and never
        # wakes the waiting task). asyncio.wait must return after timeout_sec.
        loop = asyncio.new_event_loop()
        try:
            release = False

            async def stubborn():
                nonlocal release
                while True:
                    try:
                        await asyncio.sleep(30)
                    except asyncio.CancelledError:
                        if release:
                            return

            task = loop.create_task(stubborn())
            loop.run_until_complete(asyncio.sleep(0.05))

            with caplog.at_level('WARNING', logger='backend.utils.async_helpers.async_utils'):
                _cancel_pending_tasks_bounded(loop, timeout_sec=0.05)

            assert not task.done()
            assert any('still pending' in r.message for r in caplog.records)

            release = True
            task.cancel()
            loop.run_until_complete(asyncio.sleep(0.1))
            assert task.done()
        finally:
            loop.close()


# ── call_async_from_sync loop finalization ───────────────────────────


class TestCallAsyncFromSyncFinalize:
    def test_residual_tasks_trigger_asyncgen_shutdown(self):
        async def spawns_residual():
            async def stubborn():
                try:
                    await asyncio.sleep(30)
                except asyncio.CancelledError:
                    await asyncio.sleep(30)

            asyncio.get_running_loop().create_task(stubborn())
            return 'ok'

        assert call_async_from_sync(spawns_residual, timeout=15) == 'ok'

    def test_default_executor_is_shut_down(self):
        async def uses_default_executor():
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: 42)

        assert call_async_from_sync(uses_default_executor, timeout=15) == 42

    def test_asyncgen_shutdown_timeout_swallowed(self, monkeypatch):
        holder: dict = {}

        async def spawns_residual_and_slow_asyncgen():
            async def stubborn():
                try:
                    await asyncio.sleep(30)
                except asyncio.CancelledError:
                    await asyncio.sleep(30)

            async def slow_asyncgen():
                try:
                    yield 1
                finally:
                    await asyncio.sleep(30)

            loop = asyncio.get_running_loop()
            loop.create_task(stubborn())
            gen = slow_asyncgen()
            holder['gen'] = gen  # keep alive past the coroutine's frame
            await gen.__anext__()  # suspend it so the loop registers it as open
            return 'ok'

        monkeypatch.setattr(async_utils, '_LOOP_FINALIZE_WAIT_SEC', 0.05)
        assert call_async_from_sync(spawns_residual_and_slow_asyncgen, timeout=15) == 'ok'
        try:
            asyncio.run(holder['gen'].aclose())
        except BaseException:
            pass

    def test_shutdown_executor_runs_inline(self, monkeypatch):
        class ShutdownExecutor:
            _shutdown = True

        monkeypatch.setattr(async_utils, 'EXECUTOR', ShutdownExecutor())

        async def ok():
            return 'inline'

        assert call_async_from_sync(ok, timeout=5) == 'inline'


# ── wait_all timeout ─────────────────────────────────────────────────


class TestWaitAllTimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises_and_cancels(self):
        with pytest.raises(TimeoutError):
            await wait_all([asyncio.sleep(30)], wait_timeout_sec=0.05)


# ── run_in_loop / _run_in_loop ───────────────────────────────────────


class TestRunInLoop:
    @pytest.mark.asyncio
    async def test_same_loop_awaits_directly(self):
        loop = asyncio.get_running_loop()
        assert await run_in_loop(_identity(), loop) == 'ok'

    @pytest.mark.asyncio
    async def test_cross_loop_handoff(self):
        other = asyncio.new_event_loop()
        thread = threading.Thread(target=other.run_forever, daemon=True)
        thread.start()
        try:
            result = await run_in_loop(_identity(), other)
            assert result == 'ok'
        finally:
            other.call_soon_threadsafe(other.stop)
            thread.join(timeout=5)
            other.close()

    def test_run_in_loop_timeout(self):
        other = asyncio.new_event_loop()
        thread = threading.Thread(target=other.run_forever, daemon=True)
        thread.start()
        try:
            with pytest.raises(TimeoutError):
                _run_in_loop(asyncio.sleep(30), other, 0.05)
        finally:
            other.call_soon_threadsafe(other.stop)
            thread.join(timeout=5)
            other.close()


# ── main event loop registry ─────────────────────────────────────────


class TestMainEventLoopRegistry:
    @pytest.mark.asyncio
    async def test_none_uses_running_loop(self, monkeypatch):
        monkeypatch.setattr(async_utils, '_main_event_loop', None)
        set_main_event_loop()
        assert get_main_event_loop() is asyncio.get_running_loop()

    def test_watchdog_failure_swallowed(self, monkeypatch):
        def boom(loop):
            raise RuntimeError('watchdog boom')

        monkeypatch.setattr(
            'backend.core.timeouts.loop_watchdog.start_loop_watchdog', boom
        )
        loop = asyncio.new_event_loop()
        try:
            set_main_event_loop(loop)  # must not raise
            assert get_main_event_loop() is loop
        finally:
            loop.close()
            monkeypatch.setattr(async_utils, '_main_event_loop', None)


# ── run_or_schedule dispatch paths ───────────────────────────────────


class TestRunOrSchedule:
    @pytest.mark.asyncio
    async def test_dispatches_to_registered_main_loop(self, monkeypatch):
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(async_utils, '_main_event_loop', loop)
        flag = threading.Event()

        def bg_thread():
            async def coro():
                flag.set()

            run_or_schedule(coro())

        thread = threading.Thread(target=bg_thread)
        thread.start()
        thread.join(timeout=5)
        await asyncio.sleep(0.05)
        assert flag.is_set()

    def test_fallback_loop_reused_then_recreated(self, monkeypatch):
        captured: list = []
        monkeypatch.setattr(atexit, 'register', lambda fn: captured.append(fn))
        monkeypatch.setattr(async_utils, '_fallback_loop', None)

        async def noop():
            return 1

        run_or_schedule(noop())
        first = async_utils._fallback_loop
        assert first is not None
        assert len(captured) == 1

        run_or_schedule(noop())
        assert async_utils._fallback_loop is first  # reused

        captured[0]()  # _close_fallback_loop
        assert async_utils._fallback_loop is None

        run_or_schedule(noop())
        assert async_utils._fallback_loop is not None
        assert async_utils._fallback_loop is not first  # recreated

        captured[-1]()  # close the recreated loop so nothing leaks
        assert async_utils._fallback_loop is None

        captured[1]()
        assert async_utils._fallback_loop is None
        asyncio.set_event_loop(None)


class TestScheduleOnMainLoop:
    def test_closed_loop_runtime_error_swallowed(self, monkeypatch, caplog):
        def boom(coro, *, name=None, task_set=None):
            raise RuntimeError('loop closed')

        monkeypatch.setattr(async_utils, 'create_tracked_task', boom)

        async def noop():
            pass

        with caplog.at_level('DEBUG', logger='backend.utils.async_helpers.async_utils'):
            _schedule_on_main_loop(noop())  # must not raise
        assert any('Main loop closed' in r.message for r in caplog.records)


# ── drain helpers ────────────────────────────────────────────────────


class TestDrainStepBarrier:
    @pytest.mark.asyncio
    async def test_returns_true_when_idle(self):
        assert (
            await drain_step_barrier(
                has_outstanding=lambda: False,
                timeout=1.0,
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self):
        assert (
            await drain_step_barrier(
                has_outstanding=lambda: True,
                timeout=0.2,
                poll_interval=0.05,
            )
            is False
        )


class TestDrainBackgroundTasks:
    @pytest.mark.asyncio
    async def test_gather_branch_without_timeout(self):
        bag: set[asyncio.Task] = set()

        async def noop():
            pass

        task = create_tracked_task(noop(), task_set=bag)
        await drain_background_tasks(task_set=bag)
        assert task.done()

    @pytest.mark.asyncio
    async def test_wait_branch_with_timeout(self):
        bag: set[asyncio.Task] = set()

        async def quick():
            await asyncio.sleep(0.01)

        task = create_tracked_task(quick(), task_set=bag)
        await drain_background_tasks(task_set=bag, timeout=1.0)
        assert task.done()


async def _identity():
    return 'ok'
