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
    for var in ("GITHUB_TOKEN", "GITLAB_TOKEN", "BITBUCKET_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValueError, match="Token is required."):
        resolver._get_credentials(args)


def test_determine_base_domain_defaults():
    resolver = _make_resolver_stub()
    assert resolver._determine_base_domain(None, ProviderType.GITHUB) == "github.com"
    assert resolver._determine_base_domain(None, ProviderType.GITLAB) == "gitlab.com"
    assert (
        resolver._determine_base_domain(None, ProviderType.BITBUCKET) == "bitbucket.org"
    )
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
        base_container_image=None,
        runtime_container_image="custom/runtime",
        is_experimental=False,
        runtime="docker",
    )
    assert updated.default_agent == "CodeActAgent"
    assert updated.max_iterations == 5
    assert updated.workspace_base == "/tmp/workspace"
    assert updated.agents["CodeActAgent"].disabled_microagents == ["github"]
    assert updated.sandbox.runtime_container_image == "custom/runtime"


def test_resolve_runtime_image(monkeypatch):
    resolver = IssueResolver
    assert (
        resolver._resolve_runtime_image(
            runtime_img="runtime", base_img=None, is_experimental=False
        )
        == "runtime"
    )
    assert (
        resolver._resolve_runtime_image(
            runtime_img=None, base_img="base", is_experimental=False
        )
        is None
    )
    assert (
        resolver._resolve_runtime_image(
            runtime_img=None, base_img=None, is_experimental=True
        )
        is None
    )


def test_create_sandbox_config_gitlab_ci(monkeypatch):
    monkeypatch.setattr(IssueResolver, "GITLAB_CI", True, raising=False)
    monkeypatch.setattr(
        "forge.resolver.issue_resolver.os.getuid", lambda: 0, raising=False
    )
    monkeypatch.setattr("forge.resolver.issue_resolver.get_unique_uid", lambda: 1234)

    sandbox = IssueResolver._create_sandbox_config(
        base_img="base-img", runtime_img="runtime-img"
    )
    assert isinstance(sandbox, SandboxConfig)
    assert sandbox.base_container_image == "base-img"
    assert sandbox.runtime_container_image == "runtime-img"
    assert sandbox.user_id == 1234


def test_build_workspace_base(tmp_path):
    base = IssueResolver.build_workspace_base(str(tmp_path), "issue", 7)
    expected = tmp_path / "workspace" / "issue_7"
    assert base == str(expected.resolve())
