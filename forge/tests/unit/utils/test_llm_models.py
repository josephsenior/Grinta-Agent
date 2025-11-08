from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.utils import llm


class DummySecret:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


class DummyLLMConfig(SimpleNamespace):
    pass


class DummyForgeConfig:
    def __init__(self) -> None:
        self.llms = {}
        self._llm_config = DummyLLMConfig(
            model="bedrock/model",
            aws_region_name="us-east-1",
            aws_access_key_id=DummySecret("AKIA"),
            aws_secret_access_key=DummySecret("secret"),
            base_url=None,
        )

    def get_llm_config(self):
        return self._llm_config


def test_get_openrouter_models_success(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "data": [
                    {"id": "openrouter/free-model", "pricing": {"prompt": "0", "completion": "0"}},
                    {"id": "openrouter/paid-model", "pricing": {"prompt": "1", "completion": "1"}},
                ]
            }

    monkeypatch.setattr(llm.httpx, "get", lambda *args, **kwargs: FakeResponse())
    models = llm._get_openrouter_models()
    assert models == ["openrouter/free-model", "openrouter/paid-model"]


def test_get_openrouter_models_fallback(monkeypatch):
    monkeypatch.setattr(llm.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    models = llm._get_openrouter_models()
    assert "openrouter/meta-llama/llama-3.3-70b-instruct:free" in models


def test_get_litellm_models(monkeypatch):
    monkeypatch.setattr(llm.litellm, "model_list", ["gpt-4"])
    monkeypatch.setattr(llm.litellm, "model_cost", {"gpt-3.5": 0})
    monkeypatch.setattr(llm.bedrock, "remove_error_modelId", lambda models: models)
    models = llm._get_litellm_models()
    assert "gpt-4" in models and "gpt-3.5" in models


def test_get_bedrock_models(monkeypatch):
    config = DummyForgeConfig()
    monkeypatch.setattr(llm.bedrock, "list_foundation_models", lambda *args, **kwargs: ["model-a"])
    assert llm._get_bedrock_models(config) == ["model-a"]

    config._llm_config = DummyLLMConfig(model="none", aws_region_name=None, aws_access_key_id=None, aws_secret_access_key=None)
    assert llm._get_bedrock_models(config) == []


def test_get_ollama_models(monkeypatch):
    config = DummyForgeConfig()
    config.llms = {"default": DummyLLMConfig(model="ollama/llama", ollama_base_url="http://localhost:11434")}

    class FakeResponse:
        def json(self):
            return {"models": [{"name": "llama2"}]}

    monkeypatch.setattr(llm.httpx, "get", lambda *args, **kwargs: FakeResponse())
    assert llm._get_ollama_models(config) == ["ollama/llama2"]

    monkeypatch.setattr(llm.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(llm.httpx.HTTPError("fail")))
    assert llm._get_ollama_models(config) == []


def test_openhands_models_and_deduplicate() -> None:
    models = llm._get_openhands_proprietary_models()
    assert "Openhands/claude-sonnet-4-20250514" in models
    deduped = llm._deduplicate_and_prioritize(["openrouter/model", "gpt-4", "openrouter/model"])
    assert deduped[0].startswith("openrouter/")
    assert "gpt-4" in deduped


def test_get_supported_llm_models(monkeypatch):
    config = DummyForgeConfig()
    monkeypatch.setattr(llm, "_get_litellm_models", lambda: ["litellm/model"])
    monkeypatch.setattr(llm, "_get_openrouter_models", lambda: ["openrouter/free"])
    monkeypatch.setattr(llm, "_get_bedrock_models", lambda cfg: ["bedrock/model"])
    monkeypatch.setattr(llm, "_get_ollama_models", lambda cfg: ["ollama/model"])
    monkeypatch.setattr(llm, "_get_openhands_proprietary_models", lambda: ["Openhands/custom"])
    models = llm.get_supported_llm_models(config)
    assert models[0] == "openrouter/free"
    assert {"bedrock/model", "ollama/model", "Openhands/custom"} <= set(models)

