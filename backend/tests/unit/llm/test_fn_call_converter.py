"""Extensive tests for `forge.llm.fn_call_converter` to ensure high coverage."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from typing import Any

import pytest

from forge.llm import fn_call_converter as converter


def _base_tool(name: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Tool {name}",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "cmd"},
                    "count": {"type": "integer", "description": "times"},
                    "options": {"type": "array", "description": "opts"},
                    "mode": {"type": "string", "enum": ["fast", "slow"]},
                },
                "required": ["command"],
            },
        },
    }


@pytest.fixture
def sample_tools():
    return [
        _base_tool(converter.EXECUTE_BASH_TOOL_NAME),
        _base_tool(converter.STR_REPLACE_EDITOR_TOOL_NAME),
        _base_tool(converter.BROWSER_TOOL_NAME),
        _base_tool(converter.FINISH_TOOL_NAME),
        _base_tool(converter.LLM_BASED_EDIT_TOOL_NAME),
    ]


def test_refine_prompt_handles_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert "powershell" in converter.refine_prompt("run bash command")
    monkeypatch.setattr(sys, "platform", "linux")
    assert converter.refine_prompt("keep bash") == "keep bash"


def test_get_example_for_tools_generates_content(sample_tools) -> None:
    example = converter.get_example_for_tools(sample_tools)
    assert "START OF EXAMPLE" in example
    assert "END OF EXAMPLE" in example


def test_example_builder_prefers_edit_file_when_no_str_replace() -> None:
    tools = [
        _base_tool(converter.EXECUTE_BASH_TOOL_NAME),
        _base_tool(converter.LLM_BASED_EDIT_TOOL_NAME),
    ]
    example = converter.get_example_for_tools(tools)
    assert "edit_file" in example
    assert "str_replace_editor" not in example


def test_convert_tool_call_to_string_success(sample_tools) -> None:
    tool_call = {
        "id": "call-1",
        "type": "function",
        "function": {
            "name": converter.EXECUTE_BASH_TOOL_NAME,
            "arguments": json.dumps({"command": "ls", "count": "3"}),
        },
    }
    result = converter.convert_tool_call_to_string(tool_call)
    assert "<function=execute_bash>" in result
    assert "<parameter=count>3</parameter>" in result


@pytest.mark.parametrize(
    ("tool_call", "expected"),
    [
        ({}, converter.FunctionCallConversionError),
        ({"id": "x"}, converter.FunctionCallConversionError),
        ({"id": "x", "type": "bad"}, converter.FunctionCallConversionError),
        ({"id": "x", "type": "function", "function": {"arguments": "{"}}, KeyError),
    ],
)
def test_convert_tool_call_to_string_errors(tool_call, expected) -> None:
    with pytest.raises(expected):
        converter.convert_tool_call_to_string(tool_call)


def test_parse_tool_call_arguments_invalid_json() -> None:
    tool_call = {
        "id": "x",
        "type": "function",
        "function": {"name": "fn", "arguments": "{"},
    }
    with pytest.raises(converter.FunctionCallConversionError):
        converter._parse_tool_call_arguments(tool_call)


def test_convert_tools_to_description(sample_tools) -> None:
    description = converter.convert_tools_to_description(sample_tools)
    assert "BEGIN FUNCTION #1" in description
    assert "Allowed values" in description


def test_format_parameter_multiline_and_list() -> None:
    multiline = converter._format_parameter("notes", "line1\nline2")
    assert multiline.startswith("<parameter=notes>\n")
    array_param = converter._format_parameter("items", ["a", "b"])
    assert json.loads(array_param.split(">")[1].split("<")[0]) == ["a", "b"]


def test_convert_tools_to_description_no_parameters() -> None:
    description = converter.convert_tools_to_description(
        [{"type": "function", "function": {"name": "noop", "description": "No params"}}]
    )
    assert "No parameters are required" in description


def test_process_system_and_user_messages(sample_tools) -> None:
    system = converter._process_system_message("You are helpful.", " SUFFIX")
    assert system["content"].endswith("SUFFIX")

    user_message, first_flag = converter._process_user_message(
        "First",
        sample_tools,
        add_in_context_learning_example=True,
        first_user_message_encountered=False,
    )
    assert first_flag is True
    assert (
        converter.IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(sample_tools).strip()
        in user_message["content"]
    )

    list_content = converter._process_system_message(
        [{"type": "text", "text": "msg"}], " SUFFIX"
    )["content"]
    assert list_content[-1]["text"].endswith("SUFFIX")


def test_add_example_to_list_content(sample_tools) -> None:
    content = [{"type": "text", "text": "hello"}]
    updated = converter._add_example_to_list_content(content, "EXAMPLE")
    assert updated[0]["text"].startswith("EXAMPLE")


def test_add_example_to_list_content_inserts_when_missing() -> None:
    content = [{"type": "image"}]
    updated = converter._add_example_to_list_content(content, "EXAMPLE")
    assert updated[0]["type"] == "text"


def test_add_in_context_learning_example_variants(sample_tools) -> None:
    assert converter._add_in_context_learning_example("body", []) == "body"
    list_content = [{"type": "text", "text": "item"}]
    updated = converter._add_in_context_learning_example(list_content, sample_tools)
    assert updated[0]["text"].startswith("Here's")
    with pytest.raises(converter.FunctionCallConversionError):
        converter._add_in_context_learning_example(123, sample_tools)


def test_process_system_message_invalid_type() -> None:
    with pytest.raises(converter.FunctionCallConversionError):
        converter._process_system_message({"bad": "value"}, "suffix")


def test_convert_fncall_messages_to_non_fncall_messages(
    sample_tools, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(converter, "convert_tools_to_description", lambda tools: "Desc")
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Hi"},
        {
            "role": "assistant",
            "content": "<function=finish>\n<parameter=message>Done</parameter>\n</function>",
        },
        {
            "role": "tool",
            "name": "execute_bash",
            "content": "result",
            "cache_control": {"type": "ephemeral"},
        },
    ]
    converted = converter.convert_fncall_messages_to_non_fncall_messages(
        messages, sample_tools
    )
    assert "You have access to the following functions" in converted[0]["content"]
    assert converted[1]["content"].startswith("Here's a running example")
    assert (
        converted[2]["content"]
        == "<function=finish>\n<parameter=message>Done</parameter>\n</function>"
    )
    assert converted[3]["content"][0]["text"].startswith("EXECUTION RESULT")


def test_convert_non_fncall_messages_to_fncall_messages_roundtrip(
    sample_tools, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(converter, "convert_tools_to_description", lambda tools: "Desc")
    messages = [
        {
            "role": "system",
            "content": "System prompt"
            + converter.SYSTEM_PROMPT_SUFFIX_TEMPLATE.format(description="Desc"),
        },
        {"role": "user", "content": "payload"},
        {
            "role": "assistant",
            "content": "<function=execute_bash>\n<parameter=command>ls</parameter>\n</function>",
        },
        {"role": "user", "content": "EXECUTION RESULT of [execute_bash]:\nresult"},
    ]
    converted = converter.convert_non_fncall_messages_to_fncall_messages(
        deepcopy(messages), sample_tools
    )
    assert converted[2]["tool_calls"][0]["function"]["arguments"]
    assert converted[3]["role"] == "tool"


def test_convert_non_fncall_messages_to_fncall_messages_errors(
    sample_tools, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(converter, "convert_tools_to_description", lambda tools: "Desc")
    bad_messages = [{"role": "assistant", "content": "<function=unknown></function>"}]
    converted = converter.convert_non_fncall_messages_to_fncall_messages(
        bad_messages, sample_tools
    )
    assert converted[0]["content"] == "<function=unknown></function>"


def test_convert_from_multiple_tool_calls_handles_splitting() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "Thinking",
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
                {
                    "id": "toolu_2",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "toolu_1", "content": "done"},
        {"role": "tool", "tool_call_id": "toolu_2", "content": "done2"},
    ]
    converted = converter.convert_from_multiple_tool_calls_to_single_tool_call_messages(
        messages
    )
    assistant_messages = [msg for msg in converted if msg["role"] == "assistant"]
    assert len(assistant_messages) == 2


def test_convert_from_multiple_tool_calls_detects_pending() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
                {
                    "id": "toolu_2",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
            ],
        }
    ]
    with pytest.raises(converter.FunctionCallConversionError):
        converter.convert_from_multiple_tool_calls_to_single_tool_call_messages(
            messages
        )


def test_convert_from_multiple_tool_calls_ignore_flag() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
                {
                    "id": "toolu_2",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
            ],
        }
    ]
    result = converter.convert_from_multiple_tool_calls_to_single_tool_call_messages(
        messages, ignore_final_tool_result=True
    )
    assert not result  # no conversion without tool results


def test_process_other_message_branch() -> None:
    messages = [
        {"role": "assistant", "content": "", "tool_calls": []},
        {"role": "system", "content": "info"},
    ]
    converted = converter.convert_from_multiple_tool_calls_to_single_tool_call_messages(
        messages
    )
    assert any(msg["role"] == "system" for msg in converted)


def test_process_tool_message_assertion() -> None:
    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "toolu_1",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
                {
                    "id": "toolu_2",
                    "type": "function",
                    "function": {"name": "fn", "arguments": "{}"},
                },
            ],
        },
        {"role": "tool", "tool_call_id": "missing", "content": "data"},
    ]
    with pytest.raises(TypeError):
        converter.convert_from_multiple_tool_calls_to_single_tool_call_messages(
            messages
        )


def test_extract_and_validate_params_enforces_constraints(sample_tools) -> None:
    matching_tool = sample_tools[0]["function"]
    fn_body = "<parameter=command>echo</parameter>\n<parameter=count>5</parameter>\n<parameter=options>[1,2]</parameter>\n<parameter=mode>fast</parameter>\n"
    matches = converter.re.finditer(
        converter.FN_PARAM_REGEX_PATTERN, fn_body, converter.re.DOTALL
    )
    params = converter._extract_and_validate_params(
        matching_tool, matches, matching_tool["name"]
    )
    assert params["count"] == 5
    assert params["options"] == [1, 2]

    bad_fn_body = (
        "<parameter=command>echo</parameter>\n<parameter=mode>invalid</parameter>"
    )
    matches = converter.re.finditer(
        converter.FN_PARAM_REGEX_PATTERN, bad_fn_body, converter.re.DOTALL
    )
    with pytest.raises(converter.FunctionCallValidationError):
        converter._extract_and_validate_params(
            matching_tool, matches, matching_tool["name"]
        )


def test_extract_and_validate_params_missing_required(sample_tools) -> None:
    matching_tool = sample_tools[0]["function"]
    matches = converter.re.finditer(
        converter.FN_PARAM_REGEX_PATTERN, "", converter.re.DOTALL
    )
    with pytest.raises(converter.FunctionCallValidationError):
        converter._extract_and_validate_params(
            matching_tool, matches, matching_tool["name"]
        )


def test_fix_stopword_and_normalize_tags() -> None:
    content = "<function=test>\n<parameter=x>value</parameter>\n</"
    fixed = converter._fix_stopword(content)
    assert fixed.endswith("</function>")

    malformed = "<parameter=name=value</parameter>"
    assert (
        converter._normalize_parameter_tags(malformed)
        == "<parameter=name>value</parameter>"
    )


def test_remove_in_context_learning_examples(sample_tools) -> None:
    example = converter.IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(sample_tools)
    suffix = converter.IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX
    text = example + "real" + suffix
    assert converter._remove_examples_from_string(text, sample_tools) == "real"

    content = [{"type": "text", "text": example + "real" + suffix}]
    cleaned = converter._remove_examples_from_list(content, sample_tools)
    assert cleaned[0]["text"] == "real"
    with pytest.raises(converter.FunctionCallConversionError):
        converter._remove_in_context_learning_examples(123, sample_tools)


def test_find_tool_result_and_apply_conversion() -> None:
    text = "EXECUTION RESULT of [execute_bash]:\nline"
    match = converter._find_tool_result_match(text)
    assert match
    updated = converter._apply_tool_result_conversion(text)
    assert "<tool_result>" in updated

    content_list = [{"type": "text", "text": text}]
    converter._apply_tool_result_conversion(content_list)
    assert "<tool_result>" in content_list[0]["text"]


def test_trim_content_before_function() -> None:
    content = [{"type": "text", "text": "Thought<function=call>"}]
    trimmed = converter._trim_content_before_function(content)
    assert trimmed[0]["text"] == "Thought"

    assert (
        converter._trim_content_before_function("Thought<function=call>") == "Thought"
    )


def test_process_assistant_message_for_conversion(
    sample_tools, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(converter, "convert_tools_to_description", lambda tools: "Desc")
    content = "<function=execute_bash>\n<parameter=command>ls</parameter>\n</function>"
    converted_messages: list[dict] = []
    counter = converter._process_assistant_message_for_conversion(
        content, sample_tools, 1, converted_messages, "suffix"
    )
    assert counter == 2
    assert converted_messages[0]["tool_calls"]


def test_process_assistant_message_without_tool_call(sample_tools) -> None:
    converted_messages: list[dict] = []
    counter = converter._process_assistant_message_for_conversion(
        "plain text", sample_tools, 1, converted_messages, "suffix"
    )
    assert counter == 1
    assert converted_messages[0]["content"] == "plain text"


def test_convert_tools_to_description_without_parameters() -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "noop",
                "description": "No params",
            },
        }
    ]
    description = converter.convert_tools_to_description(tools)
    assert "No parameters" in description


def test_convert_tool_results_handles_non_list() -> None:
    message = {"role": "tool", "name": "execute_bash", "content": 42}
    converted = converter.convert_fncall_messages_to_non_fncall_messages(
        [{"role": "assistant", "content": "resp"}, message], []
    )
    assert any("42" in part["text"] for part in converted[-1]["content"])


def test_validate_parameter_allowed_raises() -> None:
    with pytest.raises(converter.FunctionCallValidationError):
        converter._validate_parameter_allowed("other", {"allowed"}, "fn")


def test_convert_parameter_value_pass_through() -> None:
    assert converter._convert_parameter_value("unknown", "value", {}) == "value"


def test_convert_to_integer_and_array_errors() -> None:
    with pytest.raises(converter.FunctionCallValidationError):
        converter._convert_to_integer("count", "nan")
    with pytest.raises(converter.FunctionCallValidationError):
        converter._convert_to_array("options", "nan")


def test_validate_enum_constraint_error(sample_tools) -> None:
    matching_tool = sample_tools[0]["function"]
    with pytest.raises(converter.FunctionCallValidationError):
        converter._validate_enum_constraint("mode", "invalid", matching_tool, "fn")
