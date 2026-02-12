"""Backwards-compatibility shim – canonical location is forge.models.model_catalog."""

from backend.models.model_catalog import get_all_models, get_supported_llm_models  # noqa: F401

__all__ = ["get_supported_llm_models", "get_all_models"]

