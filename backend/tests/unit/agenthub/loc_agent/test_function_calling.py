from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from forge.agenthub.loc_agent import function_calling
from forge.core.exceptions import FunctionCallNotExistsError
from forge.events.action import AgentFinishAction, CmdRunAction, MessageAction


def make_tool_call(name: str, arguments: dict, call_id: str = "call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


def make_response(message) -> SimpleNamespace:
    return SimpleNamespace(id="resp-1", choices=[SimpleNamespace(message=message)])


def test_response_to_actions_processes_tool_calls(monkeypatch):
    thought_log = {}

    def fake_combine(action, thought):
        thought_log["thought"] = thought
        action.thought = thought
        return action

    monkeypatch.setattr(function_calling, "combine_thought", fake_combine)
    tool_call = make_tool_call("search_code_snippets", {"query": "foo"})
    assistant_msg = SimpleNamespace(
        content=[{"type": "text", "text": "thinking..."}],
        tool_calls=[tool_call],
    )
    response = make_response(assistant_msg)

    actions = function_calling.response_to_actions(response)
    assert isinstance(actions[0], CmdRunAction)
    assert "search_code_snippets" in actions[0].command
    assert actions[0].response_id == "resp-1"
    assert thought_log["thought"].startswith("thinking")


def test_response_to_actions_returns_message_action():
    assistant_msg = SimpleNamespace(content="Hello!", tool_calls=[])
    response = make_response(assistant_msg)

    actions = function_calling.response_to_actions(response)
    assert isinstance(actions[0], MessageAction)
    assert actions[0].wait_for_response is True


def test_parse_tool_arguments_invalid_json():
    tool_call = SimpleNamespace(
        function=SimpleNamespace(arguments="{bad json}")
    )
    with pytest.raises(RuntimeError):
        function_calling._parse_tool_arguments(tool_call)


def test_create_action_from_tool_call_finish(monkeypatch):
    finish_name = function_calling.FinishTool["function"]["name"]
    tool_call = make_tool_call(finish_name, {"message": "done"})
    action = function_calling._create_action_from_tool_call(tool_call, {"message": "done"})
    assert isinstance(action, AgentFinishAction)
    assert action.final_thought == "done"


def test_create_action_from_tool_call_unknown():
    tool_call = make_tool_call("unknown_tool", {})
    with pytest.raises(FunctionCallNotExistsError):
        function_calling._create_action_from_tool_call(tool_call, {})


def test_validate_response_choices_raises():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=None), SimpleNamespace(message=None)]
    )
    with pytest.raises(AssertionError):
        function_calling._validate_response_choices(response)


def test_extract_thought_handles_string_and_chunks():
    assert function_calling._extract_thought_from_message(
        SimpleNamespace(content="hi")
    ) == "hi"
    msg = SimpleNamespace(content=[{"type": "text", "text": "hello"}])
    assert function_calling._extract_thought_from_message(msg) == "hello"


def test_extract_thought_ignores_non_text_chunks():
    msg = SimpleNamespace(content=[{"type": "image", "text": "ignored"}])
    assert function_calling._extract_thought_from_message(msg) == ""


def test_extract_thought_mixed_content():
    msg = SimpleNamespace(
        content=[
            {"type": "image", "text": "ignored"},
            {"type": "text", "text": "kept"},
        ]
    )
    assert function_calling._extract_thought_from_message(msg) == "kept"


def test_get_tools_returns_expected_entries():
    tool_names = [tool["function"]["name"] for tool in function_calling.get_tools()]
    assert "explore_tree_structure" in tool_names


def test_response_to_actions_multiple_tool_calls(monkeypatch):
    captured = []

    def fake_combine(action, thought):
        captured.append(action)
        return action

    monkeypatch.setattr(function_calling, "combine_thought", fake_combine)
    calls = [
        make_tool_call("search_code_snippets", {"query": "one"}, call_id="1"),
        make_tool_call("search_code_snippets", {"query": "two"}, call_id="2"),
    ]
    assistant_msg = SimpleNamespace(
        content=[{"type": "text", "text": "thinking"}], tool_calls=calls
    )
    response = make_response(assistant_msg)
    actions = function_calling.response_to_actions(response)
    assert len(actions) == 2
    assert captured == [actions[0]]


def test_response_to_actions_missing_message_raises():
    response = SimpleNamespace(id="resp", choices=[SimpleNamespace(message=None)])
    with pytest.raises(RuntimeError):
        function_calling.response_to_actions(response)

