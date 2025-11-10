"""Unit tests for MCP routes helper functions and tools."""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

import pytest

from fastapi import status

from forge.integrations.service_types import ProviderType
from forge.server.routes import mcp as original_mcp_routes


def _async_wrap(fn):
    async def inner(*args, **kwargs):
        return fn(*args, **kwargs)

    return inner


# Ensure global reference exists for linting
mcp_routes = original_mcp_routes


@pytest.fixture(scope="module")
def mcp_module():
    import fastmcp

    original_fastmcp = fastmcp.FastMCP

    class DummyMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

    fastmcp.FastMCP = DummyMCP  # type: ignore
    mod = importlib.reload(original_mcp_routes)
    globals()["mcp_routes"] = mod
    yield mod
    fastmcp.FastMCP = original_fastmcp  # type: ignore
    importlib.reload(original_mcp_routes)
    globals()["mcp_routes"] = original_mcp_routes


@pytest.mark.asyncio
async def test_get_conversation_link_returns_body_when_not_saas(monkeypatch, mcp_module):
    monkeypatch.setattr(mcp_module.server_config, "app_mode", mcp_module.AppMode.OSS)
    service = SimpleNamespace(get_user=_async_wrap(lambda: SimpleNamespace(login="user")))
    body = await mcp_module.get_conversation_link(service, "cid", "body")
    assert body == "body"


@pytest.mark.asyncio
async def test_get_conversation_link_appends_link(monkeypatch, mcp_module):
    monkeypatch.setattr(mcp_module.server_config, "app_mode", mcp_module.AppMode.SAAS)
    service = SimpleNamespace(get_user=_async_wrap(lambda: SimpleNamespace(login="user")))
    body = await mcp_module.get_conversation_link(service, "cid", "body")
    assert "continue refining the PR" in body


@pytest.mark.asyncio
async def test_save_pr_metadata_extracts_pr(monkeypatch, mcp_module):
    conversation = SimpleNamespace(pr_number=[], conversation_id="cid")
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: conversation),
        save_metadata=_async_wrap(lambda convo: None),
    )

    class DummyStoreImpl:
        @staticmethod
        async def get_instance(config, user_id):
            return store

    monkeypatch.setattr(mcp_module, "get_conversation_store", lambda: DummyStoreImpl)
    monkeypatch.setattr(mcp_module, "get_config", lambda: "config")
    await mcp_module.save_pr_metadata("user", "cid", "https://github.com/org/repo/pull/42")
    assert conversation.pr_number == [42]


@pytest.mark.asyncio
async def test_save_pr_metadata_handles_missing_pr(monkeypatch, mcp_module):
    conversation = SimpleNamespace(pr_number=[], conversation_id="cid")
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: conversation),
        save_metadata=_async_wrap(lambda convo: None),
    )

    class DummyStoreImpl:
        @staticmethod
        async def get_instance(config, user_id):
            return store

    monkeypatch.setattr(mcp_module, "get_conversation_store", lambda: DummyStoreImpl)
    monkeypatch.setattr(mcp_module, "get_config", lambda: "config")
    await mcp_module.save_pr_metadata("user", "cid", "no pr here")
    assert conversation.pr_number == []


@pytest.mark.asyncio
async def test_save_pr_metadata_extracts_merge_request(monkeypatch, mcp_module):
    conversation = SimpleNamespace(pr_number=[], conversation_id="cid")
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: conversation),
        save_metadata=_async_wrap(lambda convo: None),
    )

    class DummyStoreImpl:
        @staticmethod
        async def get_instance(config, user_id):
            return store

    monkeypatch.setattr(mcp_module, "get_conversation_store", lambda: DummyStoreImpl)
    monkeypatch.setattr(mcp_module, "get_config", lambda: "config")
    await mcp_module.save_pr_metadata("user", "cid", "https://gitlab.com/org/repo/merge_requests/7")
    assert conversation.pr_number == [7]


def test_lazy_import_helpers(mcp_module):
    assert mcp_module.get_conversation_store() is not None
    assert mcp_module.get_config() is not None


def _build_request(headers=None):
    return SimpleNamespace(headers=headers or {})


@pytest.mark.asyncio
async def test_create_pr_success(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.GITHUB: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))

    github_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GHUser")),
        create_pr=_async_wrap(lambda **kwargs: "https://github.com/org/repo/pull/1"),
    )

    monkeypatch.setattr(mcp_module, "GithubServiceImpl", lambda **kwargs: github_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    result = await mcp_module.create_pr("org/repo", "feature", "main", "Title", "Body", draft=False, labels=["bug"])
    assert result.endswith("/pull/1")


@pytest.mark.asyncio
async def test_create_pr_handles_errors(monkeypatch, mcp_module):
    request = _build_request()
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: None))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    github_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GHUser")),
        create_pr=_async_wrap(lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setattr(mcp_module, "GithubServiceImpl", lambda **kwargs: github_service)

    with pytest.raises(mcp_module.ToolError):
        await mcp_module.create_pr("org/repo", "feature", "main", "Title", "Body")


@pytest.mark.asyncio
async def test_create_pr_conversation_link_warning(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.GITHUB: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    github_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GHUser")),
        create_pr=_async_wrap(lambda **kwargs: "https://github.com/org/repo/pull/1"),
    )
    monkeypatch.setattr(mcp_module, "GithubServiceImpl", lambda **kwargs: github_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    monkeypatch.setattr(mcp_module, "get_conversation_link", _async_wrap(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))))
    result = await mcp_module.create_pr("org/repo", "feature", "main", "Title", "Body")
    assert result.endswith("/pull/1")


@pytest.mark.asyncio
async def test_create_mr_success(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.GITLAB: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    gitlab_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GLUser")),
        create_mr=_async_wrap(lambda **kwargs: "https://gitlab.com/org/repo/merge_requests/2"),
    )
    monkeypatch.setattr(mcp_module, "GitLabServiceImpl", lambda **kwargs: gitlab_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    result = await mcp_module.create_mr("org/repo", "feature", "main", "Title", "Desc")
    assert "/merge_requests/2" in result


@pytest.mark.asyncio
async def test_create_mr_handles_errors(monkeypatch, mcp_module):
    request = _build_request()
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: None))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    gitlab_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GLUser")),
        create_mr=_async_wrap(lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setattr(mcp_module, "GitLabServiceImpl", lambda **kwargs: gitlab_service)
    with pytest.raises(mcp_module.ToolError):
        await mcp_module.create_mr("org/repo", "feature", "main", "Title", "Desc")


@pytest.mark.asyncio
async def test_create_mr_conversation_link_warning(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.GITLAB: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    gitlab_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="GLUser")),
        create_mr=_async_wrap(lambda **kwargs: "https://gitlab.com/org/repo/merge_requests/2"),
    )
    monkeypatch.setattr(mcp_module, "GitLabServiceImpl", lambda **kwargs: gitlab_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    monkeypatch.setattr(mcp_module, "get_conversation_link", _async_wrap(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))))
    result = await mcp_module.create_mr("org/repo", "feature", "main", "Title", "Desc")
    assert "/merge_requests/2" in result


@pytest.mark.asyncio
async def test_create_bitbucket_pr_success(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.BITBUCKET: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    bitbucket_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="BBUser")),
        create_pr=_async_wrap(lambda **kwargs: "https://bitbucket.org/workspace/repo/pull-requests/3"),
    )
    monkeypatch.setattr(mcp_module, "BitBucketServiceImpl", lambda **kwargs: bitbucket_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    result = await mcp_module.create_bitbucket_pr("workspace/repo", "feature", "main", "Title", "Desc")
    assert "pull-requests/3" in result


@pytest.mark.asyncio
async def test_create_bitbucket_pr_handles_errors(monkeypatch, mcp_module):
    request = _build_request()
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: None))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    bitbucket_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="BBUser")),
        create_pr=_async_wrap(lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setattr(mcp_module, "BitBucketServiceImpl", lambda **kwargs: bitbucket_service)
    with pytest.raises(mcp_module.ToolError):
        await mcp_module.create_bitbucket_pr("workspace/repo", "feature", "main", "Title", "Desc")


@pytest.mark.asyncio
async def test_create_bitbucket_pr_conversation_link_warning(monkeypatch, mcp_module):
    request = _build_request({"X-Forge-ServerConversation-ID": "cid"})
    monkeypatch.setattr(mcp_module, "get_http_request", lambda: request)
    monkeypatch.setattr(mcp_module, "get_provider_tokens", _async_wrap(lambda req: {ProviderType.BITBUCKET: SimpleNamespace(token=None, user_id="user", host=None)}))
    monkeypatch.setattr(mcp_module, "get_access_token", _async_wrap(lambda req: "access"))
    monkeypatch.setattr(mcp_module, "get_user_id", _async_wrap(lambda req: "user"))
    bitbucket_service = SimpleNamespace(
        get_user=_async_wrap(lambda: SimpleNamespace(login="BBUser")),
        create_pr=_async_wrap(lambda **kwargs: "https://bitbucket.org/workspace/repo/pull-requests/3"),
    )
    monkeypatch.setattr(mcp_module, "BitBucketServiceImpl", lambda **kwargs: bitbucket_service)
    monkeypatch.setattr(mcp_module, "save_pr_metadata", _async_wrap(lambda *args, **kwargs: None))
    monkeypatch.setattr(mcp_module, "get_conversation_link", _async_wrap(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom"))))
    result = await mcp_module.create_bitbucket_pr("workspace/repo", "feature", "main", "Title", "Desc")
    assert "pull-requests/3" in result
