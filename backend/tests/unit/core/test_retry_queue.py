import asyncio

import pytest

from forge.core.retry_queue import InMemoryRetryBackend, RetryQueue


@pytest.mark.asyncio
async def test_retry_queue_schedule_and_success():
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
        payload={"operation": "agent_step"},
        reason="ServiceUnavailableError",
        initial_delay=0.0,
    )

    ready = await queue.fetch_ready("controller-1", limit=1)
    assert ready and ready[0].id == task.id

    await queue.mark_success(ready[0])


@pytest.mark.asyncio
async def test_retry_queue_mark_failure_and_dead_letter():
    backend = InMemoryRetryBackend()
    queue = RetryQueue(
        backend,
        base_delay=0.0,
        max_delay=10.0,
        max_retries=1,
        poll_interval=0.05,
    )

    task = await queue.schedule(
        controller_id="controller-2",
        payload={"operation": "agent_step"},
        reason="Timeout",
        initial_delay=0.0,
        max_attempts=1,
    )

    ready = await queue.fetch_ready("controller-2", limit=1)
    assert ready and ready[0].id == task.id

    result = await queue.mark_failure(ready[0], error_message="Timeout again")
    assert result is None

