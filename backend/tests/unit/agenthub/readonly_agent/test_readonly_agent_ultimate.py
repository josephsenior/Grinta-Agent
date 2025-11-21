from __future__ import annotations

from types import SimpleNamespace

import pytest

import forge.agenthub.readonly_agent.readonly_agent_ultimate as module


@pytest.fixture(autouse=True)
def patch_codeact_init(monkeypatch):
    def fake_init(self, config, llm_registry):
        self.config = config
        self.llm_registry = llm_registry
        self._prompt_manager = None
        self.mcp_tools = {}
        self.tools = [{"function": {"name": "view"}}]

    monkeypatch.setattr(module.CodeActAgent, "__init__", fake_init)


class DummyFileCache:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.stats = {"total_requests": 0, "hits": 0, "hit_rate_percent": 0}
        self.cleared = False

    def get_stats(self):
        return dict(self.stats)

    def clear(self):
        self.cleared = True


def build_config(**overrides):
    defaults = {
        "readonly_cache_size": 42,
        "readonly_cache_ttl": 7,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_init_initializes_file_cache(monkeypatch):
    captured = {}

    def fake_file_cache(*args, **kwargs):
        captured["instance"] = DummyFileCache(*args, **kwargs)
        return captured["instance"]

    monkeypatch.setattr(module, "FileCache", fake_file_cache)
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    assert captured["instance"].kwargs["max_cache_size"] == 42
    assert captured["instance"].kwargs["ttl_seconds"] == 7
    assert agent.file_cache is captured["instance"]


def test_prompt_manager_cached(monkeypatch):
    sentinel = SimpleNamespace(path=None)

    class DummyPromptManager:
        def __init__(self, prompt_dir, system_prompt_filename):
            sentinel.path = prompt_dir
            sentinel.system = system_prompt_filename

    monkeypatch.setattr(module, "PromptManager", DummyPromptManager)
    monkeypatch.setattr(module, "FileCache", lambda *a, **k: DummyFileCache())
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    first = agent.prompt_manager
    second = agent.prompt_manager
    assert first is second
    assert sentinel.system == "system_prompt_ultimate.j2"
    assert "prompts" in sentinel.path


def test_get_tools_adds_optional_tools(monkeypatch):
    base_tools = [{"function": {"name": "view"}}]
    monkeypatch.setattr(
        module.readonly_function_calling, "get_tools", lambda: list(base_tools)
    )

    def fake_explorer():
        return {"function": {"name": "ultimate_explorer"}}

    def fake_semantic():
        return {"function": {"name": "semantic_search"}}

    monkeypatch.setattr(
        "forge.agenthub.readonly_agent.tools.ultimate_explorer.create_ultimate_explorer_tool",
        lambda: fake_explorer(),
    )
    monkeypatch.setattr(
        "forge.agenthub.readonly_agent.tools.semantic_search.create_semantic_search_tool",
        lambda: fake_semantic(),
    )
    monkeypatch.setattr(module, "FileCache", lambda *a, **k: DummyFileCache())
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    tools = agent._get_tools()
    names = [tool["function"]["name"] for tool in tools]
    assert "ultimate_explorer" in names
    assert "semantic_search" in names


def test_get_tools_handles_import_errors(monkeypatch):
    monkeypatch.setattr(
        module.readonly_function_calling, "get_tools", lambda: [{"function": {"name": "view"}}]
    )
    monkeypatch.setattr(
        "forge.agenthub.readonly_agent.tools.ultimate_explorer.create_ultimate_explorer_tool",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        "forge.agenthub.readonly_agent.tools.semantic_search.create_semantic_search_tool",
        lambda: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    monkeypatch.setattr(module, "FileCache", lambda *a, **k: DummyFileCache())
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    tools = agent._get_tools()
    assert len(tools) == 1


def test_set_mcp_tools_warns(monkeypatch):
    monkeypatch.setattr(module, "FileCache", lambda *a, **k: DummyFileCache())
    warnings = []

    def fake_warning(message, *args, **kwargs):
        warnings.append(message)

    monkeypatch.setattr(module.logger, "warning", fake_warning)
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    agent.set_mcp_tools([{}])
    assert any("does not support MCP tools" in msg for msg in warnings)


def test_response_to_actions_tracks_cache_stats(monkeypatch):
    class StubCache(DummyFileCache):
        def get_stats(self):
            self.stats.update(
                {"total_requests": 50, "hits": 25, "hit_rate_percent": 50}
            )
            return dict(self.stats)

    def fake_response(response, mcp_tool_names=None):
        return ["action"]

    monkeypatch.setattr(module, "FileCache", lambda *a, **k: StubCache())
    monkeypatch.setattr(
        module.readonly_function_calling, "response_to_actions", fake_response
    )
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    agent.mcp_tools = {"tool": object()}
    assert agent.response_to_actions(SimpleNamespace()) == ["action"]


def test_response_to_actions_without_logging(monkeypatch):
    class Cache(DummyFileCache):
        def get_stats(self):
            self.stats.update({"total_requests": 10})
            return dict(self.stats)

    monkeypatch.setattr(module, "FileCache", lambda *a, **k: Cache())
    monkeypatch.setattr(
        module.readonly_function_calling,
        "response_to_actions",
        lambda response, mcp_tool_names=None: ["ok"],
    )
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    assert agent.response_to_actions(SimpleNamespace()) == ["ok"]


def test_get_cache_stats_and_clear(monkeypatch):
    cache = DummyFileCache()
    monkeypatch.setattr(module, "FileCache", lambda *a, **k: cache)
    agent = module.UltimateReadOnlyAgent(build_config(), llm_registry=SimpleNamespace())
    assert agent.get_cache_stats() == cache.stats
    agent.clear_cache()
    assert cache.cleared is True

