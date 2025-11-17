from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from forge.agenthub.readonly_agent import function_calling as fc
from forge.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from forge.events.action import (
    AgentFinishAction,
    AgentThinkAction,
    CmdRunAction,
    FileReadAction,
    MCPAction,
    MessageAction,
)


def make_tool_call(name: str, args: dict, call_id: str = "call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def make_response(message) -> SimpleNamespace:
    return SimpleNamespace(id="resp-1", choices=[SimpleNamespace(message=message)])


def test_grep_to_cmdrun_includes_flags():
    cmd = fc.grep_to_cmdrun("foo", path="/repo", include="*.py")
    assert "rg -li" in cmd and "--glob" in cmd and "/repo" in cmd


def test_glob_to_cmdrun_defaults_path():
    cmd = fc.glob_to_cmdrun("**/*.js")
    assert "rg --files" in cmd and "-g '**/*.js'" in cmd


def test_extract_thought_from_content_variants():
    assert fc._extract_thought_from_content("hello") == "hello"
    assert (
        fc._extract_thought_from_content([{"type": "text", "text": "world"}])
        == "world"
    )
    assert fc._extract_thought_from_content([{"type": "image", "text": "no"}]) == ""
    assert fc._extract_thought_from_content({"unexpected": "value"}) == ""


def test_parse_tool_call_arguments_invalid_json():
    tool_call = SimpleNamespace(function=SimpleNamespace(arguments="{bad json"))
    with pytest.raises(FunctionCallValidationError):
        fc._parse_tool_call_arguments(tool_call)


def test_create_view_action_requires_path():
    with pytest.raises(FunctionCallValidationError):
        fc._create_view_action({})
    action = fc._create_view_action({"path": "file.txt", "view_range": "1-10"})
    assert isinstance(action, FileReadAction)
    assert action.path == "file.txt"


def test_create_grep_action_missing_pattern():
    with pytest.raises(FunctionCallValidationError):
        fc._create_grep_action({})
    action = fc._create_grep_action({"pattern": "foo", "path": "/repo"})
    assert isinstance(action, CmdRunAction)
    assert "rg -li" in action.command


def test_create_glob_action_missing_pattern():
    with pytest.raises(FunctionCallValidationError):
        fc._create_glob_action({})
    action = fc._create_glob_action({"pattern": "*.py"})
    assert "rg --files" in action.command


def test_create_action_from_tool_call_handles_known_tools():
    results = []
    tool_names = [
        fc.FinishTool["function"]["name"],
        fc.ViewTool["function"]["name"],
        fc.ThinkTool["function"]["name"],
        fc.GrepTool["function"]["name"],
        fc.GlobTool["function"]["name"],
    ]
    args = [
        {"message": "done"},
        {"path": "file.py"},
        {"thought": "thinking"},
        {"pattern": "foo"},
        {"pattern": "*.py"},
    ]
    for name, arg in zip(tool_names, args, strict=False):
        tool_call = make_tool_call(name, arg)
        results.append(fc._create_action_from_tool_call(tool_call, None))

    assert isinstance(results[0], AgentFinishAction)
    assert isinstance(results[1], FileReadAction)
    assert isinstance(results[2], AgentThinkAction)
    assert isinstance(results[3], CmdRunAction)
    assert isinstance(results[4], CmdRunAction)


def test_create_action_from_tool_call_mcp(monkeypatch):
    tool_call = make_tool_call("custom_mcp", {"arg": 1})
    action = fc._create_action_from_tool_call(tool_call, ["custom_mcp"])
    assert isinstance(action, MCPAction)


def test_create_action_from_tool_call_unknown():
    tool_call = make_tool_call("unknown", {})
    with pytest.raises(FunctionCallNotExistsError):
        fc._create_action_from_tool_call(tool_call, None)


def test_process_tool_calls_combines_thought(monkeypatch):
    recorded = {}

    def fake_combine(action, thought):
        recorded["thought"] = thought
        action.injected = thought
        return action

    monkeypatch.setattr(fc, "combine_thought", fake_combine)
    tool_call = make_tool_call(fc.ViewTool["function"]["name"], {"path": "file"})
    assistant_msg = SimpleNamespace(
        content=[{"type": "text", "text": "thinking"}],
        tool_calls=[tool_call],
    )
    response = make_response(assistant_msg)

    actions = fc._process_tool_calls(assistant_msg, response, None)
    assert actions[0].injected == "thinking"
    assert actions[0].tool_call_metadata.function_name == fc.ViewTool["function"]["name"]


def test_process_tool_calls_multiple_actions(monkeypatch):
    monkeypatch.setattr(fc, "combine_thought", lambda action, thought: action)
    calls = [
        make_tool_call(fc.ViewTool["function"]["name"], {"path": "first"}),
        make_tool_call(fc.ViewTool["function"]["name"], {"path": "second"}),
    ]
    assistant_msg = SimpleNamespace(content="thinking", tool_calls=calls)
    response = make_response(assistant_msg)
    actions = fc._process_tool_calls(assistant_msg, response, None)
    assert len(actions) == 2



def test_response_to_actions_with_message_only():
    assistant_msg = SimpleNamespace(content="hello", tool_calls=None)
    response = make_response(assistant_msg)
    actions = fc.response_to_actions(response)
    assert isinstance(actions[0], MessageAction)


def test_response_to_actions_missing_message_payload():
    response = SimpleNamespace(id="resp", choices=[SimpleNamespace(message=None)])
    with pytest.raises(FunctionCallValidationError):
        fc.response_to_actions(response)


def test_response_to_actions_sets_response_id(monkeypatch):
    tool_call = make_tool_call(fc.ViewTool["function"]["name"], {"path": "file"})
    assistant_msg = SimpleNamespace(content="", tool_calls=[tool_call])
    response = make_response(assistant_msg)
    actions = fc.response_to_actions(response)
    assert all(action.response_id == "resp-1" for action in actions)


def test_validate_response_choices_asserts():
    response = SimpleNamespace(choices=[SimpleNamespace(), SimpleNamespace()])
    with pytest.raises(AssertionError):
        fc._validate_response_choices(response)


def test_get_tools_returns_expected_tools():
    names = [tool["function"]["name"] for tool in fc.get_tools()]
    assert set(names) >= {
        fc.ThinkTool["function"]["name"],
        fc.FinishTool["function"]["name"],
        fc.GrepTool["function"]["name"],
        fc.GlobTool["function"]["name"],
        fc.ViewTool["function"]["name"],
    }

