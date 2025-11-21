"""Startup diagnostics for verifying external dependencies."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Callable, Coroutine

from forge.core.logger import forge_logger as logger


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _run_coro(coro_factory: Callable[[], Coroutine[Any, Any, object]]) -> None:
    """Run an async coroutine, creating an event loop if necessary."""

    try:
        asyncio.run(coro_factory())
    except RuntimeError as exc:
        if "asyncio.run()" in str(exc):
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                loop.run_until_complete(coro_factory())
            finally:
                asyncio.set_event_loop(None)
                loop.close()
        else:  # pragma: no cover - defensive
            raise


def verify_observability_dependencies(config) -> None:
    """Fail fast when strict observability is enabled but dependencies are missing."""

    if not _should_verify_observability(config):
        return

    errors: list[str] = []
    errors.extend(_check_prometheus_dependency())
    errors.extend(_check_redis_dependency(config))

    if errors:
        error_message = "Observability dependency check failed:\n" + "\n".join(
            f"- {msg}" for msg in errors
        )
        raise RuntimeError(error_message)

    logger.info("Observability dependency check passed.")


def _should_verify_observability(config) -> bool:
    strict = config.require_observability_dependencies or _env_flag(
        "FORGE_STRICT_OBSERVABILITY"
    )
    if strict:
        return True
    logger.debug(
        "Observability dependency check skipped "
        "(require_observability_dependencies disabled)."
    )
    return False


def _check_prometheus_dependency() -> list[str]:
    try:
        import prometheus_client  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on env
        return [
            "prometheus_client package is required when strict observability is enabled "
            f"({exc})"
        ]
    return []


def _check_redis_dependency(config) -> list[str]:
    redis_url = config.redis_url or os.getenv("REDIS_URL")
    if not redis_url:
        return [
            "Redis URL not configured (set ForgeConfig.redis_url or REDIS_URL) "
            "but strict observability is enabled."
        ]

    try:
        import redis.asyncio as redis
    except Exception as exc:  # pragma: no cover - depends on env
        return [f"redis.asyncio module unavailable: {exc}"]

    async def _ping() -> None:
        client = redis.from_url(
            redis_url,
            socket_connect_timeout=config.redis_connection_timeout,
            encoding="utf-8",
            decode_responses=True,
        )
        try:
            await client.ping()
        finally:
            await client.close()

    try:
        _run_coro(_ping)
    except Exception as exc:  # pragma: no cover - depends on env
        return [f"Unable to connect to Redis at {redis_url}: {exc}"]
    return []

