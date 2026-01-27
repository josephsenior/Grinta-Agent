from __future__ import annotations

import pytest
from forge.utils import llm


def test_get_supported_llm_models():
    models = llm.get_supported_llm_models()
    assert isinstance(models, list)
    assert len(models) > 0
    assert "openai/gpt-4o" in models
    assert "anthropic/claude-3-5-sonnet-latest" in models
    assert "google/gemini-1.5-pro-latest" in models
    assert "xai/grok-2-latest" in models


def test_get_all_models_alias():
    assert llm.get_all_models() == llm.get_supported_llm_models()
