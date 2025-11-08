from unittest.mock import AsyncMock, Mock, patch
import httpx
import pytest
from pydantic import SecretStr
from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import AuthenticationError, OwnerType, ProviderType, Repository, User
from forge.server.types import AppMode


@pytest.mark.asyncio
async def test_github_service_token_handling():
    token = SecretStr("test-token")
    service = GitHubService(user_id=None, token=token)
    assert service.token == token
    assert service.token.get_secret_value() == "test-token"
    headers = await service._get_headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Accept"] == "application/vnd.github.v3+json"
    service = GitHubService(user_id="test-user")
    assert service.token == SecretStr("")


@pytest.mark.asyncio
async def test_github_service_token_refresh():
    token = SecretStr("test-token")
    service = GitHubService(user_id=None, token=token)
    assert not service.refresh
    assert service._has_token_expired(401)
    assert not service._has_token_expired(200)
    assert not service._has_token_expired(404)
    latest_token = await service.get_latest_token()
    assert isinstance(latest_token, SecretStr)
    assert latest_token.get_secret_value() == "test-token"


@pytest.mark.asyncio
async def test_github_service_fetch_data():
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "test-user"}
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    with patch("httpx.AsyncClient", return_value=mock_client):
        service = GitHubService(user_id=None, token=SecretStr("test-token"))
        _ = await service._make_request("https://api.github.com/user")
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-token"
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="401 Unauthorized", request=Mock(), response=mock_response
        )
        mock_client.get.reset_mock()
        mock_client.get.return_value = mock_response
        with pytest.raises(AuthenticationError):
            _ = await service._make_request("https://api.github.com/user")


@pytest.mark.asyncio
async def test_github_get_repositories_with_user_owner_type():
    """Test that get_repositories correctly sets owner_type field for user repositories."""
    service = GitHubService(user_id=None, token=SecretStr("test-token"))
    mock_repo_data = [
        {
            "id": 123,
            "full_name": "test-user/test-repo",
            "private": False,
            "stargazers_count": 10,
            "owner": {"type": "User"},
        },
        {
            "id": 456,
            "full_name": "test-user/another-repo",
            "private": True,
            "stargazers_count": 5,
            "owner": {"type": "User"},
        },
    ]
    with patch.object(service, "_fetch_paginated_repos", return_value=mock_repo_data), patch.object(
        service, "get_installations", return_value=[123]
    ):
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        for repo in repositories:
            assert repo.owner_type == OwnerType.USER
            assert isinstance(repo, Repository)
            assert repo.git_provider == ProviderType.GITHUB


@pytest.mark.asyncio
async def test_github_get_repositories_with_organization_owner_type():
    """Test that get_repositories correctly sets owner_type field for organization repositories."""
    service = GitHubService(user_id=None, token=SecretStr("test-token"))
    mock_repo_data = [
        {
            "id": 789,
            "full_name": "test-org/org-repo",
            "private": False,
            "stargazers_count": 25,
            "owner": {"type": "Organization"},
        },
        {
            "id": 101,
            "full_name": "test-org/another-org-repo",
            "private": True,
            "stargazers_count": 15,
            "owner": {"type": "Organization"},
        },
    ]
    with patch.object(service, "_fetch_paginated_repos", return_value=mock_repo_data), patch.object(
        service, "get_installations", return_value=[123]
    ):
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        for repo in repositories:
            assert repo.owner_type == OwnerType.ORGANIZATION
            assert isinstance(repo, Repository)
            assert repo.git_provider == ProviderType.GITHUB


@pytest.mark.asyncio
async def test_github_get_repositories_mixed_owner_types():
    """Test that get_repositories correctly handles mixed user and organization repositories."""
    service = GitHubService(user_id=None, token=SecretStr("test-token"))
    mock_repo_data = [
        {
            "id": 123,
            "full_name": "test-user/user-repo",
            "private": False,
            "stargazers_count": 10,
            "owner": {"type": "User"},
        },
        {
            "id": 456,
            "full_name": "test-org/org-repo",
            "private": True,
            "stargazers_count": 25,
            "owner": {"type": "Organization"},
        },
    ]
    with patch.object(service, "_fetch_paginated_repos", return_value=mock_repo_data), patch.object(
        service, "get_installations", return_value=[123]
    ):
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        assert len(repositories) == 2
        user_repo = next((repo for repo in repositories if "user-repo" in repo.full_name))
        org_repo = next((repo for repo in repositories if "org-repo" in repo.full_name))
        assert user_repo.owner_type == OwnerType.USER
        assert org_repo.owner_type == OwnerType.ORGANIZATION


@pytest.mark.asyncio
async def test_github_get_repositories_owner_type_fallback():
    """Test that owner_type defaults to USER when owner type is not 'Organization'."""
    service = GitHubService(user_id=None, token=SecretStr("test-token"))
    mock_repo_data = [
        {
            "id": 123,
            "full_name": "test-user/test-repo",
            "private": False,
            "stargazers_count": 10,
            "owner": {"type": "User"},
        },
        {
            "id": 456,
            "full_name": "test-user/another-repo",
            "private": True,
            "stargazers_count": 5,
            "owner": {"type": "Bot"},
        },
        {"id": 789, "full_name": "test-user/third-repo", "private": False, "stargazers_count": 15, "owner": {}},
    ]
    with patch.object(service, "_fetch_paginated_repos", return_value=mock_repo_data), patch.object(
        service, "get_installations", return_value=[123]
    ):
        repositories = await service.get_all_repositories("pushed", AppMode.SAAS)
        for repo in repositories:
            assert repo.owner_type == OwnerType.USER


@pytest.mark.asyncio
async def test_github_search_repositories_with_organizations():
    """Test that search_repositories includes user organizations in the search scope."""
    service = GitHubService(user_id="test-user", token=SecretStr("test-token"))
    mock_user = User(id="123", login="testuser", avatar_url="https://example.com/avatar.jpg")
    mock_search_response = {
        "items": [
            {
                "id": 1,
                "name": "forge",
                "full_name": "All-Hands-AI/Forge",
                "private": False,
                "html_url": "https://github.com/All-Hands-AI/Forge",
                "clone_url": "https://github.com/All-Hands-AI/forge.git",
                "pushed_at": "2023-01-01T00:00:00Z",
                "owner": {"login": "All-Hands-AI", "type": "Organization"},
            }
        ]
    }
    with patch.object(service, "get_user", return_value=mock_user), patch.object(
        service, "get_user_organizations", return_value=["All-Hands-AI", "example-org"]
    ), patch.object(service, "_make_request", return_value=(mock_search_response, {})) as mock_request:
        repositories = await service.search_repositories(
            query="forge", per_page=10, sort="stars", order="desc", public=False
        )
        assert mock_request.call_count == 3
        calls = mock_request.call_args_list
        user_call = calls[0]
        user_params = user_call[0][1]
        assert user_params["q"] == "Forge user:testuser"
        org1_call = calls[1]
        org1_params = org1_call[0][1]
        assert org1_params["q"] == "Forge org:All-Hands-AI"
        org2_call = calls[2]
        org2_params = org2_call[0][1]
        assert org2_params["q"] == "Forge org:example-org"
        assert len(repositories) == 3
        assert all((repo.full_name == "All-Hands-AI/Forge" for repo in repositories))


@pytest.mark.asyncio
async def test_github_get_user_organizations():
    """Test that get_user_organizations fetches user's organizations."""
    service = GitHubService(user_id="test-user", token=SecretStr("test-token"))
    mock_orgs_response = [{"login": "All-Hands-AI", "id": 1}, {"login": "example-org", "id": 2}]
    with patch.object(service, "_make_request", return_value=(mock_orgs_response, {})):
        orgs = await service.get_user_organizations()
        assert orgs == ["All-Hands-AI", "example-org"]


@pytest.mark.asyncio
async def test_github_get_user_organizations_error_handling():
    """Test that get_user_organizations handles errors gracefully."""
    service = GitHubService(user_id="test-user", token=SecretStr("test-token"))
    with patch.object(service, "_make_request", side_effect=Exception("API Error")):
        orgs = await service.get_user_organizations()
        assert orgs == []


@pytest.mark.asyncio
async def test_github_service_base_url_configuration():
    """Test that BASE_URL is correctly configured based on base_domain."""
    service = GitHubService(user_id=None, token=SecretStr("test-token"))
    assert service.BASE_URL == "https://api.github.com"
    service = GitHubService(user_id=None, token=SecretStr("test-token"), base_domain="github.enterprise.com")
    assert service.BASE_URL == "https://github.enterprise.com/api/v3"
    service = GitHubService(user_id=None, token=SecretStr("test-token"), base_domain="github.com")
    assert service.BASE_URL == "https://api.github.com"


@pytest.mark.asyncio
async def test_github_service_graphql_url_enterprise_server():
    """Test that GraphQL URL is correctly constructed for GitHub Enterprise Server."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"viewer": {"login": "test-user"}}}
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    with patch("httpx.AsyncClient", return_value=mock_client):
        service = GitHubService(user_id=None, token=SecretStr("test-token"), base_domain="github.enterprise.com")
        query = "query { viewer { login } }"
        variables = {}
        await service.execute_graphql_query(query, variables)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        actual_url = call_args[0][0]
        assert actual_url == "https://github.enterprise.com/api/graphql"


@pytest.mark.asyncio
async def test_github_service_graphql_url_github_com():
    """Test that GraphQL URL is correctly constructed for GitHub.com."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"viewer": {"login": "test-user"}}}
    mock_response.raise_for_status = Mock()
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    with patch("httpx.AsyncClient", return_value=mock_client):
        service = GitHubService(user_id=None, token=SecretStr("test-token"))
        query = "query { viewer { login } }"
        variables = {}
        await service.execute_graphql_query(query, variables)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        actual_url = call_args[0][0]
        assert actual_url == "https://api.github.com/graphql"
