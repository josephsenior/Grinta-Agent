"""Utility helpers for managing runtime Docker containers."""

from __future__ import annotations

import contextlib

import docker
from docker.errors import DockerException

from forge.core.logger import forge_logger as logger


def stop_all_containers(prefix: str) -> None:
    """Stop all Docker containers with names matching the given prefix.

    Silently handles API errors, missing containers, and environments where Docker is unavailable.

    Args:
        prefix: Container name prefix to match

    """
    try:
        docker_client = docker.from_env()
    except DockerException as exc:  # pragma: no cover - depends on host environment
        logger.debug(
            "Skipping Docker container cleanup because the Docker client is unavailable: %s",
            exc,
        )
        return

    try:
        containers = docker_client.containers.list(all=True)
        for container in containers:
            try:
                if container.name.startswith(prefix):
                    container.stop()
            except docker.errors.APIError:
                pass
            except docker.errors.NotFound:
                pass
    except docker.errors.NotFound:
        pass
    finally:
        with contextlib.suppress(Exception):
            docker_client.close()
