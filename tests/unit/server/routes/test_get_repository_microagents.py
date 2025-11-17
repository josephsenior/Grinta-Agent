from types import MappingProxyType
from unittest.mock import AsyncMock, patch
from urllib.parse import quote
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from httpcore import Request
from pydantic import SecretStr
from forge.integrations.provider import ProviderToken, ProviderType
from forge.integrations.service_types import AuthenticationError, Repository
from forge.microagent.types import MicroagentContentResponse
from forge.server.dependencies import check_session_api_key
from forge.server.routes.git import app as git_app
from forge.server.user_auth import get_access_token, get_provider_tokens, get_user_id


@pytest.fixture
def test_client():
    """Create a test client for the git API."""
    app = FastAPI()
    app.include_router(git_app)

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content=str(exc))

    def mock_get_provider_tokens():
        return MappingProxyType(
            {
                ProviderType.GITHUB: ProviderToken(
                    token=SecretStr("ghp_test_token"), host="github.com"
                ),
                ProviderType.GITLAB: ProviderToken(
                    token=SecretStr("glpat_test_token"), host="gitlab.com"
                ),
                ProviderType.BITBUCKET: ProviderToken(
                    token=SecretStr("bb_test_token"), host="bitbucket.org"
                ),
            }
        )

    def mock_get_access_token():
        return None

    def mock_get_user_id():
        return "test_user"

    def mock_check_session_api_key():
        return None

    app.dependency_overrides[get_provider_tokens] = mock_get_provider_tokens
    app.dependency_overrides[get_access_token] = mock_get_access_token
    app.dependency_overrides[get_user_id] = mock_get_user_id
    app.dependency_overrides[check_session_api_key] = mock_check_session_api_key
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_github_repository():
    """Create a mock GitHub repository for testing."""
    return Repository(
        id="123456",
        full_name="test/repo",
        git_provider=ProviderType.GITHUB,
        is_public=True,
        stargazers_count=100,
    )


@pytest.fixture
def mock_gitlab_repository():
    """Create a mock GitLab repository for testing."""
    return Repository(
        id="123456",
        full_name="test/repo",
        git_provider=ProviderType.GITLAB,
        is_public=True,
        stargazers_count=100,
    )


@pytest.fixture
def mock_bitbucket_repository():
    """Create a mock Bitbucket repository for testing."""
    return Repository(
        id="123456",
        full_name="test/repo",
        git_provider=ProviderType.BITBUCKET,
        is_public=True,
        stargazers_count=100,
    )


@pytest.fixture
def sample_microagent_content():
    """Sample microagent file content."""
    return "---\nname: test_agent\ntype: repo\ninputs:\n  - name: query\n    type: str\n    description: Search query for the repository\nmcp_tools:\n  stdio_servers:\n    - name: git\n      command: git\n    - name: file_editor\n      command: editor\n---\n\nThis is a test repository microagent for testing purposes."


@pytest.fixture
def sample_cursorrules_content():
    """Sample .cursorrules file content."""
    return "---\nname: cursor_rules\ntype: repo\n---\n\nThese are cursor rules for the repository."


class TestGetRepositoryMicroagents:
    """Test cases for the get_repository_microagents API endpoint."""

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_github_success(
        self,
        mock_provider_handler_cls,
        test_client,
        mock_github_repository,
        sample_microagent_content,
        sample_cursorrules_content,
    ):
        """Test successful retrieval of microagents from GitHub repository."""
        # Setup mock
        mock_provider_handler = _setup_mock_provider_handler(mock_provider_handler_cls)
        _configure_mock_microagents_response(mock_provider_handler)

        # Execute request
        response = test_client.get("/api/user/repository/test/repo/microagents")

        # Verify response
        _verify_successful_response(response)

        # Verify microagent data structure
        data = response.json()
        _verify_microagent_data_structure(data)


def _setup_mock_provider_handler(mock_provider_handler_cls):
    """Setup mock provider handler for testing."""
    mock_provider_handler = AsyncMock()
    mock_provider_handler_cls.return_value = mock_provider_handler
    return mock_provider_handler


def _configure_mock_microagents_response(mock_provider_handler):
    """Configure mock microagents response."""
    mock_provider_handler.get_microagents.return_value = [
        {
            "name": "test_agent",
            "path": ".Forge/microagents/test_agent.md",
            "created_at": "2024-01-01T00:00:00",
        },
        {
            "name": "cursorrules",
            "path": ".cursorrules",
            "created_at": "2024-01-01T00:00:00",
        },
    ]


def _verify_successful_response(response):
    """Verify the response is successful."""
    assert response.status_code == 200


def _verify_microagent_data_structure(data):
    """Verify the structure of microagent data."""
    assert len(data) == 2

    for microagent in data:
        _verify_required_fields_present(microagent)
        _verify_excluded_fields_absent(microagent)


def _verify_required_fields_present(microagent):
    """Verify required fields are present in microagent data."""
    assert "name" in microagent
    assert "path" in microagent
    assert "created_at" in microagent


def _verify_excluded_fields_absent(microagent):
    """Verify excluded fields are not present in microagent data."""
    excluded_fields = ["content", "type", "triggers", "inputs", "tools"]
    for field in excluded_fields:
        assert field not in microagent

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_gitlab_success(
        self, mock_provider_handler_cls, test_client, mock_gitlab_repository
    ):
        """Test successful retrieval of microagents from GitLab repository."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.return_value = [
            {
                "name": "test_agent",
                "path": ".Forge/microagents/test_agent.md",
                "created_at": "2024-01-01T00:00:00",
            }
        ]
        response = test_client.get("/api/user/repository/test/repo/microagents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "content" not in data[0]

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_bitbucket_success(
        self, mock_provider_handler_cls, test_client, mock_bitbucket_repository
    ):
        """Test successful retrieval of microagents from Bitbucket repository."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.return_value = [
            {
                "name": "test_agent",
                "path": ".Forge/microagents/test_agent.md",
                "created_at": "2024-01-01T00:00:00",
            }
        ]
        response = test_client.get("/api/user/repository/test/repo/microagents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "content" not in data[0]

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_no_directory_found(
        self, mock_provider_handler_cls, test_client, mock_github_repository
    ):
        """Test when microagents directory is not found."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.return_value = []
        response = test_client.get("/api/user/repository/test/repo/microagents")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_authentication_error(
        self, mock_provider_handler_cls, test_client
    ):
        """Test authentication error."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.side_effect = AuthenticationError(
            "Invalid credentials"
        )
        response = test_client.get("/api/user/repository/test/repo/microagents")
        assert response.status_code == 401
        assert response.json() == "Invalid credentials"


class TestGetRepositoryMicroagentContent:
    """Test cases for the get_repository_microagent_content API endpoint."""

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_github_success(
        self, mock_provider_handler_cls, test_client, sample_microagent_content
    ):
        """Test successful retrieval of microagent content from GitHub."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.return_value = (
            MicroagentContentResponse(
                content=sample_microagent_content,
                path=".Forge/microagents/test_agent.md",
                triggers=["test", "agent"],
            )
        )
        file_path = ".Forge/microagents/test_agent.md"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == sample_microagent_content
        assert data["path"] == file_path
        assert "triggers" in data
        assert data["triggers"] == ["test", "agent"]

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_gitlab_success(
        self, mock_provider_handler_cls, test_client, sample_microagent_content
    ):
        """Test successful retrieval of microagent content from GitLab."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.return_value = (
            MicroagentContentResponse(
                content=sample_microagent_content,
                path=".Forge/microagents/test_agent.md",
                triggers=["test", "agent"],
            )
        )
        file_path = ".Forge/microagents/test_agent.md"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == sample_microagent_content
        assert data["path"] == file_path
        assert "triggers" in data
        assert data["triggers"] == ["test", "agent"]

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_bitbucket_success(
        self, mock_provider_handler_cls, test_client, sample_microagent_content
    ):
        """Test successful retrieval of microagent content from Bitbucket."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.return_value = (
            MicroagentContentResponse(
                content=sample_microagent_content,
                path=".Forge/microagents/test_agent.md",
                triggers=["test", "agent"],
            )
        )
        file_path = ".Forge/microagents/test_agent.md"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == sample_microagent_content
        assert data["path"] == file_path
        assert "triggers" in data
        assert data["triggers"] == ["test", "agent"]

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_file_not_found(
        self, mock_provider_handler_cls, test_client, mock_github_repository
    ):
        """Test when microagent file is not found."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.side_effect = RuntimeError(
            "File not found"
        )
        file_path = ".Forge/microagents/nonexistent.md"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 500
        assert "File not found" in response.json()

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_authentication_error(
        self, mock_provider_handler_cls, test_client
    ):
        """Test authentication error for content API."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.side_effect = AuthenticationError(
            "Invalid credentials"
        )
        file_path = ".Forge/microagents/test_agent.md"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 401
        assert response.json() == "Invalid credentials"

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagent_content_cursorrules(
        self, mock_provider_handler_cls, test_client, sample_cursorrules_content
    ):
        """Test retrieval of .cursorrules file content."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagent_content.return_value = (
            MicroagentContentResponse(
                content=sample_cursorrules_content,
                path=".cursorrules",
                triggers=["cursor", "rules"],
            )
        )
        file_path = ".cursorrules"
        response = test_client.get(
            f"/api/user/repository/test/repo/microagents/content?file_path={quote(file_path)}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == sample_cursorrules_content
        assert data["path"] == file_path
        assert "triggers" in data
        assert data["triggers"] == ["cursor", "rules"]


class TestSpecialRepositoryStructures:
    """Test cases for special repository structures."""

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_FORGE_repo_structure(
        self, mock_provider_handler_cls, test_client
    ):
        """Test microagents from .Forge repository structure."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.return_value = [
            {
                "name": "test_agent",
                "path": "microagents/test_agent.md",
                "created_at": "2024-01-01T00:00:00",
            }
        ]
        response = test_client.get("/api/user/repository/test/.Forge/microagents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["path"] == "microagents/test_agent.md"

    @pytest.mark.asyncio
    @patch("forge.server.routes.git.ProviderHandler")
    async def test_get_microagents_gitlab_FORGE_config_structure(
        self, mock_provider_handler_cls, test_client
    ):
        """Test microagents from GitLab Forge-config repository structure."""
        mock_provider_handler = AsyncMock()
        mock_provider_handler_cls.return_value = mock_provider_handler
        mock_provider_handler.get_microagents.return_value = [
            {
                "name": "test_agent",
                "path": "microagents/test_agent.md",
                "created_at": "2024-01-01T00:00:00",
            }
        ]
        response = test_client.get("/api/user/repository/test/Forge-config/microagents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["path"] == "microagents/test_agent.md"
