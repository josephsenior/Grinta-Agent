"""Model discovery helpers simplified for core providers."""

from __future__ import annotations

from typing import List
from forge.core.config import ForgeConfig


def get_supported_llm_models(config: ForgeConfig | None = None) -> List[str]:
    """Get all models supported by the simplified core providers.
    
    Returns a curated list of famous models from OpenAI, Anthropic, Google, and xAI.
    """
    return [
        # OpenAI
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/o1-preview",
        "openai/o1-mini",
        "openai/o3-mini",
        
        # Anthropic
        "anthropic/claude-3-5-sonnet-latest",
        "anthropic/claude-3-5-haiku-latest",
        "anthropic/claude-3-7-sonnet-latest",
        "anthropic/claude-3-opus-latest",
        
        # Google / Gemini
        "google/gemini-1.5-pro-latest",
        "google/gemini-1.5-flash-latest",
        "google/gemini-2.0-flash-exp",
        "google/gemini-2.0-flash-thinking-exp",
        
        # xAI / Grok
        "xai/grok-2-latest",
        "xai/grok-beta",
    ]


def get_all_models() -> List[str]:
    """Alias for get_supported_llm_models for backwards compatibility."""
    return get_supported_llm_models()
