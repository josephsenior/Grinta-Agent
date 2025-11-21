"""Strategies for condensing long conversation histories into summaries."""

from forge.memory.condenser.condenser import (
    CONDENSER_REGISTRY,
    Condensation,
    Condenser,
    get_condensation_metadata,
)
from forge.memory.view import View

# Import impl to trigger condenser registrations
from forge.memory.condenser import impl  # noqa: F401

__all__ = [
    "CONDENSER_REGISTRY",
    "Condensation",
    "Condenser",
    "get_condensation_metadata",
    "View",
]
