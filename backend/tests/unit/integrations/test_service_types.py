"""Comprehensive tests for forge.integrations.service_types."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from forge.integrations.service_types import (
    Branch,
    Comment,
    CreateMicroagent,
    OwnerType,
    PaginatedBranchesResponse,
    ProviderType,
    Repository,
    SuggestedTask,
    TaskType,
    TokenResponse,
    User,
)


class TestTokenResponse:
    """Test TokenResponse model validators."""

    def test_valid(self):
        """Test TokenResponse with valid token."""
        response = TokenResponse(token="valid-token-123")
        assert response.token == "valid-token-123"

    def test_empty_token(self):
        """Test TokenResponse rejects empty token."""
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(token="")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_whitespace_token(self):
        """Test TokenResponse rejects whitespace-only token."""
        # TokenResponse uses min_length=1, so whitespace passes length check
        # The validator should reject whitespace-only strings
        with pytest.raises(ValidationError) as exc_info:
            TokenResponse(token="   ")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "token cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)


class TestSuggestedTask:
    """Test SuggestedTask model validators."""

    def test_valid(self):
        """Test SuggestedTask with valid values."""
        task = SuggestedTask(
            git_provider=ProviderType.GITHUB,
            task_type=TaskType.OPEN_ISSUE,
            repo="owner/repo",
            issue_number=42,
            title="Fix bug"
        )
        assert task.repo == "owner/repo"
        assert task.title == "Fix bug"

    def test_empty_repo(self):
        """Test SuggestedTask rejects empty repo."""
        with pytest.raises(ValidationError) as exc_info:
            SuggestedTask(
                git_provider=ProviderType.GITHUB,
                task_type=TaskType.OPEN_ISSUE,
                repo="",
                issue_number=1,
                title="Title"
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_empty_title(self):
        """Test SuggestedTask rejects empty title."""
        with pytest.raises(ValidationError) as exc_info:
            SuggestedTask(
                git_provider=ProviderType.GITHUB,
                task_type=TaskType.OPEN_ISSUE,
                repo="owner/repo",
                issue_number=1,
                title=""
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_invalid_issue_number(self):
        """Test SuggestedTask rejects invalid issue_number."""
        with pytest.raises(ValidationError) as exc_info:
            SuggestedTask(
                git_provider=ProviderType.GITHUB,
                task_type=TaskType.OPEN_ISSUE,
                repo="owner/repo",
                issue_number=0,  # Must be >= 1
                title="Title"
            )
        assert "greater than or equal to 1" in str(exc_info.value)


class TestCreateMicroagent:
    """Test CreateMicroagent model validators."""

    def test_valid(self):
        """Test CreateMicroagent with valid values."""
        microagent = CreateMicroagent(
            repo="owner/repo",
            git_provider=ProviderType.GITHUB,
            title="My Microagent"
        )
        assert microagent.repo == "owner/repo"
        assert microagent.git_provider == ProviderType.GITHUB
        assert microagent.title == "My Microagent"

    def test_empty_repo(self):
        """Test CreateMicroagent rejects empty repo."""
        with pytest.raises(ValidationError) as exc_info:
            CreateMicroagent(repo="")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_empty_title(self):
        """Test CreateMicroagent rejects empty title when provided."""
        # Title is optional, but if provided, it should be validated
        # The validator checks if v is not None, then validates
        with pytest.raises(ValidationError) as exc_info:
            CreateMicroagent(repo="owner/repo", title="")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "title must be a non-empty string" in error_str or
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_none_title_allowed(self):
        """Test CreateMicroagent allows None title."""
        microagent = CreateMicroagent(repo="owner/repo", title=None)
        assert microagent.title is None


class TestUser:
    """Test User model validators."""

    def test_valid(self):
        """Test User with valid values."""
        user = User(
            id="123",
            login="testuser",
            avatar_url="https://example.com/avatar.png"
        )
        assert user.id == "123"
        assert user.login == "testuser"
        assert user.avatar_url == "https://example.com/avatar.png"

    def test_empty_id(self):
        """Test User rejects empty id."""
        with pytest.raises(ValidationError) as exc_info:
            User(id="", login="user", avatar_url="https://example.com/avatar.png")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_empty_login(self):
        """Test User rejects empty login."""
        with pytest.raises(ValidationError) as exc_info:
            User(id="123", login="", avatar_url="https://example.com/avatar.png")
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_invalid_avatar_url(self):
        """Test User rejects invalid avatar_url format."""
        with pytest.raises(ValidationError) as exc_info:
            User(id="123", login="user", avatar_url="not-a-url")
        assert "must start with http:// or https://" in str(exc_info.value)

    def test_valid_http_avatar_url(self):
        """Test User accepts http:// avatar_url."""
        user = User(id="123", login="user", avatar_url="http://example.com/avatar.png")
        assert user.avatar_url == "http://example.com/avatar.png"

    def test_optional_fields(self):
        """Test User optional fields."""
        user = User(
            id="123",
            login="user",
            avatar_url="https://example.com/avatar.png",
            company="Acme Corp",
            name="Test User",
            email="test@example.com"
        )
        assert user.company == "Acme Corp"
        assert user.name == "Test User"
        assert user.email == "test@example.com"


class TestBranch:
    """Test Branch model validators."""

    def test_valid(self):
        """Test Branch with valid values."""
        branch = Branch(
            name="main",
            commit_sha="abc123def456",
            protected=False
        )
        assert branch.name == "main"
        assert branch.commit_sha == "abc123def456"
        assert branch.protected is False

    def test_empty_name(self):
        """Test Branch rejects empty name."""
        with pytest.raises(ValidationError) as exc_info:
            Branch(name="", commit_sha="abc123", protected=False)
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_empty_commit_sha(self):
        """Test Branch rejects empty commit_sha."""
        with pytest.raises(ValidationError) as exc_info:
            Branch(name="main", commit_sha="", protected=False)
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_branch_optional_last_push_date(self):
        """Test Branch optional last_push_date field."""
        branch = Branch(
            name="main",
            commit_sha="abc123",
            protected=False,
            last_push_date="2024-01-01T00:00:00Z"
        )
        assert branch.last_push_date == "2024-01-01T00:00:00Z"


class TestPaginatedBranchesResponse:
    """Test PaginatedBranchesResponse model validators."""

    def test_paginated_branches_response_valid(self):
        """Test PaginatedBranchesResponse with valid values."""
        branches = [
            Branch(name="main", commit_sha="abc123", protected=False),
            Branch(name="dev", commit_sha="def456", protected=True)
        ]
        response = PaginatedBranchesResponse(
            branches=branches,
            has_next_page=True,
            current_page=1,
            per_page=30,
            total_count=50
        )
        assert len(response.branches) == 2
        assert response.has_next_page is True
        assert response.current_page == 1
        assert response.per_page == 30
        assert response.total_count == 50

    def test_paginated_branches_response_invalid_page(self):
        """Test PaginatedBranchesResponse rejects invalid current_page."""
        with pytest.raises(ValidationError) as exc_info:
            PaginatedBranchesResponse(
                branches=[],
                has_next_page=False,
                current_page=0,  # Must be >= 1
                per_page=30
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_paginated_branches_response_invalid_per_page(self):
        """Test PaginatedBranchesResponse rejects invalid per_page."""
        with pytest.raises(ValidationError) as exc_info:
            PaginatedBranchesResponse(
                branches=[],
                has_next_page=False,
                current_page=1,
                per_page=0  # Must be >= 1
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_paginated_branches_response_invalid_total_count(self):
        """Test PaginatedBranchesResponse rejects negative total_count."""
        with pytest.raises(ValidationError) as exc_info:
            PaginatedBranchesResponse(
                branches=[],
                has_next_page=False,
                current_page=1,
                per_page=30,
                total_count=-1  # Must be >= 0
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_paginated_branches_response_none_total_count(self):
        """Test PaginatedBranchesResponse allows None total_count."""
        response = PaginatedBranchesResponse(
            branches=[],
            has_next_page=False,
            current_page=1,
            per_page=30,
            total_count=None
        )
        assert response.total_count is None


class TestRepository:
    """Test Repository model validators."""

    def test_repository_valid(self):
        """Test Repository with valid values."""
        repo = Repository(
            id="123",
            full_name="owner/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True
        )
        assert repo.id == "123"
        assert repo.full_name == "owner/repo"
        assert repo.git_provider == ProviderType.GITHUB
        assert repo.is_public is True

    def test_repository_empty_id(self):
        """Test Repository rejects empty id."""
        with pytest.raises(ValidationError) as exc_info:
            Repository(
                id="",
                full_name="owner/repo",
                git_provider=ProviderType.GITHUB,
                is_public=True
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_repository_empty_full_name(self):
        """Test Repository rejects empty full_name."""
        with pytest.raises(ValidationError) as exc_info:
            Repository(
                id="123",
                full_name="",
                git_provider=ProviderType.GITHUB,
                is_public=True
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_repository_optional_fields(self):
        """Test Repository optional fields."""
        repo = Repository(
            id="123",
            full_name="owner/repo",
            git_provider=ProviderType.GITHUB,
            is_public=True,
            stargazers_count=100,
            link_header="<https://api.github.com/repos?page=2>; rel=\"next\"",
            pushed_at="2024-01-01T00:00:00Z",
            owner_type=OwnerType.ORGANIZATION,
            main_branch="main"
        )
        assert repo.stargazers_count == 100
        assert repo.link_header is not None
        assert repo.pushed_at == "2024-01-01T00:00:00Z"
        assert repo.owner_type == OwnerType.ORGANIZATION
        assert repo.main_branch == "main"

    def test_repository_invalid_stargazers_count(self):
        """Test Repository rejects negative stargazers_count."""
        with pytest.raises(ValidationError) as exc_info:
            Repository(
                id="123",
                full_name="owner/repo",
                git_provider=ProviderType.GITHUB,
                is_public=True,
                stargazers_count=-1  # Must be >= 0
            )
        assert "greater than or equal to 0" in str(exc_info.value)


class TestComment:
    """Test Comment model validators."""

    def test_comment_valid(self):
        """Test Comment with valid values."""
        now = datetime.now()
        comment = Comment(
            id="123",
            body="This is a comment",
            author="testuser",
            created_at=now,
            updated_at=now
        )
        assert comment.id == "123"
        assert comment.body == "This is a comment"
        assert comment.author == "testuser"
        assert comment.created_at == now
        assert comment.updated_at == now
        assert comment.system is False  # Default value

    def test_comment_empty_id(self):
        """Test Comment rejects empty id."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            Comment(
                id="",
                body="Comment",
                author="user",
                created_at=now,
                updated_at=now
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_comment_empty_author(self):
        """Test Comment rejects empty author."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            Comment(
                id="123",
                body="Comment",
                author="",
                created_at=now,
                updated_at=now
            )
        error_str = str(exc_info.value)
        assert ("field must be a non-empty string" in error_str or 
                "cannot be empty or whitespace-only" in error_str or
                "String should have at least 1 character" in error_str)

    def test_comment_system_flag(self):
        """Test Comment system flag."""
        now = datetime.now()
        comment = Comment(
            id="123",
            body="System comment",
            author="system",
            created_at=now,
            updated_at=now,
            system=True
        )
        assert comment.system is True

    def test_comment_empty_body_allowed(self):
        """Test Comment allows empty body."""
        now = datetime.now()
        comment = Comment(
            id="123",
            body="",
            author="user",
            created_at=now,
            updated_at=now
        )
        assert comment.body == ""


class TestSuggestedTaskProviderTerms:
    """Test SuggestedTask.get_provider_terms method."""

    def test_get_provider_terms_github(self):
        """Test get_provider_terms for GitHub."""
        task = SuggestedTask(
            git_provider=ProviderType.GITHUB,
            task_type=TaskType.OPEN_ISSUE,
            repo="owner/repo",
            issue_number=1,
            title="Title"
        )
        terms = task.get_provider_terms()
        assert terms["requestType"] == "Pull Request"
        assert terms["requestTypeShort"] == "PR"
        assert terms["apiName"] == "GitHub API"
        assert terms["tokenEnvVar"] == "GITHUB_TOKEN"
        assert terms["ciSystem"] == "GitHub Actions"
        assert terms["ciProvider"] == "GitHub"
        assert terms["requestVerb"] == "pull request"

    def test_get_provider_terms_invalid_provider(self):
        """Test get_provider_terms raises error for invalid provider."""
        task = SuggestedTask(
            git_provider=ProviderType.ENTERPRISE_SSO,
            task_type=TaskType.OPEN_ISSUE,
            repo="owner/repo",
            issue_number=1,
            title="Title"
        )
        with pytest.raises(ValueError, match="Provider.*for suggested task prompts"):
            task.get_provider_terms()


# Note: SuggestedTask.get_prompt_for_task is already tested in test_service_types_additional.py
# Removing duplicates to avoid redundancy

