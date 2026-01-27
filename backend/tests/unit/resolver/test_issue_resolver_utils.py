"""Focused unit tests for IssueResolver helper methods."""

from __future__ import annotations

import os
from argparse import Namespace

import pytest

from forge.core.config import ForgeConfig, SandboxConfig
from forge.integrations.service_types import ProviderType
from forge.resolver.issue_resolver import IssueResolver


def _make_resolver_stub() -> IssueResolver:
    return IssueResolver.__new__(IssueResolver)  # type: ignore[call-arg]


def test_parse_repository_success():
    resolver = _make_resolver_stub()
    owner, repo = resolver._parse_repository("all-hands/forge")
    assert owner == "all-hands"
    assert repo == "forge"


def test_parse_repository_invalid():
    resolver = _make_resolver_stub()
    with pytest.raises(ValueError, match="Invalid repository format"):
        resolver._parse_repository("invalid-format")


def test_get_credentials_from_args(monkeypatch):
    resolver = _make_resolver_stub()
    args = Namespace(token=None, username=None)
    monkeypatch.setenv("GIT_USERNAME", "forge-user")
    monkeypatch.setenv("GITHUB_TOKEN", "gh-token")
    token, username = resolver._get_credentials(args)
    assert token == "gh-token"
    assert username == "forge-user"


def test_get_credentials_missing_username(monkeypatch):
    resolver = _make_resolver_stub()
    args = Namespace(token=None, username=None)
    monkeypatch.delenv("GIT_USERNAME", raising=False)
    with pytest.raises(ValueError, match="Username is required."):
        resolver._get_credentials(args)


def test_get_credentials_missing_token(monkeypatch):
    resolver = _make_resolver_stub()
    args = Namespace(token=None, username="forge-user")
    for var in ("GITHUB_TOKEN",):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError, match="Token is required."):
        resolver._get_credentials(args)


def test_determine_base_domain_defaults():
    resolver = _make_resolver_stub()
    assert resolver._determine_base_domain(None, ProviderType.GITHUB) == "github.com"
    assert (
        resolver._determine_base_domain("custom.example.com", ProviderType.GITHUB)
        == "custom.example.com"
    )


def test_update_forge_config_sets_fields():
    config = ForgeConfig()
    updated = IssueResolver.update_FORGE_config(
        config=config,
        max_iterations=5,
        workspace_base="/tmp/workspace",
        runtime="local",
    )
    assert updated.default_agent == "CodeActAgent"
    assert updated.max_iterations == 5
    assert updated.agents["CodeActAgent"].disabled_microagents == ["github"]
    assert updated.sandbox.timeout == 300


def test_build_workspace_base(tmp_path):
    base = IssueResolver.build_workspace_base(str(tmp_path), "issue", 7)
    expected = tmp_path / "workspace" / "issue_7"
    assert base == str(expected.resolve())
