"""Adapters for bridging service contracts with monolith implementations."""

from .event_adapter import EventServiceAdapter
from .runtime_adapter import RuntimeServiceAdapter

__all__ = ["EventServiceAdapter", "RuntimeServiceAdapter"]

