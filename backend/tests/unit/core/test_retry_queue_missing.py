"""Additional tests for retry_queue.py to improve coverage."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from forge.core.retry_queue import (
    InMemoryRetryBackend,
    RetryQueue,
    RetryTask,
)


class TestRetryTask:
    """Test RetryTask serialization."""

    def test_to_dict(self):
        """Test RetryTask.to_dict serialization."""
        task = RetryTask(
            id="test-id",
            controller_id="controller-1",
            payload={"key": "value"},
            reason="Test reason",
            attempts=2,
            max_attempts=5,
            next_attempt_at=100.0,
            created_at=50.0,
            last_error="Error message",
            metadata={"meta": "data"},
        )
        result = task.to_dict()
        assert result["id"] == "test-id"
        assert result["controller_id"] == "controller-1"
        assert result["payload"] == {"key": "value"}
        assert result["reason"] == "Test reason"
        assert result["attempts"] == 2
        assert result["max_attempts"] == 5
        assert result["next_attempt_at"] == 100.0
        assert result["created_at"] == 50.0
        assert result["last_error"] == "Error message"
        assert result["metadata"] == {"meta": "data"}

    def test_from_dict(self):
        """Test RetryTask.from_dict deserialization."""
        data = {
            "id": "test-id",
            "controller_id": "controller-1",
            "payload": {"key": "value"},
            "reason": "Test reason",
            "attempts": 2,
            "max_attempts": 5,
            "next_attempt_at": 100.0,
            "created_at": 50.0,
            "last_error": "Error message",
            "metadata": {"meta": "data"},
        }
        task = RetryTask.from_dict(data)
        assert task.id == "test-id"
        assert task.controller_id == "controller-1"
        assert task.payload == {"key": "value"}
        assert task.reason == "Test reason"
        assert task.attempts == 2
        assert task.max_attempts == 5
        assert task.next_attempt_at == 100.0
        assert task.created_at == 50.0
        assert task.last_error == "Error message"
        assert task.metadata == {"meta": "data"}

    def test_from_dict_with_defaults(self):
        """Test RetryTask.from_dict with missing fields uses defaults."""
        data = {
            "id": "test-id",
            "controller_id": "controller-1",
        }
        task = RetryTask.from_dict(data)
        assert task.id == "test-id"
        assert task.controller_id == "controller-1"
        assert task.payload == {}
        assert task.reason == ""
        assert task.attempts == 0
        assert task.max_attempts == 3
        assert task.metadata == {}


class TestInMemoryRetryBackend:
    """Test InMemoryRetryBackend missing coverage."""

    @pytest.mark.asyncio
    async def test_fetch_ready_skips_missing_tasks(self):
        """Test fetch_ready skips tasks that are not in _tasks dict."""
        backend = InMemoryRetryBackend()
        # Manually add to heap without adding to tasks
        import heapq
        async with backend._lock:
            heapq.heappush(backend._heap, (time.time() - 1, "missing-task-id"))
        
        result = await backend.fetch_ready("controller-1", limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_ready_filters_by_controller_id(self):
        """Test fetch_ready only returns tasks for specified controller."""
        backend = InMemoryRetryBackend()
        
        task1 = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
            next_attempt_at=time.time() - 1,
        )
        task2 = RetryTask(
            id="task-2",
            controller_id="controller-2",
            payload={},
            reason="test",
            next_attempt_at=time.time() - 1,
        )
        
        await backend.schedule(task1)
        await backend.schedule(task2)
        
        result = await backend.fetch_ready("controller-1", limit=10)
        assert len(result) == 1
        assert result[0].id == "task-1"

    @pytest.mark.asyncio
    async def test_fetch_ready_waits_for_future_tasks(self):
        """Test fetch_ready requeues tasks that are not ready yet."""
        backend = InMemoryRetryBackend()
        
        task = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
            next_attempt_at=time.time() + 100,  # Future
        )
        
        await backend.schedule(task)
        
        result = await backend.fetch_ready("controller-1", limit=10)
        assert result == []
        
        # Task should still be in heap
        async with backend._lock:
            assert len(backend._heap) == 1

    @pytest.mark.asyncio
    async def test_mark_failure_reschedules_task(self):
        """Test mark_failure reschedules task with backoff."""
        backend = InMemoryRetryBackend()
        
        task = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
            attempts=1,
            max_attempts=3,
            next_attempt_at=time.time() - 1,
        )
        
        await backend.schedule(task)
        ready = await backend.fetch_ready("controller-1", limit=1)
        assert len(ready) == 1
        
        result = await backend.mark_failure(ready[0], backoff_seconds=10.0)
        assert result is not None
        assert result.attempts == 2
        assert result.next_attempt_at > time.time()

    @pytest.mark.asyncio
    async def test_mark_failure_moves_to_dead_letter_when_max_attempts_reached(self):
        """Test mark_failure moves to dead letter when max attempts reached."""
        backend = InMemoryRetryBackend()
        
        task = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
            attempts=2,
            max_attempts=3,
            next_attempt_at=time.time() - 1,
        )
        
        await backend.schedule(task)
        ready = await backend.fetch_ready("controller-1", limit=1)
        assert len(ready) == 1
        
        result = await backend.mark_failure(ready[0], backoff_seconds=10.0)
        assert result is None
        assert len(backend._dead_letter) == 1
        assert backend._dead_letter[0].id == "task-1"

    @pytest.mark.asyncio
    async def test_dead_letter(self):
        """Test dead_letter moves task to dead letter queue."""
        backend = InMemoryRetryBackend()
        
        task = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
        )
        
        await backend.schedule(task)
        await backend.dead_letter(task)
        
        assert len(backend._dead_letter) == 1
        assert backend._dead_letter[0].id == "task-1"
        async with backend._lock:
            assert task.id not in backend._tasks

    @pytest.mark.asyncio
    async def test_retry_queue_dead_letter(self):
        """Test RetryQueue.dead_letter method."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=0.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = RetryTask(
            id="task-1",
            controller_id="controller-1",
            payload={},
            reason="test",
        )
        
        await queue.dead_letter(task)
        assert len(backend._dead_letter) == 1


class TestRetryQueue:
    """Test RetryQueue missing coverage."""

    @pytest.mark.asyncio
    async def test_schedule_with_metadata(self):
        """Test schedule with metadata."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=1.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = await queue.schedule(
            controller_id="controller-1",
            payload={"op": "test"},
            reason="test",
            metadata={"key": "value"},
        )
        
        assert task.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_schedule_with_initial_delay(self):
        """Test schedule with initial_delay."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=1.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = await queue.schedule(
            controller_id="controller-1",
            payload={"op": "test"},
            reason="test",
            initial_delay=5.0,
        )
        
        assert task.next_attempt_at >= time.time() + 4.0

    @pytest.mark.asyncio
    async def test_schedule_with_max_attempts(self):
        """Test schedule with custom max_attempts."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=1.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = await queue.schedule(
            controller_id="controller-1",
            payload={"op": "test"},
            reason="test",
            max_attempts=5,
        )
        
        assert task.max_attempts == 5

    @pytest.mark.asyncio
    async def test_schedule_with_negative_initial_delay(self):
        """Test schedule with negative initial_delay is clamped to 0."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=1.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = await queue.schedule(
            controller_id="controller-1",
            payload={"op": "test"},
            reason="test",
            initial_delay=-5.0,
        )
        
        assert task.next_attempt_at >= time.time()

    @pytest.mark.asyncio
    async def test_mark_failure_updates_reason(self):
        """Test mark_failure updates task reason."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=0.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        task = await queue.schedule(
            controller_id="controller-1",
            payload={"op": "test"},
            reason="original",
        )
        
        ready = await queue.fetch_ready("controller-1", limit=1)
        assert len(ready) == 1
        
        result = await queue.mark_failure(ready[0], error_message="new error")
        assert result is not None
        assert result.reason == "new error"

    def test_compute_backoff(self):
        """Test _compute_backoff calculation."""
        backend = InMemoryRetryBackend()
        queue = RetryQueue(
            backend,
            base_delay=1.0,
            max_delay=10.0,
            max_retries=3,
            poll_interval=0.05,
        )
        
        # Test exponential backoff
        assert queue._compute_backoff(1) == 1.0
        assert queue._compute_backoff(2) == 2.0
        assert queue._compute_backoff(3) == 4.0
        assert queue._compute_backoff(4) == 8.0
        
        # Test max delay cap
        assert queue._compute_backoff(10) == 10.0
        
        # Test negative attempts clamped to 1
        assert queue._compute_backoff(0) == 1.0
        assert queue._compute_backoff(-1) == 1.0


class TestRedisRetryBackend:
    """Test RedisRetryBackend (mocked)."""

    @pytest.mark.asyncio
    async def test_redis_backend_init_raises_when_redis_unavailable(self, monkeypatch):
        """Test RedisRetryBackend raises when redis is not available."""
        from forge.core import retry_queue
        original_redis = retry_queue.REDIS_AVAILABLE
        monkeypatch.setattr(retry_queue, "REDIS_AVAILABLE", False)
        
        with pytest.raises(RuntimeError, match="redis.asyncio is required"):
            from forge.core.retry_queue import RedisRetryBackend
            _ = RedisRetryBackend("redis://localhost:6379")
        
        monkeypatch.setattr(retry_queue, "REDIS_AVAILABLE", original_redis)

    @pytest.mark.asyncio
    async def test_redis_backend_key_methods(self):
        """Test RedisRetryBackend key generation methods."""
        from forge.core.retry_queue import RedisRetryBackend
        
        # Mock redis availability
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_redis.Redis.return_value = MagicMock()
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                assert backend._schedule_key("ctrl-1") == "retry_queue:ctrl-1:schedule"
                assert backend._tasks_key("ctrl-1") == "retry_queue:ctrl-1:tasks"
                assert backend._dead_letter_key("ctrl-1") == "retry_queue:ctrl-1:dead_letter"

    @pytest.mark.asyncio
    async def test_redis_backend_schedule(self):
        """Test RedisRetryBackend.schedule."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
                mock_pipe.__aexit__ = AsyncMock(return_value=None)
                mock_pipe.hset = MagicMock()
                mock_pipe.zadd = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_client.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                task = RetryTask(
                    id="task-1",
                    controller_id="ctrl-1",
                    payload={"test": "data"},
                    reason="test",
                )
                
                result = await backend.schedule(task)
                assert result == task
                mock_pipe.hset.assert_called_once()
                mock_pipe.zadd.assert_called_once()
                mock_pipe.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_backend_fetch_ready(self):
        """Test RedisRetryBackend.fetch_ready."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_client.zpopmin = AsyncMock(return_value=[("task-1", time.time() - 1)])
                mock_client.hget = AsyncMock(return_value='{"id":"task-1","controller_id":"ctrl-1","payload":{},"reason":"test","attempts":0,"max_attempts":3,"next_attempt_at":0,"created_at":0,"last_error":null,"metadata":{}}')
                mock_client.zadd = AsyncMock()
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                result = await backend.fetch_ready("ctrl-1", limit=1)
                assert len(result) == 1
                assert result[0].id == "task-1"
                assert result[0].attempts == 1  # Incremented

    @pytest.mark.asyncio
    async def test_redis_backend_fetch_ready_not_ready_yet(self):
        """Test RedisRetryBackend.fetch_ready requeues future tasks."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_client.zpopmin = AsyncMock(return_value=[("task-1", time.time() + 100)])
                mock_client.zadd = AsyncMock()
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                result = await backend.fetch_ready("ctrl-1", limit=1)
                assert result == []
                mock_client.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_backend_fetch_ready_empty(self):
        """Test RedisRetryBackend.fetch_ready with no tasks."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_client.zpopmin = AsyncMock(return_value=[])
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                result = await backend.fetch_ready("ctrl-1", limit=1)
                assert result == []

    @pytest.mark.asyncio
    async def test_redis_backend_fetch_ready_missing_task(self):
        """Test RedisRetryBackend.fetch_ready skips missing tasks."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_client.zpopmin = AsyncMock(return_value=[("task-1", time.time() - 1)])
                mock_client.hget = AsyncMock(return_value=None)
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                result = await backend.fetch_ready("ctrl-1", limit=1)
                assert result == []

    @pytest.mark.asyncio
    async def test_redis_backend_mark_success(self):
        """Test RedisRetryBackend.mark_success."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_client.hdel = AsyncMock()
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                task = RetryTask(
                    id="task-1",
                    controller_id="ctrl-1",
                    payload={},
                    reason="test",
                )
                
                await backend.mark_success(task)
                mock_client.hdel.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_backend_mark_failure_reschedules(self):
        """Test RedisRetryBackend.mark_failure reschedules task."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
                mock_pipe.__aexit__ = AsyncMock(return_value=None)
                mock_pipe.hset = MagicMock()
                mock_pipe.zadd = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_client.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                task = RetryTask(
                    id="task-1",
                    controller_id="ctrl-1",
                    payload={},
                    reason="test",
                    attempts=1,
                    max_attempts=3,
                )
                
                result = await backend.mark_failure(task, backoff_seconds=10.0)
                assert result == task
                mock_pipe.hset.assert_called_once()
                mock_pipe.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_backend_mark_failure_dead_letter(self):
        """Test RedisRetryBackend.mark_failure moves to dead letter."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
                mock_pipe.__aexit__ = AsyncMock(return_value=None)
                mock_pipe.hdel = MagicMock()
                mock_pipe.lpush = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_client.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                task = RetryTask(
                    id="task-1",
                    controller_id="ctrl-1",
                    payload={},
                    reason="test",
                    attempts=3,
                    max_attempts=3,
                )
                
                result = await backend.mark_failure(task, backoff_seconds=10.0)
                assert result is None
                mock_pipe.hdel.assert_called_once()
                mock_pipe.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_backend_dead_letter(self):
        """Test RedisRetryBackend.dead_letter."""
        from forge.core.retry_queue import RedisRetryBackend
        
        with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
            with patch("forge.core.retry_queue.redis") as mock_redis:
                mock_pool = MagicMock()
                mock_redis.ConnectionPool.from_url.return_value = mock_pool
                mock_client = AsyncMock()
                mock_pipe = AsyncMock()
                mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
                mock_pipe.__aexit__ = AsyncMock(return_value=None)
                mock_pipe.hdel = MagicMock()
                mock_pipe.lpush = MagicMock()
                mock_pipe.execute = AsyncMock()
                mock_client.pipeline = MagicMock(return_value=mock_pipe)
                mock_redis.Redis.return_value = mock_client
                
                backend = RedisRetryBackend("redis://localhost:6379")
                
                task = RetryTask(
                    id="task-1",
                    controller_id="ctrl-1",
                    payload={},
                    reason="test",
                )
                
                await backend.dead_letter(task)
                mock_pipe.hdel.assert_called_once()
                mock_pipe.lpush.assert_called_once()


class TestGetRetryQueue:
    """Test get_retry_queue function."""

    def test_get_retry_queue_disabled(self, monkeypatch):
        """Test get_retry_queue returns None when disabled."""
        from forge.core.retry_queue import get_retry_queue
        import forge.core.retry_queue as rq_module
        
        # Reset singleton
        rq_module._retry_queue = None
        
        monkeypatch.setenv("RETRY_QUEUE_ENABLED", "false")
        result = get_retry_queue()
        assert result is None

    def test_get_retry_queue_in_memory_backend(self, monkeypatch):
        """Test get_retry_queue uses in-memory backend."""
        from forge.core.retry_queue import get_retry_queue
        import forge.core.retry_queue as rq_module
        
        # Reset singleton
        original = rq_module._retry_queue
        rq_module._retry_queue = None
        
        try:
            monkeypatch.setenv("RETRY_QUEUE_ENABLED", "true")
            monkeypatch.setenv("RETRY_QUEUE_BACKEND", "memory")
            monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
            monkeypatch.delenv("PYTEST_RUNNING", raising=False)
            
            result = get_retry_queue()
            assert result is not None
            assert isinstance(result.backend, InMemoryRetryBackend)
        finally:
            rq_module._retry_queue = original

    def test_get_retry_queue_redis_backend_fallback(self, monkeypatch):
        """Test get_retry_queue falls back to in-memory when Redis fails."""
        from forge.core.retry_queue import get_retry_queue, RedisRetryBackend
        import forge.core.retry_queue as rq_module
        
        # Reset singleton
        original = rq_module._retry_queue
        rq_module._retry_queue = None
        
        try:
            monkeypatch.setenv("RETRY_QUEUE_ENABLED", "true")
            monkeypatch.setenv("RETRY_QUEUE_BACKEND", "redis")
            monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
            monkeypatch.delenv("PYTEST_RUNNING", raising=False)
            
            with patch("forge.core.retry_queue.REDIS_AVAILABLE", True):
                with patch.object(RedisRetryBackend, "__init__", side_effect=Exception("Redis connection failed")):
                    result = get_retry_queue()
                    assert result is not None
                    assert isinstance(result.backend, InMemoryRetryBackend)
        finally:
            rq_module._retry_queue = original

    def test_get_retry_queue_uses_pytest_default(self, monkeypatch):
        """Test get_retry_queue defaults to memory when pytest is detected."""
        from forge.core.retry_queue import get_retry_queue
        import forge.core.retry_queue as rq_module
        
        # Reset singleton
        original = rq_module._retry_queue
        rq_module._retry_queue = None
        
        try:
            monkeypatch.setenv("RETRY_QUEUE_ENABLED", "true")
            monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_file.py::test_func")
            monkeypatch.delenv("RETRY_QUEUE_BACKEND", raising=False)
            
            result = get_retry_queue()
            assert result is not None
            assert isinstance(result.backend, InMemoryRetryBackend)
        finally:
            rq_module._retry_queue = original

    def test_get_retry_queue_singleton(self, monkeypatch):
        """Test get_retry_queue returns same instance on subsequent calls."""
        from forge.core.retry_queue import get_retry_queue
        import forge.core.retry_queue as rq_module
        
        # Reset singleton
        original = rq_module._retry_queue
        rq_module._retry_queue = None
        
        try:
            monkeypatch.setenv("RETRY_QUEUE_ENABLED", "true")
            monkeypatch.setenv("RETRY_QUEUE_BACKEND", "memory")
            
            result1 = get_retry_queue()
            result2 = get_retry_queue()
            assert result1 is result2
        finally:
            rq_module._retry_queue = original

