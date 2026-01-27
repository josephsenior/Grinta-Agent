import pytest

from forge.core.exceptions import LLMMalformedActionError
from forge.events.action import (
    Action,
    AgentFinishAction,
    AgentRejectAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    MessageAction,
    RecallAction,
)
from forge.events.action.action import ActionConfirmationStatus, ActionSecurityRisk
from forge.events.action.files import FileEditSource, FileReadSource
from forge.events.serialization import event_from_dict, event_to_dict
from forge.events.serialization.action import (
    action_from_dict,
    handle_action_deprecated_args,
)


def serialization_deserialization(
    original_action_dict, cls, max_message_chars: int = 10000
):
    action_instance = event_from_dict(original_action_dict)
    assert isinstance(action_instance, Action), (
        "The action instance should be an instance of Action."
    )
    assert isinstance(action_instance, cls), (
        f"The action instance should be an instance of {cls.__name__}."
    )
    serialized_action_dict = event_to_dict(action_instance)
    serialized_action_dict.pop("message")
    assert serialized_action_dict == original_action_dict, (
        "The serialized action should match the original action dict."
    )


def test_event_props_serialization_deserialization():
    original_action_dict = {
        "id": 42,
        "source": "agent",
        "timestamp": "2021-08-01T12:00:00",
        "action": "message",
        "args": {
            "content": "This is a test.",
            "image_urls": None,
            "file_urls": None,
            "wait_for_response": False,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, MessageAction)


def test_message_action_serialization_deserialization():
    original_action_dict = {
        "action": "message",
        "args": {
            "content": "This is a test.",
            "image_urls": None,
            "file_urls": None,
            "wait_for_response": False,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, MessageAction)


def test_agent_finish_action_serialization_deserialization():
    original_action_dict = {
        "action": "finish",
        "args": {
            "outputs": {},
            "thought": "",
            "final_thought": "",
            "force_finish": False,
        },
    }
    serialization_deserialization(original_action_dict, AgentFinishAction)


def test_agent_finish_action_legacy_task_completed_serialization():
    """Test that old conversations with task_completed can still be loaded."""
    original_action_dict = {
        "action": "finish",
        "args": {
            "outputs": {},
            "thought": "",
            "final_thought": "Task completed",
            "task_completed": "true",
        },
    }
    event = event_from_dict(original_action_dict)
    assert isinstance(event, Action)
    assert isinstance(event, AgentFinishAction)
    assert event.final_thought == "Task completed"
    assert not hasattr(event, "task_completed")
    event_dict = event_to_dict(event)
    assert "task_completed" not in event_dict["args"]


def test_agent_reject_action_serialization_deserialization():
    original_action_dict = {"action": "reject", "args": {"outputs": {}, "thought": ""}}
    serialization_deserialization(original_action_dict, AgentRejectAction)


def test_cmd_run_action_serialization_deserialization():
    original_action_dict = {
        "action": "run",
        "args": {
            "blocking": False,
            "command": 'echo "Hello world"',
            "is_input": False,
            "thought": "",
            "hidden": False,
            "confirmation_state": ActionConfirmationStatus.CONFIRMED,
            "is_static": False,
            "cwd": None,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, CmdRunAction)


def test_browse_url_action_serialization_deserialization():
    original_action_dict = {
        "action": "browse",
        "args": {
            "thought": "",
            "url": "https://www.example.com",
            "return_axtree": False,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, BrowseURLAction)


def test_browse_interactive_action_serialization_deserialization():
    original_action_dict = {
        "action": "browse_interactive",
        "args": {
            "thought": "",
            "browser_actions": 'goto("https://www.example.com")',
            "browsergym_send_msg_to_user": "",
            "return_axtree": False,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, BrowseInteractiveAction)


def test_file_read_action_serialization_deserialization():
    original_action_dict = {
        "action": "read",
        "args": {
            "path": "/path/to/file.txt",
            "start": 0,
            "end": -1,
            "thought": "None",
            "impl_source": "default",
            "view_range": None,
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, FileReadAction)


def test_file_write_action_serialization_deserialization():
    original_action_dict = {
        "action": "write",
        "args": {
            "path": "/path/to/file.txt",
            "content": "Hello world",
            "start": 0,
            "end": 1,
            "thought": "None",
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, FileWriteAction)


def test_file_edit_action_aci_serialization_deserialization():
    original_action_dict = {
        "action": "edit",
        "args": {
            "path": "/path/to/file.txt",
            "command": "str_replace",
            "file_text": None,
            "old_str": "old text",
            "new_str": "new text",
            "insert_line": None,
            "content": "",
            "start": 1,
            "end": -1,
            "thought": "Replacing text",
            "impl_source": "file_editor",
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, FileEditAction)


def test_file_edit_action_llm_serialization_deserialization():
    original_action_dict = {
        "action": "edit",
        "args": {
            "path": "/path/to/file.txt",
            "command": None,
            "file_text": None,
            "old_str": None,
            "new_str": None,
            "insert_line": None,
            "content": "Updated content",
            "start": 1,
            "end": 10,
            "thought": "Updating file content",
            "impl_source": "llm_based_edit",
            "security_risk": -1,
        },
    }
    serialization_deserialization(original_action_dict, FileEditAction)


def test_cmd_run_action_legacy_serialization():
    original_action_dict = {
        "action": "run",
        "args": {
            "blocking": False,
            "command": 'echo "Hello world"',
            "thought": "",
            "hidden": False,
            "confirmation_state": ActionConfirmationStatus.CONFIRMED,
            "keep_prompt": False,
        },
    }
    event = event_from_dict(original_action_dict)
    assert isinstance(event, Action)
    assert isinstance(event, CmdRunAction)
    assert event.command == 'echo "Hello world"'
    assert event.hidden is False
    assert not hasattr(event, "keep_prompt")
    event_dict = event_to_dict(event)
    assert "keep_prompt" not in event_dict["args"]
    assert (
        event_dict["args"]["confirmation_state"] == ActionConfirmationStatus.CONFIRMED
    )
    assert event_dict["args"]["blocking"] is False
    assert event_dict["args"]["command"] == 'echo "Hello world"'
    assert event_dict["args"]["thought"] == ""
    assert event_dict["args"]["is_input"] is False


def _create_llm_based_edit_action_dict():
    """Create test data for LLM-based edit action."""
    return {
        "action": "edit",
        "args": {
            "path": "/path/to/file.txt",
            "content": "dummy content",
            "start": 1,
            "end": -1,
            "thought": "Replacing text",
            "impl_source": "file_editor",
        },
    }


def _validate_llm_based_edit_action_event(event):
    """Validate LLM-based edit action event properties."""
    assert isinstance(event, Action)
    assert isinstance(event, FileEditAction)
    assert event.path == "/path/to/file.txt"
    assert event.thought == "Replacing text"
    assert event.impl_source == FileEditSource.FILE_EDITOR
    assert event.command == ""
    assert event.file_text is None
    assert event.old_str is None
    assert event.new_str is None
    assert event.insert_line is None
    assert event.content == "dummy content"
    assert event.start == 1
    assert event.end == -1


def _validate_llm_based_edit_action_serialization(event_dict):
    """Validate LLM-based edit action serialization."""
    assert event_dict["args"]["path"] == "/path/to/file.txt"
    assert event_dict["args"]["impl_source"] == "file_editor"
    assert event_dict["args"]["thought"] == "Replacing text"
    assert event_dict["args"]["command"] == ""
    assert event_dict["args"]["file_text"] is None
    assert event_dict["args"]["old_str"] is None
    assert event_dict["args"]["new_str"] is None
    assert event_dict["args"]["insert_line"] is None
    assert event_dict["args"]["content"] == "dummy content"
    assert event_dict["args"]["start"] == 1
    assert event_dict["args"]["end"] == -1


def test_file_llm_based_edit_action_legacy_serialization():
    """Test LLM-based edit action legacy serialization."""
    # Create test data
    original_action_dict = _create_llm_based_edit_action_dict()

    # Test deserialization
    event = event_from_dict(original_action_dict)
    _validate_llm_based_edit_action_event(event)

    # Test serialization
    event_dict = event_to_dict(event)
    _validate_llm_based_edit_action_serialization(event_dict)


def _create_file_editor_edit_action_dict():
    """Create test data for FILE_EDITOR edit action."""
    return {
        "action": "edit",
        "args": {
            "path": "/workspace/game_2048.py",
            "content": "",
            "start": 1,
            "end": -1,
            "thought": "I'll help you create a simple 2048 game in Python. I'll use the str_replace_editor to create the file.",
            "impl_source": "file_editor",
            "command": "create",
            "file_text": "New file content",
        },
    }


def _validate_file_editor_edit_action_event(event):
    """Validate FILE_EDITOR edit action event properties."""
    assert isinstance(event, Action)
    assert isinstance(event, FileEditAction)
    assert event.path == "/workspace/game_2048.py"
    assert (
        event.thought
        == "I'll help you create a simple 2048 game in Python. I'll use the str_replace_editor to create the file."
    )
    assert event.impl_source == FileEditSource.FILE_EDITOR
    assert event.command == "create"
    assert event.file_text == "New file content"
    assert event.old_str is None
    assert event.new_str is None
    assert event.insert_line is None
    assert event.content == ""
    assert event.start == 1
    assert event.end == -1


def _validate_file_editor_edit_action_serialization(event_dict):
    """Validate FILE_EDITOR edit action serialization."""
    assert event_dict["args"]["path"] == "/workspace/game_2048.py"
    assert event_dict["args"]["impl_source"] == "file_editor"
    assert (
        event_dict["args"]["thought"]
        == "I'll help you create a simple 2048 game in Python. I'll use the str_replace_editor to create the file."
    )
    assert event_dict["args"]["command"] == "create"
    assert event_dict["args"]["file_text"] == "New file content"
    assert event_dict["args"]["old_str"] is None
    assert event_dict["args"]["new_str"] is None
    assert event_dict["args"]["insert_line"] is None
    assert event_dict["args"]["content"] == ""
    assert event_dict["args"]["start"] == 1
    assert event_dict["args"]["end"] == -1


def test_file_editor_edit_action_serialization():
    """Test FILE_EDITOR edit action serialization."""
    # Create test data
    original_action_dict = _create_file_editor_edit_action_dict()

    # Test deserialization
    event = event_from_dict(original_action_dict)
    _validate_file_editor_edit_action_event(event)

    # Test serialization
    event_dict = event_to_dict(event)
    _validate_file_editor_edit_action_serialization(event_dict)


def test_agent_microagent_action_serialization_deserialization():
    original_action_dict = {
        "action": "recall",
        "args": {
            "query": "What is the capital of France?",
            "thought": "I need to find information about France",
            "recall_type": "knowledge",
        },
    }
    serialization_deserialization(original_action_dict, RecallAction)


def test_action_from_dict_normalizes_images_and_timestamp() -> None:
    action_dict = {
        "action": "message",
        "args": {
            "content": "hello",
            "images_urls": ["legacy-image"],
            "timestamp": "2024-01-02T03:04:05",
            "security_risk": ActionSecurityRisk.MEDIUM.value,
        },
    }

    action = action_from_dict(action_dict)

    assert isinstance(action, MessageAction)
    assert action.image_urls == ["legacy-image"]
    assert action.timestamp == "2024-01-02T03:04:05"
    assert action.security_risk == ActionSecurityRisk.MEDIUM


def test_action_from_dict_sets_confirmation_state_and_timeout() -> None:
    action_dict = {
        "action": "run",
        "timeout": 1.5,
        "args": {
            "command": "ls",
            "is_confirmed": ActionConfirmationStatus.AWAITING_CONFIRMATION,
            "security_risk": ActionSecurityRisk.LOW.value,
        },
    }

    action = action_from_dict(action_dict)

    assert isinstance(action, CmdRunAction)
    assert action.confirmation_state == ActionConfirmationStatus.AWAITING_CONFIRMATION
    assert action.timeout == 1.5
    assert action.security_risk == ActionSecurityRisk.LOW


def test_action_from_dict_invalid_security_risk_is_ignored() -> None:
    action_dict = {
        "action": "run",
        "args": {"command": "pwd", "security_risk": "not-a-risk"},
    }

    action = action_from_dict(action_dict)

    assert isinstance(action, CmdRunAction)
    assert action.security_risk == ActionSecurityRisk.UNKNOWN


def test_action_from_dict_raises_on_invalid_inputs() -> None:
    with pytest.raises(LLMMalformedActionError):
        action_from_dict("not a dict")  # type: ignore[arg-type]

    with pytest.raises(LLMMalformedActionError):
        action_from_dict({})

    with pytest.raises(LLMMalformedActionError):
        action_from_dict({"action": "unknown"})

    with pytest.raises(LLMMalformedActionError):
        action_from_dict({"action": "message", "args": {"unexpected": "value"}})


def test_cmd_run_action_string_representation() -> None:
    action = CmdRunAction(
        command="ls -la",
        thought="Listing files",
        is_input=True,
        hidden=True,
        cwd="/tmp",
    )

    description = str(action)
    assert "**CmdRunAction" in description
    assert "THOUGHT: Listing files" in description
    assert "COMMAND:\nls -la" in description
    assert action.message == "Running command: ls -la"