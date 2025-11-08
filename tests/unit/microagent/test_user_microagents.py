"""Tests for user directory microagent loading."""

import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest
from forge.events.stream import EventStream
from forge.memory.memory import Memory
from forge.microagent import KnowledgeMicroagent, MicroagentType, RepoMicroagent
from forge.storage import get_file_store


@pytest.fixture
def temp_user_microagents_dir():
    """Create a temporary directory to simulate ~/.Forge/microagents/."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir)
        knowledge_agent = "---\nname: user_knowledge\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - user-test\n  - personal\n---\n\n# User Knowledge Agent\n\nPersonal knowledge and guidelines.\n"
        (user_dir / "user_knowledge.md").write_text(knowledge_agent)
        repo_agent = "---\nname: user_repo\nversion: 1.0.0\nagent: CodeActAgent\n---\n\n# User Repository Agent\n\nPersonal repository-specific instructions.\n"
        (user_dir / "user_repo.md").write_text(repo_agent)
        yield user_dir


def test_user_microagents_loading(temp_user_microagents_dir):
    """Test that user microagents are loaded from ~/.Forge/microagents/."""
    with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(temp_user_microagents_dir)):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_store = get_file_store("local", temp_dir)
            event_stream = EventStream("test", file_store)
            memory = Memory(event_stream, "test_sid")
            assert "user_knowledge" in memory.knowledge_microagents
            assert "user_repo" in memory.repo_microagents
            user_knowledge = memory.knowledge_microagents["user_knowledge"]
            assert isinstance(user_knowledge, KnowledgeMicroagent)
            assert user_knowledge.type == MicroagentType.KNOWLEDGE
            assert "user-test" in user_knowledge.triggers
            assert "personal" in user_knowledge.triggers
            user_repo = memory.repo_microagents["user_repo"]
            assert isinstance(user_repo, RepoMicroagent)
            assert user_repo.type == MicroagentType.REPO_KNOWLEDGE


def test_user_microagents_directory_creation():
    """Test that user microagents directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = Path(temp_dir) / "non_existent" / "microagents"
        with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(non_existent_dir)):
            with tempfile.TemporaryDirectory() as temp_store_dir:
                file_store = get_file_store("local", temp_store_dir)
                event_stream = EventStream("test", file_store)
                Memory(event_stream, "test_sid")
                assert non_existent_dir.exists()
                assert non_existent_dir.is_dir()


def test_user_microagents_override_global():
    """Test that user microagents can override global ones with the same name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir)
        github_agent = "---\nname: github\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - github\n  - git\n---\n\n# Personal GitHub Agent\n\nMy personal GitHub workflow and preferences.\n"
        (user_dir / "github.md").write_text(github_agent)
        with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(user_dir)):
            with tempfile.TemporaryDirectory() as temp_store_dir:
                file_store = get_file_store("local", temp_store_dir)
                event_stream = EventStream("test", file_store)
                memory = Memory(event_stream, "test_sid")
                if "github" in memory.knowledge_microagents:
                    github_microagent = memory.knowledge_microagents["github"]
                    assert "My personal GitHub workflow" in github_microagent.content


def test_user_microagents_loading_error_handling():
    """Test error handling when user microagents directory has issues."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir)
        invalid_agent = "---\nname: invalid\ntype: invalid_type\n---\n\n# Invalid Agent\n"
        (user_dir / "invalid.md").write_text(invalid_agent)
        with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(user_dir)):
            with tempfile.TemporaryDirectory() as temp_store_dir:
                file_store = get_file_store("local", temp_store_dir)
                event_stream = EventStream("test", file_store)
                memory = Memory(event_stream, "test_sid")
                assert memory is not None
                assert "invalid" not in memory.knowledge_microagents
                assert "invalid" not in memory.repo_microagents


def test_user_microagents_empty_directory():
    """Test behavior when user microagents directory is empty."""
    with tempfile.TemporaryDirectory() as temp_dir:
        empty_dir = Path(temp_dir)
        with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(empty_dir)):
            with tempfile.TemporaryDirectory() as temp_store_dir:
                file_store = get_file_store("local", temp_store_dir)
                event_stream = EventStream("test", file_store)
                memory = Memory(event_stream, "test_sid")
                assert memory is not None


def test_user_microagents_nested_directories(temp_user_microagents_dir):
    """Test loading user microagents from nested directories."""
    nested_dir = temp_user_microagents_dir / "personal" / "tools"
    nested_dir.mkdir(parents=True)
    nested_agent = "---\nname: personal_tool\nversion: 1.0.0\nagent: CodeActAgent\ntriggers:\n  - personal-tool\n---\n\n# Personal Tool Agent\n\nMy personal development tools and workflows.\n"
    (nested_dir / "tool.md").write_text(nested_agent)
    with patch("forge.memory.memory.USER_MICROAGENTS_DIR", str(temp_user_microagents_dir)):
        with tempfile.TemporaryDirectory() as temp_store_dir:
            file_store = get_file_store("local", temp_store_dir)
            event_stream = EventStream("test", file_store)
            memory = Memory(event_stream, "test_sid")
            assert "personal/tools/tool" in memory.knowledge_microagents
            nested_microagent = memory.knowledge_microagents["personal/tools/tool"]
            assert isinstance(nested_microagent, KnowledgeMicroagent)
            assert "personal-tool" in nested_microagent.triggers
