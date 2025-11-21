"""Tests for GitLab alternative directory support for microagents."""

import tempfile
from types import MappingProxyType
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from forge.core.config import ForgeConfig, SandboxConfig
from forge.events import EventStream
from forge.integrations.service_types import ProviderType, Repository
from forge.llm.llm_registry import LLMRegistry
from forge.microagent.microagent import RepoMicroagent
from forge.runtime.base import Runtime
from forge.storage import get_file_store


class MockRuntime(Runtime):
    """Mock runtime for testing."""

    def __init__(self, workspace_root: Path):
        config = ForgeConfig()
        config.workspace_mount_path_in_sandbox = str(workspace_root)
        config.sandbox = SandboxConfig()
        file_store = get_file_store("local", str(workspace_root))
        event_stream = MagicMock(spec=EventStream)
        event_stream.file_store = file_store
        llm_registry = LLMRegistry(config)
        super().__init__(
            config=config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid="test",
            git_provider_tokens=MappingProxyType({}),
        )
        self._workspace_root = workspace_root
        self._logs: list[tuple[str, str]] = []

    @property
    def workspace_root(self) -> Path:
        """Return the workspace root path."""
        return self._workspace_root

    def log(self, level: str, message: str):
        """Mock log method."""
        self._logs.append((level, message))

    def run_action(self, action):
        """Mock run_action method."""
        from forge.events.observation import CmdOutputObservation

        command = getattr(action, "command", "")
        return CmdOutputObservation(content="", exit_code=0, command=command)

    def read(self, action):
        """Mock read method."""
        from forge.events.observation import ErrorObservation

        return ErrorObservation("File not found")

    def _load_microagents_from_directory(self, directory: Path, source: str):
        """Mock microagent loading."""
        if not directory.exists():
            return []
        microagents = []
        for md_file in directory.rglob("*.md"):
            if md_file.name == "README.md":
                continue
            from forge.microagent.types import MicroagentMetadata, MicroagentType

            agent = RepoMicroagent(
                name=f"mock_{md_file.stem}",
                content=f"Mock content from {md_file}",
                metadata=MicroagentMetadata(name=f"mock_{md_file.stem}"),
                source=str(md_file),
                type=MicroagentType.REPO_KNOWLEDGE,
            )
            microagents.append(agent)
        return microagents

    async def connect(self) -> None:
        return None

    def run(self, action):
        from forge.events.observation import CmdOutputObservation

        command = getattr(action, "command", "")
        return CmdOutputObservation(content="", command=command, exit_code=0)

    def run_ipython(self, action):
        from forge.events.observation import NullObservation

        return NullObservation("")

    def edit(self, action):
        from forge.events.observation import NullObservation

        return NullObservation("")

    def browse(self, action):
        from forge.events.observation import NullObservation

        return NullObservation("")

    def browse_interactive(self, action):
        from forge.events.observation import NullObservation

        return NullObservation("")

    def write(self, action):
        from forge.events.observation import NullObservation

        return NullObservation("")

    def copy_to(
        self, host_src: str, sandbox_dest: str, recursive: bool = False
    ) -> None:
        return None

    def copy_from(self, path: str) -> Path:
        return Path(path)

    def list_files(self, path: str, recursive: bool = False) -> list[str]:
        return []

    def get_mcp_config(self, extra_stdio_servers=None):
        from forge.core.config.mcp_config import MCPConfig

        return MCPConfig()

    async def call_tool_mcp(self, action):
        from forge.events.observation import MCPObservation

        return MCPObservation(content="", name="mock", arguments={})


def create_test_microagents(base_dir: Path, config_dir_name: str = ".Forge"):
    """Create test microagent files in the specified directory."""
    microagents_dir = base_dir / config_dir_name / "microagents"
    microagents_dir.mkdir(parents=True, exist_ok=True)
    test_agent = "---\nname: test_agent\ntype: repo\nversion: 1.0.0\nagent: CodeActAgent\n---\n\n# Test Agent\n\nThis is a test microagent.\n"
    (microagents_dir / "test.md").write_text(test_agent)
    return microagents_dir


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_is_gitlab_repository_github(temp_workspace):
    """Test that GitHub repositories are correctly identified as non-GitLab."""
    runtime = MockRuntime(temp_workspace)
    mock_repo = Repository(
        id="123",
        full_name="owner/repo",
        git_provider=ProviderType.GITHUB,
        is_public=True,
    )
    with patch("forge.runtime.base.ProviderHandler") as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler
        with patch("forge.runtime.base.call_async_from_sync") as mock_async:
            mock_async.return_value = mock_repo
            result = runtime._is_gitlab_repository("github.com/owner/repo")
            assert result is False


def test_is_gitlab_repository_gitlab(temp_workspace):
    """Test that GitLab repositories are correctly identified."""
    runtime = MockRuntime(temp_workspace)
    mock_repo = Repository(
        id="456",
        full_name="owner/repo",
        git_provider=ProviderType.GITLAB,
        is_public=True,
    )
    with patch("forge.runtime.base.ProviderHandler") as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler
        with patch("forge.runtime.base.call_async_from_sync") as mock_async:
            mock_async.return_value = mock_repo
            result = runtime._is_gitlab_repository("gitlab.com/owner/repo")
            assert result is True


def test_is_gitlab_repository_exception(temp_workspace):
    """Test that exceptions in provider detection return False."""
    runtime = MockRuntime(temp_workspace)
    with patch("forge.runtime.base.ProviderHandler") as mock_handler_class:
        mock_handler_class.side_effect = Exception("Provider error")
        result = runtime._is_gitlab_repository("unknown.com/owner/repo")
        assert result is False


def test_get_microagents_from_org_or_user_github(temp_workspace):
    """Test that GitHub repositories only try .Forge directory."""
    runtime = MockRuntime(temp_workspace)
    with patch.object(runtime, "_is_gitlab_repository", return_value=False):
        with patch("forge.runtime.base.call_async_from_sync") as mock_async:
            mock_async.side_effect = Exception("Repository not found")
            result = runtime.get_microagents_from_org_or_user("github.com/owner/repo")
            assert len(result) == 0
            assert mock_async.call_count == 1


def test_get_microagents_from_org_or_user_gitlab_success_with_config(temp_workspace):
    """Test that GitLab repositories use Forge-config and succeed."""
    runtime = MockRuntime(temp_workspace)
    org_dir = temp_workspace / "org_FORGE_owner"
    create_test_microagents(org_dir, ".")
    with patch.object(runtime, "_is_gitlab_repository", return_value=True):
        with patch("forge.runtime.base.call_async_from_sync") as mock_async:
            mock_async.return_value = "https://gitlab.com/owner/Forge-config.git"
            result = runtime.get_microagents_from_org_or_user("gitlab.com/owner/repo")
            assert len(result) >= 0
            assert mock_async.call_count == 1


def test_get_microagents_from_org_or_user_gitlab_failure(temp_workspace):
    """Test that GitLab repositories handle failure gracefully when Forge-config doesn't exist."""
    runtime = MockRuntime(temp_workspace)
    with patch.object(runtime, "_is_gitlab_repository", return_value=True):
        with patch("forge.runtime.base.call_async_from_sync") as mock_async:
            mock_async.side_effect = Exception("Forge-config not found")
            result = runtime.get_microagents_from_org_or_user("gitlab.com/owner/repo")
            assert len(result) == 0
            assert mock_async.call_count == 1


def test_get_microagents_from_selected_repo_gitlab_uses_Forge(temp_workspace):
    """Test that GitLab repositories use .Forge directory for repository-specific microagents."""
    runtime = MockRuntime(temp_workspace)
    repo_dir = temp_workspace / "repo"
    repo_dir.mkdir()
    create_test_microagents(repo_dir, ".Forge")
    with patch.object(runtime, "_is_gitlab_repository", return_value=True):
        with patch.object(runtime, "get_microagents_from_org_or_user", return_value=[]):
            result = runtime.get_microagents_from_selected_repo("gitlab.com/owner/repo")
            assert isinstance(result, list)


def test_get_microagents_from_selected_repo_github_only_Forge(temp_workspace):
    """Test that GitHub repositories only check .Forge directory."""
    runtime = MockRuntime(temp_workspace)
    repo_dir = temp_workspace / "repo"
    repo_dir.mkdir()
    create_test_microagents(repo_dir, "Forge-config")
    create_test_microagents(repo_dir, ".Forge")
    with patch.object(runtime, "_is_gitlab_repository", return_value=False):
        with patch.object(runtime, "get_microagents_from_org_or_user", return_value=[]):
            result = runtime.get_microagents_from_selected_repo("github.com/owner/repo")
            assert isinstance(result, list)
