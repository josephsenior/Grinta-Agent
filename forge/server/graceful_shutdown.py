"""Graceful shutdown handler for Forge server.

Ensures proper cleanup of resources on shutdown:
- Stop accepting new requests
- Wait for in-flight requests to complete
- Close Socket.IO connections gracefully
- Clean up Docker containers
- Close database connections
- Flush logs
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import Callable, Optional

from forge.core.logger import forge_logger as logger

_shutdown_handlers: list[Callable] = []
_shutdown_in_progress = False
_shutdown_timeout = 30  # seconds


def register_shutdown_handler(handler: Callable) -> None:
    """Register a handler to be called during graceful shutdown.

    Args:
        handler: Async or sync function to call during shutdown
    """
    _shutdown_handlers.append(handler)


async def graceful_shutdown() -> None:
    """Perform graceful shutdown of all registered resources."""
    global _shutdown_in_progress

    if _shutdown_in_progress:
        logger.warning("Shutdown already in progress, skipping")
        return

    _shutdown_in_progress = True
    logger.info("Starting graceful shutdown...")

    # Execute all shutdown handlers
    for handler in _shutdown_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()
            logger.debug(f"Shutdown handler {handler.__name__} completed")
        except Exception as e:
            logger.error(f"Error in shutdown handler {handler.__name__}: {e}", exc_info=True)

    logger.info("Graceful shutdown completed")


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    import signal as signal_module

    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # Run graceful shutdown in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule shutdown as a task
            asyncio.create_task(graceful_shutdown())
        else:
            # Run shutdown directly if loop is not running
            loop.run_until_complete(graceful_shutdown())
        sys.exit(0)

    # Register handlers for common shutdown signals
    signal_module.signal(signal_module.SIGTERM, signal_handler)
    signal_module.signal(signal_module.SIGINT, signal_handler)


# Auto-register signal handlers on import
setup_signal_handlers()

