"""Shared type definitions and abstract services for Forge Git integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field, SecretStr, field_validator

from backend.core.logger import forge_logger as logger
from backend.instruction.playbook import BasePlaybook
from backend.instruction.types import PlaybookContentResponse, PlaybookResponse

if TYPE_CHECKING:
    from backend.server.types import AppMode


class TokenResponse(BaseModel):
    """Response model for authentication token."""

    token: str = Field(
        ...,
        min_length=1,
        description="Authentication token string"
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate token is non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="token")


class ProviderType(Enum):
    """Git provider type enumeration."""

    GITHUB = "github"
    ENTERPRISE_SSO = "enterprise_sso"


class TaskType(str, Enum):
    """Task type enumeration for suggested tasks."""

    MERGE_CONFLICTS = "MERGE_CONFLICTS"
    FAILING_CHECKS = "FAILING_CHECKS"
    UNRESOLVED_COMMENTS = "UNRESOLVED_COMMENTS"
    OPEN_ISSUE = "OPEN_ISSUE"
    OPEN_PR = "OPEN_PR"
    CREATE_PLAYBOOK = "CREATE_PLAYBOOK"


class OwnerType(str, Enum):
    """Owner type enumeration for repositories."""

    USER = "user"
    ORGANIZATION = "organization"


class SuggestedTask(BaseModel):
    """Model representing a suggested task from a git provider."""

    git_provider: ProviderType = Field(
        ...,
        description="Git provider type (GitHub)"
    )
    task_type: TaskType = Field(
        ...,
        description="Type of suggested task"
    )
    repo: str = Field(
        ...,
        min_length=1,
        description="Repository name in format 'owner/repo'"
    )
    issue_number: int = Field(
        ...,
        ge=1,
        description="Issue or PR number"
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Task title"
    )

    @field_validator("repo", "title")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")

    def get_provider_terms(self) -> dict:
        """Get provider-specific terminology dictionary.

        Returns:
            Dictionary with provider-specific terms (PR/MR, API names, etc.)

        Raises:
            ValueError: If provider type is not supported

        """
        if self.git_provider == ProviderType.GITHUB:
            return {
                "requestType": "Pull Request",
                "requestTypeShort": "PR",
                "apiName": "GitHub API",
                "tokenEnvVar": "GITHUB_TOKEN",
                "ciSystem": "GitHub Actions",
                "ciProvider": "GitHub",
                "requestVerb": "pull request",
            }
        msg = f"Provider {self.git_provider} for suggested task prompts"
        raise ValueError(msg)

    def get_prompt_for_task(self) -> str:
        """Generate prompt text for the suggested task.

        Renders Jinja2 template based on task type with provider-specific terms.

        Returns:
            Rendered prompt string for the task

        Raises:
            ValueError: If task type is not supported

        """
        task_type = self.task_type
        issue_number = self.issue_number
        repo = self.repo
        # nosec B701 - Template rendering for prompts (not HTML), autoescape enabled
        env = Environment(
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates", "suggested_task")),
            autoescape=True,
        )
        template = None
        if task_type == TaskType.MERGE_CONFLICTS:
            template = env.get_template("merge_conflict_prompt.j2")
        elif task_type == TaskType.FAILING_CHECKS:
            template = env.get_template("failing_checks_prompt.j2")
        elif task_type == TaskType.UNRESOLVED_COMMENTS:
            template = env.get_template("unresolved_comments_prompt.j2")
        elif task_type == TaskType.OPEN_ISSUE:
            template = env.get_template("open_issue_prompt.j2")
        else:
            msg = f"Unsupported task type: {task_type}"
            raise ValueError(msg)
        terms = self.get_provider_terms()
        return template.render(issue_number=issue_number, repo=repo, **terms)


class CreatePlaybook(BaseModel):
    """Model for creating a new playbook."""

    repo: str = Field(
        ...,
        min_length=1,
        description="Repository name in format 'owner/repo'"
    )
    git_provider: ProviderType | None = Field(
        default=None,
        description="Git provider type (optional, will be auto-detected)"
    )
    title: str | None = Field(
        default=None,
        description="Optional title for the playbook"
    )

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Validate repository name is non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="repo")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Validate title is non-empty if provided."""
        if v is not None:
            from backend.core.type_safety.type_safety import validate_non_empty_string
            return validate_non_empty_string(v, name="title")
        return v


class User(BaseModel):
    """Model representing a user from a git provider."""

    id: str = Field(
        ...,
        min_length=1,
        description="User ID"
    )
    login: str = Field(
        ...,
        min_length=1,
        description="Username/login"
    )
    avatar_url: str = Field(
        ...,
        min_length=1,
        description="URL to user's avatar image"
    )
    company: str | None = Field(
        default=None,
        description="User's company name"
    )
    name: str | None = Field(
        default=None,
        description="User's display name"
    )
    email: str | None = Field(
        default=None,
        description="User's email address"
    )

    @field_validator("id", "login", "avatar_url")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str) -> str:
        """Validate avatar URL format."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        validated = validate_non_empty_string(v, name="avatar_url")
        # Basic URL format check
        if not validated.startswith(("http://", "https://")):
            raise ValueError("avatar_url must start with http:// or https://")
        return validated


class Branch(BaseModel):
    """Model representing a git branch."""

    name: str = Field(
        ...,
        min_length=1,
        description="Branch name"
    )
    commit_sha: str = Field(
        ...,
        description="SHA of the latest commit on this branch"
    )
    protected: bool = Field(
        ...,
        description="Whether the branch is protected"
    )
    last_push_date: str | None = Field(
        default=None,
        description="ISO timestamp of the last push to this branch"
    )

    @field_validator("name")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")


class PaginatedBranchesResponse(BaseModel):
    """Response model for paginated branch list."""

    branches: list[Branch] = Field(
        ...,
        description="List of branches in this page"
    )
    has_next_page: bool = Field(
        ...,
        description="Whether there are more pages available"
    )
    current_page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)"
    )
    per_page: int = Field(
        ...,
        ge=1,
        description="Number of items per page"
    )
    total_count: int | None = Field(
        default=None,
        ge=0,
        description="Total number of branches (if available)"
    )


class Repository(BaseModel):
    """Model representing a git repository."""

    id: str = Field(
        ...,
        min_length=1,
        description="Repository ID"
    )
    full_name: str = Field(
        ...,
        min_length=1,
        description="Full repository name in format 'owner/repo'"
    )
    git_provider: ProviderType = Field(
        ...,
        description="Git provider type (GitHub)"
    )
    is_public: bool = Field(
        ...,
        description="Whether the repository is public"
    )
    stargazers_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of stars (if available)"
    )
    link_header: str | None = Field(
        default=None,
        description="Link header for pagination (if available)"
    )
    pushed_at: str | None = Field(
        default=None,
        description="ISO timestamp of last push (if available)"
    )
    owner_type: OwnerType | None = Field(
        default=None,
        description="Type of repository owner (user or organization)"
    )
    main_branch: str | None = Field(
        default=None,
        description="Name of the main/default branch"
    )

    @field_validator("id", "full_name")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")


class Comment(BaseModel):
    """Model representing a comment on an issue or PR."""

    id: str = Field(
        ...,
        min_length=1,
        description="Comment ID"
    )
    body: str = Field(
        ...,
        description="Comment body/content"
    )
    author: str = Field(
        ...,
        min_length=1,
        description="Username of the comment author"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the comment was created"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the comment was last updated"
    )
    system: bool = Field(
        default=False,
        description="Whether this is a system-generated comment"
    )

    @field_validator("id", "author")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from backend.core.type_safety.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")


class AuthenticationError(ValueError):
    """Raised when there is an issue with GitHub authentication."""


class UnknownException(ValueError):
    """Raised when there is an issue with GitHub communcation."""


class RateLimitError(ValueError):
    """Raised when the git provider's API rate limits are exceeded."""


class ResourceNotFoundError(ValueError):
    """Raised when a requested resource (file, directory, etc.) is not found."""


class PlaybookParseError(ValueError):
    """Raised when there is an error parsing a playbook file."""


class RequestMethod(Enum):
    """HTTP request method enumeration."""

    POST = "post"
    GET = "get"


class BaseGitService(ABC):
    """Abstract base class describing provider-specific git service implementations."""

    @property
    def provider(self) -> str:
        """Return underlying provider identifier (e.g., github)."""
        msg = "Subclasses must implement the provider property"
        raise NotImplementedError(msg)

    @abstractmethod
    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[Any, dict]: ...

    @abstractmethod
    async def _get_cursorrules_url(self, repository: str) -> str:
        """Get the URL for checking .cursorrules file."""
        ...

    @abstractmethod
    async def _get_playbooks_directory_url(
        self,
        repository: str,
        playbooks_path: str,
    ) -> str:
        """Get the URL for checking playbooks directory."""
        ...

    @abstractmethod
    def _get_playbooks_directory_params(self, playbooks_path: str) -> dict | None:
        """Get parameters for the playbooks directory request. Return None if no parameters needed."""
        ...

    @abstractmethod
    def _is_valid_playbook_file(self, item: dict) -> bool:
        """Check if an item represents a valid playbook file."""
        ...

    @abstractmethod
    def _get_file_name_from_item(self, item: dict) -> str:
        """Extract file name from directory item."""
        ...

    @abstractmethod
    def _get_file_path_from_item(self, item: dict, playbooks_path: str) -> str:
        """Extract file path from directory item."""
        ...

    def _determine_playbooks_path(self, repository_name: str) -> str:
        """Determine the playbooks directory path based on repository name."""
        actual_repo_name = repository_name.split("/")[-1]
        if actual_repo_name == ".Forge":
            return "playbooks"
        return ".Forge/playbooks"

    def _create_playbook_response(
        self,
        file_name: str,
        path: str,
    ) -> PlaybookResponse:
        """Create a playbook response from basic file information."""
        name = file_name.replace(".md", "").replace(".cursorrules", "cursorrules")
        return PlaybookResponse(name=name, path=path, created_at=datetime.now())

    def _parse_playbook_content(
        self,
        content: str,
        file_path: str,
    ) -> PlaybookContentResponse:
        """Parse playbook content and extract triggers using BasePlaybook.load.

        Args:
            content: Raw playbook file content
            file_path: Path to the file (used for playbook loading)

        Returns:
            PlaybookContentResponse with parsed content and triggers

        Raises:
            PlaybookParseError: If the playbook file cannot be parsed

        """
        try:
            temp_path = Path(file_path)
            playbook = BasePlaybook.load(path=temp_path, file_content=content)
            triggers = playbook.metadata.triggers
            return PlaybookContentResponse(
                content=playbook.content,
                path=file_path,
                triggers=triggers,
                git_provider=self.provider,
            )
        except Exception as e:
            logger.error(
                "Error parsing playbook content for %s: %s",
                file_path,
                str(e),
            )
            msg = f"Failed to parse playbook file {file_path}: {e!s}"
            raise PlaybookParseError(
                msg,
            ) from e

    async def _fetch_cursorrules_content(self, repository: str) -> Any | None:
        """Fetch .cursorrules file content from the repository via API.

        Args:
            repository: Repository name in format specific to the provider

        Returns:
            Raw API response content if .cursorrules file exists, None otherwise

        """
        cursorrules_url = await self._get_cursorrules_url(repository)
        cursorrules_response, _ = await self._make_request(cursorrules_url)
        return cursorrules_response

    async def _check_cursorrules_file(
        self,
        repository: str,
    ) -> PlaybookResponse | None:
        """Check for .cursorrules file in the repository and return playbook response if found.

        Args:
            repository: Repository name in format specific to the provider

        Returns:
            PlaybookResponse for .cursorrules file if found, None otherwise

        """
        try:
            cursorrules_content = await self._fetch_cursorrules_content(repository)
            if cursorrules_content:
                return self._create_playbook_response(".cursorrules", ".cursorrules")
        except ResourceNotFoundError:
            logger.debug("No .cursorrules file found in %s", repository)
        except Exception as e:
            logger.warning("Error checking .cursorrules file in %s: %s", repository, e)
        return None

    async def _process_playbooks_directory(
        self,
        repository: str,
        playbooks_path: str,
    ) -> list[PlaybookResponse]:
        """Process playbooks directory and return list of playbook responses.

        Args:
            repository: Repository name in format specific to the provider
            playbooks_path: Path to the playbooks directory

        Returns:
            List of PlaybookResponse objects found in the directory

        """
        playbooks = []
        try:
            directory_url = await self._get_playbooks_directory_url(
                repository,
                playbooks_path,
            )
            directory_params = self._get_playbooks_directory_params(playbooks_path)
            response, _ = await self._make_request(directory_url, directory_params)
            items = response
            if isinstance(response, dict) and "values" in response:
                items = response["values"]
            elif isinstance(response, dict) and "nodes" in response:
                items = response["nodes"]
            for item in items:
                if self._is_valid_playbook_file(item):
                    try:
                        file_name = self._get_file_name_from_item(item)
                        file_path = self._get_file_path_from_item(
                            item,
                            playbooks_path,
                        )
                        playbooks.append(
                            self._create_playbook_response(file_name, file_path),
                        )
                    except Exception as e:
                        logger.warning(
                            "Error processing playbook %s: %s",
                            item.get("name", "unknown"),
                            str(e),
                        )
        except ResourceNotFoundError:
            logger.info(
                "No playbooks directory found in %s at %s",
                repository,
                playbooks_path,
            )
        except Exception as e:
            logger.warning("Error fetching playbooks directory: %s", str(e))
        return playbooks

    async def get_playbooks(self, repository: str) -> list[PlaybookResponse]:
        """Generic implementation of get_playbooks that works across all providers.

        Args:
            repository: Repository name in format specific to the provider

        Returns:
            List of playbooks found in the repository (without content for performance)

        """
        playbooks_path = self._determine_playbooks_path(repository)
        playbooks = []
        cursorrules_playbook = await self._check_cursorrules_file(repository)
        if cursorrules_playbook:
            playbooks.append(cursorrules_playbook)
        directory_playbooks = await self._process_playbooks_directory(
            repository,
            playbooks_path,
        )
        playbooks.extend(directory_playbooks)
        return playbooks

    def _truncate_comment(
        self,
        comment_body: str,
        max_comment_length: int = 500,
    ) -> str:
        """Truncate comment body to a maximum length."""
        if len(comment_body) > max_comment_length:
            return f"{comment_body[:max_comment_length]}..."
        return comment_body


class InstallationsService(Protocol):
    """Protocol for provider clients exposing installation/workspace listing."""

    async def get_installations(self) -> list[str]:
        """Get installations for the service; repos live underneath these installations."""
        ...


class GitService(Protocol):
    """Protocol defining the interface for Git service providers."""

    def __init__(
        self,
        user_id: str | None = None,
        token: SecretStr | None = None,
        external_auth_id: str | None = None,
        external_auth_token: SecretStr | None = None,
        external_token_manager: bool = False,
        base_domain: str | None = None,
    ) -> None:
        """Initialize the service with authentication details."""
        ...

    async def get_latest_token(self) -> SecretStr | None:
        """Get latest working token of the user."""
        ...

    async def get_user(self) -> User:
        """Get the authenticated user's information."""
        ...

    async def search_repositories(
        self,
        query: str,
        per_page: int,
        sort: str,
        order: str,
        public: bool,
    ) -> list[Repository]:
        """Search for public repositories."""
        ...

    async def get_all_repositories(
        self,
        sort: str,
        app_mode: AppMode,
    ) -> list[Repository]:
        """Get repositories for the authenticated user."""
        ...

    async def get_paginated_repos(
        self,
        page: int,
        per_page: int,
        sort: str,
        installation_id: str | None,
        query: str | None = None,
    ) -> list[Repository]:
        """Get a page of repositories for the authenticated user."""
        ...

    async def get_suggested_tasks(self) -> list[SuggestedTask]:
        """Get suggested tasks for the authenticated user across all repositories."""
        ...

    async def get_repository_details_from_repo_name(
        self,
        repository: str,
    ) -> Repository:
        """Gets all repository details from repository name."""

    async def get_branches(self, repository: str) -> list[Branch]:
        """Get branches for a repository."""

    async def get_paginated_branches(
        self,
        repository: str,
        page: int = 1,
        per_page: int = 30,
    ) -> PaginatedBranchesResponse:
        """Get branches for a repository with pagination."""

    async def search_branches(
        self,
        repository: str,
        query: str,
        per_page: int = 30,
    ) -> list[Branch]:
        """Search for branches within a repository."""

    async def get_playbooks(self, repository: str) -> list[PlaybookResponse]:
        """Get playbooks from a repository."""
        ...

    async def get_playbook_content(
        self,
        repository: str,
        file_path: str,
    ) -> PlaybookContentResponse:
        """Get content of a specific playbook file.

        Returns:
            PlaybookContentResponse with parsed content and triggers

        """
        ...

    async def get_pr_details(self, repository: str, pr_number: int) -> dict:
        """Get detailed information about a specific pull request/merge request.

        Args:
            repository: Repository name in format specific to the provider
            pr_number: The pull request/merge request number

        Returns:
            Raw API response from the git provider

        """
        ...

    async def is_pr_open(self, repository: str, pr_number: int) -> bool:
        """Check if a PR is still active (not closed/merged).

        Args:
            repository: Repository name in format 'owner/repo'
            pr_number: The PR number to check

        Returns:
            True if PR is active (open), False if closed/merged

        """
        ...
