from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import forge.controller  # ensure controller module initialized before importing planner
from forge.agenthub.codeact_agent.planner import CodeActPlanner


class DummyLLM:
    def __init__(self, model: str = "gpt-4"):
        self.config = SimpleNamespace(model=model)


class DummySafety:
    def __init__(self, tool_choice: str = "required"):
        self.calls: list[tuple[str, Any, str]] = []
        self.tool_choice = tool_choice

    def should_enforce_tools(self, message, state, default):
        self.calls.append((message, state, default))
        return self.tool_choice


@pytest.fixture
def planner_factory(monkeypatch):
    def _factory(
        *,
        model: str = "gpt-4",
        config_overrides: dict[str, Any] | None = None,
        prompt_bundle: dict[str, Any] | None = None,
        tool_optimizer: Any = None,
    ):
        config = SimpleNamespace(
            enable_cmd=True,
            enable_think=True,
            enable_finish=True,
            enable_condensation_request=False,
            enable_browsing=False,
            enable_editor=True,
            enable_llm_editor=False,
            enable_ultimate_editor=False,
            enable_jupyter=False,
            enable_plan_mode=True,
        )
        if config_overrides:
            for key, value in config_overrides.items():
                setattr(config, key, value)
        return CodeActPlanner(
            config=config,
            llm=DummyLLM(model),
            safety_manager=DummySafety(),
            prompt_optimizer=prompt_bundle,
            tool_optimizer=tool_optimizer,
        )

    return _factory


def test_should_use_short_tool_descriptions(planner_factory):
    planner = planner_factory(model="gpt-4o")
    assert planner._should_use_short_tool_descriptions() is True
    planner = planner_factory(model="custom-model")
    assert planner._should_use_short_tool_descriptions() is False


def test_should_use_short_tool_descriptions_without_llm(planner_factory):
    planner = planner_factory()
    planner._llm = None
    assert planner._should_use_short_tool_descriptions() is False


def test_add_core_tools_respects_flags(planner_factory, monkeypatch):
    added = []

    def fake_create_cmd_run_tool(**kwargs):
        added.append(("cmd", kwargs))
        return {"name": "cmd"}

    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.bash.create_cmd_run_tool",
        fake_create_cmd_run_tool,
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.condensation_request.CondensationRequestTool",
        "condense",
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.finish.FinishTool",
        "finish",
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.think.ThinkTool",
        "think",
    )

    planner = planner_factory(config_overrides={"enable_condensation_request": True})
    tools: list[Any] = []
    planner._add_core_tools(tools, use_short_tool_desc=True)
    assert {"name": "cmd"} in tools
    assert "finish" in tools and "think" in tools and "condense" in tools


def test_add_browsing_tool_skips_on_windows(planner_factory, monkeypatch, caplog):
    planner = planner_factory(config_overrides={"enable_browsing": True})
    monkeypatch.setattr(sys, "platform", "win32")
    tools: list[Any] = []
    planner._add_browsing_tool(tools)
    assert not tools

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.browser.BrowserTool", "browser"
    )
    planner._add_browsing_tool(tools)
    assert tools == ["browser"]


def test_add_editor_tools_prefers_ultimate(monkeypatch, planner_factory):
    planner = planner_factory(
        config_overrides={
            "enable_editor": False,
            "enable_llm_editor": False,
            "enable_ultimate_editor": True,
        }
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.create_ultimate_editor_tool",
        lambda use_short_description: {"ultimate": use_short_description},
    )
    tools: list[Any] = []
    planner._add_editor_tools(tools, True)
    assert tools == [{"ultimate": True}]


def test_add_editor_tools_default_editor(monkeypatch, planner_factory):
    planner = planner_factory(
        config_overrides={
            "enable_editor": True,
            "enable_llm_editor": False,
            "enable_ultimate_editor": False,
        }
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.str_replace_editor.create_str_replace_editor_tool",
        lambda use_short_description: {"basic": use_short_description},
    )
    tools: list[Any] = []
    planner._add_editor_tools(tools, False)
    assert tools == [{"basic": False}]


def test_add_specialized_tools(monkeypatch, planner_factory):
    planner = planner_factory(config_overrides={"enable_jupyter": True})
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.ipython.IPythonTool", "ipython"
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.database.get_database_tools",
        lambda: ["db"],
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.task_tracker.create_task_tracker_tool",
        lambda short: {"tracker": short},
    )
    tools: list[Any] = []
    planner._add_specialized_tools(tools, use_short_tool_desc=False)
    assert ["ipython", "db", {"tracker": False}] == tools


def test_apply_prompt_optimization_replaces_system_message(monkeypatch, planner_factory):
    class FakeVariant:
        id = "variant-id"
        content = "optimized content"

    class FakeOptimizer:
        def __init__(self):
            self.recorded = []

        def select_variant(self, prompt_id, category):
            return FakeVariant()

    bundle = {
        "optimizer": FakeOptimizer(),
        "storage": SimpleNamespace(auto_save=lambda: None),
    }
    planner = planner_factory(prompt_bundle=bundle)
    state = SimpleNamespace()
    messages = [{"role": "system", "content": "original"}]
    optimized = planner.apply_prompt_optimization(messages, state)
    assert optimized[0]["content"] == "optimized content"
    assert getattr(state, "_prompt_variant_id", None) == "variant-id"


def test_apply_prompt_optimization_handles_missing_variant(planner_factory):
    planner = planner_factory(prompt_bundle={"optimizer": SimpleNamespace(select_variant=lambda *a, **k: None)})
    messages = [{"role": "system", "content": "original"}]
    optimized = planner.apply_prompt_optimization(messages, SimpleNamespace())
    assert optimized == messages


def test_record_prompt_execution_tracks_success(monkeypatch, planner_factory):
    class FakeOptimizer:
        def __init__(self):
            self.records = []

        def record_execution(self, **kwargs):
            self.records.append(kwargs)

    class FakeStorage:
        def __init__(self):
            self.saved = 0

        def auto_save(self):
            self.saved += 1

    bundle = {
        "optimizer": FakeOptimizer(),
        "storage": FakeStorage(),
    }
    planner = planner_factory(prompt_bundle=bundle)
    state = SimpleNamespace(_prompt_variant_id="variant", agent_name="Agent", current_task="task")
    planner.record_prompt_execution(state, True, 1.23)
    assert bundle["optimizer"].records
    assert bundle["storage"].saved == 1


def test_apply_tool_optimization_handles_errors(planner_factory):
    class FakeToolOptimizer:
        def __init__(self):
            self.optimized = []

        def optimize_tool(self, tool, name):
            if name == "bad":
                raise RuntimeError("boom")
            updated = dict(tool)
            updated["function"]["name"] = name + "_opt"
            self.optimized.append(name)
            return updated

    planner = planner_factory(tool_optimizer=FakeToolOptimizer())
    tools = [
        {"function": {"name": "good"}},
        {"function": {"name": "bad"}},
        {"other": "noop"},
    ]
    optimized = planner._apply_tool_optimization(tools)
    assert optimized[0]["function"]["name"] == "good_opt"
    assert optimized[1]["function"]["name"] == "bad"
    assert optimized[2]["other"] == "noop"


def test_track_tool_usage_maps_actions(planner_factory):
    class FakeToolOptimizer:
        def __init__(self):
            self.calls = []

        def track_tool_execution(self, **kwargs):
            self.calls.append(kwargs)

        def create_tool_variants(self, **kwargs):
            pass

        tool_prompt_ids = {}

    planner = planner_factory(tool_optimizer=FakeToolOptimizer())
    actions = [SimpleNamespace(action="think", id=1)]
    planner.track_tool_usage(actions)
    assert planner._tool_optimizer.calls


def test_determine_tool_choice_uses_patterns(planner_factory):
    safety = DummySafety(tool_choice="forced")
    planner = planner_factory(config_overrides={}, prompt_bundle=None, tool_optimizer=None)
    planner._safety = safety
    messages = [{"role": "user", "content": "Why is the sky blue?"}]
    state = SimpleNamespace()
    assert planner._determine_tool_choice(messages, state) == "auto"
    messages = [{"role": "user", "content": "Write code now"}]
    assert planner._determine_tool_choice(messages, state) == "required"
    messages = [{"role": "user", "content": "Other"}]
    assert planner._determine_tool_choice(messages, state) == "forced"


def test_llm_supports_tool_choice(planner_factory):
    planner = planner_factory(model="gpt-4-turbo")
    assert planner._llm_supports_tool_choice() is True
    planner = planner_factory(model="custom-model")
    assert planner._llm_supports_tool_choice() is False


def test_get_last_user_message(planner_factory):
    planner = planner_factory()
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    assert planner._get_last_user_message(messages) == "hi"
    assert planner._get_last_user_message([]) is None


def test_is_question_and_is_action(planner_factory):
    planner = planner_factory()
    assert planner._is_question("How does this work?")
    assert planner._is_action("Please write code")


def test_build_llm_params_includes_metadata(planner_factory, monkeypatch):
    planner = planner_factory()
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.planner.check_tools",
        lambda tools, config: tools,
    )
    state = SimpleNamespace(
        to_llm_metadata=lambda model_name, agent_name: {
            "model": model_name,
            "agent": agent_name,
        }
    )
    messages = [{"role": "system", "content": "base"}]
    params = planner.build_llm_params(
        messages=messages,
        state=state,
        tools=[{"function": {"name": "cmd"}}],
        ace_context="ACE INFO",
    )
    assert params["messages"][0]["content"].endswith("ACE INFO")
    assert params["extra_body"]["metadata"]["model"] == planner._llm.config.model
    assert params["tool_choice"] == "auto"


def test_map_action_to_tool_unknown(planner_factory):
    planner = planner_factory()
    assert planner._map_action_to_tool(SimpleNamespace(action="think")) == "think"
    assert planner._map_action_to_tool(SimpleNamespace(action="unknown")) is None


def test_ensure_tool_variant_exists_creates_variants(planner_factory, monkeypatch):
    planner = planner_factory()
    registry = SimpleNamespace(get_variants_for_prompt=lambda prompt_id: [])

    class FakeToolOptimizer:
        def __init__(self):
            self.tool_prompt_ids = {"tool": "prompt-id"}
            self.created = []

        def create_tool_variants(self, **kwargs):
            self.created.append(kwargs)

    planner._prompt_optimizer = {"registry": registry}
    planner._tool_optimizer = FakeToolOptimizer()
    module = ModuleType("forge.prompt_optimization.tool_descriptions")
    module.get_optimized_description = lambda tool_name: {
        "description": "desc",
        "parameters": {},
    }
    monkeypatch.setitem(sys.modules, module.__name__, module)
    planner._ensure_tool_variant_exists("tool", SimpleNamespace(action="run"))
    assert planner._tool_optimizer.created


def test_ensure_tool_variant_exists_logs_errors(planner_factory, monkeypatch, caplog):
    planner = planner_factory()
    registry = SimpleNamespace(get_variants_for_prompt=lambda prompt_id: [])

    class BadToolOptimizer:
        def __init__(self):
            self.tool_prompt_ids = {"tool": "prompt-id"}

        def create_tool_variants(self, **kwargs):
            raise RuntimeError("boom")

    planner._prompt_optimizer = {"registry": registry}
    planner._tool_optimizer = BadToolOptimizer()
    module = ModuleType("forge.prompt_optimization.tool_descriptions")
    module.get_optimized_description = lambda tool_name: {
        "description": "desc",
        "parameters": {},
    }
    monkeypatch.setitem(sys.modules, module.__name__, module)
    planner._ensure_tool_variant_exists("tool", SimpleNamespace(action="run"))


def test_record_prompt_execution_no_variant(planner_factory):
    planner = planner_factory(prompt_bundle={"optimizer": object(), "storage": object()})
    state = SimpleNamespace()
    planner.record_prompt_execution(state, True, 1.0)  # should no-op without errors


def test_build_toolset_invokes_helpers(planner_factory, monkeypatch):
    planner = planner_factory()
    calls = []

    monkeypatch.setattr(planner, "_add_core_tools", lambda tools, short: calls.append("core"))
    monkeypatch.setattr(planner, "_add_browsing_tool", lambda tools: calls.append("browse"))
    monkeypatch.setattr(planner, "_add_specialized_tools", lambda tools, short: calls.append("special"))
    monkeypatch.setattr(planner, "_add_editor_tools", lambda tools, short: calls.append("editor"))
    monkeypatch.setattr(planner, "_apply_tool_optimization", lambda tools: tools + ["optimized"])
    planner._tool_optimizer = object()
    tools = planner.build_toolset()
    assert "optimized" in tools
    assert calls == ["core", "browse", "special", "editor"]


def test_build_toolset_without_optimizer(planner_factory, monkeypatch):
    planner = planner_factory()
    monkeypatch.setattr(planner, "_add_core_tools", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_browsing_tool", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_specialized_tools", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_editor_tools", lambda tools, short: tools.append("editor"))
    planner._tool_optimizer = None
    tools = planner.build_toolset()
    assert tools == ["editor"]


def test_add_editor_tools_no_editor_enabled(planner_factory):
    planner = planner_factory(
        config_overrides={
            "enable_editor": False,
            "enable_llm_editor": False,
            "enable_ultimate_editor": False,
        }
    )
    tools: list[Any] = []
    planner._add_editor_tools(tools, False)
    assert tools == []


def test_add_core_tools_handles_disabled_flags(planner_factory, monkeypatch):
    planner = planner_factory(
        config_overrides={
            "enable_cmd": False,
            "enable_think": False,
            "enable_finish": False,
            "enable_condensation_request": False,
        }
    )
    tools: list[Any] = []
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.bash.create_cmd_run_tool",
        lambda *a, **k: {"cmd": True},
    )
    planner._add_core_tools(tools, False)
    assert tools == []


def test_add_browsing_tool_disabled(planner_factory):
    planner = planner_factory(config_overrides={"enable_browsing": False})
    tools: list[Any] = []
    planner._add_browsing_tool(tools)
    assert tools == []


def test_add_editor_tools_llm_editor_branch(monkeypatch, planner_factory):
    planner = planner_factory(
        config_overrides={
            "enable_editor": False,
            "enable_llm_editor": True,
            "enable_ultimate_editor": False,
        }
    )
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.llm_based_edit.LLMBasedFileEditTool",
        "llm-edit",
    )
    tools: list[Any] = []
    planner._add_editor_tools(tools, False)
    assert tools == ["llm-edit"]


def test_add_specialized_tools_plan_mode_disabled(monkeypatch, planner_factory):
    planner = planner_factory(config_overrides={"enable_plan_mode": False})
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.tools.task_tracker.create_task_tracker_tool",
        lambda short: {"tracker": short},
    )
    tools: list[Any] = []
    planner._add_specialized_tools(tools, True)
    # No tracker appended when plan mode disabled
    assert tools == []


def test_apply_prompt_optimization_without_system_message(planner_factory):
    planner = planner_factory(prompt_bundle={"optimizer": object()})
    messages = [{"role": "user", "content": "hi"}]
    assert planner.apply_prompt_optimization(messages, SimpleNamespace()) == messages


def test_record_prompt_execution_without_bundle(planner_factory):
    planner = planner_factory(prompt_bundle=None)
    planner.record_prompt_execution(SimpleNamespace(_prompt_variant_id="vid"), True, 0.1)


def test_apply_tool_optimization_without_optimizer(planner_factory):
    planner = planner_factory(tool_optimizer=None)
    tools = [{"function": {"name": "cmd"}}]
    assert planner._apply_tool_optimization(tools) == tools


def test_track_tool_usage_without_optimizer(planner_factory):
    planner = planner_factory(tool_optimizer=None)
    planner.track_tool_usage([SimpleNamespace(action="think")])


def test_track_tool_usage_skips_unknown_actions(planner_factory):
    class FakeToolOptimizer:
        def __init__(self):
            self.calls = []

        def track_tool_execution(self, **kwargs):
            self.calls.append(kwargs)

        def create_tool_variants(self, **kwargs):
            pass

    planner = planner_factory(tool_optimizer=FakeToolOptimizer())
    planner.track_tool_usage([SimpleNamespace(action="unknown")])
    assert planner._tool_optimizer.calls == []


def test_ensure_tool_variant_exists_handles_missing_prompt_id(planner_factory):
    planner = planner_factory()
    planner._prompt_optimizer = {"registry": SimpleNamespace(get_variants_for_prompt=lambda pid: [])}
    planner._tool_optimizer = SimpleNamespace(tool_prompt_ids={})
    planner._ensure_tool_variant_exists("tool", SimpleNamespace(action="run"))


def test_ensure_tool_variant_exists_skips_when_variants_exist(planner_factory, monkeypatch):
    planner = planner_factory()
    planner._prompt_optimizer = {
        "registry": SimpleNamespace(get_variants_for_prompt=lambda pid: ["existing"])
    }
    planner._tool_optimizer = SimpleNamespace(tool_prompt_ids={"tool": "pid"})
    module = ModuleType("forge.prompt_optimization.tool_descriptions")
    module.get_optimized_description = lambda tool_name: {"description": "", "parameters": {}}
    monkeypatch.setitem(sys.modules, module.__name__, module)
    planner._ensure_tool_variant_exists("tool", SimpleNamespace(action="run"))


def test_ensure_tool_variant_exists_without_description(planner_factory, monkeypatch):
    planner = planner_factory()
    planner._prompt_optimizer = {
        "registry": SimpleNamespace(get_variants_for_prompt=lambda pid: [])
    }
    planner._tool_optimizer = SimpleNamespace(tool_prompt_ids={"tool": "pid"})
    module = ModuleType("forge.prompt_optimization.tool_descriptions")
    module.get_optimized_description = lambda tool_name: None
    monkeypatch.setitem(sys.modules, module.__name__, module)
    planner._ensure_tool_variant_exists("tool", SimpleNamespace(action="run"))


def test_build_llm_params_without_ace_context(planner_factory, monkeypatch):
    planner = planner_factory(model="custom-model")
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.planner.check_tools",
        lambda tools, config: tools,
    )
    state = SimpleNamespace(to_llm_metadata=lambda **kwargs: {"extra": True})
    messages = [{"role": "system", "content": "sys"}]
    params = planner.build_llm_params(messages, state, tools=[], ace_context=None)
    assert "ACE" not in params["messages"][0]["content"]
    assert "tool_choice" not in params  # llm does not support tool choice

