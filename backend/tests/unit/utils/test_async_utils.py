"""Tests for backend.utils.async_helpers.async_utils — async/sync bridging and task coordination."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from backend.utils.async_helpers import async_utils
from backend.utils.async_helpers.async_utils import (
    call_async_from_sync,
    call_coro_in_bg_thread,
    call_sync_from_async,
    create_tracked_task,
)


class TestCreateTrackedTask:
    @pytest.mark.asyncio
    async def test_creates_task(self):
        async def sample_coro():
            return 42

        task = create_tracked_task(sample_coro())
        assert isinstance(task, asyncio.Task)
        result = await task
        assert result == 42

    @pytest.mark.asyncio
    async def test_task_with_name(self):
        async def sample_coro():
            return 'named'

        task = create_tracked_task(sample_coro(), name='my_task')
        assert task.get_name() == 'my_task'
        result = await task
        assert result == 'named'


class TestCallSyncFromAsync:
    @pytest.mark.asyncio
    async def test_calls_sync_function(self):
        def sync_func(x, y):
            return x + y

        result = await call_sync_from_async(sync_func, 10, 20)
        assert result == 30


class TestCallAsyncFromSyncTimeoutsAndFallback:
    def test_call_async_from_sync_timeout(self):
        async def slow_coro():
            await asyncio.sleep(10)

        with pytest.raises(TimeoutError, match='call_async_from_sync timed out'):
            call_async_from_sync(slow_coro, timeout=0.1)

    def test_call_async_from_sync_executor_shutdown(self):
        async def quick_coro():
            return 'quick'

        with patch.object(async_utils.EXECUTOR, '_shutdown', True):
            res = call_async_from_sync(quick_coro)
            assert res == 'quick'

    @pytest.mark.asyncio
    async def test_call_coro_in_bg_thread_success(self):
        async def bg_task():
            return 'bg_res'

        res = await call_coro_in_bg_thread(bg_task, 5.0)
        assert res == 'bg_res'
