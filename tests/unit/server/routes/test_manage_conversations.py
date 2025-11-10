"""Unit tests for manage_conversations helper functions and critical endpoints."""

from __future__ import annotations

import asyncio
import contextlib
import json
from datetime import datetime, timedelta, timezone
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping

import pytest

from fastapi import status
from fastapi.responses import JSONResponse

from forge.integrations.service_types import ProviderType
from forge.server.routes import manage_conversations as mc
from forge.storage.data_models.conversation_metadata import ConversationMetadata, ConversationTrigger
from forge.storage.data_models.conversation_status import ConversationStatus


class DummyConversationManager:
    def __init__(self):
        self.connections = {}
        self.agent_loop_info = []
        async def emit(*args, **kwargs):  # noqa: ANN001
            return None

        self.sio = SimpleNamespace(emit=emit)

    async def get_connections(self, filter_to_sids=None, conversation_id=None):  # noqa: ANN001
        if conversation_id is not None:
            return self.connections.get(conversation_id)
        return {sid: sid for sid in (filter_to_sids or set())}

    async def get_agent_loop_info(self, filter_to_sids=None, **kwargs):  # noqa: ANN001
        return [info for info in self.agent_loop_info if info.conversation_id in (filter_to_sids or set())]

    async def maybe_start_agent_loop(self, **kwargs):
        return SimpleNamespace(status=ConversationStatus.RUNNING)

    async def close_session(self, conversation_id):
        self.closed = conversation_id

    async def is_agent_loop_running(self, conversation_id):
        return False


@pytest.fixture(autouse=True)
def patch_conversation_manager(monkeypatch):
    manager = DummyConversationManager()
    monkeypatch.setattr(mc, "conversation_manager", manager)
    return manager


def _async_wrap(fn):
    async def inner(*args, **kwargs):
        return fn(*args, **kwargs)

    return inner


def test_filter_conversations_by_age_filters_old_entries():
    now = datetime.now(timezone.utc)
    conversations = [
        SimpleNamespace(created_at=now - timedelta(seconds=10)),
        SimpleNamespace(created_at=now - timedelta(seconds=3600)),
        SimpleNamespace(),
    ]
    result = mc._filter_conversations_by_age(conversations, max_age_seconds=300)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_build_conversation_result_set_maps_connections(monkeypatch, patch_conversation_manager):
    metadata = SimpleNamespace(conversation_id="c1", title="", last_updated_at=None, created_at=None, trigger=None)
    patch_conversation_manager.connections = {"c1": "c1"}
    patch_conversation_manager.agent_loop_info = [SimpleNamespace(conversation_id="c1", status=ConversationStatus.RUNNING)]

    async def fake_get_conversation_info(conversation, num_connections, agent_loop_info):
        return SimpleNamespace(conversation_id=conversation.conversation_id, num_connections=num_connections, status=agent_loop_info.status)

    monkeypatch.setattr(mc, "_get_conversation_info", fake_get_conversation_info)
    result = await mc._build_conversation_result_set([metadata], next_page_id="next")
    assert result.next_page_id == "next"
    assert result.results[0].num_connections == 1


def test_determine_conversation_trigger_priority():
    trigger, repo, provider = mc._determine_conversation_trigger(None, SimpleNamespace(repo="r", git_provider=ProviderType.GITHUB), None)
    assert trigger == ConversationTrigger.MICROAGENT_MANAGEMENT
    assert repo == "r"
    trigger, repo, provider = mc._determine_conversation_trigger(SimpleNamespace(), None, mc.AuthType.BEARER)
    assert trigger == ConversationTrigger.REMOTE_API_KEY


def test_validate_remote_api_request_handles_missing_message():
    response = mc._validate_remote_api_request(ConversationTrigger.REMOTE_API_KEY, "")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert mc._validate_remote_api_request(ConversationTrigger.GUI, None) is None


@pytest.mark.asyncio
async def test_verify_repository_access_skips_none(monkeypatch):
    called = {}

    class DummyProvider:
        def __init__(self, tokens):
            called["tokens"] = tokens

        async def verify_repo_provider(self, repository, git_provider):
            called["repository"] = repository
            called["provider"] = git_provider

    monkeypatch.setattr(mc, "ProviderHandler", DummyProvider)
    await mc._verify_repository_access("owner/repo", ProviderType.GITHUB, {"token": "x"})
    assert called["repository"] == "owner/repo"
    await mc._verify_repository_access(None, ProviderType.GITHUB, {"token": "x"})


def test_handle_conversation_errors_maps_known_exceptions():
    err = mc._handle_conversation_errors(mc.MissingSettingsError("missing"))
    assert err.status_code == status.HTTP_400_BAD_REQUEST
    err = mc._handle_conversation_errors(mc.LLMAuthenticationError("bad"))
    assert err.status_code == status.HTTP_400_BAD_REQUEST
    with pytest.raises(RuntimeError):
        mc._handle_conversation_errors(RuntimeError("fail"))


def test_apply_conversation_overrides_prefers_overrides():
    repo, provider, message = mc._apply_conversation_overrides(None, None, "override", ProviderType.BITBUCKET, SimpleNamespace(get_prompt_for_task=lambda: "prompt"), None)
    assert repo == "override"
    assert provider == ProviderType.BITBUCKET
    assert message == "prompt"


def test_normalize_provider_tokens_handles_strings():
    normalized = mc._normalize_provider_tokens({"github": SimpleNamespace(token="1")})
    assert isinstance(normalized, Mapping)
    assert ProviderType.GITHUB in normalized


def test_prepare_conversation_params_defaults():
    user_id, tokens, secrets = mc._prepare_conversation_params(None, None, None)
    assert user_id == "dev-user"
    assert isinstance(tokens, Mapping)
    assert dict(secrets.custom_secrets) == {}


@pytest.mark.asyncio
async def test_search_conversations_filters(monkeypatch, patch_conversation_manager):
    now = datetime.now(timezone.utc)
    conversations = [
        ConversationMetadata(
            conversation_id="c1",
            title="title1",
            selected_repository="repo1",
            user_id="u",
            created_at=now,
            last_updated_at=now,
            trigger=ConversationTrigger.GUI,
        ),
        ConversationMetadata(
            conversation_id="c2",
            title="title2",
            selected_repository="repo",
            user_id="u",
            created_at=now,
            last_updated_at=now,
            trigger=ConversationTrigger.MICROAGENT_MANAGEMENT,
        ),
    ]
    store = SimpleNamespace(
        search=_async_wrap(lambda page_id, limit: SimpleNamespace(results=conversations, next_page_id=None))
    )
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    monkeypatch.setattr(mc.config, "conversation_max_age_seconds", 3600)
    result = await mc.search_conversations(limit=25, selected_repository="repo", conversation_trigger=ConversationTrigger.MICROAGENT_MANAGEMENT)
    assert len(result.results) == 1
    assert result.results[0].conversation_id == "c2"


@pytest.mark.asyncio
async def test_get_conversation_details_handles_missing(monkeypatch):
    store = SimpleNamespace(get_metadata=_async_wrap(lambda cid: (_ for _ in ()).throw(FileNotFoundError())))
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    result = await mc.get_conversation("c1")
    assert result is None


@pytest.mark.asyncio
async def test_get_conversation_details_returns_info(monkeypatch, patch_conversation_manager):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="c1",
        title="title",
        selected_repository="repo",
        user_id="u",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(get_metadata=_async_wrap(lambda cid: metadata))
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))

    async def fake_get_conversation_info(conversation, num_connections, agent_loop_info):
        return SimpleNamespace(conversation_id=conversation.conversation_id, num_connections=num_connections)

    monkeypatch.setattr(mc, "_get_conversation_info", fake_get_conversation_info)
    patch_conversation_manager.agent_loop_info = [SimpleNamespace(conversation_id="c1", status=ConversationStatus.RUNNING)]
    info = await mc.get_conversation("c1")
    assert info.conversation_id == "c1"


@pytest.mark.asyncio
async def test_delete_conversation_entry_handles_missing(monkeypatch):
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: (_ for _ in ()).throw(FileNotFoundError())),
    )
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    result = await mc.delete_conversation("c1")
    assert result is False


@pytest.mark.asyncio
async def test_delete_conversation_entry_success(monkeypatch, patch_conversation_manager):
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: ConversationMetadata(
            conversation_id=cid,
            title="title",
            selected_repository="repo",
            user_id="u",
            created_at=datetime.now(timezone.utc),
            last_updated_at=datetime.now(timezone.utc),
            trigger=ConversationTrigger.GUI,
        )),
        delete_metadata=_async_wrap(lambda cid: None),
    )
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    runtime = SimpleNamespace(delete=_async_wrap(lambda cid: None))
    monkeypatch.setattr(mc, "get_runtime_cls", lambda runtime_name: runtime)
    result = await mc.delete_conversation("c1")
    assert result is True


def test_get_contextual_events_merges_before_and_after(monkeypatch):
    class DummyEventStore:
        def __init__(self):
            self.calls = []

        def search_events(self, **kwargs):
            self.calls.append(kwargs)
            start_id = kwargs.get("start_id", 0)
            if kwargs.get("reverse"):
                yield f"before-{start_id}"
            else:
                yield f"after-{start_id}"

    store = DummyEventStore()
    result = mc._get_contextual_events(store, 5)
    assert "before-5" in result and "after-6" in result


def test_generate_prompt_template_renders(monkeypatch):
    class DummyTemplate:
        def render(self, **kwargs):
            return f"rendered {kwargs['events']}"

    class DummyEnv:
        def get_template(self, name):
            return DummyTemplate()

    monkeypatch.setattr(mc, "Environment", lambda **kwargs: DummyEnv())
    result = mc.generate_prompt_template("events")
    assert result == "rendered events"


def test_generate_prompt_parses_xml(monkeypatch):
    class DummyConversationManager:
        @staticmethod
        def request_llm_completion(tag, conversation_id, llm_config, messages):
            return "<update_prompt>trim me</update_prompt>"

    monkeypatch.setattr(mc, "ConversationManagerImpl", DummyConversationManager)
    prompt = mc.generate_prompt(SimpleNamespace(), "template", "cid")
    assert prompt == "trim me"
    monkeypatch.setattr(mc.ConversationManagerImpl, "request_llm_completion", staticmethod(lambda *args, **kwargs: "no tags"))
    with pytest.raises(ValueError):
        mc.generate_prompt(SimpleNamespace(), "template", "cid")


@pytest.mark.asyncio
async def test_update_conversation_success(monkeypatch):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="c1",
        user_id="user",
        title="old",
        selected_repository="repo",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: metadata),
        save_metadata=_async_wrap(lambda meta: None),
    )
    failing_manager = DummyConversationManager()

    async def failing_emit(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("emit fail")

    failing_manager.sio = SimpleNamespace(emit=failing_emit)
    monkeypatch.setattr(mc, "conversation_manager", failing_manager)

    result = await mc.update_conversation(
        data=mc.UpdateConversationRequest(title="new"),
        conversation_id="c1",
        user_id="user",
        conversation_store=store,
    )
    assert result is True


@pytest.mark.asyncio
async def test_update_conversation_permission_denied(monkeypatch):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="c1",
        user_id="owner",
        title="old",
        selected_repository="repo",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: metadata),
        save_metadata=_async_wrap(lambda meta: None),
    )

    response = await mc.update_conversation(
        data=mc.UpdateConversationRequest(title="new"),
        conversation_id="c1",
        user_id="user",
        conversation_store=store,
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_update_conversation_not_found():
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: (_ for _ in ()).throw(FileNotFoundError())),
    )

    response = await mc.update_conversation(
        data=mc.UpdateConversationRequest(title="new"),
        conversation_id="c1",
        user_id="user",
        conversation_store=store,
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_conversation_error(monkeypatch):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="c1",
        user_id="user",
        title="old",
        selected_repository="repo",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(
        get_metadata=_async_wrap(lambda cid: metadata),
        save_metadata=_async_wrap(lambda meta: (_ for _ in ()).throw(RuntimeError("fail"))),
    )

    response = await mc.update_conversation(
        data=mc.UpdateConversationRequest(title="new"),
        conversation_id="c1",
        user_id="user",
        conversation_store=store,
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_add_experiment_config_for_conversation(monkeypatch):
    calls = []

    class DummyFileStore:
        def read(self, path):
            raise FileNotFoundError

        def write(self, path, content):
            calls.append((path, content))

    monkeypatch.setattr(mc, "file_store", DummyFileStore())
    monkeypatch.setattr(mc, "model_dump_json", lambda exp_config: "json")
    monkeypatch.setattr(mc, "get_experiment_config_filename", lambda cid: f"{cid}.json")
    result = mc.add_experiment_config_for_conversation(SimpleNamespace(), "cid")
    assert result is False
    assert calls[0][0] == "cid.json"


@pytest.mark.asyncio
async def test_get_microagent_management_conversations_filters(monkeypatch):
    now = datetime.now(timezone.utc)
    conversations = [
        ConversationMetadata(
            conversation_id="c1",
            title="title1",
            selected_repository="repo",
            user_id="u",
            created_at=now,
            last_updated_at=now,
            trigger=ConversationTrigger.MICROAGENT_MANAGEMENT,
            pr_number=[1],
            git_provider=ProviderType.GITHUB,
        ),
        ConversationMetadata(
            conversation_id="c2",
            title="title2",
            selected_repository="repo",
            user_id="u",
            created_at=now,
            last_updated_at=now,
            trigger=ConversationTrigger.MICROAGENT_MANAGEMENT,
            pr_number=[2],
            git_provider=ProviderType.GITHUB,
        ),
    ]
    store = SimpleNamespace(
        search=_async_wrap(lambda page_id, limit: SimpleNamespace(results=conversations, next_page_id=None))
    )

    class DummyProviderHandler:
        def __init__(self, tokens):
            pass

        async def is_pr_open(self, repository, pr_number, provider):
            return pr_number == 1

    monkeypatch.setattr(mc, "ProviderHandler", DummyProviderHandler)
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override: store))
    monkeypatch.setattr(mc.config, "conversation_max_age_seconds", 3600)
    captured = {}

    async def fake_build(conversations, next_page_id):
        captured["count"] = len(conversations)
        captured["ids"] = [c.conversation_id for c in conversations]
        return SimpleNamespace(results=conversations, next_page_id=next_page_id)

    monkeypatch.setattr(mc, "_build_conversation_result_set", fake_build)
    await mc.get_microagent_management_conversations("repo", provider_tokens={"github": SimpleNamespace(token="x")})
    assert captured["count"] == 1
    assert captured["ids"] == ["c1"]


@pytest.mark.asyncio
async def test_handle_metasop_conversation_success(monkeypatch, patch_conversation_manager):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="cid",
        title="title",
        selected_repository="repo",
        user_id="user",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    monkeypatch.setattr(mc, "initialize_conversation", _async_wrap(lambda *args, **kwargs: metadata))

    emitted = {}

    async def emit(event, payload, to=None):
        emitted["payload"] = payload

    patch_conversation_manager.sio = SimpleNamespace(emit=emit)
    monkeypatch.setattr(mc, "run_metasop_for_conversation", _async_wrap(lambda *args, **kwargs: None))

    created = {}

    def fake_create_task(coro):
        created["task"] = coro
        return None

    monkeypatch.setattr(mc.asyncio, "create_task", fake_create_task)

    response = await mc._handle_metasop_conversation(
        user_id="user",
        conversation_id="cid",
        repository="repo",
        selected_branch="main",
        conversation_trigger=ConversationTrigger.GUI,
        git_provider=ProviderType.GITHUB,
        initial_user_msg="hello",
    )
    assert response.conversation_status == ConversationStatus.STARTING
    assert "Starting MetaSOP" in emitted["payload"]["message"]
    assert created["task"] is not None


@pytest.mark.asyncio
async def test_handle_metasop_conversation_failure(monkeypatch):
    monkeypatch.setattr(mc, "initialize_conversation", _async_wrap(lambda *args, **kwargs: None))
    with pytest.raises(RuntimeError):
        await mc._handle_metasop_conversation(
            user_id="user",
            conversation_id="cid",
            repository=None,
            selected_branch=None,
            conversation_trigger=ConversationTrigger.GUI,
            git_provider=None,
            initial_user_msg=None,
        )


@pytest.mark.asyncio
async def test_handle_regular_conversation_returns_status(monkeypatch):
    agent_loop_info = SimpleNamespace(status=ConversationStatus.RUNNING)
    monkeypatch.setattr(mc, "create_new_conversation", _async_wrap(lambda **kwargs: agent_loop_info))
    response = await mc._handle_regular_conversation(
        user_id="user",
        conversation_id="cid",
        repository="repo",
        selected_branch="main",
        initial_user_msg="hi",
        image_urls=["img"],
        replay_json=None,
        conversation_trigger=ConversationTrigger.GUI,
        conversation_instructions=None,
        git_provider=ProviderType.GITHUB,
        provider_tokens=MappingProxyType({}),
        user_secrets=SimpleNamespace(custom_secrets=None),
        mcp_config=None,
    )
    assert response.conversation_status == ConversationStatus.RUNNING


@pytest.mark.asyncio
async def test_new_conversation_remote_missing_message():
    response = await mc.new_conversation(mc.InitSessionRequest(), auth_type=mc.AuthType.BEARER)
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_new_conversation_success(monkeypatch):
    monkeypatch.setattr(
        mc,
        "_extract_request_data",
        lambda data: ("owner/repo", "main", "hello", ["img"], None, None, None, ProviderType.GITHUB, None),
    )
    monkeypatch.setattr(
        mc,
        "_determine_conversation_trigger",
        lambda suggested_task, create_microagent, auth_type: (ConversationTrigger.GUI, None, None),
    )
    monkeypatch.setattr(
        mc,
        "_apply_conversation_overrides",
        lambda repo, provider, override_repo, override_provider, task, msg: (repo, provider, msg),
    )
    monkeypatch.setattr(mc, "_prepare_conversation_params", lambda uid, tokens, secrets: ("user", MappingProxyType({}), SimpleNamespace(custom_secrets=None)))

    verify_called = {}

    async def fake_verify(repository, git_provider, provider_tokens):
        verify_called["repository"] = repository

    monkeypatch.setattr(mc, "_verify_repository_access", fake_verify)
    expected_response = mc.ConversationResponse(status="ok", conversation_id="cid", conversation_status=ConversationStatus.RUNNING)
    monkeypatch.setattr(mc, "_handle_regular_conversation", _async_wrap(lambda **kwargs: expected_response))
    monkeypatch.setattr(mc.uuid, "uuid4", lambda: SimpleNamespace(hex="cid"))

    result = await mc.new_conversation(mc.InitSessionRequest(), user_id="user")
    assert result is expected_response
    assert verify_called["repository"] == "owner/repo"


@pytest.mark.asyncio
async def test_new_conversation_handles_known_error(monkeypatch):
    monkeypatch.setattr(
        mc,
        "_extract_request_data",
        lambda data: (None, None, "msg", [], None, None, None, None, None),
    )
    monkeypatch.setattr(
        mc,
        "_determine_conversation_trigger",
        lambda *args, **kwargs: (ConversationTrigger.GUI, None, None),
    )
    monkeypatch.setattr(mc, "_apply_conversation_overrides", lambda *args, **kwargs: (None, None, "msg"))
    monkeypatch.setattr(mc, "_prepare_conversation_params", lambda uid, tokens, secrets: ("user", MappingProxyType({}), SimpleNamespace(custom_secrets=None)))
    monkeypatch.setattr(mc, "_handle_regular_conversation", _async_wrap(lambda **kwargs: (_ for _ in ()).throw(mc.MissingSettingsError("missing"))))

    response = await mc.new_conversation(mc.InitSessionRequest(), user_id="user")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_start_conversation_success(monkeypatch, patch_conversation_manager):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="cid",
        title="title",
        selected_repository="repo",
        user_id="user",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(get_metadata=_async_wrap(lambda cid: metadata))
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    monkeypatch.setattr(mc, "setup_init_conversation_settings", _async_wrap(lambda *args, **kwargs: SimpleNamespace()))

    response = await mc.start_conversation(mc.ProvidersSetModel(providers_set=[ProviderType.GITHUB]), conversation_id="cid", user_id="user")
    assert isinstance(response, mc.ConversationResponse)
    assert response.conversation_status == ConversationStatus.RUNNING


@pytest.mark.asyncio
async def test_start_conversation_not_found(monkeypatch):
    store = SimpleNamespace(get_metadata=_async_wrap(lambda cid: (_ for _ in ()).throw(RuntimeError("missing"))))
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))

    response = await mc.start_conversation(mc.ProvidersSetModel(), conversation_id="cid", user_id="user")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_start_conversation_error(monkeypatch, patch_conversation_manager):
    now = datetime.now(timezone.utc)
    metadata = ConversationMetadata(
        conversation_id="cid",
        title="title",
        selected_repository="repo",
        user_id="user",
        created_at=now,
        last_updated_at=now,
        trigger=ConversationTrigger.GUI,
    )
    store = SimpleNamespace(get_metadata=_async_wrap(lambda cid: metadata))
    monkeypatch.setattr(mc, "_resolve_conversation_store", _async_wrap(lambda store_override, user_id=None: store))
    monkeypatch.setattr(mc, "setup_init_conversation_settings", _async_wrap(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail"))))

    response = await mc.start_conversation(mc.ProvidersSetModel(), conversation_id="cid", user_id="user")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_stop_conversation_not_running(patch_conversation_manager):
    response = await mc.stop_conversation(conversation_id="cid", user_id="user")
    assert response.message == "Conversation was not running"


@pytest.mark.asyncio
async def test_stop_conversation_running(monkeypatch, patch_conversation_manager):
    patch_conversation_manager.agent_loop_info = [SimpleNamespace(conversation_id="cid", status=ConversationStatus.RUNNING)]
    closed = {}

    async def close_session(conversation_id):
        closed["id"] = conversation_id

    patch_conversation_manager.close_session = close_session
    response = await mc.stop_conversation(conversation_id="cid", user_id="user")
    assert response.conversation_status == ConversationStatus.RUNNING
    assert closed["id"] == "cid"


@pytest.mark.asyncio
async def test_stop_conversation_error(monkeypatch, patch_conversation_manager):
    async def failing_get_agent_loop_info(*args, **kwargs):
        raise RuntimeError("fail")

    patch_conversation_manager.get_agent_loop_info = failing_get_agent_loop_info
    response = await mc.stop_conversation(conversation_id="cid", user_id="user")
    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_add_experiment_config_existing_file(monkeypatch):
    class DummyFileStore:
        def __init__(self):
            self.read_calls = 0

        def read(self, path):
            self.read_calls += 1
            return "already"

        def write(self, path, content):
            raise AssertionError("should not write")

    dummy_store = DummyFileStore()
    monkeypatch.setattr(mc, "file_store", dummy_store)
    monkeypatch.setattr(mc, "get_experiment_config_filename", lambda cid: f"{cid}.json")
    assert mc.add_experiment_config_for_conversation(SimpleNamespace(), "cid") is False
    assert dummy_store.read_calls == 1


def test_add_experiment_config_write_failure(monkeypatch):
    class DummyFileStore:
        def read(self, path):
            raise FileNotFoundError

        def write(self, path, content):
            raise RuntimeError("fail")

    monkeypatch.setattr(mc, "file_store", DummyFileStore())
    monkeypatch.setattr(mc, "model_dump_json", lambda exp_config: "json")
    monkeypatch.setattr(mc, "get_experiment_config_filename", lambda cid: f"{cid}.json")
    assert mc.add_experiment_config_for_conversation(SimpleNamespace(), "cid") is True


def test_normalize_provider_tokens_converts(monkeypatch):
    class DummyProviderToken:
        @staticmethod
        def from_value(value):
            return value

    monkeypatch.setattr(mc, "ProviderToken", DummyProviderToken)
    tokens = {"github": "value", "invalid": "value"}
    normalized = mc._normalize_provider_tokens(tokens)
    assert ProviderType.GITHUB in normalized
    assert len(normalized) == 1


@pytest.mark.asyncio
async def test_test_conversations_endpoint():
    response = await mc.test_conversations_endpoint()
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_simple_conversations_endpoint():
    response = await mc.simple_conversations_endpoint()
    assert response["status"] == "simple_working"


@pytest.mark.asyncio
async def test_search_conversations_route_invokes_impl(monkeypatch):
    request = SimpleNamespace()
    monkeypatch.setattr(mc, "get_user_id", _async_wrap(lambda req: "user"))
    monkeypatch.setattr(mc, "get_conversation_store", _async_wrap(lambda req: "store"))

    async def fake_impl(**kwargs):
        assert kwargs["user_id"] == "user"
        assert kwargs["conversation_store"] == "store"
        return "result"

    monkeypatch.setattr(mc, "_search_conversations_impl", fake_impl)
    result = await mc.search_conversations_route(request, page_id="p", limit=5)
    assert result == "result"


@pytest.mark.asyncio
async def test_get_conversation_route(monkeypatch):
    request = SimpleNamespace()
    monkeypatch.setattr(mc, "get_user_id", _async_wrap(lambda req: "user"))
    monkeypatch.setattr(mc, "get_conversation_store", _async_wrap(lambda req: "store"))
    monkeypatch.setattr(mc, "get_conversation_details", _async_wrap(lambda cid, conversation_store, user_id: "details"))
    result = await mc._get_conversation_route(request, conversation_id="cid")
    assert result == "details"


@pytest.mark.asyncio
async def test_delete_conversation_route(monkeypatch):
    request = SimpleNamespace()
    monkeypatch.setattr(mc, "get_user_id", _async_wrap(lambda req: "user"))
    monkeypatch.setattr(mc, "get_conversation_store", _async_wrap(lambda req: "store"))
    monkeypatch.setattr(mc, "delete_conversation_entry", _async_wrap(lambda cid, user_id, conversation_store: True))
    result = await mc._delete_conversation_route(request, conversation_id="cid")
    assert result is True


@pytest.mark.asyncio
async def test_get_prompt_success(monkeypatch):
    monkeypatch.setattr(mc, "EventStore", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(mc, "_get_contextual_events", lambda event_store, event_id: "events")

    class DummySettingsStore:
        async def load(self):
            return SimpleNamespace(llm_model="model", llm_api_key="key", llm_base_url="url")

    monkeypatch.setattr(mc, "generate_prompt_template", lambda events: "template")
    monkeypatch.setattr(mc, "generate_prompt", lambda config, template, conversation_id: "prompt")
    response = await mc.get_prompt(
        event_id=1,
        conversation_id="cid",
        user_settings=DummySettingsStore(),
        metadata=SimpleNamespace(user_id="user"),
    )
    assert response.status_code == status.HTTP_200_OK
    assert json.loads(response.body)["prompt"] == "prompt"


@pytest.mark.asyncio
async def test_get_prompt_missing_settings(monkeypatch):
    monkeypatch.setattr(mc, "EventStore", lambda **kwargs: SimpleNamespace())
    monkeypatch.setattr(mc, "_get_contextual_events", lambda event_store, event_id: "events")

    class DummySettingsStore:
        async def load(self):
            return None

    with pytest.raises(ValueError):
        await mc.get_prompt(
            event_id=1,
            conversation_id="cid",
            user_settings=DummySettingsStore(),
            metadata=SimpleNamespace(user_id="user"),
        )


@pytest.mark.asyncio
async def test_get_conversation_info_error(monkeypatch):
    conversation = ConversationMetadata(
        conversation_id="cid",
        title="",
        selected_repository="repo",
        user_id="user",
    )

    def failing_default_title(conversation_id):
        raise RuntimeError("fail")

    monkeypatch.setattr(mc, "get_default_conversation_title", failing_default_title)
    result = await mc._get_conversation_info(conversation, num_connections=0, agent_loop_info=None)
    assert result is None
