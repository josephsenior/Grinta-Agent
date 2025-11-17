from __future__ import annotations

from types import SimpleNamespace

import pytest

import forge.agenthub.loc_agent.loc_agent_ultimate as module


@pytest.fixture(autouse=True)
def patch_codeact_init(monkeypatch):
    def fake_init(self, config, llm_registry):
        self.config = config
        self.llm_registry = llm_registry
        self._prompt_manager = None
        self.mcp_tools = {}

    monkeypatch.setattr(module.CodeActAgent, "__init__", fake_init)


class DummyGraphCache:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.stats = {"total_requests": 0, "hits": 0, "hit_rate_percent": 0}
        self.cleared = False
        self.invalidated = None

    def get_stats(self):
        return dict(self.stats)

    def clear(self):
        self.cleared = True

    def _invalidate_repo(self, repo_path):
        self.invalidated = repo_path


def build_config(tmp_path, **overrides):
    defaults = {
        "loc_cache_dir": str(tmp_path / "cache"),
        "loc_cache_ttl": 123,
        "loc_cache_persist": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_init_initializes_tools_and_graph_cache(tmp_path, monkeypatch):
    dummy_tools = [{"function": {"name": "search_code_snippets"}}]
    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: dummy_tools
    )

    created_cache = {}

    def fake_graph_cache(*args, **kwargs):
        created_cache["instance"] = DummyGraphCache(*args, **kwargs)
        return created_cache["instance"]

    monkeypatch.setattr(module, "GraphCache", fake_graph_cache)

    config = build_config(tmp_path)
    agent = module.UltimateLocAgent(config=config, llm_registry=SimpleNamespace())

    assert agent.tools == dummy_tools
    cache_kwargs = created_cache["instance"].kwargs
    assert cache_kwargs["cache_dir"] == config.loc_cache_dir
    assert cache_kwargs["ttl_seconds"] == config.loc_cache_ttl
    assert cache_kwargs["enable_persistence"] == config.loc_cache_persist


def test_prompt_manager_cached(tmp_path, monkeypatch):
    sentinel = SimpleNamespace(path=None)

    class DummyPromptManager:
        def __init__(self, prompt_dir):
            sentinel.path = prompt_dir

    monkeypatch.setattr(module, "PromptManager", DummyPromptManager)
    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: []
    )
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: DummyGraphCache())

    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    first = agent.prompt_manager
    second = agent.prompt_manager
    assert first is second
    assert sentinel.path.endswith("prompts")


def test_response_to_actions_tracks_stats(monkeypatch, tmp_path):
    called_with = {}

    def fake_response_to_actions(response, mcp_tool_names=None):
        called_with["names"] = mcp_tool_names
        return ["ok"]

    class Cache(DummyGraphCache):
        def get_stats(self):
            self.stats.update(
                {"total_requests": 20, "hits": 10, "hit_rate_percent": 50}
            )
            return dict(self.stats)

    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: []
    )
    monkeypatch.setattr(
        module.locagent_function_calling, "response_to_actions", fake_response_to_actions
    )
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: Cache())

    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    agent.mcp_tools = {"tool-a": object()}

    result = agent.response_to_actions(SimpleNamespace())
    assert result == ["ok"]
    assert called_with["names"] == ["tool-a"]


def test_repository_and_cache_helpers(tmp_path, monkeypatch):
    cache = DummyGraphCache()
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: cache)
    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: []
    )

    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    agent.set_repository("repo-path")
    assert agent.current_repo == "repo-path"

    assert agent.get_graph_stats() == cache.stats
    agent.clear_graph_cache()
    assert cache.cleared is True

    cache.stats["full_rebuilds"] = 0
    agent.rebuild_graph("repo-path")
    assert cache.invalidated == "repo-path"
    assert cache.stats["full_rebuilds"] == 1


def test_init_handles_non_dict_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: ["not-a-dict"]
    )
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: DummyGraphCache())
    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    assert agent.tools == ["not-a-dict"]


def test_response_to_actions_skips_stats_log_when_threshold_not_met(monkeypatch, tmp_path):
    class Cache(DummyGraphCache):
        def get_stats(self):
            self.stats.update({"total_requests": 3})
            return dict(self.stats)

    monkeypatch.setattr(
        module.locagent_function_calling, "get_tools", lambda: []
    )
    monkeypatch.setattr(
        module.locagent_function_calling,
        "response_to_actions",
        lambda response, mcp_tool_names=None: ["ok"],
    )
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: Cache())

    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    assert agent.response_to_actions(SimpleNamespace()) == ["ok"]


def test_init_handles_tool_without_string_name(tmp_path, monkeypatch):
    tools = [{"function": {"name": None}}]
    monkeypatch.setattr(module.locagent_function_calling, "get_tools", lambda: tools)
    monkeypatch.setattr(module, "GraphCache", lambda *a, **k: DummyGraphCache())
    agent = module.UltimateLocAgent(build_config(tmp_path), llm_registry=SimpleNamespace())
    assert agent.tools == tools

