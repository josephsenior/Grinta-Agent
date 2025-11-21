"""Shared gRPC client utilities for service adapters."""

from __future__ import annotations

import logging
from typing import Iterable, Sequence

import grpc

_LOGGER = logging.getLogger(__name__)


DEFAULT_CHANNEL_OPTIONS: Sequence[tuple[str, int]] = (
    ("grpc.keepalive_time_ms", 60_000),
    ("grpc.keepalive_timeout_ms", 20_000),
    ("grpc.keepalive_permit_without_calls", 1),
    ("grpc.http2.max_pings_without_data", 0),
    ("grpc.http2.min_time_between_pings_ms", 10_000),
    ("grpc.max_receive_message_length", 32 * 1024 * 1024),
    ("grpc.max_send_message_length", 32 * 1024 * 1024),
)


def create_insecure_channel(
    endpoint: str,
    *,
    options: Iterable[tuple[str, int]] | None = None,
) -> grpc.Channel:
    """Create an insecure gRPC channel with keepalive defaults."""

    channel_options = list(options or DEFAULT_CHANNEL_OPTIONS)
    _LOGGER.debug("Creating insecure gRPC channel endpoint=%s options=%s", endpoint, channel_options)
    return grpc.insecure_channel(endpoint, options=channel_options)
