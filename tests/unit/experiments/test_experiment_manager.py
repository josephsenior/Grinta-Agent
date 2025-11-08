"""Tests for experiment configuration loading and application."""

from __future__ import annotations

import importlib
import json
import sys
import types
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from forge.experiments import experiment_manager
from forge.experiments.experiment_manager import ExperimentManager, load_experiment_config
from forge.storage.locations import get_experiment_config_filename


class DummyFileStore:
    """Minimal file store stub that mimics read behaviour."""

    def __init__(self, contents: dict[str, str]) -> None:
        self._contents = contents

    def read(self, path: str) -> str:
        if path not in self._contents:
            raise FileNotFoundError(path)
        return self._contents[path]


@dataclass
class DummyConversationSettings:
    """Stand-in for ConversationInitData that lets us observe mutation."""

    topic: str


class DummyAgentConfig:
    """Simple agent config object with a mutable attribute for overrides."""

    temperature: float = 0.1
    model: str = "gpt-4o"


class DummyForgeConfig:
    """ForgeConfig stub exposing default_agent + getter."""

    default_agent = "primary"

    def __init__(self) -> None:
        self._agent = DummyAgentConfig()

    def get_agent_config(self, agent_name: str) -> DummyAgentConfig:
        assert agent_name == self.default_agent
        return self._agent


def test_load_experiment_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid JSON should be parsed into ExperimentConfig."""
    conversation_id = "abc123"
    path = get_experiment_config_filename(conversation_id)
    payload = {"config": {"temperature": "0.8"}}
    monkeypatch.setattr(
        experiment_manager,
        "file_store",
        DummyFileStore({path: json.dumps(payload)}),
        raising=False,
    )

    result = load_experiment_config(conversation_id)

    assert result is not None
    assert result.config == {"temperature": "0.8"}


def test_load_experiment_config_handles_file_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing files should be swallowed gracefully."""
    conversation_id = "missing"
    monkeypatch.setattr(
        experiment_manager,
        "file_store",
        DummyFileStore({}),
        raising=False,
    )

    assert load_experiment_config(conversation_id) is None


def test_load_experiment_config_logs_on_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-JSON payloads should trigger warning and return None."""
    conversation_id = "broken"
    path = get_experiment_config_filename(conversation_id)
    warnings: list[str] = []

    def fake_warning(message: str, *args: object) -> None:
        warnings.append(message % args if args else message)

    monkeypatch.setattr(
        experiment_manager,
        "file_store",
        DummyFileStore({path: "{not json"}),
        raising=False,
    )
    monkeypatch.setattr(experiment_manager.logger, "warning", fake_warning)

    assert load_experiment_config(conversation_id) is None
    assert any("Failed to load experiment config" in msg for msg in warnings)


def test_run_config_variant_test_applies_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Overrides should be applied to the default agent config when present."""
    conversation_id = "config"
    path = get_experiment_config_filename(conversation_id)
    payload = {"config": {"temperature": "0.6", "nonexistent": "ignore"}}
    monkeypatch.setattr(
        experiment_manager,
        "file_store",
        DummyFileStore({path: json.dumps(payload)}),
        raising=False,
    )
    config = DummyForgeConfig()

    updated = ExperimentManager.run_config_variant_test("user", conversation_id, config)

    assert updated.get_agent_config("primary").temperature == "0.6"
    # Unknown keys should be ignored silently
    assert not hasattr(updated.get_agent_config("primary"), "nonexistent")


def test_run_config_variant_test_is_noop_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no experiment config is present, config object should be returned unchanged."""
    conversation_id = "no-config"
    monkeypatch.setattr(
        experiment_manager,
        "file_store",
        DummyFileStore({}),
        raising=False,
    )
    config = DummyForgeConfig()
    original_agent = config.get_agent_config("primary")

    updated = ExperimentManager.run_config_variant_test("user", conversation_id, config)

    assert updated is config
    assert updated.get_agent_config("primary") is original_agent


def test_experiment_manager_impl_respects_custom_class(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment override should allow selecting a custom ExperimentManager implementation."""

    module_name = "tests.unit.experiments._custom_experiment_manager"
    module = types.ModuleType(module_name)

    class CustomExperimentManager(experiment_manager.ExperimentManager):
        calls: list[tuple[str, str]] = []

        @staticmethod
        def run_conversation_variant_test(user_id: str, conversation_id: str, conversation_settings):
            CustomExperimentManager.calls.append((user_id, conversation_id))
            return conversation_settings

    module.CustomExperimentManager = CustomExperimentManager
    sys.modules[module_name] = module
    monkeypatch.setenv("FORGE_EXPERIMENT_MANAGER_CLS", f"{module_name}.CustomExperimentManager")
    try:
        experiment_manager.get_impl.cache_clear()
        impl = experiment_manager.get_impl(
            experiment_manager.ExperimentManager,
            f"{module_name}.CustomExperimentManager",
        )
        monkeypatch.setattr(experiment_manager, "ExperimentManagerImpl", impl, raising=False)
        assert experiment_manager.ExperimentManagerImpl is CustomExperimentManager

        conversation_settings = DummyConversationSettings(topic="chatting")
        result = experiment_manager.ExperimentManagerImpl.run_conversation_variant_test("user", "conv", conversation_settings)

        assert result is conversation_settings
        assert CustomExperimentManager.calls == [("user", "conv")]
    finally:
        monkeypatch.delenv("FORGE_EXPERIMENT_MANAGER_CLS", raising=False)
        experiment_manager.get_impl.cache_clear()
        sys.modules.pop(module_name, None)

