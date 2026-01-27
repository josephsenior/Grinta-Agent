import json
import re

import pytest

from forge.events.event import FileEditSource, FileReadSource, RecallType
from forge.events.observation.agent import (
    AgentCondensationObservation,
    AgentStateChangedObservation,
    AgentThinkObservation,
    MicroagentKnowledge,
    RecallObservation,
)
from forge.events.observation.browse import BrowserOutputObservation
from forge.events.observation.commands import (
    CMD_OUTPUT_METADATA_PS1_REGEX,
    CMD_OUTPUT_PS1_BEGIN,
    CMD_OUTPUT_PS1_END,
    CmdOutputMetadata,
    CmdOutputObservation,
)
from forge.events.observation.empty import NullObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.file_download import FileDownloadObservation
from forge.events.observation.files import (
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
)
from forge.events.observation.mcp import MCPObservation
from forge.events.observation.observation import Observation
from forge.events.serialization.observation import (
    handle_observation_deprecated_extras,
    observation_from_dict,
)
from forge.events.observation.reject import UserRejectObservation
from forge.events.observation.server import ServerReadyObservation
from forge.events.observation.success import SuccessObservation
from forge.events.observation.task_tracking import TaskTrackingObservation


def test_cmd_output_metadata_ps1_helpers_roundtrip():
    prompt = CmdOutputMetadata.to_ps1_prompt()
    assert prompt.startswith(CMD_OUTPUT_PS1_BEGIN)
    assert prompt.strip().endswith(CMD_OUTPUT_PS1_END)

    sample_json = json.dumps(
        {
            "pid": "1234",
            "exit_code": "0",
            "username": "user",
            "hostname": "host",
            "working_dir": "/tmp",
            "py_interpreter_path": "/usr/bin/python",
        },
        indent=2,
    )
    mock_output = f"{CMD_OUTPUT_PS1_BEGIN}{sample_json}{CMD_OUTPUT_PS1_END}"
    matches = CmdOutputMetadata.matches_ps1_metadata(mock_output)
    assert matches, "Expected mock output to contain valid JSON metadata"
    metadata = CmdOutputMetadata.from_ps1_match(matches[0])
    assert isinstance(metadata, CmdOutputMetadata)
    assert metadata.exit_code == 0


def test_cmd_output_metadata_handles_invalid_blocks(caplog):
    invalid = f"{CMD_OUTPUT_PS1_BEGIN}{{'not': 'json'}}{CMD_OUTPUT_PS1_END}"
    caplog.clear()
    matches = CmdOutputMetadata.matches_ps1_metadata(invalid)
    assert matches == []


def test_cmd_output_observation_initialization_and_properties():
    metadata_dict = {
        "exit_code": 0,
        "pid": 123,
        "working_dir": "/tmp",
        "py_interpreter_path": "/usr/bin/python",
    }
    observation = CmdOutputObservation(
        content="output",
        command="ls",
        metadata=metadata_dict,
        exit_code=1,
        command_id=456,
    )
    assert isinstance(observation.metadata, CmdOutputMetadata)
    assert observation.exit_code == 1
    assert observation.command_id == 456
    assert observation.error is True
    assert observation.success is False
    assert "exit code 1" in observation.message
    agent_view = observation.to_agent_observation()
    assert "[Current working directory: /tmp]" in agent_view
    assert "[Command finished with exit code 1]" in agent_view
    string_repr = str(observation)
    assert "CmdOutputObservation" in string_repr
    assert json.dumps(metadata_dict["working_dir"]).strip('"') in string_repr


def test_observation_serialization_helpers_cover_edge_cases():
    extras = handle_observation_deprecated_extras(
        {"exit_code": 3, "command_id": 9, "formatted_output_and_error": "text"}
    )
    assert isinstance(extras["metadata"], CmdOutputMetadata)
    assert extras["metadata"].exit_code == 3 and extras["metadata"].pid == 9

    updated_metadata = handle_observation_deprecated_extras(
        {"metadata": CmdOutputMetadata(), "exit_code": 5}
    )
    assert updated_metadata["metadata"].exit_code == 5

    metadata_none = CmdOutputObservation._maybe_truncate("abcdef", max_size=5)
    assert "Observation truncated" in metadata_none

    minimal = observation_from_dict(
        {
            "observation": "run",
            "content": "body",
            "extras": {"command": "ls", "metadata": {"exit_code": 0}},
        }
    )
    assert isinstance(minimal.metadata, CmdOutputMetadata)

    recall_dict = {
        "observation": "recall",
        "content": "body",
        "extras": {
            "recall_type": RecallType.WORKSPACE_CONTEXT.value,
            "microagent_knowledge": [{"name": "n", "trigger": "t", "content": "c"}],
        },
    }
    recall = observation_from_dict(recall_dict)
    assert recall.recall_type is RecallType.WORKSPACE_CONTEXT
    assert recall.microagent_knowledge[0].name == "n"

    with pytest.raises(KeyError):
        observation_from_dict({})

    default_metadata_obs = observation_from_dict(
        {"observation": "run", "content": "body", "extras": {"command": "ls"}}
    )
    assert isinstance(default_metadata_obs.metadata, CmdOutputMetadata)


def test_cmd_output_observation_truncation_behavior():
    long_text = "a" * 10
    truncated = CmdOutputObservation._maybe_truncate(long_text, max_size=6)
    assert "[... Observation truncated due to length ...]" in truncated
    hidden = CmdOutputObservation(content=long_text, command="ls", hidden=True)
    assert hidden.content == long_text


def test_browser_output_observation_str_includes_context(tmp_path):
    screenshot_path = tmp_path / "shot.png"
    screenshot_path.write_text("png")
    obs = BrowserOutputObservation(
        content="Page content",
        url="https://example.com",
        trigger_by_action="browse",
        screenshot_path=str(screenshot_path),
        open_pages_urls=["https://example.com", "https://example.org"],
        active_page_index=1,
        last_browser_action="Click link",
        last_browser_action_error="",
        focused_element_bid="42",
    )
    assert obs.message == "Visited https://example.com"
    rendered = str(obs)
    assert "BrowserOutputObservation" in rendered
    assert "Active page index: 1" in rendered
    assert "Screenshot saved to" in rendered


def test_file_observations_messages_and_strings():
    read_obs = FileReadObservation(content="hello", path="doc.txt")
    assert read_obs.message == "I read the file doc.txt."
    assert "[Read from doc.txt" in str(read_obs)
    assert read_obs.impl_source is FileReadSource.DEFAULT

    write_obs = FileWriteObservation(content="hello", path="doc.txt")
    assert write_obs.message == "I wrote to the file doc.txt."
    assert "Write to doc.txt" in str(write_obs)


def test_file_edit_observation_diff_generation_and_caching():
    edit_obs = FileEditObservation(
        content="diff",
        path="code.py",
        prev_exist=True,
        old_content="print('hi')\n",
        new_content="print('hello')\n",
        impl_source=FileEditSource.LLM_BASED_EDIT,
    )
    groups = edit_obs.get_edit_groups()
    assert groups, "Expected differences to be detected"
    first_render = edit_obs.visualize_diff()
    second_render = edit_obs.visualize_diff()
    assert first_render == second_render  # cached result
    assert "[Existing file code.py is edited" in first_render
    assert edit_obs.message == "I edited the file code.py."

    new_file_obs = FileEditObservation(
        content="new",
        path="new.txt",
        prev_exist=False,
        old_content="",
        new_content="data",
        impl_source=FileEditSource.LLM_BASED_EDIT,
    )
    assert "[New file new.txt is created" in str(new_file_obs)

    aci_obs = FileEditObservation(
        content="Generated content",
        path="code.py",
        impl_source=FileEditSource.FILE_EDITOR,
    )
    assert aci_obs.__str__() == aci_obs.content


def test_observation_simple_messages_and_defaults():
    null_obs = NullObservation(content="nothing")
    assert null_obs.message == "No observation"

    error_obs = ErrorObservation(content="Failure", error_id="E1")
    assert "Failure" in error_obs.message
    assert "**ErrorObservation**" in str(error_obs)

    success_obs = SuccessObservation(content="Done")
    assert success_obs.message == "Done"

    reject_obs = UserRejectObservation(content="No thanks")
    assert reject_obs.message == "No thanks"

    state_obs = AgentStateChangedObservation(content="state", agent_state="new")
    assert state_obs.message == ""

    think_obs = AgentThinkObservation(content="Thinking")
    assert think_obs.message == "Thinking"

    task_obs = TaskTrackingObservation(content="Updated")
    assert task_obs.message == "Updated"

    mcp_obs = MCPObservation(content="MCP result", name="tool")
    assert mcp_obs.message == "MCP result"


def test_recall_observation_formats_based_on_type():
    knowledge = MicroagentKnowledge(
        name="python", trigger="py", content="Always use venv"
    )
    recall_workspace = RecallObservation(
        content="workspace",
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="repo",
        repo_instructions="Follow instructions",
        runtime_hosts={"host": 1},
        microagent_knowledge=[knowledge],
    )
    assert recall_workspace.message == "Added workspace context"
    rendered = str(recall_workspace)
    assert "recall_type" in rendered
    assert "microagent_knowledge=python" in rendered

    recall_knowledge = RecallObservation(
        content="knowledge",
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=[knowledge],
    )
    assert recall_knowledge.message == "Added microagent knowledge"


def test_condensation_observation_outputs_content():
    observation = AgentCondensationObservation(content="Summary")
    assert observation.message == "Summary"


def test_server_ready_observation_message_uses_health_status():
    healthy = ServerReadyObservation(
        content="", port=8080, url="http://localhost:8080", health_status="healthy"
    )
    waiting = ServerReadyObservation(content="", port=8080, url="http://localhost:8080")
    assert healthy.message.startswith("✅")
    assert waiting.message.startswith("🔄")


def test_file_download_observation_formatting():
    obs = FileDownloadObservation(content="done", file_path="/tmp/file.txt")
    assert "Downloaded the file" in obs.message
    assert "FileDownloadObservation" in str(obs)


def test_backward_compatibility_imports():
    import forge.events.observation.browser_output as browser_output
    import forge.events.observation.cmd_output as cmd_output

    assert browser_output.BrowserOutputObservation is BrowserOutputObservation
    assert cmd_output.CmdOutputObservation is CmdOutputObservation
