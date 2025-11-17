"""Tests for Bitbucket integration."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import SecretStr
from forge.integrations.bitbucket.bitbucket_service import BitBucketService
from forge.integrations.provider import ProviderToken, ProviderType
from forge.integrations.service_types import OwnerType, Repository
from forge.integrations.service_types import ProviderType as ServiceProviderType
from forge.integrations.utils import validate_provider_token
from forge.resolver.interfaces.bitbucket import BitbucketIssueHandler
from forge.resolver.interfaces.issue import Issue
from forge.resolver.interfaces.issue_definitions import ServiceContextIssue
from forge.resolver.send_pull_request import send_pull_request
from forge.runtime.base import Runtime
from forge.server.routes.secrets import check_provider_tokens
from forge.server.settings import POSTProviderModel
from forge.server.types import AppMode


@pytest.fixture
def bitbucket_handler():
    return BitbucketIssueHandler(
        owner="test-workspace",
        repo="test-repo",
        token="test-token",
        username="test-user",
    )


def test_init():
    handler = BitbucketIssueHandler(
        owner="test-workspace",
        repo="test-repo",
        token="test-token",
        username="test-user",
    )
    assert handler.owner == "test-workspace"
    assert handler.repo == "test-repo"
    assert handler.token == "test-token"
    assert handler.username == "test-user"
    assert handler.base_domain == "bitbucket.org"
    assert handler.base_url == "https://api.bitbucket.org/2.0"
    assert (
        handler.download_url
        == "https://bitbucket.org/test-workspace/test-repo/get/master.zip"
    )
    assert handler.clone_url == "https://bitbucket.org/test-workspace/test-repo.git"
    assert handler.headers == {
        "Authorization": "Bearer test-token",
        "Accept": "application/json",
    }


def test_get_repo_url(bitbucket_handler):
    assert (
        bitbucket_handler.get_repo_url()
        == "https://bitbucket.org/test-workspace/test-repo"
    )


def test_get_issue_url(bitbucket_handler):
    assert (
        bitbucket_handler.get_issue_url(123)
        == "https://bitbucket.org/test-workspace/test-repo/issues/123"
    )


def test_get_pr_url(bitbucket_handler):
    assert (
        bitbucket_handler.get_pr_url(123)
        == "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
    )


@pytest.mark.asyncio
@patch("httpx.AsyncClient")
async def test_get_issue(mock_client, bitbucket_handler):
    mock_response = MagicMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "id": 123,
        "title": "Test Issue",
        "content": {"raw": "Test Issue Body"},
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/issues/123"
            }
        },
        "state": "open",
        "reporter": {"display_name": "Test User"},
        "assignee": [{"display_name": "Assignee User"}],
    }
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_response
    mock_client.return_value.__aenter__.return_value = mock_client_instance
    issue = await bitbucket_handler.get_issue(123)
    assert issue.number == 123
    assert issue.title == "Test Issue"
    assert issue.body == "Test Issue Body"


@patch("httpx.post")
def test_create_pr(mock_post, bitbucket_handler):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "links": {
            "html": {
                "href": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
            }
        }
    }
    mock_post.return_value = mock_response
    pr_url = bitbucket_handler.create_pr(
        title="Test PR", body="Test PR Body", head="feature-branch", base="main"
    )
    assert pr_url == "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
    expected_payload = {
        "title": "Test PR",
        "description": "Test PR Body",
        "source": {"branch": {"name": "feature-branch"}},
        "destination": {"branch": {"name": "main"}},
        "close_source_branch": False,
    }
    mock_post.assert_called_once_with(
        "https://api.bitbucket.org/2.0/repositories/test-workspace/test-repo/pullrequests",
        headers=bitbucket_handler.headers,
        json=expected_payload,
    )


@patch("forge.resolver.send_pull_request.ServiceContextIssue")
@patch("forge.resolver.send_pull_request.BitbucketIssueHandler")
@patch("subprocess.run")
def test_send_pull_request_bitbucket(
    mock_run, mock_bitbucket_handler, mock_service_context
):
    mock_run.return_value = MagicMock(returncode=0)
    mock_instance = MagicMock(spec=BitbucketIssueHandler)
    mock_bitbucket_handler.return_value = mock_instance
    mock_service = MagicMock(spec=ServiceContextIssue)
    mock_service.get_branch_name.return_value = "Forge-fix-123"
    mock_service.branch_exists.return_value = True
    mock_service.get_default_branch_name.return_value = "main"
    mock_service.get_clone_url.return_value = (
        "https://bitbucket.org/test-workspace/test-repo.git"
    )
    mock_service.create_pull_request.return_value = {
        "html_url": "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
    }
    mock_strategy = MagicMock()
    mock_service._strategy = mock_strategy
    mock_service_context.return_value = mock_service
    mock_issue = Issue(
        number=123,
        title="Test Issue",
        owner="test-workspace",
        repo="test-repo",
        body="Test body",
        head_branch="feature-branch",
        thread_ids=None,
    )
    result = send_pull_request(
        issue=mock_issue,
        token="test-token",
        username=None,
        platform=ServiceProviderType.BITBUCKET,
        patch_dir="/tmp",  # nosec B108 - Safe: test directory
        pr_type="ready",
        pr_title="Test PR",
        target_branch="main",
    )
    assert result == "https://bitbucket.org/test-workspace/test-repo/pull-requests/123"
    mock_bitbucket_handler.assert_called_once_with(
        "test-workspace", "test-repo", "test-token", None, "bitbucket.org"
    )
    mock_service_context.assert_called_once()
    expected_body = "This pull request fixes #123.\n\nAutomatic fix generated by [Forge](https://github.com/All-Hands-AI/Forge/) 🙌"
    mock_service.create_pull_request.assert_called_once_with(
        {
            "title": "Test PR",
            "description": expected_body,
            "source_branch": "Forge-fix-123",
            "target_branch": "main",
            "draft": False,
        }
    )


class TestBitbucketProviderDomain(unittest.TestCase):
    """Test that Bitbucket provider domain is properly handled in Runtime.clone_or_init_repo."""

    @patch("forge.runtime.base.Runtime.__abstractmethods__", set())
    @patch("forge.runtime.utils.edit.FileEditRuntimeMixin.__init__", return_value=None)
    @patch("forge.runtime.base.ProviderHandler")
    @pytest.mark.asyncio
    async def test_get_authenticated_git_url_bitbucket(
        self, mock_provider_handler, mock_file_edit_init, *args
    ):
        """Test that _get_authenticated_git_url correctly handles Bitbucket repositories."""
        mock_repository = Repository(
            id="1",
            full_name="workspace/repo",
            git_provider=ServiceProviderType.BITBUCKET,
            is_public=True,
        )
        mock_provider_instance = MagicMock()
        mock_provider_instance.verify_repo_provider.return_value = mock_repository
        mock_provider_handler.return_value = mock_provider_instance
        config = MagicMock()
        config.get_llm_config.return_value.model = "test_model"
        runtime = MagicMock(spec=Runtime)
        runtime.config = config
        runtime.event_stream = MagicMock()
        runtime._get_authenticated_git_url = AsyncMock(
            side_effect=[
                "https://bitbucket.org/workspace/repo.git",
                "https://username:app_password@bitbucket.org/workspace/repo.git",
                "https://user@example.com:app_password@bitbucket.org/workspace/repo.git",
                "https://x-token-auth:simple_token@bitbucket.org/workspace/repo.git",
            ]
        )
        url = await runtime._get_authenticated_git_url("workspace/repo", None)
        self.assertEqual(url, "https://bitbucket.org/workspace/repo.git")
        git_provider_tokens = {
            ProviderType.BITBUCKET: ProviderToken(
                token=SecretStr("username:app_password"), host="bitbucket.org"
            )
        }
        url = await runtime._get_authenticated_git_url(
            "workspace/repo", git_provider_tokens
        )
        self.assertEqual(
            url, "https://username:app_password@bitbucket.org/workspace/repo.git"
        )
        git_provider_tokens = {
            ProviderType.BITBUCKET: ProviderToken(
                token=SecretStr("user@example.com:app_password"), host="bitbucket.org"
            )
        }
        url = await runtime._get_authenticated_git_url(
            "workspace/repo", git_provider_tokens
        )
        self.assertEqual(
            url,
            "https://user@example.com:app_password@bitbucket.org/workspace/repo.git",
        )
        git_provider_tokens = {
            ProviderType.BITBUCKET: ProviderToken(
                token=SecretStr("simple_token"), host="bitbucket.org"
            )
        }
        url = await runtime._get_authenticated_git_url(
            "workspace/repo", git_provider_tokens
        )
        self.assertEqual(
            url, "https://x-token-auth:simple_token@bitbucket.org/workspace/repo.git"
        )

    @patch("forge.runtime.base.ProviderHandler")
    @patch.object(Runtime, "run_action")
    async def test_bitbucket_provider_domain(
        self, mock_run_action, mock_provider_handler
    ):
        mock_repository = Repository(
            id="1",
            full_name="test/repo",
            git_provider=ServiceProviderType.BITBUCKET,
            is_public=True,
        )
        mock_provider_instance = MagicMock()
        mock_provider_instance.verify_repo_provider.return_value = mock_repository
        mock_provider_handler.return_value = mock_provider_instance
        runtime = MagicMock(spec=Runtime)
        runtime.workspace_root = "/workspace"
        await Runtime.clone_or_init_repo(
            runtime,
            git_provider_tokens=None,
            selected_repository="test/repo",
            selected_branch=None,
        )
        self.assertTrue(mock_run_action.called)


@pytest.mark.asyncio
async def test_validate_provider_token_with_bitbucket_token():
    """Test that validate_provider_token correctly identifies a Bitbucket token.

    and doesn't try to validate it as GitHub or GitLab.
    """
    with (
        patch("forge.integrations.utils.GitHubService") as mock_github_service,
        patch("forge.integrations.utils.GitLabService") as mock_gitlab_service,
        patch("forge.integrations.utils.BitBucketService") as mock_bitbucket_service,
    ):
        github_instance = AsyncMock()
        github_instance.verify_access.side_effect = Exception("Invalid GitHub token")
        mock_github_service.return_value = github_instance
        gitlab_instance = AsyncMock()
        gitlab_instance.get_user.side_effect = Exception("Invalid GitLab token")
        mock_gitlab_service.return_value = gitlab_instance
        bitbucket_instance = AsyncMock()
        bitbucket_instance.get_user.return_value = {"username": "test_user"}
        mock_bitbucket_service.return_value = bitbucket_instance
        token = SecretStr("username:app_password")
        result = await validate_provider_token(token)
        mock_github_service.assert_called_once()
        mock_gitlab_service.assert_called_once()
        mock_bitbucket_service.assert_called_once()
        assert result == ProviderType.BITBUCKET


@pytest.mark.asyncio
async def test_check_provider_tokens_with_only_bitbucket():
    """Test that check_provider_tokens doesn't try to validate GitHub or GitLab tokens.

    when only a Bitbucket token is provided.
    """
    mock_validate = AsyncMock()
    mock_validate.return_value = ProviderType.BITBUCKET
    provider_tokens = {
        "bitbucket": ProviderToken(
            token=SecretStr("username:app_password"), host="bitbucket.org"
        ),
        "github": ProviderToken(token=SecretStr(""), host="github.com"),
        "gitlab": ProviderToken(token=SecretStr(""), host="gitlab.com"),
    }
    post_model = POSTProviderModel(provider_tokens=provider_tokens)
    with patch("forge.server.routes.secrets.validate_provider_token", mock_validate):
        result = await check_provider_tokens(post_model, None)
        assert mock_validate.call_count == 1
        args, kwargs = mock_validate.call_args
        assert args[0].get_secret_value() == "username:app_password"
        message, normalized = result
        assert message == ""
        assert normalized["bitbucket"].host == "bitbucket.org"


@pytest.mark.asyncio
async def test_bitbucket_sort_parameter_mapping():
    """Test that the Bitbucket service correctly maps sort parameters."""
    service = BitBucketService(token=SecretStr("test-token"))
    with patch.object(service, "_make_request") as mock_request:
        mock_request.side_effect = [
            ({"values": [{"slug": "test-workspace", "name": "Test Workspace"}]}, {}),
            ({"values": []}, {}),
        ]
        await service.get_all_repositories("pushed", AppMode.SAAS)
        assert mock_request.call_count == 2
        second_call_args = mock_request.call_args_list[1]
        url, params = second_call_args[0]
        assert params["sort"] == "-updated_on"
        assert "repositories/test-workspace" in url


@pytest.mark.asyncio
async def test_bitbucket_pagination():
    """Test that the Bitbucket service correctly handles pagination for repositories."""
    service = BitBucketService(token=SecretStr("test-token"))
    with patch.object(service, "_make_request") as mock_request:
        mock_request.side_effect = [
            ({"values": [{"slug": "test-workspace", "name": "Test Workspace"}]}, {}),
            (
                {
                    "values": [
                        {
                            "uuid": "repo-1",
                            "slug": "repo1",
                            "workspace": {"slug": "test-workspace"},
                            "is_private": False,
                            "updated_on": "2023-01-01T00:00:00Z",
                        },
                        {
                            "uuid": "repo-2",
                            "slug": "repo2",
                            "workspace": {"slug": "test-workspace"},
                            "is_private": True,
                            "updated_on": "2023-01-02T00:00:00Z",
                        },
                    ],
                    "next": "https://api.bitbucket.org/2.0/repositories/test-workspace?page=2",
                },
                {},
            ),
            (
                {
                    "values": [
                        {
                            "uuid": "repo-3",
                            "slug": "repo3",
                            "workspace": {"slug": "test-workspace"},
                            "is_private": False,
                            "updated_on": "2023-01-03T00:00:00Z",
                        }
                    ]
                },
                {},
            ),
        ]
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert mock_request.call_count == 3
        assert len(repositories) == 3
        assert repositories[0].id == "repo-1"
        assert repositories[1].id == "repo-2"
        assert repositories[2].id == "repo-3"
        assert repositories[0].full_name == "test-workspace/repo1"
        assert repositories[0].is_public is True
        assert repositories[1].is_public is False
        assert repositories[2].is_public is True


@pytest.mark.asyncio
async def test_validate_provider_token_with_empty_tokens():
    """Test that validate_provider_token handles empty tokens correctly."""
    with (
        patch("forge.integrations.utils.GitHubService") as mock_github_service,
        patch("forge.integrations.utils.GitLabService") as mock_gitlab_service,
        patch("forge.integrations.utils.BitBucketService") as mock_bitbucket_service,
    ):
        mock_github_service.return_value.verify_access.side_effect = Exception(
            "Invalid token"
        )
        mock_gitlab_service.return_value.verify_access.side_effect = Exception(
            "Invalid token"
        )
        mock_bitbucket_service.return_value.verify_access.side_effect = Exception(
            "Invalid token"
        )
        token = SecretStr("")
        result = await validate_provider_token(token)
        mock_github_service.assert_called_once()
        mock_gitlab_service.assert_called_once()
        mock_bitbucket_service.assert_called_once()
        assert result is None
        mock_github_service.reset_mock()
        mock_gitlab_service.reset_mock()
        mock_bitbucket_service.reset_mock()
        token = SecretStr("   ")
        result = await validate_provider_token(token)
        mock_github_service.assert_called_once()
        mock_gitlab_service.assert_called_once()
        mock_bitbucket_service.assert_called_once()
        assert result is None


@pytest.mark.asyncio
async def test_bitbucket_get_repositories_with_user_owner_type():
    """Test that get_repositories correctly sets owner_type field for user repositories."""
    service = BitBucketService(token=SecretStr("test-token"))
    mock_workspaces = [{"slug": "test-user", "name": "Test User"}]
    mock_repos = [
        {
            "uuid": "repo-1",
            "slug": "user-repo1",
            "workspace": {"slug": "test-user", "is_private": True},
            "is_private": False,
            "updated_on": "2023-01-01T00:00:00Z",
        },
        {
            "uuid": "repo-2",
            "slug": "user-repo2",
            "workspace": {"slug": "test-user", "is_private": True},
            "is_private": True,
            "updated_on": "2023-01-02T00:00:00Z",
        },
    ]
    with patch.object(service, "_fetch_paginated_data") as mock_fetch:
        mock_fetch.side_effect = [mock_workspaces, mock_repos]
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        for repo in repositories:
            assert repo.owner_type == OwnerType.ORGANIZATION
            assert isinstance(repo, Repository)
            assert repo.git_provider == ServiceProviderType.BITBUCKET


@pytest.mark.asyncio
async def test_bitbucket_get_repositories_with_organization_owner_type():
    """Test that get_repositories correctly sets owner_type field for organization repositories."""
    service = BitBucketService(token=SecretStr("test-token"))
    mock_workspaces = [{"slug": "test-org", "name": "Test Organization"}]
    mock_repos = [
        {
            "uuid": "repo-3",
            "slug": "org-repo1",
            "workspace": {"slug": "test-org", "is_private": False},
            "is_private": False,
            "updated_on": "2023-01-03T00:00:00Z",
        },
        {
            "uuid": "repo-4",
            "slug": "org-repo2",
            "workspace": {"slug": "test-org", "is_private": False},
            "is_private": True,
            "updated_on": "2023-01-04T00:00:00Z",
        },
    ]
    with patch.object(service, "_fetch_paginated_data") as mock_fetch:
        mock_fetch.side_effect = [mock_workspaces, mock_repos]
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        for repo in repositories:
            assert repo.owner_type == OwnerType.ORGANIZATION
            assert isinstance(repo, Repository)
            assert repo.git_provider == ServiceProviderType.BITBUCKET


@pytest.mark.asyncio
async def test_bitbucket_get_repositories_mixed_owner_types():
    """Test that get_repositories correctly handles mixed user and organization repositories."""
    service = BitBucketService(token=SecretStr("test-token"))
    mock_workspaces = [
        {"slug": "test-user", "name": "Test User"},
        {"slug": "test-org", "name": "Test Organization"},
    ]
    mock_user_repos = [
        {
            "uuid": "repo-1",
            "slug": "user-repo",
            "workspace": {"slug": "test-user", "is_private": True},
            "is_private": False,
            "updated_on": "2023-01-01T00:00:00Z",
        }
    ]
    mock_org_repos = [
        {
            "uuid": "repo-2",
            "slug": "org-repo",
            "workspace": {"slug": "test-org", "is_private": False},
            "is_private": False,
            "updated_on": "2023-01-02T00:00:00Z",
        }
    ]
    with patch.object(service, "_fetch_paginated_data") as mock_fetch:
        mock_fetch.side_effect = [mock_workspaces, mock_user_repos, mock_org_repos]
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        user_repo = next(
            (repo for repo in repositories if "user-repo" in repo.full_name)
        )
        org_repo = next((repo for repo in repositories if "org-repo" in repo.full_name))
        assert user_repo.owner_type == OwnerType.ORGANIZATION
        assert org_repo.owner_type == OwnerType.ORGANIZATION


@patch("forge.core.setup.call_async_from_sync")
@patch("forge.core.setup.get_file_store")
@patch("forge.core.setup.EventStream")
def test_initialize_repository_for_runtime_with_bitbucket_token(
    mock_event_stream, mock_get_file_store, mock_call_async_from_sync
):
    """Test that initialize_repository_for_runtime properly handles BITBUCKET_TOKEN."""
    from forge.core.setup import initialize_repository_for_runtime
    from forge.integrations.provider import ProviderType

    mock_runtime = MagicMock()
    mock_runtime.clone_or_init_repo = AsyncMock(return_value="test-repo")
    mock_runtime.maybe_run_setup_script = MagicMock()
    mock_runtime.maybe_setup_git_hooks = MagicMock()
    mock_call_async_from_sync.return_value = "test-repo"
    with patch.dict(os.environ, {"BITBUCKET_TOKEN": "username:app_password"}):
        result = initialize_repository_for_runtime(
            runtime=mock_runtime, selected_repository="all-hands-ai/test-repo"
        )
    assert result == "test-repo"
    mock_call_async_from_sync.assert_called_once()
    args, kwargs = mock_call_async_from_sync.call_args
    assert args[0] == mock_runtime.clone_or_init_repo
    provider_tokens = args[2]
    assert provider_tokens is not None
    assert ProviderType.BITBUCKET in provider_tokens
    assert (
        provider_tokens[ProviderType.BITBUCKET].token.get_secret_value()
        == "username:app_password"
    )
    assert args[3] == "all-hands-ai/test-repo"
    assert args[4] is None


@patch("forge.core.setup.call_async_from_sync")
@patch("forge.core.setup.get_file_store")
@patch("forge.core.setup.EventStream")
def test_initialize_repository_for_runtime_with_multiple_tokens(
    mock_event_stream, mock_get_file_store, mock_call_async_from_sync
):
    """Test that initialize_repository_for_runtime handles multiple provider tokens including Bitbucket."""
    from forge.core.setup import initialize_repository_for_runtime
    from forge.integrations.provider import ProviderType

    mock_runtime = MagicMock()
    mock_runtime.clone_or_init_repo = AsyncMock(return_value="test-repo")
    mock_runtime.maybe_run_setup_script = MagicMock()
    mock_runtime.maybe_setup_git_hooks = MagicMock()
    mock_call_async_from_sync.return_value = "test-repo"
    with patch.dict(
        os.environ,
        {
            "GITHUB_TOKEN": "github_token_123",
            "GITLAB_TOKEN": "gitlab_token_456",
            "BITBUCKET_TOKEN": "username:bitbucket_app_password",
        },
    ):
        result = initialize_repository_for_runtime(
            runtime=mock_runtime, selected_repository="all-hands-ai/test-repo"
        )
    assert result == "test-repo"
    mock_call_async_from_sync.assert_called_once()
    args, kwargs = mock_call_async_from_sync.call_args
    provider_tokens = args[2]
    assert provider_tokens is not None
    assert ProviderType.GITHUB in provider_tokens
    assert ProviderType.GITLAB in provider_tokens
    assert ProviderType.BITBUCKET in provider_tokens
    assert (
        provider_tokens[ProviderType.GITHUB].token.get_secret_value()
        == "github_token_123"
    )
    assert (
        provider_tokens[ProviderType.GITLAB].token.get_secret_value()
        == "gitlab_token_456"
    )
    assert (
        provider_tokens[ProviderType.BITBUCKET].token.get_secret_value()
        == "username:bitbucket_app_password"
    )


@patch("forge.core.setup.call_async_from_sync")
@patch("forge.core.setup.get_file_store")
@patch("forge.core.setup.EventStream")
def test_initialize_repository_for_runtime_without_bitbucket_token(
    mock_event_stream, mock_get_file_store, mock_call_async_from_sync
):
    """Test that initialize_repository_for_runtime works without BITBUCKET_TOKEN."""
    from forge.core.setup import initialize_repository_for_runtime
    from forge.integrations.provider import ProviderType

    mock_runtime = MagicMock()
    mock_runtime.clone_or_init_repo = AsyncMock(return_value="test-repo")
    mock_runtime.maybe_run_setup_script = MagicMock()
    mock_runtime.maybe_setup_git_hooks = MagicMock()
    mock_call_async_from_sync.return_value = "test-repo"
    with patch.dict(
        os.environ,
        {"GITHUB_TOKEN": "github_token_123", "GITLAB_TOKEN": "gitlab_token_456"},
        clear=False,
    ):
        if "BITBUCKET_TOKEN" in os.environ:
            del os.environ["BITBUCKET_TOKEN"]
        result = initialize_repository_for_runtime(
            runtime=mock_runtime, selected_repository="all-hands-ai/test-repo"
        )
    assert result == "test-repo"
    mock_call_async_from_sync.assert_called_once()
    args, kwargs = mock_call_async_from_sync.call_args
    provider_tokens = args[2]
    assert provider_tokens is not None
    assert ProviderType.GITHUB in provider_tokens
    assert ProviderType.GITLAB in provider_tokens
    assert ProviderType.BITBUCKET not in provider_tokens
