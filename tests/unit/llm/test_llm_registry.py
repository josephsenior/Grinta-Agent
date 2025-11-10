"""Tests for `forge.llm.llm_registry.LLMRegistry`."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export
from forge.llm import llm_registry
from forge.llm.llm_registry import LLMRegistry, RegistryEvent


@dataclass
class DummyResponse:
    content: str

    @property
    def message(self):
        return SimpleNamespace(content=self.content, tool_calls=[])


class FakeLLM:
    def __init__(self, service_id: str, config: LLMConfig, retry_listener=None):
        self.service_id = service_id
        self.config = config
        self.retry_listener = retry_listener
        self.calls: list[tuple] = []

    def completion(self, messages):
        self.calls.append(tuple(messages))
        return SimpleNamespace(choices=[DummyResponse(" ok ")])


class DummyForgeConfig:
    def __init__(self):
        with suppress_llm_env_export():
            self.llm_config = LLMConfig(model="demo", num_retries=1)
        self.default_agent = "agent"

    def get_agent_to_llm_config_map(self):
        return {"agent": self.llm_config}

    def get_llm_config_from_agent(self, agent_cls: str):
        return self.llm_config

    def get_llm_config_from_agent_config(self, agent_config):
        return self.llm_config


def test_registry_get_llm_and_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_registry, "LLM", FakeLLM)
    config = DummyForgeConfig()
    registry = LLMRegistry(config)

    events: list[RegistryEvent] = []
    registry.subscribe(events.append)

    llm = registry.get_llm("service-1", config.llm_config)
    assert registry.get_llm("service-1", config.llm_config) is llm

    other_config = LLMConfig(model="other")
    with pytest.raises(ValueError):
        registry.get_llm("service-1", other_config)

    registry._set_active_llm("service-1")
    assert registry.get_active_llm() is llm

    with pytest.raises(ValueError):
        registry._set_active_llm("missing")

    assert events
    assert any(event.service_id == "service-1" for event in events)


def test_request_extraneous_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_registry, "LLM", FakeLLM)
    registry = LLMRegistry(DummyForgeConfig())

    response = registry.request_extraneous_completion(
        service_id="temp", llm_config=registry.config.get_llm_config_from_agent("agent"), messages=[{"role": "user"}]
    )
    assert response == "ok"


def test_get_llm_from_agent_config_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_registry, "LLM", FakeLLM)
    registry = LLMRegistry(DummyForgeConfig())
    service_id = "svc"

    class DummyAgentConfig:
        pass

    agent_config = DummyAgentConfig()
    llm = registry.get_llm_from_agent_config(service_id, agent_config)
    assert registry.get_llm_from_agent_config(service_id, agent_config) is llm


def test_get_llm_without_config_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_registry, "LLM", FakeLLM)
    registry = LLMRegistry(DummyForgeConfig())
    with pytest.raises(ValueError):
        registry.get_llm("no-config")


def test_notify_handles_subscriber_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_registry, "LLM", FakeLLM)
    registry = LLMRegistry(DummyForgeConfig())
    events: list[RegistryEvent] = []
    registry.subscribe(events.append)

    logger = SimpleNamespace(records=[])

    def warning(message, *args, **kwargs):
        logger.records.append(message % args if args else message)

    monkeypatch.setattr(llm_registry, "logger", SimpleNamespace(warning=warning, info=lambda *a, **k: None))

    def bad_subscriber(event):
        raise RuntimeError("boom")

    registry.subscribe(bad_subscriber)
    registry.notify(RegistryEvent(event_type="update"))
    assert any("Failed to emit event" in item for item in logger.records)
