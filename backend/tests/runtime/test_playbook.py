"""Tests for playbook loading in runtime."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from conftest import _close_test_runtime, _load_runtime
from backend.core.config import MCPConfig
from backend.core.config.mcp_config import MCPStdioServerConfig
from backend.mcp.utils import add_mcp_tools_to_agent
from backend.instruction.playbook import (
    BasePlaybook,
    KnowledgePlaybook,
    RepoPlaybook,
    TaskPlaybook,
)
from backend.instruction.types import PlaybookType


def _create_test_playbooks(test_dir: str):
    """Create test playbook files in the given directory."""
    playbooks_dir = Path(test_dir) / ".Forge" / "playbooks"
    playbooks_dir.mkdir(parents=True, exist_ok=True)
    knowledge_dir = playbooks_dir / "knowledge"
    knowledge_dir.mkdir(exist_ok=True)
    knowledge_agent = "---\nname: test_knowledge_agent\ntype: knowledge\nversion: 1.0.0\nagent: Orchestrator\ntriggers:\n  - test\n  - pytest\n---\n\n# Test Guidelines\n\nTesting best practices and guidelines.\n"
    (knowledge_dir / "knowledge.md").write_text(knowledge_agent)
    repo_agent = "---\nname: test_repo_agent\ntype: repo\nversion: 1.0.0\nagent: Orchestrator\n---\n\n# Test Repository Agent\n\nRepository-specific test instructions.\n"
    (playbooks_dir / "repo.md").write_text(repo_agent)
    legacy_instructions = (
        "# Legacy Instructions\n\nThese are legacy repository instructions.\n"
    )
    (Path(test_dir) / ".FORGE_instructions").write_text(legacy_instructions)


def test_load_playbooks_with_trailing_slashes(temp_dir, runtime_cls, run_as_Forge):
    """Test loading playbooks when directory paths have trailing slashes."""
    _create_test_playbooks(temp_dir)
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        loaded_agents = runtime.get_playbooks_from_selected_repo(None)
        knowledge_agents = [
            a for a in loaded_agents if isinstance(a, KnowledgePlaybook)
        ]
        repo_agents = [a for a in loaded_agents if isinstance(a, RepoPlaybook)]
        assert len(knowledge_agents) == 1
        agent = knowledge_agents[0]
        assert agent.name == "knowledge/knowledge"
        assert "test" in agent.triggers
        assert "pytest" in agent.triggers
        assert len(repo_agents) == 2
        repo_names = {a.name for a in repo_agents}
        assert "repo" in repo_names
        assert "repo_legacy" in repo_names
    finally:
        _close_test_runtime(runtime)


def test_load_playbooks_with_selected_repo(temp_dir, runtime_cls, run_as_Forge):
    """Test loading playbooks from a selected repository."""
    repo_dir = Path(temp_dir) / "forge"
    repo_dir.mkdir(parents=True)
    _create_test_playbooks(str(repo_dir))
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        loaded_agents = runtime.get_playbooks_from_selected_repo("Forge/Forge")
        knowledge_agents = [
            a for a in loaded_agents if isinstance(a, KnowledgePlaybook)
        ]
        repo_agents = [a for a in loaded_agents if isinstance(a, RepoPlaybook)]
        assert len(knowledge_agents) == 1
        agent = knowledge_agents[0]
        assert agent.name == "knowledge/knowledge"
        assert "test" in agent.triggers
        assert "pytest" in agent.triggers
        assert len(repo_agents) == 2
        repo_names = {a.name for a in repo_agents}
        assert "repo" in repo_names
        assert "repo_legacy" in repo_names
    finally:
        _close_test_runtime(runtime)


def test_load_playbooks_with_missing_files(temp_dir, runtime_cls, run_as_Forge):
    """Test loading playbooks when some files are missing."""
    playbooks_dir = Path(temp_dir) / ".Forge" / "playbooks"
    playbooks_dir.mkdir(parents=True, exist_ok=True)
    repo_agent = "---\nname: test_repo_agent\ntype: repo\nversion: 1.0.0\nagent: Orchestrator\n---\n\n# Test Repository Agent\n\nRepository-specific test instructions.\n"
    (playbooks_dir / "repo.md").write_text(repo_agent)
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        loaded_agents = runtime.get_playbooks_from_selected_repo(None)
        knowledge_agents = [
            a for a in loaded_agents if isinstance(a, KnowledgePlaybook)
        ]
        repo_agents = [a for a in loaded_agents if isinstance(a, RepoPlaybook)]
        assert not knowledge_agents
        assert len(repo_agents) == 1
        agent = repo_agents[0]
        assert agent.name == "repo"
    finally:
        _close_test_runtime(runtime)


def test_task_playbook_creation():
    """Test that a TaskPlaybook is created correctly."""
    content = '---\nname: test_task\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ntriggers:\n- /test_task\ninputs:\n  - name: TEST_VAR\n    description: "Test variable"\n---\n\nThis is a test task playbook with a variable: ${test_var}.\n'
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, TaskPlaybook)
        assert agent.type == PlaybookType.TASK
        assert agent.name == "test_task"
        assert "/test_task" in agent.triggers
        assert "If the user didn't provide any of these variables" in agent.content


def test_task_playbook_variable_extraction():
    """Test that variables are correctly extracted from the content."""
    content = '---\nname: test_task\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ntriggers:\n- /test_task\ninputs:\n  - name: var1\n    description: "Variable 1"\n---\n\nThis is a test with variables: ${var1}, ${var2}, and ${var3}.\n'
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, TaskPlaybook)
        variables = agent.extract_variables(agent.content)
        assert set(variables) == {"var1", "var2", "var3"}
        assert agent.requires_user_input()


def test_knowledge_playbook_no_prompt():
    """Test that a regular KnowledgePlaybook doesn't get the prompt."""
    content = "---\nname: test_knowledge\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ntriggers:\n- test_knowledge\n---\n\nThis is a test knowledge playbook.\n"
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, KnowledgePlaybook)
        assert agent.type == PlaybookType.KNOWLEDGE
        assert "If the user didn't provide any of these variables" not in agent.content


def test_task_playbook_trigger_addition():
    """Test that a trigger is added if not present."""
    content = '---\nname: test_task\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ninputs:\n  - name: TEST_VAR\n    description: "Test variable"\n---\n\nThis is a test task playbook.\n'
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, TaskPlaybook)
        assert "/test_task" in agent.triggers


def test_task_playbook_no_duplicate_trigger():
    """Test that a trigger is not duplicated if already present."""
    content = '---\nname: test_task\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ntriggers:\n- /test_task\n- another_trigger\ninputs:\n  - name: TEST_VAR\n    description: "Test variable"\n---\n\nThis is a test task playbook.\n'
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, TaskPlaybook)
        assert agent.triggers.count("/test_task") == 1
        assert len(agent.triggers) == 2
        assert "another_trigger" in agent.triggers
        assert "/test_task" in agent.triggers


def test_task_playbook_match_trigger():
    """Test that a task playbook matches its trigger correctly."""
    content = '---\nname: test_task\nversion: 1.0.0\nauthor: Forge\nagent: Orchestrator\ntriggers:\n- /test_task\ninputs:\n  - name: TEST_VAR\n    description: "Test variable"\n---\n\nThis is a test task playbook.\n'
    with tempfile.NamedTemporaryFile(suffix=".md") as f:
        f.write(content.encode())
        f.flush()
        agent = BasePlaybook.load(f.name)
        assert isinstance(agent, TaskPlaybook)
        assert agent.match_trigger("/test_task") == "/test_task"
        assert agent.match_trigger("  /test_task  ") == "/test_task"
        assert agent.match_trigger("This contains /test_task") == "/test_task"
        assert agent.match_trigger("/other_task") is None


def test_default_tools_playbook_exists():
    """Test that the default-tools playbook exists in the global playbooks directory."""
    import backend

    project_root = os.path.dirname(backend.__file__)
    parent_dir = os.path.dirname(project_root)
    playbooks_dir = os.path.join(parent_dir, "playbooks")
    default_tools_path = os.path.join(playbooks_dir, "default-tools.md")
    assert os.path.exists(default_tools_path), (
        f"default-tools.md not found at {default_tools_path}"
    )
    with open(default_tools_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "type: repo" in content, "default-tools.md should be a repo playbook"
    assert 'name: "fetch"' in content, "default-tools.md should have a fetch tool"
    assert 'command: "uvx"' in content, "default-tools.md should use uvx command"
    assert 'args: ["mcp-server-fetch"]' in content, (
        "default-tools.md should use mcp-server-fetch"
    )


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="MCP functionality is disabled on Windows"
)
async def test_add_mcp_tools_from_playbooks():
    """Test that add_mcp_tools_to_agent adds tools from playbooks."""
    from backend.runtime.drivers.action_execution.action_execution_client import (
        ActionExecutionClient,
    )

    mock_agent = MagicMock()
    mock_runtime = MagicMock(spec=ActionExecutionClient)
    mock_memory = MagicMock()
    mock_stdio_server = MCPStdioServerConfig(
        name="test-tool", command="test-command", args=["test-arg1", "test-arg2"]
    )
    mock_playbook_mcp_config = MCPConfig(stdio_servers=[mock_stdio_server])
    mock_memory.get_playbook_mcp_tools.return_value = [mock_playbook_mcp_config]
    mock_runtime.runtime_initialized = True
    mock_runtime.get_mcp_config.return_value = mock_playbook_mcp_config
    mock_tool = {
        "type": "function",
        "function": {
            "name": "test-tool",
            "description": "Test tool description",
            "parameters": {},
        },
    }
    with patch(
        "backend.mcp.utils.fetch_mcp_tools_from_config",
        new=AsyncMock(return_value=[mock_tool]),
    ):
        await add_mcp_tools_to_agent(mock_agent, mock_runtime, mock_memory)
        mock_memory.get_playbook_mcp_tools.assert_called_once()
        mock_runtime.get_mcp_config.assert_called_once()
        args, kwargs = mock_runtime.get_mcp_config.call_args
        assert len(args) == 1
        assert len(args[0]) == 1
        assert args[0][0].name == "test-tool"
        mock_agent.set_mcp_tools.assert_called_once_with([mock_tool])

