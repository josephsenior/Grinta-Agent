"""Async helper utilities for bridging sync/async execution and task coordination."""

import asyncio
from collections.abc import Coroutine, Iterable
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

GENERAL_TIMEOUT: int = 15
EXECUTOR = ThreadPoolExecutor()


async def call_sync_from_async(fn: Callable, *args, **kwargs):
    """Shorthand for running a function in the default background thread pool executor.

    and awaiting the result. The nature of synchronous code is that the future
    returned by this function is not cancellable.
    """
    loop = asyncio.get_event_loop()
    coro = loop.run_in_executor(None, lambda: fn(*args, **kwargs))
    return await coro


def call_async_from_sync(corofn: Callable, timeout: float = GENERAL_TIMEOUT, *args, **kwargs):
    """Shorthand for running a coroutine in the default background thread pool executor.

    and awaiting the result.
    """
    if corofn is None:
        msg = "corofn is None"
        raise ValueError(msg)
    if not asyncio.iscoroutinefunction(corofn):
        msg = "corofn is not a coroutine function"
        raise ValueError(msg)

    async def arun():
        """Execute target coroutine function with provided args/kwargs."""
        coro = corofn(*args, **kwargs)
        return await coro

    def run():
        """Run coroutine in fresh event loop within worker thread."""
        loop_for_thread = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop_for_thread)
            return asyncio.run(arun())
        finally:
            loop_for_thread.close()

    if getattr(EXECUTOR, "_shutdown", False):
        return run()
    future = EXECUTOR.submit(run)
    futures.wait([future], timeout=timeout or None)
    return future.result()


async def call_coro_in_bg_thread(corofn: Callable, timeout: float = GENERAL_TIMEOUT, *args, **kwargs) -> None:
    """Function for running a coroutine in a background thread."""
    await call_sync_from_async(call_async_from_sync, corofn, timeout, *args, **kwargs)


async def wait_all(iterable: Iterable[Coroutine], timeout: int = GENERAL_TIMEOUT) -> list:
    """Shorthand for waiting for all the coroutines in the iterable given in parallel.

    Creates a task for each coroutine. Returns a list of results in the original order. If any single task
    raised an exception, this is raised. If multiple tasks raised exceptions, an AsyncException is raised
    containing all exceptions.
    """
    tasks = [asyncio.create_task(c) for c in iterable]
    if not tasks:
        return []
    _, pending = await asyncio.wait(tasks, timeout=timeout)
    if pending:
        for task in pending:
            task.cancel()
        raise asyncio.TimeoutError
    results = []
    errors = []
    for task in tasks:
        try:
            results.append(task.result())
        except Exception as e:
            errors.append(e)
    if errors:
        if len(errors) == 1:
            raise errors[0]
        raise AsyncException(errors)
    return [task.result() for task in tasks]


class AsyncException(Exception):
    """Aggregate exception capturing multiple errors raised by wait_all."""

    def __init__(self, exceptions) -> None:
        """Store the sequence of exceptions aggregated from awaited tasks."""
        self.exceptions = exceptions

    def __str__(self) -> str:
        """Join aggregated exception messages into a newline-delimited string."""
        return "\n".join(str(e) for e in self.exceptions)


async def run_in_loop(coro: Coroutine, loop: asyncio.AbstractEventLoop, timeout: float = GENERAL_TIMEOUT):
    """Run `coro` on `loop`, using thread handoff when switching event loops."""
    running_loop = asyncio.get_running_loop()
    if running_loop == loop:
        return await coro
    return await call_sync_from_async(_run_in_loop, coro, loop, timeout)


def _run_in_loop(coro: Coroutine, loop: asyncio.AbstractEventLoop, timeout: float):
    """Run a coroutine in a specific event loop with timeout.

    Args:
        coro: The coroutine to run.
        loop: The event loop to run the coroutine in.
        timeout: Timeout in seconds for the coroutine execution.

    Returns:
        The result of the coroutine execution.

    """
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)
