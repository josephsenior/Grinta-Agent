"""Factory helpers for provisioning resolver service handlers per provider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.integrations.service_types import ProviderType
from backend.resolver.interfaces.github import GithubIssueHandler, GithubPRHandler
from backend.resolver.interfaces.issue_definitions import (
    ServiceContextIssue,
    ServiceContextPR,
)

if TYPE_CHECKING:
    from backend.core.config import LLMConfig


class IssueHandlerFactory:
    """Factory that instantiates provider-specific issue/PR handlers."""

    def __init__(
        self,
        owner: str,
        repo: str,
        token: str,
        username: str,
        platform: ProviderType,
        base_domain: str,
        issue_type: str,
        llm_config: LLMConfig,
    ) -> None:
        """Capture provider context, credentials, and requested issue type for handler creation."""
        self.owner = owner
        self.repo = repo
        self.token = token
        self.username = username
        self.platform = platform
        self.base_domain = base_domain
        self.issue_type = issue_type
        self.llm_config = llm_config

    def create(self) -> ServiceContextIssue | ServiceContextPR:
        """Return appropriate ServiceContext wrapper for configured provider/issue type."""
        if self.issue_type == "issue":
            if str(self.platform) == str(ProviderType.GITHUB) or self.platform == "github":
                return ServiceContextIssue(
                    GithubIssueHandler(
                        self.owner,
                        self.repo,
                        self.token,
                        self.username,
                        self.base_domain,
                    ),
                    self.llm_config,
                )
            msg = f"Unsupported platform: {self.platform}"
            raise ValueError(msg)
        if self.issue_type == "pr":
            if str(self.platform) == str(ProviderType.GITHUB) or self.platform == "github":
                return ServiceContextPR(
                    GithubPRHandler(
                        self.owner,
                        self.repo,
                        self.token,
                        self.username,
                        self.base_domain,
                    ),
                    self.llm_config,
                )
            msg = f"Unsupported platform: {self.platform}"
            raise ValueError(msg)
        msg = f"Unsupported issue type: {self.issue_type}"
        raise ValueError(msg)
