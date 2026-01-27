"""Tests for the CodeAct function calling utilities."""

from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace
from typing import Any, cast

import pytest

from forge.agenthub.codeact_agent import function_calling as fc
from forge.core.exceptions import (
    FunctionCallNotExistsError,
    FunctionCallValidationError,
)
from forge.events.action import (
    ActionSecurityRisk,
    AgentFinishAction,
    AgentThinkAction,
    BrowseInteractiveAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    MessageAction,
    TaskTrackingAction,
)
from forge.events.action.mcp import MCPAction
from forge.events.event import FileEditSource, FileReadSource


def _make_editor_result(
    success: bool = True,
    message: str = "ok",
    parent_name: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        success=success,
        message=message,
        node_type="function",
        line_start=1,
        line_end=2,
        parent_name=parent_name,
    )


def test_combine_thought_appends_text() -> None:
    action = CmdRunAction(command="ls", thought="existing")
    combined = fc.combine_thought(action, "new thought")
    assert isinstance(combined, CmdRunAction)
    assert "existing" in combined.thought
    assert combined.thought.startswith("new thought")


def test_set_security_risk_assigns_enum() -> None:
    action = CmdRunAction(command="echo hi")
    fc.set_security_risk(action, {"security_risk": "LOW"})
    assert action.security_risk == ActionSecurityRisk.LOW


def test_set_security_risk_invalid_value_logs_warning() -> None:
    action = CmdRunAction(command="noop")
    fc.set_security_risk(action, {"security_risk": "INVALID"})


def test_handle_cmd_run_tool_parses_timeout() -> None:
    action = fc._handle_cmd_run_tool({"command": "ls", "timeout": "1.5"})
    assert isinstance(action, CmdRunAction)
    assert action.command == "ls"
    assert action.timeout == 1.5


def test_handle_cmd_run_tool_missing_command_raises() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_cmd_run_tool({})


def test_handle_cmd_run_tool_invalid_timeout_raises() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_cmd_run_tool({"command": "ls", "timeout": "not-a-number"})


def test_handle_finish_tool() -> None:
    action = fc._handle_finish_tool({"message": "done"})
    assert isinstance(action, AgentFinishAction)
    assert action.final_thought == "done"


def test_handle_llm_based_file_edit_tool_defaults() -> None:
    action = fc._handle_llm_based_file_edit_tool(
        {"path": "file.py", "content": "print()"}
    )
    assert isinstance(action, FileEditAction)
    assert action.start == 1
    assert action.end == -1
    assert action.impl_source == FileEditSource.LLM_BASED_EDIT

    with pytest.raises(FunctionCallValidationError):
        fc._handle_llm_based_file_edit_tool({"content": "print()"})


def test_filter_valid_editor_kwargs_validates_keys() -> None:
    valid_kwargs = fc._filter_valid_editor_kwargs(
        {"security_risk": "LOW", "command": "edit"}
    )
    assert "command" in valid_kwargs

    with pytest.raises(FunctionCallValidationError):
        fc._filter_valid_editor_kwargs({"invalid": True})


def test_handle_str_replace_editor_tool_view_command() -> None:
    action = fc._handle_str_replace_editor_tool(
        {"command": "view", "path": "file.py", "view_range": [1, 10]}
    )
    assert isinstance(action, FileReadAction)
    assert action.impl_source == FileReadSource.FILE_EDITOR
    assert action.view_range == [1, 10]


def test_handle_str_replace_editor_tool_edit_command() -> None:
    args = {
        "command": "str_replace",
        "path": "file.py",
        "old_str": "foo",
        "new_str": "bar",
    }
    action = fc._handle_str_replace_editor_tool(args)
    assert isinstance(action, FileEditAction)
    assert action.command == "str_replace"


def test_handle_think_tool() -> None:
    action = fc._handle_think_tool({"thought": "ponder"})
    assert isinstance(action, AgentThinkAction)
    assert action.thought == "ponder"


def test_handle_condensation_request_tool_returns_action() -> None:
    action = fc._handle_condensation_request_tool({})
    assert isinstance(action, fc.CondensationRequestAction)


def test_handle_task_tracker_tool_validates_inputs() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({})
    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({"command": "plan"})
    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({"command": "plan", "task_list": "oops"})
    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({"command": "plan", "task_list": [42]})


def test_handle_task_tracker_tool_normalizes_tasks() -> None:
    action = fc._handle_task_tracker_tool(
        {
            "command": "plan",
            "task_list": [{"title": "Task", "status": "doing", "notes": "note"}],
        }
    )
    assert isinstance(action, TaskTrackingAction)
    assert action.task_list[0]["id"] == "task-1"


def test_handle_task_tracker_tool_rejects_bad_entry() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({"command": "plan", "task_list": ["oops"]})


def test_handle_mcp_tool_non_mapping() -> None:
    action = fc._handle_mcp_tool("tool", "invalid")
    assert isinstance(action, MCPAction)
    assert action.arguments == {}


def test_handle_browser_tool_requires_code() -> None:
    action = fc._handle_browser_tool({"code": "goto('url')"})
    assert isinstance(action, BrowseInteractiveAction)

    with pytest.raises(FunctionCallValidationError):
        fc._handle_browser_tool({})


def test_handle_task_tracker_tool_normalizes_tasks() -> None:
    action = fc._handle_task_tracker_tool(
        {"command": "plan", "task_list": [{"title": "Task"}]}
    )
    assert isinstance(action, TaskTrackingAction)
    assert action.task_list[0]["status"] == "todo"

    with pytest.raises(FunctionCallValidationError):
        fc._handle_task_tracker_tool({"command": "plan"})


def test_handle_mcp_tool_wraps_arguments() -> None:
    action = fc._handle_mcp_tool("custom_tool", {"foo": "bar"})
    assert isinstance(action, MCPAction)
    assert action.name == "custom_tool"


def test_handle_database_connect_tool_validates_arguments() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_database_connect_tool({})

    action = fc._handle_database_connect_tool(
        {"connection_name": "main", "db_type": "postgres", "env_prefix": "PG"}
    )
    assert "connect_postgres" in action.code


def test_handle_database_schema_tool() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_database_schema_tool({})

    action = fc._handle_database_schema_tool({"connection_name": "main"})
    assert "get_schema" in action.code


def test_handle_database_query_tool() -> None:
    with pytest.raises(FunctionCallValidationError):
        fc._handle_database_query_tool({"connection_name": "main"})

    action = fc._handle_database_query_tool(
        {"connection_name": "main", "query": "SELECT 1"}
    )
    assert "execute_query" in action.code
    assert "SELECT 1" in action.code


def test_handle_ultimate_editor_tool_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResult:
        def __init__(
            self,
            success=True,
            message="ok",
            node_type="function",
            line_start=1,
            line_end=2,
            parent_name=None,
        ):
            self.success = success
            self.message = message
            self.node_type = node_type
            self.line_start = line_start
            self.line_end = line_end
            self.parent_name = parent_name

    class DummyEditor:
        def edit_function(self, file_path, function_name, new_body):
            return DummyResult()

        def rename_symbol(self, file_path, old_name, new_name):
            return DummyResult()

        def find_symbol(self, file_path, symbol_name, symbol_type=None):
            return DummyResult(parent_name="Parent")

        def replace_code_range(self, file_path, start, end, new_code):
            return DummyResult()

        def normalize_file_indent(self, file_path, style, size):
            return DummyResult()

    monkeypatch.setitem(
        __import__("sys").modules,
        "forge.agenthub.codeact_agent.tools.ultimate_editor",
        SimpleNamespace(UltimateEditor=DummyEditor),
    )
    monkeypatch.setattr(
        fc,
        "FileReadSource",
        SimpleNamespace(AGENT="agent", FILE_EDITOR="file_editor", DEFAULT="default"),
        raising=False,
    )

    action = fc._handle_ultimate_editor_tool(
        {
            "command": "edit_function",
            "file_path": "file.py",
            "function_name": "foo",
            "new_body": "pass",
        }
    )
    assert isinstance(action, FileReadAction)

    action = fc._handle_ultimate_editor_tool(
        {"command": "find_symbol", "file_path": "file.py", "symbol_name": "foo"}
    )
    assert isinstance(action, MessageAction)
    assert "Parent" in action.content

    with pytest.raises(FunctionCallValidationError):
        fc._handle_ultimate_editor_tool({"command": "edit_function"})


def test_handle_edit_function_command_validation_and_failure() -> None:
    editor = SimpleNamespace(edit_function=lambda *a, **k: _make_editor_result())
    with pytest.raises(FunctionCallValidationError):
        fc._handle_edit_function_command(editor, "file.py", {"function_name": "foo"})

    failing_editor = SimpleNamespace(
        edit_function=lambda *a, **k: _make_editor_result(success=False, message="fail")
    )
    action = fc._handle_edit_function_command(
        failing_editor,
        "file.py",
        {"function_name": "foo", "new_body": "body"},
    )
    assert isinstance(action, MessageAction)
    assert "fail" in action.content


def test_handle_rename_symbol_command_validation_and_failure() -> None:
    editor = SimpleNamespace(
        rename_symbol=lambda *a, **k: _make_editor_result(success=False, message="oops")
    )
    with pytest.raises(FunctionCallValidationError):
        fc._handle_rename_symbol_command(editor, "file.py", {"old_name": "a"})
    action = fc._handle_rename_symbol_command(
        editor,
        "file.py",
        {"old_name": "a", "new_name": "b"},
    )
    assert isinstance(action, MessageAction)
    assert "oops" in action.content


def test_handle_find_symbol_command_not_found() -> None:
    editor = SimpleNamespace(find_symbol=lambda *a, **k: None)
    action = fc._handle_find_symbol_command(
        editor, "file.py", {"symbol_name": "target"}
    )
    assert isinstance(action, MessageAction)
    assert "not found" in action.content


def test_handle_replace_range_command_validation_and_failure() -> None:
    editor = SimpleNamespace(
        replace_code_range=lambda *a, **k: _make_editor_result(
            success=False, message="replace fail"
        )
    )
    with pytest.raises(FunctionCallValidationError):
        fc._handle_replace_range_command(
            editor, "file.py", {"start_line": 1, "end_line": 2}
        )
    action = fc._handle_replace_range_command(
        editor,
        "file.py",
        {"start_line": 1, "end_line": 2, "new_code": "pass"},
    )
    assert isinstance(action, MessageAction)
    assert "replace fail" in action.content


def test_handle_normalize_indent_command_failure() -> None:
    editor = SimpleNamespace(
        normalize_file_indent=lambda *a, **k: _make_editor_result(
            success=False, message="indent fail"
        )
    )
    action = fc._handle_normalize_indent_command(
        editor, "file.py", {"style": "spaces", "size": 2}
    )
    assert isinstance(action, MessageAction)
    assert "indent fail" in action.content


def test_handle_ultimate_editor_tool_import_and_command_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failing_module = SimpleNamespace(
        UltimateEditor=lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    monkeypatch.setitem(
        sys.modules,
        "forge.agenthub.codeact_agent.tools.ultimate_editor",
        failing_module,
    )
    with pytest.raises(FunctionCallValidationError):
        fc._handle_ultimate_editor_tool({"command": "edit_function", "file_path": "f"})

    monkeypatch.setitem(
        sys.modules,
        "forge.agenthub.codeact_agent.tools.ultimate_editor",
        SimpleNamespace(UltimateEditor=lambda: SimpleNamespace()),
    )
    result = fc._handle_ultimate_editor_tool(
        {"command": "unknown", "file_path": "f", "function_name": "foo"}
    )
    assert isinstance(result, MessageAction)


def test_handle_ultimate_editor_tool_handler_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    editor = SimpleNamespace()

    monkeypatch.setitem(
        sys.modules,
        "forge.agenthub.codeact_agent.tools.ultimate_editor",
        SimpleNamespace(UltimateEditor=lambda: editor),
    )
    monkeypatch.setattr(
        fc,
        "_handle_edit_function_command",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("handler boom")),
    )
    result = fc._handle_ultimate_editor_tool(
        {
            "command": "edit_function",
            "file_path": "file.py",
            "function_name": "foo",
            "new_body": "pass",
        }
    )
    assert isinstance(result, MessageAction)
    assert "handler boom" in result.content


def test_create_tool_dispatch_map_contains_known_tools() -> None:
    dispatch = fc._create_tool_dispatch_map()
    assert fc.create_cmd_run_tool()["function"]["name"] in dispatch
    browser_tool = cast(dict[str, Any], fc.BrowserTool)
    assert browser_tool["function"]["name"] in dispatch


def test_extract_thought_from_content_handles_list() -> None:
    content = [
        {"type": "text", "text": "Thought 1"},
        {"type": "text", "text": "Thought 2"},
    ]
    thought = fc._extract_thought_from_content(content)
    assert "Thought 1" in thought and "Thought 2" in thought


def test_process_single_tool_call_unknown_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="unknown", arguments="{}")
    )
    with pytest.raises(FunctionCallNotExistsError):
        fc._process_single_tool_call(tool_call, {}, None)


def test_process_single_tool_call_mcp_tool() -> None:
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="mcp-tool", arguments="{}")
    )
    action = fc._process_single_tool_call(tool_call, {}, ["mcp-tool"])
    assert isinstance(action, MCPAction)


def test_process_single_tool_call_json_error() -> None:
    tool_call = SimpleNamespace(
        function=SimpleNamespace(name="tool", arguments="{invalid"), id="1"
    )
    with pytest.raises(FunctionCallValidationError):
        fc._process_single_tool_call(tool_call, {}, None)


def test_response_to_actions_with_message() -> None:
    message = SimpleNamespace(content="Hello world", tool_calls=[])
    response = SimpleNamespace(id="resp1", choices=[SimpleNamespace(message=message)])
    actions = fc.response_to_actions(response)
    assert isinstance(actions[0], MessageAction)
    assert actions[0].wait_for_response is True
    assert actions[0].response_id == "resp1"


def test_response_to_actions_with_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatch = {
        "custom_tool": lambda arguments: MessageAction(content=arguments["msg"])
    }
    monkeypatch.setattr(fc, "_create_tool_dispatch_map", lambda: dispatch)

    class DummyToolMetadata:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    from forge.events import event as event_module

    monkeypatch.setattr(fc, "ToolCallMetadata", DummyToolMetadata, raising=False)
    monkeypatch.setattr(
        event_module, "ToolCallMetadata", DummyToolMetadata, raising=False
    )

    tool_call = SimpleNamespace(
        id="tool-1",
        function=SimpleNamespace(
            name="custom_tool", arguments=json.dumps({"msg": "hello"})
        ),
    )
    message = SimpleNamespace(content="Thought", tool_calls=[tool_call])
    response = SimpleNamespace(id="resp1", choices=[SimpleNamespace(message=message)])

    actions = fc.response_to_actions(response)
    assert isinstance(actions[0], MessageAction)
    metadata = actions[0].tool_call_metadata
    assert metadata is not None
    assert metadata.function_name == "custom_tool"


def test_create_message_action_from_content_handles_none() -> None:
    actions = fc._create_message_action_from_content(None)
    first_action = actions[0]
    assert isinstance(first_action, MessageAction)
    assert first_action.content == ""


def test_set_response_id_for_actions_assigns_all() -> None:
    actions = [MessageAction("hi"), CmdRunAction(command="ls")]
    response = SimpleNamespace(id="resp123")
    fc._set_response_id_for_actions(actions, response)
    assert all(action.response_id == "resp123" for action in actions)
