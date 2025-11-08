"""Tests for `forge.llm.model_features`."""

from __future__ import annotations

from forge.llm.model_features import (
    FUNCTION_CALLING_PATTERNS,
    PROMPT_CACHE_PATTERNS,
    REASONING_EFFORT_PATTERNS,
    SUPPORTS_STOP_WORDS_FALSE_PATTERNS,
    ModelFeatures,
    get_features,
    model_matches,
    normalize_model_name,
)


def test_normalize_model_name_handles_variants() -> None:
    assert normalize_model_name("OpenRouter/anthropic/Claude-3.5-Sonnet:beta") == "claude-3.5-sonnet"
    assert normalize_model_name("local-model-gguf") == "local-model"


def test_model_matches_supports_provider_patterns() -> None:
    assert model_matches("anthropic/claude-3-5-sonnet-20241022", FUNCTION_CALLING_PATTERNS)
    assert not model_matches("example/model", PROMPT_CACHE_PATTERNS)
    assert model_matches("o3-mini-2025-01-31", REASONING_EFFORT_PATTERNS)
    assert model_matches("grok-4-0709", SUPPORTS_STOP_WORDS_FALSE_PATTERNS)


def test_get_features_combines_capabilities() -> None:
    features = get_features("openrouter/anthropic/claude-sonnet-4")
    assert isinstance(features, ModelFeatures)
    assert features.supports_function_calling is True
    assert features.supports_prompt_cache is True
    assert features.supports_reasoning_effort is False
    assert features.supports_stop_words is True


