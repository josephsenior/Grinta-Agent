"""Additional unit tests for forge.storage to improve coverage."""

from __future__ import annotations

import base64
import io
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import botocore
import pytest
import tenacity
from pydantic import SecretStr

import forge.storage as storage_module
import forge.storage.data_models.settings as settings_module
from forge.storage import get_file_store
from forge.storage.batched_web_hook import BatchedWebHookFileStore
from forge.storage.data_models.conversation_status import ConversationStatus
from forge.storage.data_models.conversation_metadata import ConversationMetadata
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
)
from forge.storage.data_models.slack_integration import (
    SlackConversationLink,
    SlackOAuthState,
    SlackUserLink,
    SlackWorkspace,
)
from forge.storage.knowledge_base_store import (
    KnowledgeBaseStore,
    get_knowledge_base_store,
)
from forge.storage.locations import (
    get_conversation_agent_state_filename,
    get_conversation_dir,
    get_conversation_event_filename,
    get_conversation_events_dir,
    get_conversation_init_data_filename,
    get_conversation_llm_registry_filename,
    get_conversation_metadata_filename,
    get_conversation_stats_filename,
    get_experiment_config_filename,
)
from forge.storage.memory import InMemoryFileStore
from forge.storage.files import FileStore
from forge.storage.s3 import S3FileStore
from forge.storage.secrets.file_secrets_store import FileSecretsStore
from forge.storage.slack_store import SlackStore
from forge.storage.web_hook import WebHookFileStore
from forge.storage.conversation.file_conversation_store import FileConversationStore, _sort_key
from forge.core.config.mcp_config import MCPConfig, MCPSHTTPServerConfig, MCPSSEServerConfig, MCPStdioServerConfig

class ImmediateExecutor:
    """Executor that executes submitted callables immediately for deterministic tests."""

    def submit(self, fn: Callable, *args, **kwargs):
        fn(*args, **kwargs)

        class _Result:
            def result(self, timeout: float | None = None) -> None:
                return None

        return _Result()


class StubFileStore(InMemoryFileStore):
    """Simple file store implementation for webhook tests."""

    def write(self, path: str, contents: str | bytes) -> None:
        self.files[path] = contents

    def read(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        value = self.files[path]
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value

@pytest.fixture(autouse=True)
def _isolate_executor(monkeypatch: pytest.MonkeyPatch):
    """Ensure background webhook tasks run synchronously during tests."""
    immediate = ImmediateExecutor()
    monkeypatch.setattr("forge.storage.web_hook.EXECUTOR", immediate)
    monkeypatch.setattr("forge.storage.batched_web_hook.EXECUTOR", immediate)
    yield


def test_get_file_store_local_requires_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SESSION_API_KEY", raising=False)
    with pytest.raises(ValueError):
        get_file_store("local")


def test_get_file_store_default_inmemory() -> None:
    store = get_file_store("in-memory-does-not-exist")
    assert isinstance(store, InMemoryFileStore)


def test_get_file_store_with_webhook_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, Any] = {}

    class DummyLocalStore:
        def __init__(self, path: str):
            created["path"] = path

    class DummyClient:
        def __init__(self, headers: dict | None = None):
            created["headers"] = headers or {}

    class DummyBatchStore:
        def __init__(self, store: Any, url: str, client: Any):
            created["wrapped"] = store
            created["url"] = url
            created["client"] = client

    monkeypatch.setenv("SESSION_API_KEY", "secret-token")
    monkeypatch.setattr(storage_module, "LocalFileStore", DummyLocalStore)
    httpx_module = SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(storage_module, "httpx", httpx_module, raising=False)
    monkeypatch.setattr(storage_module, "BatchedWebHookFileStore", DummyBatchStore)

    result = get_file_store(
        "local",
        file_store_path="/tmp/store",
        file_store_web_hook_url="https://hooks.example/",
        file_store_web_hook_batch=True,
    )

    assert isinstance(result, DummyBatchStore)
    assert created["path"] == "/tmp/store"
    assert created["url"] == "https://hooks.example/"
    assert created["headers"]["X-Session-API-Key"] == "secret-token"


def test_get_file_store_with_webhook_non_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        def __init__(self, headers: dict | None = None):
            self.headers = headers or {}

    class DummyInner(InMemoryFileStore):
        pass

    class DummyWebhook(WebHookFileStore):
        pass

    monkeypatch.setattr(storage_module, "InMemoryFileStore", DummyInner)
    httpx_module = SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(storage_module, "httpx", httpx_module, raising=False)
    monkeypatch.setattr(storage_module, "WebHookFileStore", DummyWebhook)

    result = get_file_store(
        "memory",
        file_store_web_hook_url="https://hooks.example/",
        file_store_web_hook_headers={"X-Test": "1"},
    )

    assert isinstance(result, DummyWebhook)
    assert isinstance(result.client, DummyClient)
    assert result.client.headers["X-Test"] == "1"


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("starting", ConversationStatus.STARTING),
        ("Started", ConversationStatus.RUNNING),
        ("ACTIVE", ConversationStatus.RUNNING),
        ("stopping", ConversationStatus.STOPPED),
        ("pause", ConversationStatus.PAUSED),
        ("deleted", ConversationStatus.ARCHIVED),
        (None, ConversationStatus.UNKNOWN),
        ("something-else", ConversationStatus.UNKNOWN),
    ],
)
def test_conversation_status_from_runtime_status(input_value: str | None, expected: ConversationStatus) -> None:
    assert ConversationStatus.from_runtime_status(input_value) is expected


def test_conversation_location_helpers() -> None:
    assert get_conversation_dir("123") == "sessions/123/"
    assert get_conversation_dir("123", "user") == "users/user/conversations/123/"
    assert get_conversation_events_dir("123") == "sessions/123/events/"
    assert (
        get_conversation_event_filename("123", 5, user_id="user")
        == "users/user/conversations/123/events/5.json"
    )
    assert get_conversation_metadata_filename("sid") == "sessions/sid/metadata.json"
    assert get_conversation_init_data_filename("sid", "user") == "users/user/conversations/sid/init.json"
    assert get_conversation_agent_state_filename("sid") == "sessions/sid/agent_state.pkl"
    assert get_conversation_llm_registry_filename("sid") == "sessions/sid/llm_registry.json"
    assert get_conversation_stats_filename("sid", "user") == "users/user/conversations/sid/conversation_stats.pkl"
    assert get_experiment_config_filename("sid") == "sessions/sid/exp_config.json"


def test_knowledge_base_store_persistence(tmp_path) -> None:
    store_path = tmp_path / "kb"
    store_path.mkdir()
    store = KnowledgeBaseStore(store_path)

    collection = store.create_collection("user-1", "Docs", "desc")
    document = KnowledgeBaseDocument(
        collection_id=collection.id,
        filename="notes.txt",
        content_hash="hash123",
        file_size_bytes=42,
        mime_type="text/plain",
        content_preview="hello world",
    )
    store.add_document(document)

    reloaded = KnowledgeBaseStore(store_path)
    loaded_collections = reloaded.list_collections("user-1")
    assert loaded_collections and loaded_collections[0].name == "Docs"
    loaded_docs = reloaded.list_documents(collection.id)
    assert loaded_docs and loaded_docs[0].filename == "notes.txt"
    assert reloaded.get_document_by_hash("hash123").id == document.id

    stats = reloaded.get_stats()
    assert stats["total_collections"] == 1
    assert stats["total_documents"] == 1
    assert stats["total_size_bytes"] == 42

    assert reloaded.delete_document(document.id) is True
    assert reloaded.list_documents(collection.id) == []

    assert reloaded.delete_collection(collection.id) is True
    assert reloaded.list_collections("user-1") == []


def test_get_knowledge_base_store_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("forge.storage.knowledge_base_store._store", None, raising=False)

    sentinel = object()

    def fake_constructor():
        return sentinel

    monkeypatch.setattr("forge.storage.knowledge_base_store.KnowledgeBaseStore", fake_constructor)

    first = get_knowledge_base_store()
    second = get_knowledge_base_store()
    assert first is sentinel
    assert second is sentinel


def make_slack_store(tmp_path) -> SlackStore:
    config = SimpleNamespace(workspace_base=str(tmp_path))
    return SlackStore(config)


def test_slack_store_workspace_and_links(tmp_path: pytest.TempPathFactory) -> None:
    store = make_slack_store(tmp_path)

    workspace = SlackWorkspace(
        id="workspace-id",
        team_id="T1",
        team_name="Team",
        bot_token="xoxb",
        bot_user_id="Ubot",
    )
    store.save_workspace(workspace)
    assert store.get_workspace("T1").team_name == "Team"
    assert store.list_workspaces()[0].team_id == "T1"
    assert store.delete_workspace("T1") is True
    assert store.get_workspace("T1") is None

    store.save_workspace(workspace)
    user_link = SlackUserLink(slack_user_id="U1", slack_workspace_id="workspace-id", FORGE_user_id="forge-1")
    store.save_user_link(user_link)
    assert store.get_user_link("workspace-id", "U1").FORGE_user_id == "forge-1"
    assert store.get_user_links_by_FORGE_user("forge-1")[0].slack_user_id == "U1"
    assert store.delete_user_link("workspace-id", "U1") is True

    conversation_link = SlackConversationLink(
        slack_channel_id="C1",
        slack_thread_ts="123.456",
        slack_workspace_id="workspace-id",
        conversation_id="conv-1",
        created_by_slack_user_id="U1",
    )
    store.save_conversation_link(conversation_link)
    assert store.get_conversation_link("workspace-id", "C1", "123.456").conversation_id == "conv-1"
    assert store.get_conversation_links_by_conversation_id("conv-1")[0].slack_channel_id == "C1"
    assert store.delete_conversation_link("workspace-id", "C1", "123.456") is True


def test_slack_store_oauth_state_management(monkeypatch: pytest.MonkeyPatch, tmp_path: pytest.TempPathFactory) -> None:
    store = make_slack_store(tmp_path)

    fake_uuid = SimpleNamespace(hex="abc123")
    monkeypatch.setattr("forge.storage.slack_store.uuid.uuid4", lambda: fake_uuid)

    generated = store.generate_oauth_state("user-1", redirect_url="https://example.com")
    assert generated == "abc123"
    saved_state = store.get_oauth_state("abc123")
    assert saved_state.user_id == "user-1"

    expired_state = SlackOAuthState(
        state="expired",
        user_id="user-2",
        created_at=datetime.utcnow() - timedelta(minutes=15),
    )
    store.save_oauth_state(expired_state)
    removed = store.cleanup_expired_oauth_states(expiry_minutes=5)
    assert removed == 1
    assert store.delete_oauth_state("abc123") is True
    assert store.get_oauth_state("abc123") is None


def test_slack_store_read_invalid_json(tmp_path: pytest.TempPathFactory) -> None:
    store = make_slack_store(tmp_path)
    invalid_file = store.workspaces_file
    invalid_file.write_text("{not-json")
    assert store._read_json_file(invalid_file) == {}


@pytest.mark.asyncio
async def test_file_secrets_store_load_and_store(monkeypatch: pytest.MonkeyPatch) -> None:
    backing_store = InMemoryFileStore()
    store = FileSecretsStore(backing_store, user_id="user-42")
    path = store._build_default_path()
    assert path == "users/user-42/user_secrets.json"

    backing_store.write(
        path,
        json.dumps(
            {
                "user_id": "user-42",
                "provider_tokens": {
                    "github": "token123",
                    "gitlab": {"token": "abc", "workspace": "w1"},
                    "invalid": None,
                },
            }
        ),
    )

    loaded = await store.load()
    assert loaded is not None
    assert loaded.provider_tokens is not None

    from forge.integrations.provider import ProviderToken
    from forge.integrations.service_types import ProviderType
    from pydantic import SecretStr

    assert ProviderType.GITHUB in loaded.provider_tokens
    github_token = loaded.provider_tokens[ProviderType.GITHUB]
    assert github_token.token is not None
    assert github_token.token.get_secret_value() == "token123"

    updated = loaded.model_copy(
        update={
            "provider_tokens": {
                ProviderType.GITHUB: ProviderToken(token=SecretStr("updated")),
                ProviderType.GITLAB: ProviderToken(token=SecretStr("abc")),
            }
        }
    )
    await store.store(updated)
    stored_json = json.loads(backing_store.read(path))
    assert stored_json["provider_tokens"]["github"]["token"] == "updated"


@pytest.mark.asyncio
async def test_file_secrets_store_get_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        file_store="memory",
        file_store_path="/tmp",
        file_store_web_hook_url=None,
        file_store_web_hook_headers=None,
        file_store_web_hook_batch=False,
    )
    dummy_store = InMemoryFileStore()
    monkeypatch.setattr("forge.storage.secrets.file_secrets_store.get_file_store", lambda **_: dummy_store)

    instance = await FileSecretsStore.get_instance(config, user_id="user-1")
    assert instance.file_store is dummy_store
    assert instance.user_id == "user-1"


def test_web_hook_file_store_triggers_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = StubFileStore()
    called: dict[str, Any] = {}

    class DummyResponse:
        def __init__(self):
            called["raised"] = True

        def raise_for_status(self) -> None:
            called["status_checked"] = True

    class DummyClient:
        def __init__(self):
            self.requests: list[tuple[str, Any]] = []

        def post(self, url: str, content: Any):
            self.requests.append(("POST", url, content))
            return DummyResponse()

        def delete(self, url: str):
            self.requests.append(("DELETE", url, None))
            return DummyResponse()

    client = DummyClient()
    store = WebHookFileStore(inner, "https://hook/", client=client)
    store.write("path.txt", "data")
    assert inner.read("path.txt") == "data"
    assert ("POST", "https://hook/path.txt", "data") in client.requests

    store.delete("path.txt")
    store._on_write("other.txt", b"bytes")
    store._on_delete("other.txt")

    assert ("DELETE", "https://hook/path.txt", None) in client.requests
    assert ("POST", "https://hook/other.txt", b"bytes") in client.requests
    assert ("DELETE", "https://hook/other.txt", None) in client.requests
    assert called["status_checked"] is True
    with pytest.raises(FileNotFoundError):
        inner.read("path.txt")


def test_batched_web_hook_file_store_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = StubFileStore()
    payloads: list[Any] = []

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

    class DummyClient:
        def post(self, url: str, json: Any):
            payloads.append((url, json))
            return DummyResponse()

    store = BatchedWebHookFileStore(
        inner,
        "https://batch/",
        client=DummyClient(),
        batch_timeout_seconds=0.1,
        batch_size_limit_bytes=4096,
    )
    store.write("file.txt", "hello")
    store.write("binary.bin", b"\xff\x00")
    store.delete("file.txt")
    store.flush()

    assert inner.files["binary.bin"] == b"\xff\x00"
    assert payloads, "expected batched payload to be sent"
    _, batch_json = payloads[0]
    methods = {item["method"] for item in batch_json}
    paths = {item["path"] for item in batch_json}
    assert methods == {"POST", "DELETE"}
    assert {"file.txt", "binary.bin"} & paths
    binary_entry = next(item for item in batch_json if item["path"] == "binary.bin")
    assert binary_entry["encoding"] == "base64"


class DummyS3Client:
    """Minimal in-memory fake S3 client."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:  # noqa: N803
        self.objects[Key] = Body

    def get_object(self, Bucket: str, Key: str) -> dict:  # noqa: N803
        if Key not in self.objects:
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchKey"}},
                "GetObject",
            )
        return {"Body": io.BytesIO(self.objects[Key])}

    def list_objects_v2(self, Bucket: str, Prefix: str):  # noqa: N803
        contents = [{"Key": key} for key in self.objects if key.startswith(Prefix)]
        return {"Contents": contents or None}

    def delete_object(self, Bucket: str, Key: str):  # noqa: N803
        self.objects.pop(Key, None)


def test_s3_file_store_basic_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyS3Client()
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: dummy)
    monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
    store = S3FileStore("bucket-name")

    store.write("folder/file.txt", "hello")
    assert store.read("folder/file.txt") == "hello"
    listing = store.list("folder")
    assert "folder/file.txt" in listing or "folder/" in listing
    store.delete("folder/file.txt")
    assert dummy.objects == {}


def test_s3_file_store_error_translation(monkeypatch: pytest.MonkeyPatch) -> None:
    class RaisingClient(DummyS3Client):
        def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "AccessDenied"}},
                "PutObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: RaisingClient())
    store = S3FileStore("bucket-name")

    with pytest.raises(FileNotFoundError) as err:
        store.write("path", "data")
    assert "Access denied" in str(err.value)


def test_s3_file_store_url_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyS3Client()
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: dummy)
    store = S3FileStore("bucket-name")
    assert store._ensure_url_scheme(True, "http://example.com") == "https://example.com"
    assert store._ensure_url_scheme(False, "https://example.com") == "http://example.com"
    assert store._ensure_url_scheme(True, None) is None


def test_batched_webhook_enqueues_on_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = StubFileStore()
    payloads: list[Any] = []

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

    class DummyClient:
        def post(self, url: str, json: Any):
            payloads.append(json)
            return DummyResponse()

    store = BatchedWebHookFileStore(
        inner,
        "https://batch/",
        client=DummyClient(),
        batch_timeout_seconds=10,
        batch_size_limit_bytes=1,
    )
    store.write("big.txt", "A" * 10)
    assert payloads, "batch should be flushed when size limit exceeded"
    assert payloads[0][0]["path"] == "big.txt"


def test_web_hook_on_write_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = StubFileStore()
    attempts: list[int] = []

    class DummyResponse:
        def raise_for_status(self) -> None:
            if len(attempts) < 2:
                raise botocore.exceptions.EndpointConnectionError(endpoint_url="http://error")

    class DummyClient:
        def post(self, url: str, content: Any):
            attempts.append(1)
            return DummyResponse()

        def delete(self, url: str):
            return DummyResponse()

    store = WebHookFileStore(inner, "https://hook/", client=DummyClient())
    store._on_write("path", "content")
    assert len(attempts) >= 2


def test_web_hook_delete_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    inner = StubFileStore()
    attempts: list[int] = []

    class DummyResponse:
        def raise_for_status(self) -> None:
            raise botocore.exceptions.EndpointConnectionError(endpoint_url="http://error")

    class DummyClient:
        def post(self, url: str, content: Any):
            return DummyResponse()

        def delete(self, url: str):
            attempts.append(1)
            return DummyResponse()

    store = WebHookFileStore(inner, "https://hook/", client=DummyClient())
    with pytest.raises(tenacity.RetryError):
        store._on_delete("file")
    assert len(attempts) == 3


@pytest.mark.asyncio
async def test_file_conversation_store_initializes_default_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "forge.core.config.forge_config.ForgeConfig",
        lambda: SimpleNamespace(workspace_base=str(tmp_path)),
    )
    store = FileConversationStore(StubFileStore(), config=None, user_id="user-abc")
    expected = tmp_path / ".Forge" / "conversations" / "user-abc"
    assert expected.exists()


@pytest.mark.asyncio
async def test_file_conversation_store_get_metadata_removes_legacy_fields(tmp_path: Path) -> None:
    config = SimpleNamespace(workspace_base=str(tmp_path))
    store = FileConversationStore(StubFileStore(), config=config)
    path = store.get_conversation_metadata_filename("conv-1")
    legacy_payload = {
        "conversation_id": "conv-1",
        "title": "Legacy Conversation",
        "selected_repository": None,
        "user_id": "user",
        "created_at": "2024-01-01T00:00:00+00:00",
        "last_updated_at": "2024-01-01T00:00:00+00:00",
        "github_user_id": "123",
    }
    store.file_store.write(path, json.dumps(legacy_payload))
    metadata = await store.get_metadata("conv-1")
    assert isinstance(metadata, ConversationMetadata)
    assert metadata.conversation_id == "conv-1"


@pytest.mark.asyncio
async def test_file_conversation_store_get_metadata_creates_when_invalid(tmp_path: Path) -> None:
    store = FileConversationStore(StubFileStore(), config=SimpleNamespace(workspace_base=str(tmp_path)))
    path = store.get_conversation_metadata_filename("new-conv")
    store.file_store.write(path, "{}")
    metadata = await store.get_metadata("new-conv")
    assert metadata.conversation_id == "new-conv"
    saved = json.loads(store.file_store.read(path))
    assert saved["conversation_id"] == "new-conv"


@pytest.mark.asyncio
async def test_file_conversation_store_get_metadata_no_create(tmp_path: Path) -> None:
    store = FileConversationStore(StubFileStore(), config=SimpleNamespace(workspace_base=str(tmp_path)))
    path = store.get_conversation_metadata_filename("missing")
    store.file_store.write(path, "{}")
    with pytest.raises(FileNotFoundError):
        await store.get_metadata("missing", create_if_missing=False)


@pytest.mark.asyncio
async def test_file_conversation_store_delete_and_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    class TrackingStore(StubFileStore):
        def __init__(self) -> None:
            super().__init__()
            self.deleted: str | None = None

        def delete(self, path: str) -> None:
            self.deleted = path
            super().delete(path)

    tracking = TrackingStore()
    store = FileConversationStore(tracking, config=SimpleNamespace(workspace_base=None))
    path = store.get_conversation_metadata_filename("conv")
    store.file_store.write(
        path,
        json.dumps(
            {
                "conversation_id": "conv",
                "title": "Test",
                "selected_repository": None,
                "user_id": "user",
                "created_at": "2024-01-01T00:00:00+00:00",
                "last_updated_at": "2024-01-01T00:00:00+00:00",
            }
        ),
    )
    assert await store.exists("conv") is True
    await store.delete_metadata("conv")
    assert tracking.deleted == get_conversation_dir("conv")
    assert await store.exists("conv") is False


@pytest.mark.asyncio
async def test_file_conversation_store_search_with_pagination(caplog: pytest.LogCaptureFixture) -> None:
    store = FileConversationStore(StubFileStore(), config=SimpleNamespace(workspace_base=None))

    def write_metadata(cid: str, created: str) -> None:
        store.file_store.write(
            store.get_conversation_metadata_filename(cid),
            json.dumps(
                {
                    "conversation_id": cid,
                    "title": cid,
                    "selected_repository": None,
                    "user_id": "user",
                    "created_at": created,
                    "last_updated_at": created,
                }
            ),
        )

    write_metadata("conv-a", "2024-01-01T00:00:00+00:00")
    write_metadata("conv-b", "2024-01-02T00:00:00+00:00")
    write_metadata("conv-c", "2024-01-03T00:00:00+00:00")
    store.file_store.write(store.get_conversation_metadata_filename("invalid"), "{}")

    with caplog.at_level("WARNING"):
        result = await store.search(limit=2)
    assert [meta.conversation_id for meta in result.results] == ["conv-c", "conv-b"]
    assert result.next_page_id is not None
    next_offset = int(base64.b64decode(result.next_page_id).decode())
    assert next_offset == 2

    result_page_2 = await store.search(page_id=result.next_page_id, limit=2)
    assert [meta.conversation_id for meta in result_page_2.results] == ["conv-a"]
    assert result_page_2.next_page_id is None


@pytest.mark.asyncio
async def test_file_conversation_store_search_handles_missing_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    store = FileConversationStore(StubFileStore(), config=SimpleNamespace(workspace_base=None))

    def raise_not_found(path: str) -> list[str]:
        raise FileNotFoundError

    monkeypatch.setattr(store.file_store, "list", raise_not_found)
    result = await store.search()
    assert result.results == []
    assert result.next_page_id is None


@pytest.mark.asyncio
async def test_file_conversation_store_get_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get_file_store(**kwargs):
        captured.update(kwargs)
        return StubFileStore()

    monkeypatch.setattr("forge.storage.conversation.file_conversation_store.get_file_store", fake_get_file_store)
    config = SimpleNamespace(
        file_store="memory",
        file_store_path="/tmp",
        file_store_web_hook_url=None,
        file_store_web_hook_headers={"x": "1"},
        file_store_web_hook_batch=False,
        workspace_base=None,
    )
    store = await FileConversationStore.get_instance(config, user_id="user")
    assert isinstance(store, FileConversationStore)
    assert captured["file_store_type"] == "memory"
    assert captured["file_store_path"] == "/tmp"


def test_file_conversation_sort_key() -> None:
    metadata = ConversationMetadata(
        conversation_id="conv",
        title="Title",
        selected_repository=None,
        created_at=datetime.now(timezone.utc),
    )
    assert _sort_key(metadata) == metadata.created_at.isoformat()


def test_knowledge_base_store_uses_default_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    store = KnowledgeBaseStore()
    default_path = tmp_path / ".Forge" / "kb"
    assert store.storage_dir == default_path
    assert default_path.exists()


def test_knowledge_base_store_handles_corrupt_files(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    store_path = tmp_path / "kb"
    store_path.mkdir()
    (store_path / "collections.json").write_text("{invalid json")
    (store_path / "documents.json").write_text("{invalid json")
    with caplog.at_level("ERROR"):
        store = KnowledgeBaseStore(store_path)
    assert store.list_collections("user") == []


def test_knowledge_base_store_update_and_delete(tmp_path: Path) -> None:
    store = KnowledgeBaseStore(tmp_path)
    collection = store.create_collection("user", "Old", "desc")
    store.add_document(
        KnowledgeBaseDocument(
            collection_id=collection.id,
            filename="one.txt",
            content_hash="hash-1",
            file_size_bytes=100,
            mime_type="text/plain",
        )
    )
    updated = store.update_collection(collection.id, name="New", description="updated")
    assert updated and updated.name == "New"
    assert updated.description == "updated"
    assert store.delete_document(updated.id) is False
    assert store.delete_collection(collection.id) is True
    assert store.list_collections("user") == []


def test_knowledge_base_store_delete_document_updates_stats(tmp_path: Path) -> None:
    store = KnowledgeBaseStore(tmp_path)
    collection = store.create_collection("user", "Docs")
    doc = KnowledgeBaseDocument(
        collection_id=collection.id,
        filename="one.txt",
        content_hash="hash-1",
        file_size_bytes=50,
        mime_type="text/plain",
    )
    store.add_document(doc)
    assert store.get_stats()["total_documents"] == 1
    assert store.delete_document(doc.id) is True
    stats = store.get_stats()
    assert stats["total_documents"] == 0
    assert stats["total_size_bytes"] == 0


def test_s3_file_store_read_missing_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingBucketClient(DummyS3Client):
        def get_object(self, Bucket: str, Key: str):  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchBucket"}},
                "GetObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: MissingBucketClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.read("key")


def test_s3_file_store_read_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingKeyClient(DummyS3Client):
        def get_object(self, Bucket: str, Key: str):  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchKey"}},
                "GetObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: MissingKeyClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.read("missing")


def test_s3_file_store_delete_handles_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    class DeletingClient(DummyS3Client):
        def __init__(self):
            super().__init__()
            self.deleted_keys: list[str] = []

        def list_objects_v2(self, Bucket: str, Prefix: str):  # noqa: N803
            return {"Contents": [{"Key": f"{Prefix}a.txt"}, {"Key": f"{Prefix}b.txt"}]}

        def delete_object(self, Bucket: str, Key: str):  # noqa: N803
            self.deleted_keys.append(Key)

    client = DeletingClient()
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: client)
    store = S3FileStore("bucket")
    store.delete("folder")
    assert set(client.deleted_keys) == {"folder", "folder/a.txt", "folder/b.txt"}


def test_s3_file_store_delete_access_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    class AccessDeniedClient(DummyS3Client):
        def delete_object(self, Bucket: str, Key: str):  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "AccessDenied"}},
                "DeleteObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: AccessDeniedClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.delete("path")


def test_s3_file_store_list_returns_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyS3Client()
    client.put_object(Bucket="bucket", Key="folder/a.txt", Body=b"a")
    client.put_object(Bucket="bucket", Key="folder/b.txt", Body=b"b")
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: client)
    store = S3FileStore("bucket")
    listing = store.list("folder")
    assert "folder/" not in listing
    assert "folder/a.txt" in listing or "folder/a/" in listing


def test_s3_file_store_list_root_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    client = DummyS3Client()
    client.put_object(Bucket="bucket", Key="root.txt", Body=b"data")
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: client)
    store = S3FileStore("bucket")
    listing = store.list("")
    assert "root.txt" in listing


def test_s3_file_store_write_other_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class OtherErrorClient(DummyS3Client):
        def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "Throttled"}},
                "PutObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: OtherErrorClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.write("key", "value")


def test_s3_file_store_read_general_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenClient(DummyS3Client):
        def get_object(self, Bucket: str, Key: str):  # noqa: N803
            raise RuntimeError("boom")

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: BrokenClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.read("key")


def test_s3_file_store_delete_no_such_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingBucketClient(DummyS3Client):
        def delete_object(self, Bucket: str, Key: str):  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchBucket"}},
                "DeleteObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: MissingBucketClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.delete("path")


def test_s3_file_store_delete_no_such_key(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingKeyClient(DummyS3Client):
        def delete_object(self, Bucket: str, Key: str):  # noqa: N803
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchKey"}},
                "DeleteObject",
            )

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: MissingKeyClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.delete("path")


def test_s3_file_store_delete_general_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenClient(DummyS3Client):
        def delete_object(self, Bucket: str, Key: str):  # noqa: N803
            raise RuntimeError("broken")

    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: BrokenClient())
    store = S3FileStore("bucket")
    with pytest.raises(FileNotFoundError):
        store.delete("path")


def test_s3_file_store_delete_empty_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    class SimpleClient(DummyS3Client):
        def __init__(self):
            super().__init__()
            self.list_calls: list[tuple[str, str]] = []

        def list_objects_v2(self, Bucket: str, Prefix: str):  # noqa: N803
            self.list_calls.append((Bucket, Prefix))
            return {"Contents": []}

    client = SimpleClient()
    monkeypatch.setattr("forge.storage.s3.boto3.client", lambda *args, **kwargs: client)
    store = S3FileStore("bucket")
    store.delete("")
    assert client.list_calls[0] == ("bucket", "/")


def test_file_store_base_methods() -> None:
    class DummyFileStore(FileStore):
        def write(self, path: str, contents: str | bytes) -> None:
            super().write(path, contents)

        def read(self, path: str) -> str:
            super().read(path)
            return ""

        def list(self, path: str) -> list[str]:
            super().list(path)
            return []

        def delete(self, path: str) -> None:
            super().delete(path)

    store = DummyFileStore()
    assert store.write("path", "value") is None
    assert store.read("path") == ""
    assert store.list("path") == []
    assert store.delete("path") is None


def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_module, "_settings_from_config_cache", None, raising=False)
    monkeypatch.setattr(settings_module, "_settings_from_config_cache_time", 0.0, raising=False)
    monkeypatch.setattr(settings_module, "_settings_from_config_cache_loader_id", None, raising=False)


def test_settings_api_key_serializer_exposes_when_requested() -> None:
    settings = settings_module.Settings(
        llm_api_key=SecretStr("secret"),
        search_api_key=SecretStr("search"),
    )
    masked = settings.model_dump()
    assert masked["llm_api_key"] != "secret"
    revealed = settings.model_dump(context={"expose_secrets": True})
    assert revealed["llm_api_key"] == "secret"
    assert revealed["search_api_key"] == "search"


def test_settings_convert_provider_tokens() -> None:
    data = {
        "secrets_store": {
            "provider_tokens": {"github": {"token": "abc"}},
            "custom_secrets": {"name": {"secret": "value", "description": "desc"}},
        }
    }
    converted = settings_module.Settings.convert_provider_tokens(data.copy())
    secret_store = converted["secret_store"]
    assert isinstance(secret_store, settings_module.UserSecrets)


def test_settings_validate_condenser_max_size() -> None:
    assert settings_module.Settings.validate_condenser_max_size(None) is None
    with pytest.raises(ValueError):
        settings_module.Settings.validate_condenser_max_size(10)
    assert settings_module.Settings.validate_condenser_max_size(40) == 40


def test_settings_secrets_store_serializer() -> None:
    serialized = settings_module.Settings().model_dump()
    assert serialized["secrets_store"] == {"provider_tokens": {}}


def test_settings_check_explicit_llm_config_env(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = SimpleNamespace(api_key=SecretStr("env"))
    app_config = SimpleNamespace(llms={"llm": explicit})
    monkeypatch.setenv("FORGE_API_KEY", "env")
    assert settings_module.Settings._check_explicit_llm_config(app_config) is True
    monkeypatch.delenv("FORGE_API_KEY", raising=False)
    explicit.api_key = SecretStr("")
    assert settings_module.Settings._check_explicit_llm_config(app_config) is False


def test_settings_validate_api_key_cases() -> None:
    assert settings_module.Settings._validate_api_key(None) is False
    assert settings_module.Settings._validate_api_key(SecretStr("")) is False
    assert settings_module.Settings._validate_api_key(SecretStr("key")) is True


def build_app_config(api_key: str | None = "secret") -> Any:
    llm_config = SimpleNamespace(
        model="gpt",
        api_key=SecretStr(api_key) if api_key is not None else None,
        base_url="https://example.com",
    )
    security = SimpleNamespace(security_analyzer="analyzer", confirmation_mode=True)
    sandbox = SimpleNamespace(remote_runtime_resource_factor=2)
    return SimpleNamespace(
        default_agent="assistant",
        max_iterations=5,
        security=security,
        sandbox=sandbox,
        mcp=MCPConfig(sse_servers=[], stdio_servers=[], shttp_servers=[]),
        search_api_key=SecretStr("search"),
        max_budget_per_task=123.0,
        llms={},
        get_llm_config=lambda: llm_config,
    )


def test_settings_from_config_caches_results(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache(monkeypatch)
    calls = {"count": 0}

    def fake_loader():
        calls["count"] += 1
        return build_app_config()

    monkeypatch.setattr(settings_module, "load_FORGE_config", fake_loader)
    first = settings_module.Settings.from_config()
    second = settings_module.Settings.from_config()
    assert first is second
    assert calls["count"] == 1


def test_settings_from_config_handles_explicit_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache(monkeypatch)

    def fake_loader():
        config = build_app_config()
        config.llms = {"llm": SimpleNamespace(api_key=None)}
        return config

    monkeypatch.setattr(settings_module, "load_FORGE_config", fake_loader)
    monkeypatch.setattr(
        settings_module.Settings,
        "_check_explicit_llm_config",
        staticmethod(lambda app_config: True),
    )
    assert settings_module.Settings.from_config() is None


def test_settings_from_config_invalid_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache(monkeypatch)

    def fake_loader():
        return build_app_config(api_key="")

    monkeypatch.setattr(settings_module, "load_FORGE_config", fake_loader)
    assert settings_module.Settings.from_config() is None


def test_settings_merge_with_config_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_settings_cache(monkeypatch)
    config = build_app_config()
    config.mcp = MCPConfig(
        sse_servers=[MCPSSEServerConfig(url="https://config-sse.example")],
        stdio_servers=[MCPStdioServerConfig(name="config", command="cmd")],
        shttp_servers=[MCPSHTTPServerConfig(url="https://config-shttp.example")],
    )
    monkeypatch.setattr(settings_module, "load_FORGE_config", lambda: config)
    base_settings = settings_module.Settings(
        mcp_config=MCPConfig(
            sse_servers=[MCPSSEServerConfig(url="https://store-sse.example")],
            stdio_servers=[],
            shttp_servers=[],
        ),
    )
    merged = base_settings.merge_with_config_settings()
    assert {server.url for server in merged.mcp_config.sse_servers} == {
        "https://config-sse.example",
        "https://store-sse.example",
    }

