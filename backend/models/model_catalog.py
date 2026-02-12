"""Model discovery helpers driven by the unified model catalog."""

from __future__ import annotations

from typing import List
from backend.core.config import ForgeConfig
from backend.models.catalog_loader import get_featured_models


def get_supported_llm_models(config: ForgeConfig | None = None) -> List[str]:
    """Get all models marked ``featured`` in catalog.toml.

    Returns ``provider/name`` strings suitable for the API model picker.
    """
    return get_featured_models()


def get_all_models() -> List[str]:
    """Alias for get_supported_llm_models for backwards compatibility."""
    return get_supported_llm_models()
