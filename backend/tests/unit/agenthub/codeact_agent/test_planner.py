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
            enable_plan_mode=True,
        )
        if config_overrides:
            for key, value in config_overrides.items():
                setattr(config, key, value)
        return CodeActPlanner(
            config=config,
            llm=DummyLLM(model),
            safety_manager=DummySafety(),
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
    planner = planner_factory()
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
    assert ["db", {"tracker": False}] == tools


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
    )
    assert params["extra_body"]["metadata"]["model"] == planner._llm.config.model
    assert params["tool_choice"] == "auto"


def test_build_toolset_invokes_helpers(planner_factory, monkeypatch):
    planner = planner_factory()
    calls = []

    monkeypatch.setattr(planner, "_add_core_tools", lambda tools, short: calls.append("core"))
    monkeypatch.setattr(planner, "_add_browsing_tool", lambda tools: calls.append("browse"))
    monkeypatch.setattr(planner, "_add_specialized_tools", lambda tools, short: calls.append("special"))
    monkeypatch.setattr(planner, "_add_editor_tools", lambda tools, short: calls.append("editor"))
    
    tools = planner.build_toolset()
    assert calls == ["core", "browse", "special", "editor"]


def test_build_toolset_no_optimizer(planner_factory, monkeypatch):
    planner = planner_factory()
    monkeypatch.setattr(planner, "_add_core_tools", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_browsing_tool", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_specialized_tools", lambda *a, **k: None)
    monkeypatch.setattr(planner, "_add_editor_tools", lambda tools, short: tools.append("editor"))
    
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


def test_build_llm_params_metadata(planner_factory, monkeypatch):
    planner = planner_factory(model="custom-model")
    monkeypatch.setattr(
        "forge.agenthub.codeact_agent.planner.check_tools",
        lambda tools, config: tools,
    )
    state = SimpleNamespace(to_llm_metadata=lambda **kwargs: {"extra": True})
    messages = [{"role": "system", "content": "sys"}]
    params = planner.build_llm_params(messages, state, tools=[])
    assert "tool_choice" not in params  # llm does not support tool choice

