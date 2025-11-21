"""Unit tests for Slack integration routes."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import types
from collections.abc import Awaitable, Coroutine
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import SecretStr

from forge.core.schemas import AgentState
from forge.events.action import AgentThinkAction, CmdRunAction, MessageAction
from forge.events.observation import AgentStateChangedObservation, CmdOutputObservation
from forge.integrations.slack_client import SlackClient
from forge.server.routes import slack as slack_routes
from forge.storage.data_models.slack_integration import (
    SlackConversationLink,
    SlackOutgoingMessage,
    SlackUserLink,
    SlackWorkspace,
)
from forge.storage.slack_store import SlackStore


class DummySlackClient:
    def __init__(self, token: str):
        self.token = token
        self.posted: list[SlackOutgoingMessage] = []
        self.ephemeral: list[tuple[str, str, str]] = []
        self.updated: list[tuple[str, str, str]] = []

    def post_message(self, message: SlackOutgoingMessage) -> dict[str, Any]:
        self.posted.append(message)
        return {"ts": "123.456"}

    def post_ephemeral_message(
        self,
        channel: str,
        user: str,
        text: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        self.ephemeral.append((channel, user, text))
        return {"ok": True}

    def update_message(self, channel: str, ts: str, text: str) -> dict[str, Any]:
        self.updated.append((channel, ts, text))
        return {"ok": True}

    def format_code_block(self, content: str, language: str | None = None) -> str:
        return f"```{language or ''}\n{content}\n```"

    def remove_bot_mention(self, text: str, bot_user_id: str | None) -> str:
        return text.replace(f"<@{bot_user_id}>", "").strip()

    def extract_repo_from_text(self, text: str) -> str | None:
        return "owner/repo" if "repo:" in text else None


class DummySlackStore:
    def __init__(self):
        self.oauth_states: dict[str, SimpleNamespace] = {}
        self.workspaces: dict[str, SlackWorkspace] = {}
        self.user_links: dict[tuple[str, str], SlackUserLink] = {}
        self.conversation_links: dict[tuple[str, str, str], SlackConversationLink] = {}

    def generate_oauth_state(self, user_id: str, redirect_url: str | None) -> str:
        state = f"state-{user_id}"
        self.oauth_states[state] = SimpleNamespace(
            user_id=user_id, redirect_url=redirect_url
        )
        return state

    def get_oauth_state(self, state: str) -> SimpleNamespace | None:
        return self.oauth_states.get(state)

    def delete_oauth_state(self, state: str) -> None:
        self.oauth_states.pop(state, None)

    def save_workspace(self, workspace: SlackWorkspace) -> None:
        self.workspaces[workspace.team_id] = workspace

    def get_workspace(self, team_id: str) -> SlackWorkspace | None:
        return self.workspaces.get(team_id)

    def list_workspaces(self) -> list[SlackWorkspace]:
        return list(self.workspaces.values())

    def save_user_link(self, link: SlackUserLink) -> None:
        self.user_links[(link.slack_workspace_id, link.slack_user_id)] = link

    def get_user_link(self, team_id: str, user_id: str) -> SlackUserLink | None:
        return self.user_links.get((team_id, user_id))

    def save_conversation_link(self, link: SlackConversationLink) -> None:
        self.conversation_links[
            (link.slack_workspace_id, link.slack_channel_id, link.slack_thread_ts)
        ] = link

    def get_conversation_link(
        self, team_id: str, channel_id: str, thread_ts: str
    ) -> SlackConversationLink | None:
        return self.conversation_links.get((team_id, channel_id, thread_ts))

    def delete_workspace(self, team_id: str) -> None:
        self.workspaces.pop(team_id, None)


class DummyRequest:
    def __init__(
        self,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
        json_data: Any | None = None,
    ):
        self.headers = headers or {}
        self._body = body
        self._json_data = json_data

    async def body(self) -> bytes:
        return self._body

    async def json(self) -> Any:
        if callable(self._json_data):
            return self._json_data()
        return self._json_data


@pytest.fixture(autouse=True)
def patch_slack_client(monkeypatch):
    monkeypatch.setattr(slack_routes, "SlackClient", DummySlackClient)
    monkeypatch.setattr(slack_routes, "_slack_event_listeners", {})
    return DummySlackClient


def _run(awaitable: Awaitable[None]) -> None:
    """Run coroutine synchronously for tests."""
    asyncio.run(cast(Coroutine[Any, Any, None], awaitable))


def _store_cast(store: DummySlackStore) -> SlackStore:
    """View dummy store as SlackStore for typing."""
    return cast(SlackStore, store)


def test_create_slack_event_callback_posts_messages(monkeypatch):
    client = DummySlackClient("token")
    typed_client = cast(SlackClient, client)
    callback = slack_routes.create_slack_event_callback(
        typed_client, "channel", "thread", "cid"
    )

    _run(callback(AgentThinkAction(thought="ponder")))
    _run(callback(CmdRunAction(command="ls")))
    _run(callback(CmdOutputObservation(content="result", command="ls", exit_code=0)))
    _run(callback(MessageAction(content="hello")))
    _run(
        callback(
            AgentStateChangedObservation(
                content="", agent_state=AgentState.FINISHED.value
            )
        )
    )
    _run(
        callback(
            AgentStateChangedObservation(content="", agent_state=AgentState.ERROR.value)
        )
    )
    _run(
        callback(
            AgentStateChangedObservation(
                content="", agent_state=AgentState.RUNNING.value
            )
        )
    )
    _run(callback(AgentStateChangedObservation(content="", agent_state="OTHER")))


def test_create_slack_event_callback_truncates_output():
    client = DummySlackClient("token")
    callback = slack_routes.create_slack_event_callback(
        cast(SlackClient, client), "channel", "thread", "cid"
    )
    long_output = "x" * 600
    _run(callback(CmdOutputObservation(content=long_output, command="ls", exit_code=1)))
    assert any("output truncated" in msg.text for msg in client.posted)


def test_create_slack_event_callback_handles_errors(monkeypatch):
    class ErrorClient(DummySlackClient):
        def post_message(self, message: SlackOutgoingMessage):
            raise RuntimeError("fail")

    client = ErrorClient("token")
    callback = slack_routes.create_slack_event_callback(
        cast(SlackClient, client), "channel", "thread", "cid"
    )
    _run(callback(MessageAction(content="oops")))


@pytest.mark.asyncio
async def test_verify_slack_signature_success(monkeypatch):
    import hmac
    import hashlib

    body = b"payload"
    timestamp = str(int(time.time()))
    secret = "secret"
    base_string = f"v0:{timestamp}:{body.decode()}"
    signature = (
        "v0="
        + hmac.new(secret.encode(), base_string.encode(), hashlib.sha256).hexdigest()
    )

    request = cast(
        Request,
        DummyRequest(
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": signature,
            },
            body=body,
        ),
    )
    assert await slack_routes.verify_slack_signature(request, secret) is True


@pytest.mark.asyncio
async def test_verify_slack_signature_invalid(monkeypatch):
    timestamp = str(int(time.time()) - 4000)
    request = cast(
        Request,
        DummyRequest(
            headers={
                "X-Slack-Request-Timestamp": timestamp,
                "X-Slack-Signature": "sig",
            },
            body=b"data",
        ),
    )
    assert await slack_routes.verify_slack_signature(request, "secret") is False


@pytest.mark.asyncio
async def test_verify_slack_signature_missing_headers():
    request = cast(Request, DummyRequest(headers={}, body=b""))
    assert await slack_routes.verify_slack_signature(request, "secret") is False


@pytest.mark.asyncio
async def test_verify_slack_signature_no_secret():
    request = cast(
        Request,
        DummyRequest(
            headers={
                "X-Slack-Request-Timestamp": str(int(time.time())),
                "X-Slack-Signature": "sig",
            },
            body=b"",
        ),
    )
    assert await slack_routes.verify_slack_signature(request, None) is True


@pytest.mark.asyncio
async def test_slack_install_success(monkeypatch):
    slack_routes.FORGE_config.SLACK_CLIENT_ID = "client"
    store = DummySlackStore()
    response = await slack_routes.slack_install(
        "user-1", "https://redirect", slack_store=_store_cast(store)
    )
    data = json.loads(bytes(response.body))
    assert "state-user-1" in data["url"]


@pytest.mark.asyncio
async def test_slack_install_not_configured(monkeypatch):
    slack_routes.FORGE_config.SLACK_CLIENT_ID = None
    store = DummySlackStore()
    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_install("user", slack_store=_store_cast(store))
    assert exc.value.status_code == 501


@pytest.mark.asyncio
async def test_slack_oauth_callback_error(monkeypatch):
    store = DummySlackStore()
    response = await slack_routes.slack_oauth_callback(
        state="s", error="access_denied", slack_store=_store_cast(store)
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_slack_oauth_callback_invalid_state(monkeypatch):
    store = DummySlackStore()
    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_oauth_callback(
            state="missing", code="code", slack_store=_store_cast(store)
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_slack_oauth_callback_missing_code(monkeypatch):
    store = DummySlackStore()
    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_oauth_callback(
            state="s", slack_store=_store_cast(store)
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_slack_oauth_callback_sdk_not_installed(monkeypatch):
    store = DummySlackStore()
    store.oauth_states["state"] = SimpleNamespace(user_id="user", redirect_url=None)
    monkeypatch.setattr(slack_routes, "SLACK_SDK_AVAILABLE", False)
    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_oauth_callback(
            state="state", code="code", slack_store=_store_cast(store)
        )
    assert exc.value.status_code == 501


@pytest.mark.asyncio
async def test_slack_oauth_callback_success(monkeypatch):
    store = DummySlackStore()
    store.oauth_states["state"] = SimpleNamespace(
        user_id="user", redirect_url="/return"
    )
    slack_routes.FORGE_config.SLACK_CLIENT_ID = "client"
    slack_routes.FORGE_config.SLACK_CLIENT_SECRET = SecretStr("secret")
    monkeypatch.setattr(slack_routes, "SLACK_SDK_AVAILABLE", True)

    class DummyWebClient:
        def oauth_v2_access(self, client_id, client_secret, code):
            return {
                "ok": True,
                "team": {"id": "team", "name": "Team"},
                "access_token": "bot-token",
                "bot_user_id": "bot",
                "authed_user": {"id": "U1", "access_token": "user-token"},
            }

    dummy_module = types.ModuleType("slack_sdk")
    setattr(dummy_module, "WebClient", DummyWebClient)
    monkeypatch.setitem(sys.modules, "slack_sdk", dummy_module)

    response = await slack_routes.slack_oauth_callback(
        state="state", code="code", slack_store=_store_cast(store)
    )
    assert response.status_code == 200
    assert "Slack installed successfully" in bytes(response.body).decode()


@pytest.mark.asyncio
async def test_slack_oauth_callback_exchange_failure(monkeypatch):
    store = DummySlackStore()
    store.oauth_states["state"] = SimpleNamespace(user_id="user", redirect_url=None)
    slack_routes.FORGE_config.SLACK_CLIENT_ID = "client"
    slack_routes.FORGE_config.SLACK_CLIENT_SECRET = SecretStr("secret")
    monkeypatch.setattr(slack_routes, "SLACK_SDK_AVAILABLE", True)

    class DummyWebClient:
        def oauth_v2_access(self, *args, **kwargs):
            return {"ok": False}

    dummy_module = types.ModuleType("slack_sdk")
    setattr(dummy_module, "WebClient", DummyWebClient)
    monkeypatch.setitem(sys.modules, "slack_sdk", dummy_module)

    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_oauth_callback(
            state="state", code="code", slack_store=_store_cast(store)
        )
    assert exc.value.status_code == 500


def test_get_slack_store_helpers(monkeypatch):
    monkeypatch.setattr(slack_routes, "SlackStore", lambda cfg: "store")
    assert slack_routes.get_slack_store() == "store"
    assert slack_routes._resolve_slack_store() == "store"


@pytest.mark.asyncio
async def test_slack_events_url_verification(monkeypatch):
    request = DummyRequest(json_data={"type": "url_verification", "challenge": "abc"})
    store = DummySlackStore()
    slack_routes.FORGE_config.SLACK_SIGNING_SECRET = None
    response = await slack_routes.slack_events(
        cast(Request, request), slack_store=_store_cast(store)
    )
    assert json.loads(bytes(response.body))["challenge"] == "abc"


@pytest.mark.asyncio
async def test_slack_events_invalid_signature(monkeypatch):
    request = cast(Request, DummyRequest(json_data={"event": {}}, headers={}))

    slack_routes.FORGE_config.SLACK_SIGNING_SECRET = SecretStr("secret")

    async def fake_verify(req, secret):
        return False

    monkeypatch.setattr(slack_routes, "verify_slack_signature", fake_verify)
    with pytest.raises(HTTPException) as exc:
        await slack_routes.slack_events(
            request, slack_store=_store_cast(DummySlackStore())
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_slack_events_app_mention(monkeypatch):
    called = {}

    async def fake_handle(event, store):
        called["event"] = event

    request = cast(
        Request, DummyRequest(json_data={"event": {"type": "app_mention"}}, headers={})
    )

    slack_routes.FORGE_config.SLACK_SIGNING_SECRET = SecretStr("secret")

    async def true_verify(req, secret):
        return True

    monkeypatch.setattr(slack_routes, "verify_slack_signature", true_verify)
    monkeypatch.setattr(slack_routes, "handle_app_mention", fake_handle)
    await slack_routes.slack_events(request, slack_store=_store_cast(DummySlackStore()))
    assert called["event"]["type"] == "app_mention"


@pytest.mark.asyncio
async def test_slack_events_thread_message(monkeypatch):
    called = {}

    async def fake_thread(event, store):
        called["event"] = event

    body = {"event": {"type": "message", "thread_ts": "thread", "ts": "parent"}}
    request = cast(Request, DummyRequest(json_data=body, headers={}))

    slack_routes.FORGE_config.SLACK_SIGNING_SECRET = SecretStr("secret")

    async def true_verify(req, secret):
        return True

    monkeypatch.setattr(slack_routes, "verify_slack_signature", true_verify)
    monkeypatch.setattr(slack_routes, "handle_thread_message", fake_thread)
    await slack_routes.slack_events(request, slack_store=_store_cast(DummySlackStore()))
    assert called["event"]["type"] == "message"


@pytest.mark.asyncio
async def test_handle_app_mention_missing_fields():
    await slack_routes.handle_app_mention({}, _store_cast(DummySlackStore()))


@pytest.mark.asyncio
async def test_handle_app_mention_workspace_missing():
    event = {
        "team": "team",
        "channel": "channel",
        "user": "user",
        "ts": "ts",
        "text": "hello",
    }
    await slack_routes.handle_app_mention(event, _store_cast(DummySlackStore()))


@pytest.mark.asyncio
async def test_handle_app_mention_user_not_linked(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    event = {
        "team": "team",
        "channel": "channel",
        "user": "user",
        "ts": "ts",
        "text": "<@bot> help",
    }
    await slack_routes.handle_app_mention(event, _store_cast(store))


@pytest.mark.asyncio
async def test_handle_app_mention_existing_conversation(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    link = SlackConversationLink(
        slack_channel_id="channel",
        slack_thread_ts="ts",
        slack_workspace_id="team",
        conversation_id="cid",
        repository=None,
        created_by_slack_user_id="user",
    )
    store.save_conversation_link(link)
    store.save_user_link(
        SlackUserLink(
            slack_user_id="user",
            slack_workspace_id="team",
            FORGE_user_id="forge",
            user_token=None,
        )
    )

    called: dict[str, bool] = {"flag": False}

    async def fake_continue(link, text, workspace, store):
        called["flag"] = True

    monkeypatch.setattr(slack_routes, "continue_conversation", fake_continue)

    event = {
        "team": "team",
        "channel": "channel",
        "user": "user",
        "ts": "ts",
        "text": "hello",
    }
    await slack_routes.handle_app_mention(event, _store_cast(store))
    assert called["flag"] is True


@pytest.mark.asyncio
async def test_handle_app_mention_starts_conversation(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    store.save_user_link(
        SlackUserLink(
            slack_user_id="user",
            slack_workspace_id="team",
            FORGE_user_id="forge",
            user_token=None,
        )
    )

    called: dict[str, bool] = {"flag": False}

    async def fake_start(*args, **kwargs):
        called["flag"] = True

    monkeypatch.setattr(slack_routes, "start_new_conversation", fake_start)

    event = {
        "team": "team",
        "channel": "channel",
        "user": "user",
        "ts": "ts",
        "text": "<@bot> repo: x",
    }
    await slack_routes.handle_app_mention(event, _store_cast(store))
    assert called["flag"] is True


@pytest.mark.asyncio
async def test_handle_app_mention_handles_exception(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    store.save_user_link(
        SlackUserLink(
            slack_user_id="user",
            slack_workspace_id="team",
            FORGE_user_id="forge",
            user_token=None,
        )
    )

    async def failing_start(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(slack_routes, "start_new_conversation", failing_start)
    event = {
        "team": "team",
        "channel": "channel",
        "user": "user",
        "ts": "ts",
        "text": "hello",
    }
    await slack_routes.handle_app_mention(event, _store_cast(store))


@pytest.mark.asyncio
async def test_start_new_conversation_success(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    user_link = SlackUserLink(
        slack_user_id="user",
        slack_workspace_id="team",
        FORGE_user_id="forge",
        user_token=None,
    )
    store.save_user_link(user_link)

    async def fake_new_conversation(**kwargs):
        return SimpleNamespace(conversation_id="cid")

    monkeypatch.setattr(slack_routes, "new_conversation", fake_new_conversation)

    class DummyEventStream:
        def subscribe(self, *args, **kwargs):
            pass

    shared = __import__("forge.server.shared", fromlist=["conversation_manager"])
    monkeypatch.setattr(
        shared,
        "conversation_manager",
        SimpleNamespace(
            get_agent_session=lambda cid: SimpleNamespace(
                event_stream=DummyEventStream()
            ),
        ),
    )
    stream_module = types.ModuleType("forge.events.stream")
    setattr(stream_module, "EventStreamSubscriber", SimpleNamespace(SERVER="server"))
    monkeypatch.setitem(sys.modules, "forge.events.stream", stream_module)
    monkeypatch.setattr(
        slack_routes, "InitSessionRequest", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    await slack_routes.start_new_conversation(
        team_id="team",
        channel_id="channel",
        thread_ts="thread",
        user_id="user",
        text="repo: test",
        user_link=user_link,
        workspace=workspace,
        slack_store=_store_cast(store),
    )

    assert ("team", "channel", "thread") in store.conversation_links


@pytest.mark.asyncio
async def test_start_new_conversation_error_response(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    user_link = SlackUserLink(
        slack_user_id="user",
        slack_workspace_id="team",
        FORGE_user_id="forge",
        user_token=None,
    )
    store.save_user_link(user_link)

    async def fake_new_conversation(**kwargs):
        resp = JSONResponse(content={"error": "failure"}, status_code=400)
        resp.body = b"error text"
        return resp

    monkeypatch.setattr(slack_routes, "new_conversation", fake_new_conversation)
    monkeypatch.setattr(
        slack_routes, "InitSessionRequest", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    await slack_routes.start_new_conversation(
        team_id="team",
        channel_id="channel",
        thread_ts="thread",
        user_id="user",
        text="hello",
        user_link=user_link,
        workspace=workspace,
        slack_store=_store_cast(store),
    )


@pytest.mark.asyncio
async def test_start_new_conversation_error_response_bytes(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    user_link = SlackUserLink(
        slack_user_id="user",
        slack_workspace_id="team",
        FORGE_user_id="forge",
        user_token=None,
    )
    store.save_user_link(user_link)

    async def fake_new_conversation(**kwargs):
        return JSONResponse(content={"error": "failure"}, status_code=400)

    monkeypatch.setattr(slack_routes, "new_conversation", fake_new_conversation)
    monkeypatch.setattr(
        slack_routes, "InitSessionRequest", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    await slack_routes.start_new_conversation(
        team_id="team",
        channel_id="channel",
        thread_ts="thread",
        user_id="user",
        text="hello",
        user_link=user_link,
        workspace=workspace,
        slack_store=_store_cast(store),
    )


@pytest.mark.asyncio
async def test_start_new_conversation_subscription_error(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    user_link = SlackUserLink(
        slack_user_id="user",
        slack_workspace_id="team",
        FORGE_user_id="forge",
        user_token=None,
    )
    store.save_user_link(user_link)

    async def fake_new_conversation(**kwargs):
        return SimpleNamespace(conversation_id="cid")

    monkeypatch.setattr(slack_routes, "new_conversation", fake_new_conversation)

    class DummyEventStream:
        def subscribe(self, *args, **kwargs):
            raise ValueError("exists")

    shared = __import__("forge.server.shared", fromlist=["conversation_manager"])
    monkeypatch.setattr(
        shared,
        "conversation_manager",
        SimpleNamespace(
            get_agent_session=lambda cid: SimpleNamespace(
                event_stream=DummyEventStream()
            )
        ),
    )
    stream_module = types.ModuleType("forge.events.stream")
    setattr(stream_module, "EventStreamSubscriber", SimpleNamespace(SERVER="server"))
    monkeypatch.setitem(sys.modules, "forge.events.stream", stream_module)
    monkeypatch.setattr(
        slack_routes, "InitSessionRequest", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    await slack_routes.start_new_conversation(
        team_id="team",
        channel_id="channel",
        thread_ts="thread",
        user_id="user",
        text="hello",
        user_link=user_link,
        workspace=workspace,
        slack_store=_store_cast(store),
    )


@pytest.mark.asyncio
async def test_start_new_conversation_exception(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    user_link = SlackUserLink(
        slack_user_id="user",
        slack_workspace_id="team",
        FORGE_user_id="forge",
        user_token=None,
    )
    store.save_user_link(user_link)

    async def failing_new_conversation(**kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(slack_routes, "new_conversation", failing_new_conversation)
    monkeypatch.setattr(
        slack_routes, "InitSessionRequest", lambda **kwargs: SimpleNamespace(**kwargs)
    )

    with pytest.raises(RuntimeError):
        await slack_routes.start_new_conversation(
            team_id="team",
            channel_id="channel",
            thread_ts="thread",
            user_id="user",
            text="hello",
            user_link=user_link,
            workspace=workspace,
            slack_store=_store_cast(store),
        )


@pytest.mark.asyncio
async def test_continue_conversation(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    link = SlackConversationLink(
        slack_channel_id="channel",
        slack_thread_ts="thread",
        slack_workspace_id="team",
        conversation_id="cid",
        repository=None,
        created_by_slack_user_id="user",
    )

    async def fake_send_event(cid, event):
        assert cid == "cid"

    shared = __import__("forge.server.shared", fromlist=["conversation_manager"])
    monkeypatch.setattr(
        shared,
        "conversation_manager",
        SimpleNamespace(send_event_to_conversation=fake_send_event),
    )
    monkeypatch.setattr(slack_routes, "SlackClient", DummySlackClient)

    await slack_routes.continue_conversation(
        link, "message", workspace, _store_cast(store)
    )


@pytest.mark.asyncio
async def test_continue_conversation_error(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    link = SlackConversationLink(
        slack_channel_id="channel",
        slack_thread_ts="thread",
        slack_workspace_id="team",
        conversation_id="cid",
        repository=None,
        created_by_slack_user_id="user",
    )

    async def failing_send_event(cid, event):
        raise RuntimeError("fail")

    shared = __import__("forge.server.shared", fromlist=["conversation_manager"])
    monkeypatch.setattr(
        shared,
        "conversation_manager",
        SimpleNamespace(send_event_to_conversation=failing_send_event),
    )
    monkeypatch.setattr(slack_routes, "SlackClient", DummySlackClient)

    with pytest.raises(RuntimeError):
        await slack_routes.continue_conversation(
            link, "message", workspace, _store_cast(store)
        )


@pytest.mark.asyncio
async def test_handle_thread_message(monkeypatch):
    store = DummySlackStore()
    workspace = SlackWorkspace(
        id="team",
        team_id="team",
        team_name="Team",
        bot_token="token",
        bot_user_id="bot",
        installed_by_user_id="user",
    )
    store.save_workspace(workspace)
    link = SlackConversationLink(
        slack_channel_id="channel",
        slack_thread_ts="thread",
        slack_workspace_id="team",
        conversation_id="cid",
        repository=None,
        created_by_slack_user_id="user",
    )
    store.save_conversation_link(link)

    async def fake_continue(link, text, workspace, store):
        assert text == "hello"

    monkeypatch.setattr(slack_routes, "continue_conversation", fake_continue)

    event = {
        "team": "team",
        "channel": "channel",
        "thread_ts": "thread",
        "text": "hello",
    }
    await slack_routes.handle_thread_message(event, _store_cast(store))


@pytest.mark.asyncio
async def test_handle_thread_message_bot_or_missing():
    await slack_routes.handle_thread_message(
        {"bot_id": "bot"}, _store_cast(DummySlackStore())
    )
    await slack_routes.handle_thread_message(
        {"team": "team", "channel": "channel", "thread_ts": "thread"},
        _store_cast(DummySlackStore()),
    )
    await slack_routes.handle_thread_message(
        {"team": "team", "thread_ts": "thread"}, _store_cast(DummySlackStore())
    )


@pytest.mark.asyncio
async def test_handle_thread_message_workspace_missing():
    store = DummySlackStore()
    link = SlackConversationLink(
        slack_channel_id="channel",
        slack_thread_ts="thread",
        slack_workspace_id="team",
        conversation_id="cid",
        repository=None,
        created_by_slack_user_id="user",
    )
    store.save_conversation_link(link)
    await slack_routes.handle_thread_message(
        {"team": "team", "channel": "channel", "thread_ts": "thread"},
        _store_cast(store),
    )


@pytest.mark.asyncio
async def test_list_workspaces(monkeypatch):
    store = DummySlackStore()
    store.save_workspace(
        SlackWorkspace(
            id="team",
            team_id="team",
            team_name="Team",
            bot_token="token",
            bot_user_id="bot",
            installed_by_user_id="user",
        )
    )
    response = await slack_routes.list_workspaces(
        "user", slack_store=_store_cast(store)
    )
    data = json.loads(bytes(response.body))
    assert data["workspaces"][0]["team_id"] == "team"


@pytest.mark.asyncio
async def test_uninstall_workspace(monkeypatch):
    store = DummySlackStore()
    store.save_workspace(
        SlackWorkspace(
            id="team",
            team_id="team",
            team_name="Team",
            bot_token="token",
            bot_user_id="bot",
            installed_by_user_id="user",
        )
    )
    response = await slack_routes.uninstall_workspace(
        "team", "user", slack_store=_store_cast(store)
    )
    assert json.loads(bytes(response.body))["ok"] is True


@pytest.mark.asyncio
async def test_uninstall_workspace_not_found(monkeypatch):
    store = DummySlackStore()
    with pytest.raises(HTTPException) as exc:
        await slack_routes.uninstall_workspace(
            "team", "user", slack_store=_store_cast(store)
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cleanup_slack_listener():
    slack_routes._slack_event_listeners["cid"] = (
        cast(SlackClient, DummySlackClient("t")),
        "c",
        "ts",
    )
    response = await slack_routes.cleanup_slack_listener("cid")
    assert json.loads(bytes(response.body))["ok"] is True
