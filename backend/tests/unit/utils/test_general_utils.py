from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.utils import utils as general_utils


class DummyLLMConfig(SimpleNamespace):
    pass


class DummyConfig:
    def __init__(self) -> None:
        self._llm_config = DummyLLMConfig(model="base", api_key=None, base_url=None)
        self.file_store = "local"
        self.file_store_path = "/tmp"
        self.file_store_web_hook_url = None
        self.file_store_web_hook_headers = None
        self.file_store_web_hook_batch = None

    def get_llm_config(self):
        return DummyLLMConfig(**self._llm_config.__dict__)

    def set_llm_config(self, cfg):
        self._llm_config = cfg


class DummySettings(SimpleNamespace):
    pass


def test_setup_llm_config_updates_from_settings() -> None:
    config = DummyConfig()
    settings = DummySettings(llm_model="gpt", llm_api_key="k", llm_base_url="http://")
    updated = general_utils.setup_llm_config(config, settings)
    cfg = updated.get_llm_config()
    assert cfg.model == "gpt"
    assert cfg.api_key == "k"
    assert cfg.base_url == "http://"


def test_create_registry_and_conversation_stats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = DummyConfig()

    class FakeRegistry:
        def __init__(self, user_config, agent_cls):
            self.user_config = user_config
            self.agent_cls = agent_cls
            self.handlers = []

        def subscribe(self, handler):
            self.handlers.append(handler)

    class FakeConversationStats:
        def __init__(self, file_store, sid, user_id):
            self.file_store = file_store
            self.sid = sid
            self.user_id = user_id

        def register_llm(self):
            return "registered"

    monkeypatch.setattr(general_utils, "LLMRegistry", FakeRegistry)
    monkeypatch.setattr(general_utils, "ConversationStats", FakeConversationStats)
    monkeypatch.setattr(
        general_utils, "get_file_store", lambda **kwargs: {"store": "ok"}
    )

    settings = DummySettings(
        llm_model="custom", llm_api_key="secret", llm_base_url="url", agent="agent"
    )
    registry, stats, new_config = general_utils.create_registry_and_conversation_stats(
        config, "session", "user", user_settings=settings
    )

    assert registry.agent_cls == "agent"
    assert stats.sid == "session"
    assert new_config.get_llm_config().model == "custom"
    assert registry.handlers[0]() == "registered"
