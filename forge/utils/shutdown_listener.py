"""This module monitors the app for shutdown signals. This exists because the atexit module.

does not play nocely with stareltte / uvicorn shutdown signals.
"""

from __future__ import annotations

import asyncio
import signal
import threading
import time
from typing import TYPE_CHECKING, Callable
from uuid import UUID, uuid4

from uvicorn.server import HANDLED_SIGNALS

from forge.core.logger import forge_logger as logger

if TYPE_CHECKING:
    from types import FrameType

_should_exit = None
_shutdown_listeners: dict[UUID, Callable] = {}


def _register_signal_handler(sig: signal.Signals) -> None:
    """Register a signal handler for shutdown signals.

    Args:
        sig: The signal to register a handler for.

    """
    original_handler = None

    def handler(signum, frame):
        """Signal handler that sets shutdown flag and invokes cleanup callback."""
        if should_continue():
            logger.debug("shutdown_signal:%s", sig)
            global _should_exit
            if not _should_exit:
                _should_exit = True
                listeners = list(_shutdown_listeners.values())
                for callable in listeners:
                    try:
                        callable()
                    except Exception:
                        logger.exception("Error calling shutdown listener")
            if original_handler:
                original_handler(sig, frame)

    original_handler = signal.signal(sig, handler)


def _register_signal_handlers() -> None:
    """Register all shutdown signal handlers."""
    global _should_exit
    if _should_exit is not None:
        return
    _should_exit = False
    logger.debug("_register_signal_handlers")
    if threading.current_thread() is threading.main_thread():
        logger.debug("_register_signal_handlers:main_thread")
        for sig in HANDLED_SIGNALS:
            _register_signal_handler(sig)
    else:
        logger.debug("_register_signal_handlers:not_main_thread")


def should_exit() -> bool:
    """Check if the application should exit due to shutdown signals.

    Returns:
        bool: True if the application should exit, False otherwise.

    """
    _register_signal_handlers()
    return bool(_should_exit)


def should_continue() -> bool:
    """Check if the application should continue running.

    Returns:
        bool: True if the application should continue, False if it should exit.

    """
    _register_signal_handlers()
    return not _should_exit


def sleep_if_should_continue(timeout: float) -> None:
    """Sleep for the specified timeout, waking up early if shutdown is requested.

    Args:
        timeout: The maximum time to sleep in seconds.

    """
    if timeout <= 1:
        time.sleep(timeout)
        return
    start_time = time.time()
    while time.time() - start_time < timeout and should_continue():
        time.sleep(1)


async def async_sleep_if_should_continue(timeout: float) -> None:
    """Asynchronously sleep for the specified timeout, waking up early if shutdown is requested.

    Args:
        timeout: The maximum time to sleep in seconds.

    """
    if timeout <= 1:
        await asyncio.sleep(timeout)
        return
    start_time = time.time()
    while time.time() - start_time < timeout and should_continue():
        await asyncio.sleep(1)


def add_shutdown_listener(callable: Callable) -> UUID:
    """Add a shutdown listener function.

    Args:
        callable: Function to call when shutdown signals are received.

    Returns:
        UUID: Unique identifier for the listener.

    """
    id_ = uuid4()
    _shutdown_listeners[id_] = callable
    return id_


def remove_shutdown_listener(id_: UUID) -> bool:
    """Remove a shutdown listener by its ID.

    Args:
        id_: The UUID of the listener to remove.

    Returns:
        bool: True if the listener was found and removed, False otherwise.

    """
    return _shutdown_listeners.pop(id_, None) is not None
