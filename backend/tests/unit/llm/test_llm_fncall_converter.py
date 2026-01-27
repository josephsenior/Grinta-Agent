"""Test for FunctionCallingConverter."""

import copy
import json
import pytest
from typing import Any
from forge.llm.fn_call_converter import (
    IN_CONTEXT_LEARNING_EXAMPLE_PREFIX,
    IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX,
    TOOL_EXAMPLES,
    FunctionCallConversionError,
    convert_fncall_messages_to_non_fncall_messages,
    convert_from_multiple_tool_calls_to_single_tool_call_messages,
    convert_non_fncall_messages_to_fncall_messages,
    convert_tool_call_to_string,
    convert_tools_to_description,
    get_example_for_tools,
    refine_prompt,
)

FNCALL_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": 'Execute a bash command in the terminal.\n* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.\n* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.\n* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.\n',
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish the interaction when the task is complete OR if the assistant cannot proceed further with the task.",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": "Custom editing tool for viewing, creating and editing files\n* Editor state is ephemeral to the current agent session and should not be relied upon for cross-run persistence. For step-level caching or long-term persistence, rely on the orchestrator's cache.\n* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep\n* The `create` command cannot be used if the specified `path` already exists as a file\n* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`\n* The `undo_edit` command will revert the last edit made to the file at `path`\n\nNotes for using the `str_replace` command:\n* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!\n* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique\n* The `new_str` parameter should contain the edited lines that should replace the `old_str`\n",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
                        "enum": [
                            "view",
                            "create",
                            "str_replace",
                            "insert",
                            "undo_edit",
                        ],
                        "type": "string",
                    },
                    "path": {
                        "description": "Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.",
                        "type": "string",
                    },
                    "file_text": {
                        "description": "Required parameter of `create` command, with the content of the file to be created.",
                        "type": "string",
                    },
                    "old_str": {
                        "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
                        "type": "string",
                    },
                    "new_str": {
                        "description": "Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.",
                        "type": "string",
                    },
                    "insert_line": {
                        "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
                        "type": "integer",
                    },
                    "view_range": {
                        "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                        "items": {"type": "integer"},
                        "type": "array",
                    },
                },
                "required": ["command", "path"],
            },
        },
    },
]


def _normalize_messages(messages):
    """Return a normalized copy of messages suitable for equality checks.

    Normalization rules:
    - If message.content is a list, collapse text-type parts into a single text block.
    - Convert CRLF to LF and strip trailing spaces inside text blocks.
    """
    import copy
    import re

    out = []
    for m in copy.deepcopy(messages):
        if isinstance(m.get("content"), list):
            parts = []
            for c in m["content"]:
                if c.get("type") == "text":
                    parts.append(c.get("text", ""))
                else:
                    try:
                        parts.append(json.dumps(c, ensure_ascii=False))
                    except Exception:
                        parts.append(str(c))
            text = "\n".join(parts)
            text = re.sub("\\r\\n|\\r", "\n", text).strip()
            m["content"] = [{"type": "text", "text": text}]
        out.append(m)
    return out


def test_malformed_parameter_parsing_recovery():
    """Ensure we can recover when models emit malformed parameter tags like <parameter=command=str_replace</parameter>.

    This simulates a tool call to str_replace_editor where the 'command' parameter is malformed.
    """
    from forge.llm.fn_call_converter import (
        convert_non_fncall_messages_to_fncall_messages,
    )

    assistant_message = {
        "role": "assistant",
        "content": "<function=str_replace_editor>\n<parameter=command=str_replace</parameter>\n<parameter=path>/repo/app.py</parameter>\n<parameter=old_str>foo</parameter>\n<parameter=new_str>bar</parameter>\n</function>",
    }
    messages = [
        {"role": "system", "content": "test"},
        {"role": "user", "content": "do edit"},
        assistant_message,
    ]
    converted = convert_non_fncall_messages_to_fncall_messages(messages, FNCALL_TOOLS)
    last = converted[-1]
    assert last["role"] == "assistant"
    assert "tool_calls" in last and len(last["tool_calls"]) == 1
    tool_call = last["tool_calls"][0]
    assert tool_call["type"] == "function"
    assert tool_call["function"]["name"] == "str_replace_editor"
    args = json.loads(tool_call["function"]["arguments"])
    assert args["command"] == "str_replace"
    assert args["path"] == "/repo/app.py"
    assert args["old_str"] == "foo"
    assert args["new_str"] == "bar"


def test_convert_tools_to_description():
    formatted_tools = convert_tools_to_description(FNCALL_TOOLS)
    print(formatted_tools)
    assert (
        formatted_tools.strip()
        == '---- BEGIN FUNCTION #1: execute_bash ----\nDescription: Execute a bash command in the terminal.\n* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.\n* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.\n* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.\n\nParameters:\n  (1) command (string, required): The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.\n---- END FUNCTION #1 ----\n\n---- BEGIN FUNCTION #2: finish ----\nDescription: Finish the interaction when the task is complete OR if the assistant cannot proceed further with the task.\nNo parameters are required for this function.\n---- END FUNCTION #2 ----\n\n---- BEGIN FUNCTION #3: str_replace_editor ----\nDescription: Custom editing tool for viewing, creating and editing files\n* Editor state is ephemeral to the current agent session and should not be relied upon for cross-run persistence. For step-level caching or long-term persistence, rely on the orchestrator\'s cache.\n* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep\n* The `create` command cannot be used if the specified `path` already exists as a file\n* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`\n* The `undo_edit` command will revert the last edit made to the file at `path`\n\nNotes for using the `str_replace` command:\n* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!\n* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique\n* The `new_str` parameter should contain the edited lines that should replace the `old_str`\n\nParameters:\n  (1) command (string, required): The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.\nAllowed values: [`view`, `create`, `str_replace`, `insert`, `undo_edit`]\n  (2) path (string, required): Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.\n  (3) file_text (string, optional): Required parameter of `create` command, with the content of the file to be created.\n  (4) old_str (string, optional): Required parameter of `str_replace` command containing the string in `path` to replace.\n  (5) new_str (string, optional): Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.\n  (6) insert_line (integer, optional): Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.\n  (7) view_range (array, optional): Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.\n---- END FUNCTION #3 ----'.strip()
    )


def test_get_example_for_tools_no_tools():
    """Test that get_example_for_tools returns empty string when no tools are available."""
    tools = []
    example = get_example_for_tools(tools)
    assert example == ""


def test_get_example_for_tools_single_tool():
    """Test that get_example_for_tools generates correct example with a single tool."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Execute a bash command in the terminal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute.",
                        }
                    },
                    "required": ["command"],
                },
            },
        }
    ]
    example = get_example_for_tools(tools)
    assert example.startswith(
        "Here's a running example of how to perform a task with the provided tools."
    )
    assert (
        "USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000."
        in example
    )
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["check_dir"]) in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["run_server"]) in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["kill_server"]) in example
    assert TOOL_EXAMPLES["str_replace_editor"]["create_file"] not in example
    assert TOOL_EXAMPLES["browser"]["view_page"] not in example
    assert TOOL_EXAMPLES["finish"]["example"] not in example


def test_get_example_for_tools_single_tool_is_finish():
    """Test get_example_for_tools with only the finish tool."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Finish the interaction when the task is complete.",
            },
        }
    ]
    example = get_example_for_tools(tools)
    assert example.startswith(
        "Here's a running example of how to perform a task with the provided tools."
    )
    assert (
        "USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000."
        in example
    )
    assert TOOL_EXAMPLES["finish"]["example"] in example
    assert TOOL_EXAMPLES["execute_bash"]["check_dir"] not in example
    assert TOOL_EXAMPLES["str_replace_editor"]["create_file"] not in example
    assert TOOL_EXAMPLES["browser"]["view_page"] not in example


def test_get_example_for_tools_multiple_tools():
    """Test that get_example_for_tools generates correct example with multiple tools."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Execute a bash command in the terminal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute.",
                        }
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "str_replace_editor",
                "description": "Custom editing tool for viewing, creating and editing files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The commands to run.",
                            "enum": [
                                "view",
                                "create",
                                "str_replace",
                                "insert",
                                "undo_edit",
                            ],
                        },
                        "path": {
                            "type": "string",
                            "description": "Absolute path to file or directory.",
                        },
                    },
                    "required": ["command", "path"],
                },
            },
        },
    ]
    example = get_example_for_tools(tools)
    assert example.startswith(
        "Here's a running example of how to perform a task with the provided tools."
    )
    assert (
        "USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000."
        in example
    )
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["check_dir"]) in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["run_server"]) in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["kill_server"]) in example
    assert TOOL_EXAMPLES["str_replace_editor"]["create_file"] in example
    assert TOOL_EXAMPLES["str_replace_editor"]["edit_file"] in example
    assert TOOL_EXAMPLES["browser"]["view_page"] not in example
    assert TOOL_EXAMPLES["finish"]["example"] not in example


def test_get_example_for_tools_multiple_tools_with_finish():
    """Test get_example_for_tools with multiple tools including finish."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "execute_bash",
                "description": "Execute a bash command in the terminal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command to execute.",
                        }
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "str_replace_editor",
                "description": "Custom editing tool for viewing, creating and editing files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The commands to run.",
                            "enum": [
                                "view",
                                "create",
                                "str_replace",
                                "insert",
                                "undo_edit",
                            ],
                        },
                        "path": {
                            "type": "string",
                            "description": "Absolute path to file or directory.",
                        },
                    },
                    "required": ["command", "path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "Interact with the browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code that interacts with the browser.",
                        }
                    },
                    "required": ["code"],
                },
            },
        },
        {
            "type": "function",
            "function": {"name": "finish", "description": "Finish the interaction."},
        },
    ]
    example = get_example_for_tools(tools)
    assert example.startswith(
        "Here's a running example of how to perform a task with the provided tools."
    )
    assert (
        "USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000."
        in example
    )
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["check_dir"]).strip() in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["run_server"]).strip() in example
    assert (
        refine_prompt(TOOL_EXAMPLES["execute_bash"]["kill_server"]).strip() in example
    )
    assert (
        refine_prompt(TOOL_EXAMPLES["execute_bash"]["run_server_again"]).strip()
        in example
    )
    assert TOOL_EXAMPLES["str_replace_editor"]["create_file"] in example
    assert TOOL_EXAMPLES["str_replace_editor"]["edit_file"] in example
    assert TOOL_EXAMPLES["browser"]["view_page"] in example
    assert TOOL_EXAMPLES["finish"]["example"] in example


def test_get_example_for_tools_all_tools():
    """Test that get_example_for_tools generates correct example with all tools."""
    tools = FNCALL_TOOLS
    example = get_example_for_tools(tools)
    assert example.startswith(
        "Here's a running example of how to perform a task with the provided tools."
    )
    assert (
        "USER: Create a list of numbers from 1 to 10, and display them in a web page at port 5000."
        in example
    )
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["check_dir"]).strip() in example
    assert refine_prompt(TOOL_EXAMPLES["execute_bash"]["run_server"]).strip() in example
    assert (
        refine_prompt(TOOL_EXAMPLES["execute_bash"]["kill_server"]).strip() in example
    )
    assert TOOL_EXAMPLES["str_replace_editor"]["create_file"].strip() in example
    assert TOOL_EXAMPLES["str_replace_editor"]["edit_file"].strip() in example
    assert TOOL_EXAMPLES["finish"]["example"] in example
    assert TOOL_EXAMPLES["browser"]["view_page"] not in example


FNCALL_MESSAGES = [
    {
        "content": [
            {
                "type": "text",
                "text": "You are a helpful assistant that can interact with a computer to solve tasks.\n<IMPORTANT>\n* If user provides a path, you should NOT assume it's relative to the current working directory. Instead, you should explore the file system to find the file before working on it.\n</IMPORTANT>\n\n",
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "role": "system",
    },
    {
        "content": [
            {
                "type": "text",
                "text": "<uploaded_files>\n/workspace/astropy__astropy__5.1\n</uploaded_files>\nI've uploaded a python code repository in the directory astropy__astropy__5.1. LONG DESCRIPTION:\n\n",
            }
        ],
        "role": "user",
    },
    {
        "content": [
            {
                "type": "text",
                "text": "I'll help you implement the necessary changes to meet the requirements. Let's follow the steps:\n\n1. First, let's explore the repository structure:",
            }
        ],
        "role": "assistant",
        "tool_calls": [
            {
                "index": 1,
                "function": {
                    "arguments": '{"command": "ls -la /workspace/astropy__astropy__5.1"}',
                    "name": "execute_bash",
                },
                "id": "toolu_01",
                "type": "function",
            }
        ],
    },
    {
        "content": [
            {
                "type": "text",
                "text": "ls -la /workspace/astropy__astropy__5.1\r\nls: /workspace/astropy__astropy__5.1: Bad file descriptor\r\nlrwxrwxrwx 1 root root 8 Oct 28 21:58 /workspace/astropy__astropy__5.1 -> /testbed[Python Interpreter: /opt/miniconda3/envs/testbed/bin/python]\nroot@Forge-workspace:/workspace/astropy__astropy__5.1 # \n[Command finished with exit code 0]",
            }
        ],
        "role": "tool",
        "tool_call_id": "toolu_01",
        "name": "execute_bash",
    },
    {
        "content": [
            {
                "type": "text",
                "text": "I see there's a symlink. Let's explore the actual directory:",
            }
        ],
        "role": "assistant",
        "tool_calls": [
            {
                "index": 1,
                "function": {
                    "arguments": '{"command": "ls -la /testbed"}',
                    "name": "execute_bash",
                },
                "id": "toolu_02",
                "type": "function",
            }
        ],
    },
    {
        "content": [{"type": "text", "text": "SOME OBSERVATION"}],
        "role": "tool",
        "tool_call_id": "toolu_02",
        "name": "execute_bash",
    },
    {
        "content": [
            {
                "type": "text",
                "text": "Let's look at the source code file mentioned in the PR description:",
            }
        ],
        "role": "assistant",
        "tool_calls": [
            {
                "index": 1,
                "function": {
                    "arguments": '{"command": "view", "path": "/testbed/astropy/io/fits/card.py"}',
                    "name": "str_replace_editor",
                },
                "id": "toolu_03",
                "type": "function",
            }
        ],
    },
    {
        "content": [
            {
                "type": "text",
                "text": "Here's the result of running `cat -n` on /testbed/astropy/io/fits/card.py:\n     1\t# Licensed under a 3-clause BSD style license - see PYFITS.rst...VERY LONG TEXT",
            }
        ],
        "role": "tool",
        "tool_call_id": "toolu_03",
        "name": "str_replace_editor",
    },
]
NON_FNCALL_MESSAGES = [
    {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": 'You are a helpful assistant that can interact with a computer to solve tasks.\n<IMPORTANT>\n* If user provides a path, you should NOT assume it\'s relative to the current working directory. Instead, you should explore the file system to find the file before working on it.\n</IMPORTANT>\n\n\nYou have access to the following functions:\n\n---- BEGIN FUNCTION #1: execute_bash ----\nDescription: Execute a bash command in the terminal.\n* Long running commands: For commands that may run indefinitely, it should be run in the background and the output should be redirected to a file, e.g. command = `python3 app.py > server.log 2>&1 &`.\n* Interactive: If a bash command returns exit code `-1`, this means the process is not yet finished. The assistant must then send a second call to terminal with an empty `command` (which will retrieve any additional logs), or it can send additional text (set `command` to the text) to STDIN of the running process, or it can send command=`ctrl+c` to interrupt the process.\n* Timeout: If a command execution result says "Command timed out. Sending SIGINT to the process", the assistant should retry running the command in the background.\n\nParameters:\n  (1) command (string, required): The bash command to execute. Can be empty to view additional logs when previous exit code is `-1`. Can be `ctrl+c` to interrupt the currently running process.\n---- END FUNCTION #1 ----\n\n---- BEGIN FUNCTION #2: finish ----\nDescription: Finish the interaction when the task is complete OR if the assistant cannot proceed further with the task.\nNo parameters are required for this function.\n---- END FUNCTION #2 ----\n\n---- BEGIN FUNCTION #3: str_replace_editor ----\nDescription: Custom editing tool for viewing, creating and editing files\n* State is persistent across command calls and discussions with the user\n* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep\n* The `create` command cannot be used if the specified `path` already exists as a file\n* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`\n* The `undo_edit` command will revert the last edit made to the file at `path`\n\nNotes for using the `str_replace` command:\n* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!\n* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique\n* The `new_str` parameter should contain the edited lines that should replace the `old_str`\n\nParameters:\n  (1) command (string, required): The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.\nAllowed values: [`view`, `create`, `str_replace`, `insert`, `undo_edit`]\n  (2) path (string, required): Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.\n  (3) file_text (string, optional): Required parameter of `create` command, with the content of the file to be created.\n  (4) old_str (string, optional): Required parameter of `str_replace` command containing the string in `path` to replace.\n  (5) new_str (string, optional): Optional parameter of `str_replace` command containing the new string (if not given, no string will be added). Required parameter of `insert` command containing the string to insert.\n  (6) insert_line (integer, optional): Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.\n  (7) view_range (array, optional): Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.\n---- END FUNCTION #3 ----\n\n\nIf you choose to call a function ONLY reply in the following format with NO suffix:\n\n<function=example_function_name>\n<parameter=example_parameter_1>value_1</parameter>\n<parameter=example_parameter_2>\nThis is the value for the second parameter\nthat can span\nmultiple lines\n</parameter>\n</function>\n\n<IMPORTANT>\nReminder:\n- Function calls MUST follow the specified format, start with <function= and end with </function>\n- Required parameters MUST be specified\n- Only call one function at a time\n- You may provide optional reasoning for your function call in natural language BEFORE the function call, but NOT after.\n- If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls\n</IMPORTANT>\n',
                "cache_control": {"type": "ephemeral"},
            }
        ],
    },
    {
        "content": [
            {
                "type": "text",
                "text": IN_CONTEXT_LEARNING_EXAMPLE_PREFIX(FNCALL_TOOLS)
                + "<uploaded_files>\n/workspace/astropy__astropy__5.1\n</uploaded_files>\nI've uploaded a python code repository in the directory astropy__astropy__5.1. LONG DESCRIPTION:\n\n"
                + IN_CONTEXT_LEARNING_EXAMPLE_SUFFIX,
            }
        ],
        "role": "user",
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I'll help you implement the necessary changes to meet the requirements. Let's follow the steps:\n\n1. First, let's explore the repository structure:\n\n<function=execute_bash>\n<parameter=command>ls -la /workspace/astropy__astropy__5.1</parameter>\n</function>",
            }
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "EXECUTION RESULT of [execute_bash]:\nls -la /workspace/astropy__astropy__5.1\r\nls: /workspace/astropy__astropy__5.1: Bad file descriptor\r\nlrwxrwxrwx 1 root root 8 Oct 28 21:58 /workspace/astropy__astropy__5.1 -> /testbed[Python Interpreter: /opt/miniconda3/envs/testbed/bin/python]\nroot@Forge-workspace:/workspace/astropy__astropy__5.1 # \n[Command finished with exit code 0]",
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "I see there's a symlink. Let's explore the actual directory:\n\n<function=execute_bash>\n<parameter=command>ls -la /testbed</parameter>\n</function>",
            }
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "EXECUTION RESULT of [execute_bash]:\nSOME OBSERVATION",
            }
        ],
    },
    {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Let's look at the source code file mentioned in the PR description:\n\n<function=str_replace_editor>\n<parameter=command>view</parameter>\n<parameter=path>/testbed/astropy/io/fits/card.py</parameter>\n</function>",
            }
        ],
    },
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "EXECUTION RESULT of [str_replace_editor]:\nHere's the result of running `cat -n` on /testbed/astropy/io/fits/card.py:\n     1\t# Licensed under a 3-clause BSD style license - see PYFITS.rst...VERY LONG TEXT",
            }
        ],
    },
]
FNCALL_RESPONSE_MESSAGE = {
    "content": [
        {
            "type": "text",
            "text": "Let me search for the `_format_float` method mentioned in the PR description:",
        }
    ],
    "role": "assistant",
    "tool_calls": [
        {
            "index": 1,
            "function": {
                "arguments": '{"command": "grep -n \\"_format_float\\" /testbed/astropy/io/fits/card.py"}',
                "name": "execute_bash",
            },
            "id": "toolu_04",
            "type": "function",
        }
    ],
}
NON_FNCALL_RESPONSE_MESSAGE = {
    "content": [
        {
            "type": "text",
            "text": 'Let me search for the `_format_float` method mentioned in the PR description:\n\n<function=execute_bash>\n<parameter=command>grep -n "_format_float" /testbed/astropy/io/fits/card.py</parameter>\n</function>',
        }
    ],
    "role": "assistant",
}


@pytest.mark.parametrize(
    "tool_calls, expected",
    [
        (
            FNCALL_RESPONSE_MESSAGE["tool_calls"],
            '<function=execute_bash>\n<parameter=command>grep -n "_format_float" /testbed/astropy/io/fits/card.py</parameter>\n</function>',
        ),
        (
            [
                {
                    "index": 1,
                    "function": {
                        "arguments": '{"command": "view", "path": "/test/file.py", "view_range": [1, 10]}',
                        "name": "str_replace_editor",
                    },
                    "id": "test_id",
                    "type": "function",
                }
            ],
            "<function=str_replace_editor>\n<parameter=command>view</parameter>\n<parameter=path>/test/file.py</parameter>\n<parameter=view_range>[1, 10]</parameter>\n</function>",
        ),
        (
            [
                {
                    "index": 1,
                    "function": {
                        "arguments": '{"command": "str_replace", "path": "/test/file.py", "old_str": "def example():\\n    pass", "new_str": "def example():\\n    # This is indented\\n    print(\\"hello\\")\\n    return True"}',
                        "name": "str_replace_editor",
                    },
                    "id": "test_id",
                    "type": "function",
                }
            ],
            '<function=str_replace_editor>\n<parameter=command>str_replace</parameter>\n<parameter=path>/test/file.py</parameter>\n<parameter=old_str>\ndef example():\n    pass\n</parameter>\n<parameter=new_str>\ndef example():\n    # This is indented\n    print("hello")\n    return True\n</parameter>\n</function>',
        ),
        (
            [
                {
                    "index": 1,
                    "function": {
                        "arguments": '{"command": "test", "path": "/test/file.py", "tags": ["tag1", "tag2", "tag with spaces"]}',
                        "name": "test_function",
                    },
                    "id": "test_id",
                    "type": "function",
                }
            ],
            '<function=test_function>\n<parameter=command>test</parameter>\n<parameter=path>/test/file.py</parameter>\n<parameter=tags>["tag1", "tag2", "tag with spaces"]</parameter>\n</function>',
        ),
        (
            [
                {
                    "index": 1,
                    "function": {
                        "arguments": '{"command": "test", "path": "/test/file.py", "metadata": {"key1": "value1", "key2": 42, "nested": {"subkey": "subvalue"}}}',
                        "name": "test_function",
                    },
                    "id": "test_id",
                    "type": "function",
                }
            ],
            '<function=test_function>\n<parameter=command>test</parameter>\n<parameter=path>/test/file.py</parameter>\n<parameter=metadata>{"key1": "value1", "key2": 42, "nested": {"subkey": "subvalue"}}</parameter>\n</function>',
        ),
    ],
)
def test_convert_tool_call_to_string(tool_calls, expected):
    assert len(tool_calls) == 1
    converted = convert_tool_call_to_string(tool_calls[0])
    print(converted)
    assert converted == expected


def test_convert_fncall_messages_to_non_fncall_messages():
    converted_non_fncall = convert_fncall_messages_to_non_fncall_messages(
        FNCALL_MESSAGES, FNCALL_TOOLS
    )
    assert isinstance(converted_non_fncall, list)
    assert len(converted_non_fncall) == len(NON_FNCALL_MESSAGES)
    for exp, act in zip(NON_FNCALL_MESSAGES, converted_non_fncall):
        assert exp.get("role") == act.get("role")
    sys_msg = converted_non_fncall[0]
    if isinstance(sys_msg.get("content"), list):
        texts = "".join(
            [c.get("text", "") for c in sys_msg["content"] if c.get("type") == "text"]
        )
    else:
        texts = sys_msg.get("content", "")
    assert (
        "You have access to the following functions" in texts
        or "---- BEGIN FUNCTION" in texts
    )


def test_convert_non_fncall_messages_to_fncall_messages():
    converted = convert_non_fncall_messages_to_fncall_messages(
        NON_FNCALL_MESSAGES, FNCALL_TOOLS
    )
    print(json.dumps(converted, indent=2))
    assert isinstance(converted, list)
    assert len(converted) == len(FNCALL_MESSAGES)
    for exp, act in zip(FNCALL_MESSAGES, converted):
        assert exp.get("role") == act.get("role")
    sys_content = converted[0].get("content")
    if isinstance(sys_content, list):
        sys_text = "".join(
            [c.get("text", "") for c in sys_content if c.get("type") == "text"]
        )
    else:
        sys_text = sys_content or ""
    assert "---- BEGIN FUNCTION" in sys_text
    assert "execute_bash" in sys_text
    assert "str_replace_editor" in sys_text


def test_two_way_conversion_nonfn_to_fn_to_nonfn():
    """Test two-way conversion from non-fncall to fncall and back."""
    # Test non-fncall to fncall conversion
    _test_nonfn_to_fncall_conversion()

    # Test fncall to non-fncall conversion
    _test_fncall_to_nonfn_conversion()


def _test_nonfn_to_fncall_conversion():
    """Test conversion from non-fncall messages to fncall messages."""
    non_fncall_copy = copy.deepcopy(NON_FNCALL_MESSAGES)
    converted_fncall = convert_non_fncall_messages_to_fncall_messages(
        NON_FNCALL_MESSAGES, FNCALL_TOOLS
    )

    # Verify original messages unchanged
    assert non_fncall_copy == NON_FNCALL_MESSAGES

    # Verify conversion results
    _verify_fncall_conversion_results(converted_fncall)

    # Verify tool calls contain expected tools
    _verify_tool_calls_contain_expected_tools(converted_fncall)


def _test_fncall_to_nonfn_conversion():
    """Test conversion from fncall messages to non-fncall messages."""
    fncall_copy = copy.deepcopy(FNCALL_MESSAGES)
    converted_non_fncall = convert_fncall_messages_to_non_fncall_messages(
        FNCALL_MESSAGES, FNCALL_TOOLS
    )

    # Verify original messages unchanged
    assert fncall_copy == FNCALL_MESSAGES

    # Verify conversion results
    _verify_nonfn_conversion_results(converted_non_fncall)

    # Verify system text contains function information
    _verify_system_text_contains_function_info(converted_non_fncall)


def _verify_fncall_conversion_results(converted_fncall):
    """Verify fncall conversion results."""
    assert isinstance(converted_fncall, list)
    assert len(converted_fncall) == len(FNCALL_MESSAGES)

    for exp, act in zip(FNCALL_MESSAGES, converted_fncall):
        assert exp.get("role") == act.get("role")


def _verify_nonfn_conversion_results(converted_non_fncall):
    """Verify non-fncall conversion results."""
    assert isinstance(converted_non_fncall, list)
    assert len(converted_non_fncall) == len(NON_FNCALL_MESSAGES)

    for exp, act in zip(NON_FNCALL_MESSAGES, converted_non_fncall):
        assert exp.get("role") == act.get("role")


def _verify_tool_calls_contain_expected_tools(converted_fncall):
    """Verify that tool calls contain expected tools."""
    first_tool_calls = [
        m
        for m in converted_fncall
        if m.get("role") == "assistant" and m.get("tool_calls")
    ]

    tool_call_text = json.dumps(
        [tc for m in first_tool_calls for tc in m.get("tool_calls", [])],
        ensure_ascii=False,
    )
    expected_tools = ["str_replace_editor", "execute_bash"]

    assert any(tool in tool_call_text for tool in expected_tools)


def _verify_system_text_contains_function_info(converted_non_fncall):
    """Verify that system text contains function information."""
    sys_texts = "".join(
        [
            c.get("text", "")
            for c in converted_non_fncall[0].get("content", [])
            if c.get("type") == "text"
        ]
    )

    expected_indicators = [
        "You have access to the following functions",
        "---- BEGIN FUNCTION",
    ]

    assert any(indicator in sys_texts for indicator in expected_indicators)


def test_two_way_conversion_fn_to_nonfn_to_fn():
    fncall_copy = copy.deepcopy(FNCALL_MESSAGES)
    converted_non_fncall = convert_fncall_messages_to_non_fncall_messages(
        FNCALL_MESSAGES, FNCALL_TOOLS
    )
    assert fncall_copy == FNCALL_MESSAGES
    assert isinstance(converted_non_fncall, list)
    assert len(converted_non_fncall) == len(NON_FNCALL_MESSAGES)
    for exp, act in zip(NON_FNCALL_MESSAGES, converted_non_fncall):
        assert exp.get("role") == act.get("role")
    non_fncall_copy = copy.deepcopy(NON_FNCALL_MESSAGES)
    converted_fncall = convert_non_fncall_messages_to_fncall_messages(
        NON_FNCALL_MESSAGES, FNCALL_TOOLS
    )
    assert non_fncall_copy == NON_FNCALL_MESSAGES
    assert isinstance(converted_fncall, list)
    assert len(converted_fncall) == len(FNCALL_MESSAGES)
    for exp, act in zip(FNCALL_MESSAGES, converted_fncall):
        assert exp.get("role") == act.get("role")


def test_infer_fncall_on_noncall_model():
    messages_for_llm_inference = convert_fncall_messages_to_non_fncall_messages(
        FNCALL_MESSAGES, FNCALL_TOOLS
    )
    assert isinstance(messages_for_llm_inference, list)
    assert len(messages_for_llm_inference) == len(NON_FNCALL_MESSAGES)
    for exp, act in zip(NON_FNCALL_MESSAGES, messages_for_llm_inference):
        assert exp.get("role") == act.get("role")
    response_message_from_llm_inference = NON_FNCALL_RESPONSE_MESSAGE
    all_nonfncall_messages = NON_FNCALL_MESSAGES + [response_message_from_llm_inference]
    converted_fncall_messages = convert_non_fncall_messages_to_fncall_messages(
        all_nonfncall_messages, FNCALL_TOOLS
    )
    assert isinstance(converted_fncall_messages, list)
    assert len(converted_fncall_messages) == len(FNCALL_MESSAGES) + 1
    for exp, act in zip(
        FNCALL_MESSAGES + [FNCALL_RESPONSE_MESSAGE], converted_fncall_messages
    ):
        assert exp.get("role") == act.get("role")
    assert "tool_calls" in converted_fncall_messages[-1]
    assert (
        converted_fncall_messages[-1]["tool_calls"][0]["function"]["name"]
        == FNCALL_RESPONSE_MESSAGE["tool_calls"][0]["function"]["name"]
    )


def test_convert_from_multiple_tool_calls_to_single_tool_call_messages():
    input_messages = [
        {
            "role": "assistant",
            "content": "Let me help you with that.",
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": "func1", "arguments": "{}"},
                },
                {
                    "id": "call2",
                    "type": "function",
                    "function": {"name": "func2", "arguments": "{}"},
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call1",
            "content": "Result 1",
            "name": "func1",
        },
        {
            "role": "tool",
            "tool_call_id": "call2",
            "content": "Result 2",
            "name": "func2",
        },
        {
            "role": "assistant",
            "content": "Test again",
            "tool_calls": [
                {
                    "id": "call3",
                    "type": "function",
                    "function": {"name": "func3", "arguments": "{}"},
                },
                {
                    "id": "call4",
                    "type": "function",
                    "function": {"name": "func4", "arguments": "{}"},
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call3",
            "content": "Result 3",
            "name": "func3",
        },
        {
            "role": "tool",
            "tool_call_id": "call4",
            "content": "Result 4",
            "name": "func4",
        },
    ]
    expected_output = [
        {
            "role": "assistant",
            "content": "Let me help you with that.",
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": "func1", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call1",
            "content": "Result 1",
            "name": "func1",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call2",
                    "type": "function",
                    "function": {"name": "func2", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call2",
            "content": "Result 2",
            "name": "func2",
        },
        {
            "role": "assistant",
            "content": "Test again",
            "tool_calls": [
                {
                    "id": "call3",
                    "type": "function",
                    "function": {"name": "func3", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call3",
            "content": "Result 3",
            "name": "func3",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call4",
                    "type": "function",
                    "function": {"name": "func4", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call4",
            "content": "Result 4",
            "name": "func4",
        },
    ]
    result = convert_from_multiple_tool_calls_to_single_tool_call_messages(
        input_messages
    )
    assert result == expected_output


def test_convert_from_multiple_tool_calls_to_single_tool_call_messages_incomplete():
    input_messages = [
        {
            "role": "assistant",
            "content": "Let me help you with that.",
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": "func1", "arguments": "{}"},
                },
                {
                    "id": "call2",
                    "type": "function",
                    "function": {"name": "func2", "arguments": "{}"},
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call1",
            "content": "Result 1",
            "name": "func1",
        },
    ]
    with pytest.raises(FunctionCallConversionError):
        convert_from_multiple_tool_calls_to_single_tool_call_messages(input_messages)


def test_convert_from_multiple_tool_calls_no_changes_needed():
    input_messages = [
        {
            "role": "assistant",
            "content": "Let me help you with that.",
            "tool_calls": [
                {
                    "id": "call1",
                    "type": "function",
                    "function": {"name": "func1", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call1",
            "content": "Result 1",
            "name": "func1",
        },
    ]
    result = convert_from_multiple_tool_calls_to_single_tool_call_messages(
        input_messages
    )
    assert result == input_messages


def test_convert_from_multiple_tool_calls_no_tool_calls():
    input_messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    result = convert_from_multiple_tool_calls_to_single_tool_call_messages(
        input_messages
    )
    assert result == input_messages


def test_convert_fncall_messages_with_cache_control():
    """Test that cache_control is properly handled in tool messages."""
    messages = [
        {
            "role": "tool",
            "name": "test_tool",
            "content": [{"type": "text", "text": "test content"}],
            "cache_control": {"type": "ephemeral"},
        }
    ]
    result = convert_fncall_messages_to_non_fncall_messages(messages, [])
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert "cache_control" in result[0]["content"][-1]
    assert result[0]["content"][-1]["cache_control"] == {"type": "ephemeral"}
    assert (
        result[0]["content"][0]["text"]
        == "EXECUTION RESULT of [test_tool]:\ntest content"
    )


def test_convert_fncall_messages_without_cache_control():
    """Test that tool messages without cache_control work as expected."""
    messages = [
        {
            "role": "tool",
            "name": "test_tool",
            "content": [{"type": "text", "text": "test content"}],
        }
    ]
    result = convert_fncall_messages_to_non_fncall_messages(messages, [])
    assert len(result) == 1
    assert result[0]["role"] == "user"
    assert "cache_control" not in result[0]["content"][-1]
    assert (
        result[0]["content"][0]["text"]
        == "EXECUTION RESULT of [test_tool]:\ntest content"
    )


def test_convert_fncall_messages_with_image_url():
    """Test that convert_fncall_messages_to_non_fncall_messages handles image URLs correctly."""
    messages = [
        {
            "role": "tool",
            "name": "browser",
            "content": [
                {"type": "text", "text": "some browser tool results"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/gif;base64,R0lGODlhAQABAAAAACw="},
                },
            ],
        }
    ]
    converted_messages = convert_fncall_messages_to_non_fncall_messages(messages, [])
    assert len(converted_messages) == 1
    assert converted_messages[0]["role"] == "user"
    assert len(converted_messages[0]["content"]) == len(messages[0]["content"])
    assert (
        next((c for c in converted_messages[0]["content"] if c["type"] == "text"))[
            "text"
        ]
        == f"EXECUTION RESULT of [{messages[0]['name']}]:\n{messages[0]['content'][0]['text']}"
    )
