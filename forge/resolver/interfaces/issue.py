"""Common resolver issue abstractions shared across provider implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class ReviewThread(BaseModel):
    """Model representing a review thread with comments and affected files."""

    comment: str
    files: list[str]


class Issue(BaseModel):
    """Model representing an issue or pull request with all context."""

    owner: str
    repo: str
    number: int
    title: str
    body: str
    thread_comments: list[str] | None = None
    closing_issues: list[str] | None = None
    review_comments: list[str] | None = None
    review_threads: list[ReviewThread] | None = None
    thread_ids: list[str] | None = None
    head_branch: str | None = None
    base_branch: str | None = None


class IssueHandlerInterface(ABC):
    """Abstract interface for issue tracking platform integrations."""

    @abstractmethod
    def set_owner(self, owner: str) -> None:
        """Set repository owner for issue operations."""
        pass

    @abstractmethod
    def download_issues(self) -> list[Any]:
        """Download issues from the tracking platform."""
        pass

    @abstractmethod
    def get_issue_comments(
        self, issue_number: int, comment_id: int | None = None
    ) -> list[str] | None:
        """Get comments for an issue, optionally starting from a specific comment."""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """Get base URL of the repository/issue tracker."""
        pass

    @abstractmethod
    def get_branch_url(self, branch_name: str) -> str:
        """Get URL for a specific branch."""
        pass

    @abstractmethod
    def get_download_url(self) -> str:
        """Get repository download URL."""
        pass

    @abstractmethod
    def get_clone_url(self) -> str:
        """Get repository clone URL."""
        pass

    @abstractmethod
    def get_pull_url(self, pr_number: int) -> str:
        """Get URL for a specific pull request."""
        pass

    @abstractmethod
    def get_graphql_url(self) -> str:
        """Get GraphQL API URL for the service."""
        pass

    @abstractmethod
    def get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        pass

    @abstractmethod
    def get_compare_url(self, branch_name: str) -> str:
        """Get URL for comparing branch with default branch."""
        pass

    @abstractmethod
    def get_branch_name(self, base_branch_name: str) -> str:
        """Generate branch name for issue fix."""
        pass

    @abstractmethod
    def get_default_branch_name(self) -> str:
        """Get default branch name (e.g., 'main', 'master')."""
        pass

    @abstractmethod
    def branch_exists(self, branch_name: str) -> bool:
        """Check if a branch exists in the repository."""
        pass

    @abstractmethod
    def reply_to_comment(self, pr_number: int, comment_id: str, reply: str) -> None:
        """Reply to a specific comment on a pull request."""
        pass

    @abstractmethod
    def send_comment_msg(self, issue_number: int, msg: str) -> None:
        """Send a comment message to an issue."""
        pass

    @abstractmethod
    def get_authorize_url(self) -> str:
        """Get OAuth authorization URL."""
        pass

    @abstractmethod
    def create_pull_request(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create a pull request with the provided data."""
        if data is None:
            data = {}
        raise NotImplementedError

    @abstractmethod
    def request_reviewers(self, reviewer: str, pr_number: int) -> None:
        """Request review from a user on a pull request."""
        pass

    @abstractmethod
    def get_context_from_external_issues_references(
        self,
        closing_issues: list[str],
        closing_issue_numbers: list[int],
        issue_body: str,
        review_comments: list[str] | None,
        review_threads: list[ReviewThread],
        thread_comments: list[str] | None,
    ) -> list[str]:
        """Extract and format context from external issue references."""
        pass

    @abstractmethod
    def get_converted_issues(
        self,
        issue_numbers: list[int] | None = None,
        comment_id: int | None = None,
    ) -> list[Issue]:
        """Download issues from the git provider (GitHub, GitLab, or Bitbucket)."""
