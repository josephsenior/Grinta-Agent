from forge.core.schema.observation import ObservationType
from forge.events.action.files import FileEditSource
from forge.events.event import RecallType
from forge.events.observation import (
    CmdOutputMetadata,
    CmdOutputObservation,
    FileEditObservation,
    Observation,
    RecallObservation,
)
from forge.events.observation.agent import MicroagentKnowledge
from forge.events.observation.commands import MAX_CMD_OUTPUT_SIZE
from forge.events.serialization import event_from_dict, event_to_dict, event_to_trajectory
from forge.events.serialization.observation import observation_from_dict


def serialization_deserialization(original_observation_dict, cls, max_message_chars: int = 10000):
    observation_instance = event_from_dict(original_observation_dict)
    assert isinstance(
        observation_instance, Observation
    ), "The observation instance should be an instance of Observation."
    assert isinstance(observation_instance, cls), f"The observation instance should be an instance of {cls}."
    serialized_observation_dict = event_to_dict(observation_instance)
    serialized_observation_trajectory = event_to_trajectory(observation_instance)
    assert (
        serialized_observation_dict == original_observation_dict
    ), "The serialized observation should match the original observation dict."
    assert (
        serialized_observation_trajectory == original_observation_dict
    ), "The serialized observation trajectory should match the original observation dict."


def test_observation_event_props_serialization_deserialization():
    original_observation_dict = {
        "id": 42,
        "source": "agent",
        "timestamp": "2021-08-01T12:00:00",
        "observation": "run",
        "message": "Command `ls -l` executed with exit code 0.",
        "extras": {
            "command": "ls -l",
            "hidden": False,
            "metadata": {
                "exit_code": 0,
                "hostname": None,
                "pid": -1,
                "prefix": "",
                "py_interpreter_path": None,
                "suffix": "",
                "username": None,
                "working_dir": None,
            },
        },
        "content": "foo.txt",
        "success": True,
    }
    serialization_deserialization(original_observation_dict, CmdOutputObservation)


def test_command_output_observation_serialization_deserialization():
    original_observation_dict = {
        "observation": "run",
        "extras": {
            "command": "ls -l",
            "hidden": False,
            "metadata": {
                "exit_code": 0,
                "hostname": None,
                "pid": -1,
                "prefix": "",
                "py_interpreter_path": None,
                "suffix": "",
                "username": None,
                "working_dir": None,
            },
        },
        "message": "Command `ls -l` executed with exit code 0.",
        "content": "foo.txt",
        "success": True,
    }
    serialization_deserialization(original_observation_dict, CmdOutputObservation)


def test_success_field_serialization():
    obs = CmdOutputObservation(content="Command succeeded", command="ls -l", metadata=CmdOutputMetadata(exit_code=0))
    serialized = event_to_dict(obs)
    assert serialized["success"] is True
    obs = CmdOutputObservation(
        content="No such file or directory", command="ls -l", metadata=CmdOutputMetadata(exit_code=1)
    )
    serialized = event_to_dict(obs)
    assert serialized["success"] is False


def test_cmd_output_truncation():
    """Test that large command outputs are truncated during initialization."""
    large_content = "a" * 60000
    obs = CmdOutputObservation(content=large_content, command="ls -R", metadata=CmdOutputMetadata(exit_code=0))
    assert len(obs.content) < 60000
    truncation_msg = "[... Observation truncated due to length ...]"
    assert truncation_msg in obs.content
    margin = int(MAX_CMD_OUTPUT_SIZE * 0.01)
    assert len(obs.content) <= MAX_CMD_OUTPUT_SIZE + margin
    half_size = MAX_CMD_OUTPUT_SIZE // 2
    assert obs.content.startswith("a" * half_size)
    assert obs.content.endswith("a" * half_size)


def test_cmd_output_no_truncation():
    """Test that small command outputs are not truncated."""
    small_content = "a" * 1000
    obs = CmdOutputObservation(content=small_content, command="ls", metadata=CmdOutputMetadata(exit_code=0))
    assert len(obs.content) == 1000
    assert obs.content == small_content


def test_legacy_serialization():
    original_observation_dict = {
        "id": 42,
        "source": "agent",
        "timestamp": "2021-08-01T12:00:00",
        "observation": "run",
        "message": "Command `ls -l` executed with exit code 0.",
        "extras": {"command": "ls -l", "hidden": False, "exit_code": 0, "command_id": 3},
        "content": "foo.txt",
        "success": True,
    }
    event = event_from_dict(original_observation_dict)
    assert isinstance(event, Observation)
    assert isinstance(event, CmdOutputObservation)
    assert event.metadata.exit_code == 0
    assert event.success is True
    assert event.command == "ls -l"
    assert event.hidden is False
    event_dict = event_to_dict(event)
    assert event_dict["success"] is True
    assert event_dict["extras"]["metadata"]["exit_code"] == 0
    assert event_dict["extras"]["metadata"]["pid"] == 3
    assert event_dict["extras"]["command"] == "ls -l"
    assert event_dict["extras"]["hidden"] is False


def test_file_edit_observation_serialization():
    original_observation_dict = {
        "observation": "edit",
        "extras": {
            "_diff_cache": None,
            "impl_source": FileEditSource.LLM_BASED_EDIT,
            "new_content": None,
            "old_content": None,
            "path": "",
            "prev_exist": False,
            "diff": None,
        },
        "message": "I edited the file .",
        "content": "[Existing file /path/to/file.txt is edited with 1 changes.]",
    }
    serialization_deserialization(original_observation_dict, FileEditObservation)


def test_file_edit_observation_new_file_serialization():
    original_observation_dict = {
        "observation": "edit",
        "content": "[New file /path/to/newfile.txt is created with the provided content.]",
        "extras": {
            "_diff_cache": None,
            "impl_source": FileEditSource.LLM_BASED_EDIT,
            "new_content": None,
            "old_content": None,
            "path": "",
            "prev_exist": False,
            "diff": None,
        },
        "message": "I edited the file .",
    }
    serialization_deserialization(original_observation_dict, FileEditObservation)


def test_file_edit_observation_oh_aci_serialization():
    original_observation_dict = {
        "observation": "edit",
        "content": "The file /path/to/file.txt is edited with the provided content.",
        "extras": {
            "_diff_cache": None,
            "impl_source": FileEditSource.LLM_BASED_EDIT,
            "new_content": None,
            "old_content": None,
            "path": "",
            "prev_exist": False,
            "diff": None,
        },
        "message": "I edited the file .",
    }
    serialization_deserialization(original_observation_dict, FileEditObservation)


def test_file_edit_observation_legacy_serialization():
    original_observation_dict = {
        "observation": "edit",
        "content": "content",
        "extras": {
            "path": "/workspace/game_2048.py",
            "prev_exist": False,
            "old_content": None,
            "new_content": "new content",
            "impl_source": "oh_aci",
            "formatted_output_and_error": "File created successfully at: /workspace/game_2048.py",
        },
    }
    event = event_from_dict(original_observation_dict)
    assert isinstance(event, Observation)
    assert isinstance(event, FileEditObservation)
    assert event.impl_source == FileEditSource.OH_ACI
    assert event.path == "/workspace/game_2048.py"
    assert event.prev_exist is False
    assert event.old_content is None
    assert event.new_content == "new content"
    assert not hasattr(event, "formatted_output_and_error")
    event_dict = event_to_dict(event)
    assert event_dict["extras"]["impl_source"] == "oh_aci"
    assert event_dict["extras"]["path"] == "/workspace/game_2048.py"
    assert event_dict["extras"]["prev_exist"] is False
    assert event_dict["extras"]["old_content"] is None
    assert event_dict["extras"]["new_content"] == "new content"
    assert "formatted_output_and_error" not in event_dict["extras"]


def test_microagent_observation_serialization():
    original_observation_dict = {
        "observation": "recall",
        "content": "",
        "message": "Added workspace context",
        "extras": {
            "recall_type": "workspace_context",
            "repo_name": "some_repo_name",
            "repo_directory": "some_repo_directory",
            "repo_branch": "",
            "working_dir": "",
            "runtime_hosts": {"host1": 8080, "host2": 8081},
            "repo_instructions": "complex_repo_instructions",
            "additional_agent_instructions": "You know it all about this runtime",
            "custom_secrets_descriptions": {"SECRET": "CUSTOM"},
            "date": "04/12/1023",
            "microagent_knowledge": [],
            "conversation_instructions": "additional_context",
        },
    }
    serialization_deserialization(original_observation_dict, RecallObservation)


def test_microagent_observation_microagent_knowledge_serialization():
    original_observation_dict = {
        "observation": "recall",
        "content": "",
        "message": "Added microagent knowledge",
        "extras": {
            "recall_type": "knowledge",
            "repo_name": "",
            "repo_directory": "",
            "repo_branch": "",
            "repo_instructions": "",
            "runtime_hosts": {},
            "working_dir": "",
            "additional_agent_instructions": "",
            "custom_secrets_descriptions": {},
            "conversation_instructions": "additional_context",
            "date": "",
            "microagent_knowledge": [
                {"name": "microagent1", "trigger": "trigger1", "content": "content1"},
                {"name": "microagent2", "trigger": "trigger2", "content": "content2"},
            ],
        },
    }
    serialization_deserialization(original_observation_dict, RecallObservation)


def test_microagent_observation_knowledge_microagent_serialization():
    """Test serialization of a RecallObservation with KNOWLEDGE_MICROAGENT type."""
    original = RecallObservation(
        content="Knowledge microagent information",
        recall_type=RecallType.KNOWLEDGE,
        repo_branch="",
        microagent_knowledge=[
            MicroagentKnowledge(
                name="python_best_practices",
                trigger="python",
                content="Always use virtual environments for Python projects.",
            ),
            MicroagentKnowledge(
                name="git_workflow", trigger="git", content="Create a new branch for each feature or bugfix."
            ),
        ],
    )
    serialized = event_to_dict(original)
    assert serialized["observation"] == ObservationType.RECALL
    assert serialized["content"] == "Knowledge microagent information"
    assert serialized["extras"]["recall_type"] == RecallType.KNOWLEDGE.value
    assert len(serialized["extras"]["microagent_knowledge"]) == 2
    assert serialized["extras"]["microagent_knowledge"][0]["trigger"] == "python"
    deserialized = observation_from_dict(serialized)
    assert deserialized.recall_type == RecallType.KNOWLEDGE
    assert deserialized.microagent_knowledge == original.microagent_knowledge
    assert deserialized.content == original.content
    assert deserialized.repo_name == ""
    assert deserialized.repo_directory == ""
    assert deserialized.repo_instructions == ""
    assert deserialized.runtime_hosts == {}


def test_microagent_observation_environment_serialization():
    """Test serialization of a RecallObservation with ENVIRONMENT type."""
    original = RecallObservation(
        content="Environment information",
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="forge",
        repo_directory="/workspace/Forge",
        repo_branch="main",
        repo_instructions="Follow the project's coding style guide.",
        runtime_hosts={"127.0.0.1": 8080, "localhost": 5000},
        additional_agent_instructions="You know it all about this runtime",
    )
    serialized = event_to_dict(original)
    assert serialized["observation"] == ObservationType.RECALL
    assert serialized["content"] == "Environment information"
    assert serialized["extras"]["recall_type"] == RecallType.WORKSPACE_CONTEXT.value
    assert serialized["extras"]["repo_name"] == "forge"
    assert serialized["extras"]["runtime_hosts"] == {"127.0.0.1": 8080, "localhost": 5000}
    assert serialized["extras"]["additional_agent_instructions"] == "You know it all about this runtime"
    deserialized = observation_from_dict(serialized)
    assert deserialized.recall_type == RecallType.WORKSPACE_CONTEXT
    assert deserialized.repo_name == original.repo_name
    assert deserialized.repo_directory == original.repo_directory
    assert deserialized.repo_instructions == original.repo_instructions
    assert deserialized.runtime_hosts == original.runtime_hosts
    assert deserialized.additional_agent_instructions == original.additional_agent_instructions
    assert deserialized.microagent_knowledge == []


def test_microagent_observation_combined_serialization():
    """Test serialization of a RecallObservation with both types of information."""
    original = RecallObservation(
        content="Combined information",
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="forge",
        repo_directory="/workspace/Forge",
        repo_branch="main",
        repo_instructions="Follow the project's coding style guide.",
        runtime_hosts={"127.0.0.1": 8080},
        additional_agent_instructions="You know it all about this runtime",
        microagent_knowledge=[
            MicroagentKnowledge(
                name="python_best_practices",
                trigger="python",
                content="Always use virtual environments for Python projects.",
            )
        ],
    )
    serialized = event_to_dict(original)
    assert serialized["extras"]["recall_type"] == RecallType.WORKSPACE_CONTEXT.value
    assert serialized["extras"]["repo_name"] == "forge"
    assert serialized["extras"]["microagent_knowledge"][0]["name"] == "python_best_practices"
    assert serialized["extras"]["additional_agent_instructions"] == "You know it all about this runtime"
    deserialized = observation_from_dict(serialized)
    assert deserialized.recall_type == RecallType.WORKSPACE_CONTEXT
    assert deserialized.repo_name == original.repo_name
    assert deserialized.repo_directory == original.repo_directory
    assert deserialized.repo_instructions == original.repo_instructions
    assert deserialized.runtime_hosts == original.runtime_hosts
    assert deserialized.additional_agent_instructions == original.additional_agent_instructions
    assert deserialized.microagent_knowledge == original.microagent_knowledge
