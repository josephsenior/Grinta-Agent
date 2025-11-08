import os
import shutil
import pytest
from forge.controller.state.control_flags import IterationControlFlag
from forge.controller.state.state import State
from forge.core.message import Message, TextContent
from forge.events.observation.agent import MicroagentKnowledge
from forge.microagent import BaseMicroagent
from forge.utils.prompt import ConversationInstructions, PromptManager, RepositoryInfo, RuntimeInfo


@pytest.fixture
def prompt_dir(tmp_path):
    shutil.copytree("Forge/agenthub/codeact_agent/prompts", tmp_path, dirs_exist_ok=True)
    return tmp_path


def test_prompt_manager_template_rendering(prompt_dir):
    """Test PromptManager's template rendering functionality."""
    with open(os.path.join(prompt_dir, "system_prompt.j2"), "w") as f:
        f.write("System prompt: bar")
    with open(os.path.join(prompt_dir, "user_prompt.j2"), "w") as f:
        f.write("User prompt: foo")
    with open(os.path.join(prompt_dir, "additional_info.j2"), "w") as f:
        f.write(
            "\n{% if repository_info %}\n<REPOSITORY_INFO>\nAt the user's request, repository {{ repository_info.repo_name }} has been cloned to the current working directory {{ repository_info.repo_directory }}.\n</REPOSITORY_INFO>\n{% endif %}\n"
        )
    manager = PromptManager(prompt_dir)
    assert manager.get_system_message() == "System prompt: bar"
    assert manager.get_example_user_message() == "User prompt: foo"
    manager = PromptManager(prompt_dir=prompt_dir)
    repo_info = RepositoryInfo(repo_name="owner/repo", repo_directory="/workspace/repo", branch_name="main")
    system_msg = manager.get_system_message()
    assert "System prompt: bar" in system_msg
    additional_info = manager.build_workspace_context(
        repository_info=repo_info, runtime_info=None, repo_instructions="", conversation_instructions=None
    )
    assert "<REPOSITORY_INFO>" in additional_info
    assert (
        "At the user's request, repository owner/repo has been cloned to the current working directory /workspace/repo."
        in additional_info
    )
    assert "</REPOSITORY_INFO>" in additional_info
    assert manager.get_example_user_message() == "User prompt: foo"
    os.remove(os.path.join(prompt_dir, "system_prompt.j2"))
    os.remove(os.path.join(prompt_dir, "user_prompt.j2"))
    os.remove(os.path.join(prompt_dir, "additional_info.j2"))


def test_prompt_manager_file_not_found(prompt_dir):
    """Test PromptManager behavior when a template file is not found."""
    with pytest.raises(FileNotFoundError):
        BaseMicroagent.load(os.path.join(prompt_dir, "micro", "non_existent_microagent.md"))


def test_build_microagent_info(prompt_dir):
    """Test the build_microagent_info method with the microagent_info.j2 template."""
    template_path = os.path.join(prompt_dir, "microagent_info.j2")
    if not os.path.exists(template_path):
        with open(template_path, "w", encoding='utf-8') as f:
            f.write(
                '{% for agent_info in triggered_agents %}\n<EXTRA_INFO>\nThe following information has been included based on a keyword match for "{{ agent_info.trigger }}".\nIt may or may not be relevant to the user\'s request.\n\n{{ agent_info.content }}\n</EXTRA_INFO>\n{% endfor %}\n'
            )
    manager = PromptManager(prompt_dir=prompt_dir)
    triggered_agents = [
        MicroagentKnowledge(name="test_agent1", trigger="keyword1", content="This is information from agent 1")
    ]
    result = manager.build_microagent_info(triggered_agents)
    expected = '<EXTRA_INFO>\nThe following information has been included based on a keyword match for "keyword1".\nIt may or may not be relevant to the user\'s request.\n\nThis is information from agent 1\n</EXTRA_INFO>'
    assert result.strip() == expected.strip()
    triggered_agents = [
        MicroagentKnowledge(name="test_agent1", trigger="keyword1", content="This is information from agent 1"),
        MicroagentKnowledge(name="test_agent2", trigger="keyword2", content="This is information from agent 2"),
    ]
    result = manager.build_microagent_info(triggered_agents)
    expected = '<EXTRA_INFO>\nThe following information has been included based on a keyword match for "keyword1".\nIt may or may not be relevant to the user\'s request.\n\nThis is information from agent 1\n</EXTRA_INFO>\n\n<EXTRA_INFO>\nThe following information has been included based on a keyword match for "keyword2".\nIt may or may not be relevant to the user\'s request.\n\nThis is information from agent 2\n</EXTRA_INFO>'
    assert result.strip() == expected.strip()
    result = manager.build_microagent_info([])
    assert result.strip() == ""


def test_add_turns_left_reminder(prompt_dir):
    """Test adding turns left reminder to messages."""
    manager = PromptManager(prompt_dir=prompt_dir)
    state = State(iteration_flag=IterationControlFlag(current_value=3, max_value=10, limit_increase_amount=10))
    user_message = Message(role="user", content=[TextContent(text="User content")])
    assistant_message = Message(role="assistant", content=[TextContent(text="Assistant content")])
    messages = [assistant_message, user_message]
    manager.add_turns_left_reminder(messages, state)
    assert len(user_message.content) == 2
    assert "ENVIRONMENT REMINDER: You have 7 turns left to complete the task." in user_message.content[1].text


def test_build_workspace_context_with_repo_and_runtime(prompt_dir):
    """Test building additional info with repository and runtime information."""
    with open(os.path.join(prompt_dir, "additional_info.j2"), "w") as f:
        f.write(
            "\n{% if repository_info %}\n<REPOSITORY_INFO>\nAt the user's request, repository {{ repository_info.repo_name }} has been cloned to directory {{ repository_info.repo_directory }}.\n</REPOSITORY_INFO>\n{% endif %}\n\n{% if repository_instructions %}\n<REPOSITORY_INSTRUCTIONS>\n{{ repository_instructions }}\n</REPOSITORY_INSTRUCTIONS>\n{% endif %}\n\n{% if runtime_info and (runtime_info.available_hosts or runtime_info.additional_agent_instructions) -%}\n<RUNTIME_INFORMATION>\n{% if runtime_info.available_hosts %}\nThe user has access to the following hosts for accessing a web application,\neach of which has a corresponding port:\n{% for host, port in runtime_info.available_hosts.items() %}\n* {{ host }} (port {{ port }})\n{% endfor %}\n{% endif %}\n\n{% if runtime_info.additional_agent_instructions %}\n{{ runtime_info.additional_agent_instructions }}\n{% endif %}\n\nToday's date is {{ runtime_info.date }}\n</RUNTIME_INFORMATION>\n{% if conversation_instructions.content %}\n<CONVERSATION_INSTRUCTIONS>\n{{ conversation_instructions.content }}\n</CONVERSATION_INSTRUCTIONS>\n{% endif %}\n{% endif %}\n"
        )
    manager = PromptManager(prompt_dir=prompt_dir)
    repo_info = RepositoryInfo(repo_name="owner/repo", repo_directory="/workspace/repo", branch_name="main")
    runtime_info = RuntimeInfo(
        date="02/12/1232",
        available_hosts={"example.com": 8080},
        additional_agent_instructions="You know everything about this runtime.",
        working_dir="/workspace",
    )
    repo_instructions = "This repository contains important code."
    conversation_instructions = ConversationInstructions(content="additional context")
    result = manager.build_workspace_context(
        repository_info=repo_info,
        runtime_info=runtime_info,
        repo_instructions=repo_instructions,
        conversation_instructions=conversation_instructions,
    )
    assert "<REPOSITORY_INFO>" in result
    assert "owner/repo" in result
    assert "/workspace/repo" in result
    assert "<REPOSITORY_INSTRUCTIONS>" in result
    assert "This repository contains important code." in result
    assert "<RUNTIME_INFORMATION>" in result
    assert "example.com (port 8080)" in result
    assert "You know everything about this runtime." in result
    assert "Today's date is 02/12/1232" in result
    assert "additional context" in result
    os.remove(os.path.join(prompt_dir, "additional_info.j2"))


def test_prompt_manager_initialization_error():
    """Test that PromptManager raises an error if the prompt directory is not set."""
    with pytest.raises(ValueError, match="Prompt directory is not set"):
        PromptManager(None)


def test_prompt_manager_custom_system_prompt_filename(prompt_dir):
    """Test that PromptManager can use a custom system prompt filename."""
    with open(os.path.join(prompt_dir, "custom_system.j2"), "w") as f:
        f.write("Custom system prompt: {{ custom_var }}")
    with open(os.path.join(prompt_dir, "system_prompt.j2"), "w") as f:
        f.write("Default system prompt")
    manager = PromptManager(prompt_dir=prompt_dir, system_prompt_filename="custom_system.j2")
    system_msg = manager.get_system_message()
    assert "Custom system prompt:" in system_msg
    manager_default = PromptManager(prompt_dir=prompt_dir)
    default_msg = manager_default.get_system_message()
    assert "Default system prompt" in default_msg
    os.remove(os.path.join(prompt_dir, "custom_system.j2"))
    os.remove(os.path.join(prompt_dir, "system_prompt.j2"))


def test_prompt_manager_custom_system_prompt_filename_not_found(prompt_dir):
    """Test that PromptManager raises an error if custom system prompt file is not found."""
    with pytest.raises(FileNotFoundError, match="Prompt file .*[/\\\\]non_existent\\.j2 not found"):
        PromptManager(prompt_dir=prompt_dir, system_prompt_filename="non_existent.j2")


def test_jinja2_template_inheritance(prompt_dir):
    """Test that PromptManager._load_template works with Jinja2 template inclusion.

    This test demonstrates that we can use {% include %} to import a base system_prompt.j2
    into other templates without defining any blocks in the base template, and that
    PromptManager._load_template can load these templates correctly.
    """
    with open(os.path.join(prompt_dir, "system_prompt.j2"), "w") as f:
        f.write(
            "You are Forge agent, a helpful AI assistant that can interact with a computer to solve tasks.\n\n<ROLE>\nYour primary role is to assist users by executing commands, modifying code, and solving technical problems effectively.\n</ROLE>\n"
        )
    with open(os.path.join(prompt_dir, "system_prompt_interactive.j2"), "w") as f:
        f.write(
            '{% include "system_prompt.j2" %}\n\n<INTERACTION_RULES>\n1. Always respond in a friendly, helpful manner\n2. Ask clarifying questions when needed\n3. Provide step-by-step explanations\n</INTERACTION_RULES>\n'
        )
    with open(os.path.join(prompt_dir, "system_prompt_long_horizon.j2"), "w") as f:
        f.write(
            '{% include "system_prompt.j2" %}\n\n<TASK_MANAGEMENT>\n1. Break down complex tasks into smaller steps\n2. Track progress through a TODO list\n3. Focus on one task at a time\n</TASK_MANAGEMENT>\n'
        )
    base_manager = PromptManager(prompt_dir=prompt_dir)
    base_template = base_manager._load_template("system_prompt.j2")
    base_msg = base_template.render().strip()
    assert "You are Forge agent" in base_msg
    assert "<ROLE>" in base_msg
    assert "<INTERACTION_RULES>" not in base_msg
    assert "<TASK_MANAGEMENT>" not in base_msg
    interactive_manager = PromptManager(prompt_dir=prompt_dir, system_prompt_filename="system_prompt_interactive.j2")
    interactive_template = interactive_manager._load_template("system_prompt_interactive.j2")
    interactive_msg = interactive_template.render().strip()
    assert "You are Forge agent" in interactive_msg
    assert "<ROLE>" in interactive_msg
    assert "<INTERACTION_RULES>" in interactive_msg
    assert "Ask clarifying questions when needed" in interactive_msg
    assert "<TASK_MANAGEMENT>" not in interactive_msg
    long_horizon_manager = PromptManager(prompt_dir=prompt_dir, system_prompt_filename="system_prompt_long_horizon.j2")
    long_horizon_template = long_horizon_manager._load_template("system_prompt_long_horizon.j2")
    long_horizon_msg = long_horizon_template.render().strip()
    assert "You are Forge agent" in long_horizon_msg
    assert "<ROLE>" in long_horizon_msg
    assert "<INTERACTION_RULES>" not in long_horizon_msg
    assert "<TASK_MANAGEMENT>" in long_horizon_msg
    assert "Track progress through a TODO list" in long_horizon_msg
    os.remove(os.path.join(prompt_dir, "system_prompt.j2"))
    os.remove(os.path.join(prompt_dir, "system_prompt_interactive.j2"))
    os.remove(os.path.join(prompt_dir, "system_prompt_long_horizon.j2"))


def _create_test_prompt_template(prompt_dir):
    """Create test prompt template file."""
    template_content = """You are Forge agent.

{% if cli_mode %}
<CLI_MODE>
You are running in CLI mode. Direct file system access is available.
</CLI_MODE>
{% else %}
<SANDBOX_MODE>
You are running inside sandbox. Container-scoped operations are available.
</SANDBOX_MODE>
{% endif %}

<COMMON_INSTRUCTIONS>
Always be helpful and follow user instructions.
</COMMON_INSTRUCTIONS>"""

    template_path = os.path.join(prompt_dir, "system_prompt.j2")
    with open(template_path, "w", encoding='utf-8') as f:
        f.write(template_content)
    return template_path


def _validate_cli_message(cli_message):
    """Validate CLI mode message content."""
    assert "You are Forge agent" in cli_message
    assert "<CLI_MODE>" in cli_message
    assert "CLI mode" in cli_message
    assert "Direct file system access" in cli_message
    assert "<SANDBOX_MODE>" not in cli_message
    assert "inside sandbox" not in cli_message
    assert "<COMMON_INSTRUCTIONS>" in cli_message


def _validate_sandbox_message(sandbox_message):
    """Validate sandbox mode message content."""
    assert "You are Forge agent" in sandbox_message
    assert "<SANDBOX_MODE>" in sandbox_message
    assert "inside sandbox" in sandbox_message
    assert "Container-scoped operations" in sandbox_message
    assert "<CLI_MODE>" not in sandbox_message
    assert "CLI mode" not in sandbox_message
    assert "<COMMON_INSTRUCTIONS>" in sandbox_message


def _validate_default_message(default_message):
    """Validate default message content."""
    assert "You are Forge agent" in default_message
    assert "<COMMON_INSTRUCTIONS>" in default_message
    assert "<SANDBOX_MODE>" in default_message
    assert "<CLI_MODE>" not in default_message


def _validate_mixed_message(mixed_message):
    """Validate mixed parameters message content."""
    assert "<CLI_MODE>" in mixed_message
    assert "<COMMON_INSTRUCTIONS>" in mixed_message


def _validate_message_differences(cli_message, sandbox_message):
    """Validate that CLI and sandbox messages are different."""
    assert cli_message != sandbox_message
    assert len(cli_message) != len(sandbox_message)


def test_prompt_manager_cli_mode_context(prompt_dir):
    """Test that PromptManager.get_system_message() supports cli_mode context parameter."""
    # Create test template
    template_path = _create_test_prompt_template(prompt_dir)

    try:
        # Setup manager
        manager = PromptManager(prompt_dir)

        # Test CLI mode
        cli_message = manager.get_system_message(cli_mode=True)
        _validate_cli_message(cli_message)

        # Test sandbox mode
        sandbox_message = manager.get_system_message(cli_mode=False)
        _validate_sandbox_message(sandbox_message)

        # Test default mode
        default_message = manager.get_system_message()
        _validate_default_message(default_message)

        # Test mixed parameters
        mixed_message = manager.get_system_message(cli_mode=True, custom_var="test_value")
        _validate_mixed_message(mixed_message)

        # Validate differences
        _validate_message_differences(cli_message, sandbox_message)
    finally:
        # Cleanup
        os.remove(template_path)
