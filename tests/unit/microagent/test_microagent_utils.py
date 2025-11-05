"""Tests for the microagent system."""

import tempfile
from pathlib import Path
import pytest
from openhands.microagent import (
    BaseMicroagent,
    KnowledgeMicroagent,
    MicroagentMetadata,
    MicroagentType,
    RepoMicroagent,
    load_microagents_from_dir,
)

CONTENT = "# dummy header\ndummy content\n## dummy subheader\ndummy subcontent\n"


def test_legacy_micro_agent_load(tmp_path):
    """Test loading of legacy microagents."""
    legacy_file = tmp_path / ".openhands_instructions"
    legacy_file.write_text(CONTENT)
    micro_agent = BaseMicroagent.load(legacy_file, tmp_path)
    assert isinstance(micro_agent, RepoMicroagent)
    assert micro_agent.name == "repo_legacy"
    assert micro_agent.content == CONTENT
    assert micro_agent.type == MicroagentType.REPO_KNOWLEDGE


@pytest.fixture
def temp_microagents_dir():
    """Create a temporary directory with test microagents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        knowledge_agent = "---\n# type: knowledge\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - test\n  - pytest\n---\n\n# Test Guidelines\n\nTesting best practices and guidelines.\n"
        (root / "knowledge.md").write_text(knowledge_agent)
        repo_agent = "---\n# type: repo\nversion: 1.0.0\nagent: CodeActAgent\n---\n\n# Test Repository Agent\n\nRepository-specific test instructions.\n"
        (root / "repo.md").write_text(repo_agent)
        yield root


def test_knowledge_agent():
    """Test knowledge agent functionality."""
    agent = KnowledgeMicroagent(
        name="test",
        content="Test content",
        metadata=MicroagentMetadata(name="test", triggers=["test", "pytest"]),
        source="test.md",
        type=MicroagentType.KNOWLEDGE,
    )
    assert agent.match_trigger("running a test") == "test"
    assert agent.match_trigger("using pytest") == "test"
    assert agent.match_trigger("no match here") is None
    assert agent.triggers == ["test", "pytest"]


def test_load_microagents(temp_microagents_dir):
    """Test loading microagents from directory."""
    repo_agents, knowledge_agents = load_microagents_from_dir(temp_microagents_dir)
    assert len(knowledge_agents) == 1
    agent_k = knowledge_agents["knowledge"]
    assert isinstance(agent_k, KnowledgeMicroagent)
    assert agent_k.type == MicroagentType.KNOWLEDGE
    assert "test" in agent_k.triggers
    assert len(repo_agents) == 1
    agent_r = repo_agents["repo"]
    assert isinstance(agent_r, RepoMicroagent)
    assert agent_r.type == MicroagentType.REPO_KNOWLEDGE


def test_load_microagents_with_nested_dirs(temp_microagents_dir):
    """Test loading microagents from nested directories."""
    nested_dir = temp_microagents_dir / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    nested_agent = "---\n# type: knowledge\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - nested\n---\n\n# Nested Test Guidelines\n\nTesting nested directory loading.\n"
    (nested_dir / "nested.md").write_text(nested_agent)
    repo_agents, knowledge_agents = load_microagents_from_dir(temp_microagents_dir)
    assert len(knowledge_agents) == 2
    agent_n = knowledge_agents["nested/dir/nested"]
    assert isinstance(agent_n, KnowledgeMicroagent)
    assert agent_n.type == MicroagentType.KNOWLEDGE
    assert "nested" in agent_n.triggers


def test_load_microagents_with_trailing_slashes(temp_microagents_dir):
    """Test loading microagents when directory paths have trailing slashes."""
    knowledge_dir = temp_microagents_dir / "test_knowledge/"
    knowledge_dir.mkdir(exist_ok=True)
    knowledge_agent = "---\n# type: knowledge\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - trailing\n---\n\n# Trailing Slash Test\n\nTesting loading with trailing slashes.\n"
    (knowledge_dir / "trailing.md").write_text(knowledge_agent)
    repo_agents, knowledge_agents = load_microagents_from_dir(f"{str(temp_microagents_dir)}/")
    assert len(knowledge_agents) == 2
    agent_t = knowledge_agents["test_knowledge/trailing"]
    assert isinstance(agent_t, KnowledgeMicroagent)
    assert agent_t.type == MicroagentType.KNOWLEDGE
    assert "trailing" in agent_t.triggers


def test_invalid_microagent_type(temp_microagents_dir):
    """Test loading a microagent with an invalid type."""
    invalid_agent = "---\nname: invalid_type_agent\ntype: invalid_type\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - test\n---\n\n# Invalid Type Test\n\nThis microagent has an invalid type.\n"
    invalid_file = temp_microagents_dir / "invalid_type.md"
    invalid_file.write_text(invalid_agent)
    from openhands.core.exceptions import MicroagentValidationError

    with pytest.raises(MicroagentValidationError) as excinfo:
        load_microagents_from_dir(temp_microagents_dir)
    error_msg = str(excinfo.value)
    assert "invalid_type.md" in error_msg
    assert 'Invalid "type" value: "invalid_type"' in error_msg
    assert "Valid types are:" in error_msg
    assert '"knowledge"' in error_msg
    assert '"repo"' in error_msg
    assert '"task"' in error_msg


def test_cursorrules_file_load():
    """Test loading .cursorrules file as a RepoMicroagent."""
    cursorrules_content = (
        "Always use Python for new files.\nFollow the existing code style.\nAdd proper error handling."
    )
    cursorrules_path = Path(".cursorrules")
    agent = BaseMicroagent.load(cursorrules_path, file_content=cursorrules_content)
    assert isinstance(agent, RepoMicroagent)
    assert agent.name == "cursorrules"
    assert agent.content == cursorrules_content
    assert agent.type == MicroagentType.REPO_KNOWLEDGE
    assert agent.metadata.name == "cursorrules"
    from pathlib import Path as _P

    assert _P(agent.source).name == cursorrules_path.name


def test_microagent_version_as_integer():
    """Test loading a microagent with version as integer (reproduces the bug)."""
    microagent_content = "---\nname: test_agent\ntype: knowledge\nversion: 2512312\nagent: CodeActAgent\ntriggers:\n  - test\n---\n\n# Test Agent\n\nThis is a test agent with integer version.\n"
    test_path = Path("test_agent.md")
    agent = BaseMicroagent.load(test_path, file_content=microagent_content)
    assert isinstance(agent, KnowledgeMicroagent)
    assert agent.name == "test_agent"
    assert agent.metadata.version == "2512312"
    assert isinstance(agent.metadata.version, str)
    assert agent.type == MicroagentType.KNOWLEDGE


def test_microagent_version_as_float():
    """Test loading a microagent with version as float."""
    microagent_content = "---\nname: test_agent_float\ntype: knowledge\nversion: 1.5\nagent: CodeActAgent\ntriggers:\n  - test\n---\n\n# Test Agent Float\n\nThis is a test agent with float version.\n"
    test_path = Path("test_agent_float.md")
    agent = BaseMicroagent.load(test_path, file_content=microagent_content)
    assert isinstance(agent, KnowledgeMicroagent)
    assert agent.name == "test_agent_float"
    assert agent.metadata.version == "1.5"
    assert isinstance(agent.metadata.version, str)
    assert agent.type == MicroagentType.KNOWLEDGE


def test_microagent_version_as_string_unchanged():
    """Test loading a microagent with version as string (should remain unchanged)."""
    microagent_content = '---\nname: test_agent_string\ntype: knowledge\nversion: "1.0.0"\nagent: CodeActAgent\ntriggers:\n  - test\n---\n\n# Test Agent String\n\nThis is a test agent with string version.\n'
    test_path = Path("test_agent_string.md")
    agent = BaseMicroagent.load(test_path, file_content=microagent_content)
    assert isinstance(agent, KnowledgeMicroagent)
    assert agent.name == "test_agent_string"
    assert agent.metadata.version == "1.0.0"
    assert isinstance(agent.metadata.version, str)
    assert agent.type == MicroagentType.KNOWLEDGE


@pytest.fixture
def temp_microagents_dir_with_cursorrules():
    """Create a temporary directory with test microagents and .cursorrules file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        microagents_dir = root / ".openhands" / "microagents"
        microagents_dir.mkdir(parents=True, exist_ok=True)
        cursorrules_content = "Always use TypeScript for new files.\nFollow the existing code style."
        (root / ".cursorrules").write_text(cursorrules_content)
        repo_agent = "---\n# type: repo\nversion: 1.0.0\nagent: CodeActAgent\n---\n\n# Test Repository Agent\n\nRepository-specific test instructions.\n"
        (microagents_dir / "repo.md").write_text(repo_agent)
        yield root


def test_load_microagents_with_cursorrules(temp_microagents_dir_with_cursorrules):
    """Test loading microagents when .cursorrules file exists."""
    microagents_dir = temp_microagents_dir_with_cursorrules / ".openhands" / "microagents"
    repo_agents, knowledge_agents = load_microagents_from_dir(microagents_dir)
    assert len(repo_agents) == 2
    assert "repo" in repo_agents
    assert "cursorrules" in repo_agents
    cursorrules_agent = repo_agents["cursorrules"]
    assert isinstance(cursorrules_agent, RepoMicroagent)
    assert cursorrules_agent.name == "cursorrules"
    assert "Always use TypeScript for new files" in cursorrules_agent.content
    assert cursorrules_agent.type == MicroagentType.REPO_KNOWLEDGE


@pytest.fixture
def temp_dir_with_cursorrules_only():
    """Create a temporary directory with only .cursorrules file (no .openhands/microagents directory)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        cursorrules_content = "Always use Python for new files.\nFollow PEP 8 style guidelines."
        (root / ".cursorrules").write_text(cursorrules_content)
        yield root


def test_load_cursorrules_without_microagents_dir(temp_dir_with_cursorrules_only):
    """Test loading .cursorrules file when .openhands/microagents directory doesn't exist.

    This test reproduces the bug where .cursorrules is only loaded when
    .openhands/microagents directory exists.
    """
    microagents_dir = temp_dir_with_cursorrules_only / ".openhands" / "microagents"
    repo_agents, knowledge_agents = load_microagents_from_dir(microagents_dir)
    assert len(repo_agents) == 1
    assert "cursorrules" in repo_agents
    assert len(knowledge_agents) == 0
    cursorrules_agent = repo_agents["cursorrules"]
    assert isinstance(cursorrules_agent, RepoMicroagent)
    assert cursorrules_agent.name == "cursorrules"
    assert "Always use Python for new files" in cursorrules_agent.content
    assert cursorrules_agent.type == MicroagentType.REPO_KNOWLEDGE


def test_agents_md_file_load():
    """Test loading AGENTS.md file as a RepoMicroagent."""
    agents_content = "# Project Setup\n\n## Setup commands\n\n- Install deps: `npm install`\n- Start dev server: `npm run dev`\n- Run tests: `npm test`\n\n## Code style\n\n- TypeScript strict mode\n- Single quotes, no semicolons\n- Use functional patterns where possible"
    agents_path = Path("AGENTS.md")
    agent = BaseMicroagent.load(agents_path, file_content=agents_content)
    assert isinstance(agent, RepoMicroagent)
    assert agent.name == "agents"
    assert agent.content == agents_content
    assert agent.type == MicroagentType.REPO_KNOWLEDGE
    assert agent.metadata.name == "agents"
    from pathlib import Path as _P

    assert _P(agent.source).name == agents_path.name


def test_agents_md_case_insensitive():
    """Test that AGENTS.md loading is case-insensitive."""
    agents_content = "# Development Guide\n\nUse TypeScript for all new files."
    test_cases = ["AGENTS.md", "agents.md", "AGENT.md", "agent.md"]
    for filename in test_cases:
        agents_path = Path(filename)
        agent = BaseMicroagent.load(agents_path, file_content=agents_content)
        assert isinstance(agent, RepoMicroagent)
        assert agent.name == "agents"
        assert agent.content == agents_content
        assert agent.type == MicroagentType.REPO_KNOWLEDGE


@pytest.fixture
def temp_dir_with_agents_md_only():
    """Create a temporary directory with only AGENTS.md file (no .openhands/microagents directory)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        agents_content = "# Development Guide\n\n## Setup commands\n\n- Install deps: `poetry install`\n- Start dev server: `poetry run python app.py`\n- Run tests: `poetry run pytest`\n\n## Code style\n\n- Python 3.12+\n- Follow PEP 8 guidelines\n- Use type hints everywhere"
        (root / "AGENTS.md").write_text(agents_content)
        yield root


def test_load_agents_md_without_microagents_dir(temp_dir_with_agents_md_only):
    """Test loading AGENTS.md file when .openhands/microagents directory doesn't exist."""
    microagents_dir = temp_dir_with_agents_md_only / ".openhands" / "microagents"
    repo_agents, knowledge_agents = load_microagents_from_dir(microagents_dir)
    assert len(repo_agents) == 1
    assert "agents" in repo_agents
    assert len(knowledge_agents) == 0
    agents_agent = repo_agents["agents"]
    assert isinstance(agents_agent, RepoMicroagent)
    assert agents_agent.name == "agents"
    assert "Install deps: `poetry install`" in agents_agent.content
    assert agents_agent.type == MicroagentType.REPO_KNOWLEDGE


@pytest.fixture
def temp_dir_with_both_cursorrules_and_agents():
    """Create a temporary directory with both .cursorrules and AGENTS.md files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        cursorrules_content = "Always use Python for new files.\nFollow PEP 8 style guidelines."
        (root / ".cursorrules").write_text(cursorrules_content)
        agents_content = "# Development Guide\n\n## Setup commands\n\n- Install deps: `poetry install`\n- Run tests: `poetry run pytest`"
        (root / "AGENTS.md").write_text(agents_content)
        yield root


def test_load_both_cursorrules_and_agents_md(temp_dir_with_both_cursorrules_and_agents):
    """Test loading both .cursorrules and AGENTS.md files when .openhands/microagents doesn't exist."""
    microagents_dir = temp_dir_with_both_cursorrules_and_agents / ".openhands" / "microagents"
    repo_agents, knowledge_agents = load_microagents_from_dir(microagents_dir)
    assert len(repo_agents) == 2
    assert "cursorrules" in repo_agents
    assert "agents" in repo_agents
    assert len(knowledge_agents) == 0
    cursorrules_agent = repo_agents["cursorrules"]
    assert isinstance(cursorrules_agent, RepoMicroagent)
    assert "Always use Python for new files" in cursorrules_agent.content
    agents_agent = repo_agents["agents"]
    assert isinstance(agents_agent, RepoMicroagent)
    assert "Install deps: `poetry install`" in agents_agent.content
