from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from forge.utils import utils as utils_module
from forge.utils.utils import create_registry_and_conversation_stats, setup_llm_config


@dataclass
class DummyLLMConfig:
    model: str = ""
    api_key: str | None = None
    base_url: str | None = None


@dataclass
class DummyConfig:
    llm_config: DummyLLMConfig = field(default_factory=DummyLLMConfig)
    file_store: str = "memory"
    file_store_path: str | None = "path"
    file_store_web_hook_url: str | None = "url"
    file_store_web_hook_headers: dict | None = field(default_factory=dict)
    file_store_web_hook_batch: bool = False

    def get_llm_config(self) -> DummyLLMConfig:
        return DummyLLMConfig(
            model=self.llm_config.model,
            api_key=self.llm_config.api_key,
            base_url=self.llm_config.base_url,
        )

    def set_llm_config(self, config: DummyLLMConfig) -> None:
        self.llm_config = config


def test_setup_llm_config_updates_copy():
    original = DummyConfig()
    settings = SimpleNamespace(llm_model="gpt", llm_api_key="key", llm_base_url="base")
    updated = setup_llm_config(original, settings)
    assert updated is not original
    assert updated.llm_config.model == "gpt"
    assert updated.llm_config.api_key == "key"
    assert updated.llm_config.base_url == "base"
    # Original config remains unchanged
    assert original.llm_config.model == ""
    assert original.llm_config.api_key is None


def test_create_registry_and_conversation_stats(monkeypatch):
    config = DummyConfig()
    store_instance = object()
    registry_calls: dict[str, object] = {}

    class DummyRegistry:
        def __init__(self, cfg, agent):
            registry_calls["config"] = cfg
            registry_calls["agent"] = agent
            self.subscribers = []

        def subscribe(self, fn):
            self.subscribers.append(fn)

    class DummyStats:
        def __init__(self, store, sid, user_id):
            registry_calls["stats_args"] = (store, sid, user_id)

        def register_llm(self, *args, **kwargs):
            pass

    monkeypatch.setattr(utils_module, "LLMRegistry", DummyRegistry)
    monkeypatch.setattr(utils_module, "ConversationStats", DummyStats)
    monkeypatch.setattr(utils_module, "get_file_store", lambda **_: store_instance)

    user_settings = SimpleNamespace(
        llm_model="model",
        llm_api_key="key",
        llm_base_url="url",
        agent="agent_cls",
    )

    registry, stats, user_config = create_registry_and_conversation_stats(
        config,
        sid="session-id",
        user_id="user-id",
        user_settings=user_settings,
    )

    assert isinstance(registry, DummyRegistry)
    assert isinstance(stats, DummyStats)
    assert registry_calls["agent"] == "agent_cls"
    assert registry_calls["stats_args"] == (store_instance, "session-id", "user-id")
    assert registry.subscribers == [stats.register_llm]
    assert user_config.llm_config.model == "model"

