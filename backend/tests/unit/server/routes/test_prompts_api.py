"""Unit tests for prompts API routes."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient
from pydantic import SecretStr

from forge.integrations.provider import ProviderToken, ProviderType
from forge.server.routes import prompts as prompts_routes
from forge.server.app import app
from forge.server.user_auth.user_auth import UserAuth
from forge.storage.data_models.user_secrets import UserSecrets
from forge.storage.memory import InMemoryFileStore
from forge.storage.secrets.secrets_store import SecretsStore
from forge.storage.settings.file_settings_store import FileSettingsStore
from forge.storage.settings.settings_store import SettingsStore
from forge.storage.data_models.prompt_template import (
    PromptCategory,
    PromptTemplate,
)


class MockUserAuth(UserAuth):
    """Mock implementation of UserAuth for testing."""

    def __init__(self):
        self._settings = None
        self._settings_store = MagicMock(spec=SettingsStore)
        self._settings_store.load = AsyncMock(return_value=None)
        self._settings_store.store = AsyncMock()
        self._secrets_store = AsyncMock(spec=SecretsStore)

    async def get_user_id(self) -> str | None:
        return "test-user"

    async def get_user_email(self) -> str | None:
        return "test@example.com"

    async def get_access_token(self) -> SecretStr | None:
        return SecretStr("test-token")

    async def get_provider_tokens(
        self,
    ) -> MappingProxyType[ProviderType, ProviderToken] | None:
        return MappingProxyType({})

    async def get_user_settings_store(self) -> SettingsStore:
        return cast(SettingsStore, self._settings_store)

    async def get_secrets_store(self) -> SecretsStore:
        return cast(SecretsStore, self._secrets_store)

    async def get_user_secrets(self) -> UserSecrets | None:
        return None

    @classmethod
    async def get_instance(cls, request: Request) -> UserAuth:
        return MockUserAuth()


@pytest.fixture
def test_client(tmp_path):
    # Set up workspace directory
    workspace_dir = str(tmp_path / "workspace")
    os.makedirs(workspace_dir, exist_ok=True)

    with (
        patch.dict(
            os.environ,
            {
                "SESSION_API_KEY": "",
                "CSRF_PROTECTION_ENABLED": "false",  # Disable CSRF for tests
                "RATE_LIMITING_ENABLED": "false",  # Disable rate limiting for tests
            },
            clear=False,
        ),
        patch("forge.server.dependencies._SESSION_API_KEY", None),
        patch(
            "forge.server.user_auth.user_auth.UserAuth.get_instance",
            return_value=MockUserAuth(),
        ),
        patch(
            "forge.storage.settings.file_settings_store.FileSettingsStore.get_instance",
            AsyncMock(return_value=FileSettingsStore(InMemoryFileStore())),
        ),
        patch("forge.server.shared.config.workspace_base", workspace_dir),
    ):
        with TestClient(app) as client:
            yield client


@pytest.fixture
def workspace_base(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts_routes.config, "workspace_base", str(tmp_path))
    return tmp_path


@pytest.mark.asyncio
async def test_create_prompt(test_client):
    """Test creating a new prompt."""
    prompt_data = {
        "title": "Test Prompt",
        "content": "This is a test prompt: {{variable1}}",
        "description": "Test description",
        "category": "coding",
        "variables": [
            {"name": "variable1", "description": "Test variable", "required": True}
        ],
        "tags": ["test", "example"],
    }

    response = test_client.post("/api/prompts/", json=prompt_data)
    assert response.status_code in [200, 201]  # Accept both OK and Created
    data = response.json()
    assert data["title"] == "Test Prompt"
    assert data["category"] == "coding"
    assert len(data["tags"]) == 2
    assert "id" in data


@pytest.mark.asyncio
async def test_list_prompts(test_client):
    """Test listing prompts."""
    # Create a prompt first
    prompt_data = {
        "title": "List Test Prompt",
        "content": "Test content",
        "category": "coding",
    }
    test_client.post("/api/prompts/", json=prompt_data)

    # List prompts
    response = test_client.get("/api/prompts/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_prompt(test_client):
    """Test getting a specific prompt."""
    # Create a prompt
    prompt_data = {"title": "Get Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Get the prompt
    response = test_client.get(f"/api/prompts/{prompt_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == prompt_id
    assert data["title"] == "Get Test"


@pytest.mark.asyncio
async def test_update_prompt(test_client):
    """Test updating a prompt."""
    # Create a prompt
    prompt_data = {"title": "Update Test", "content": "Original", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Update the prompt
    update_data = {"title": "Updated Title", "content": "Updated content"}
    response = test_client.patch(f"/api/prompts/{prompt_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["content"] == "Updated content"


@pytest.mark.asyncio
async def test_delete_prompt(test_client):
    """Test deleting a prompt."""
    # Create a prompt
    prompt_data = {"title": "Delete Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Delete the prompt
    response = test_client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == 204  # 204 No Content for successful deletion

    # Verify it's deleted
    get_response = test_client.get(f"/api/prompts/{prompt_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_search_prompts(test_client):
    """Test searching prompts."""
    # Create test prompts
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Python Debugging",
            "content": "Debug code",
            "category": "debugging",
        },
    )
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Code Review",
            "content": "Review code",
            "category": "code_review",
        },
    )

    # Search for "debug" using POST /api/prompts/search endpoint
    response = test_client.post(
        "/api/prompts/search", json={"query": "debug", "limit": 100, "offset": 0}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("Debug" in p["title"] for p in data)


@pytest.mark.asyncio
async def test_toggle_favorite_prompt(test_client):
    """Test toggling prompt favorite status using PATCH."""
    # Create a prompt
    prompt_data = {"title": "Favorite Test", "content": "Test", "category": "coding"}
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Set favorite to true
    response = test_client.patch(
        f"/api/prompts/{prompt_id}", json={"is_favorite": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_favorite"] is True

    # Set favorite to false
    response = test_client.patch(
        f"/api/prompts/{prompt_id}", json={"is_favorite": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_favorite"] is False


@pytest.mark.asyncio
async def test_export_import_prompts(test_client):
    """Test exporting and importing prompts."""
    # Create prompts
    test_client.post(
        "/api/prompts/",
        json={"title": "Export Test 1", "content": "Content 1", "category": "coding"},
    )
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Export Test 2",
            "content": "Content 2",
            "category": "debugging",
        },
    )

    # Export
    response = test_client.get("/api/prompts/export")
    assert response.status_code == 200
    export_data = response.json()
    assert "prompts" in export_data
    assert len(export_data["prompts"]) >= 2

    # Import
    import_response = test_client.post("/api/prompts/import", json=export_data)
    assert import_response.status_code == 200
    result = import_response.json()
    assert "imported" in result or "updated" in result


@pytest.mark.asyncio
async def test_get_prompt_stats(test_client):
    """Test getting prompt statistics."""
    # Create some prompts
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Stats Test 1",
            "content": "Content 1",
            "category": "coding",
            "is_favorite": True,
        },
    )
    test_client.post(
        "/api/prompts/",
        json={"title": "Stats Test 2", "content": "Content 2", "category": "coding"},
    )
    test_client.post(
        "/api/prompts/",
        json={"title": "Stats Test 3", "content": "Content 3", "category": "debugging"},
    )

    # Get stats
    response = test_client.get("/api/prompts/stats")
    assert response.status_code == 200
    stats = response.json()
    assert "total_prompts" in stats
    assert "prompts_by_category" in stats
    assert "total_favorites" in stats
    assert "total_tags" in stats
    assert stats["total_prompts"] >= 3
    assert stats["total_favorites"] >= 1


@pytest.mark.asyncio
async def test_render_prompt_with_variables(test_client):
    """Test rendering a prompt with variables."""
    # Create a prompt with variables
    prompt_data = {
        "title": "Render Test",
        "content": "Hello {{name}}, your task is: {{task}}",
        "category": "coding",
        "variables": [
            {"name": "name", "description": "User name", "required": True},
            {"name": "task", "description": "Task description", "required": True},
        ],
    }
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]

    # Render the prompt with variables
    render_data = {
        "prompt_id": prompt_id,
        "variables": {"name": "Alice", "task": "Write a Python function"},
    }
    response = test_client.post("/api/prompts/render", json=render_data)
    assert response.status_code == 200
    result = response.json()
    assert "rendered" in result
    assert "Alice" in result["rendered"]
    assert "Write a Python function" in result["rendered"]


@pytest.mark.asyncio
async def test_track_prompt_usage(test_client):
    """Test tracking prompt usage."""
    # Create a prompt
    prompt_data = {
        "title": "Usage Test",
        "content": "Test content",
        "category": "coding",
    }
    create_response = test_client.post("/api/prompts/", json=prompt_data)
    prompt_id = create_response.json()["id"]
    initial_usage = create_response.json()["usage_count"]

    # Track usage
    response = test_client.post(f"/api/prompts/{prompt_id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == initial_usage + 1

    # Track usage again
    response = test_client.post(f"/api/prompts/{prompt_id}/use")
    assert response.status_code == 200
    data = response.json()
    assert data["usage_count"] == initial_usage + 2


def test_validate_prompt_helpers_raise():
    """Ensure validation helpers raise HTTPException for invalid input."""
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_title(" ")
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_title(
            "a" * (prompts_routes.MAX_PROMPT_TITLE_LENGTH + 1)
        )
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_content(" ")
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_content(
            "a" * (prompts_routes.MAX_PROMPT_CONTENT_LENGTH + 1)
        )
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_tags(
            [str(i) for i in range(prompts_routes.MAX_TAGS_PER_PROMPT + 1)]
        )
    with pytest.raises(HTTPException):
        prompts_routes._validate_prompt_tags(["valid", "bad!"])
    with pytest.raises(HTTPException):
        prompts_routes._validate_variable_name("invalid-name")
    with pytest.raises(HTTPException):
        prompts_routes._validate_variable_name(
            "a" * (prompts_routes.MAX_VARIABLE_NAME_LENGTH + 1)
        )


def test_filter_sort_paginate_helpers():
    """Verify filtering, sorting, and pagination helper behaviour."""
    now = datetime.now()
    prompt1 = PromptTemplate(
        id="p1",
        title="Alpha",
        description="First",
        category=PromptCategory.CODING,
        content="Alpha content",
        variables=[],
        tags=["analysis", "alpha"],
        is_favorite=True,
        usage_count=10,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(hours=1),
    )
    prompt2 = PromptTemplate(
        id="p2",
        title="Beta",
        description="Second",
        category=PromptCategory.DEBUGGING,
        content="Beta content",
        variables=[],
        tags=["debug"],
        is_favorite=False,
        usage_count=3,
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(hours=3),
    )
    prompt3 = PromptTemplate(
        id="p3",
        title="Gamma",
        description="Third",
        category=PromptCategory.CODING,
        content="Gamma content",
        variables=[],
        tags=["analysis", "gamma"],
        is_favorite=False,
        usage_count=20,
        created_at=now,
        updated_at=now,
    )

    prompts = [prompt1, prompt2, prompt3]

    assert prompts_routes._filter_prompts_by_category(
        prompts, PromptCategory.CODING
    ) == [prompt1, prompt3]
    assert prompts_routes._filter_prompts_by_category(prompts, None) == prompts

    assert prompts_routes._filter_prompts_by_favorite(prompts, True) == [prompt1]
    assert prompts_routes._filter_prompts_by_favorite(prompts, None) == prompts

    assert prompts_routes._filter_prompts_by_tags(prompts, ["analysis"]) == [
        prompt1,
        prompt3,
    ]
    assert prompts_routes._filter_prompts_by_tags(prompts, None) == prompts

    query_filtered = prompts_routes._filter_prompts_by_query(prompts, "content")
    assert len(query_filtered) == 3
    assert prompts_routes._filter_prompts_by_query(prompts, "gamma") == [prompt3]

    sorted_usage = prompts_routes._sort_prompts(prompts, "usage")
    assert sorted_usage[0] == prompt3
    sorted_date = prompts_routes._sort_prompts(prompts, "date")
    assert sorted_date[0] == prompt3
    sorted_title = prompts_routes._sort_prompts(prompts, "title")
    assert [p.title for p in sorted_title] == ["Alpha", "Beta", "Gamma"]

    paginated = prompts_routes._paginate_prompt_results(sorted_title, offset=1, limit=1)
    assert paginated == [prompt2]


def test_load_prompt_handles_io_error(workspace_base, monkeypatch):
    """_load_prompt should swallow IO errors and return None."""
    prompts_dir = workspace_base / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompts_dir / "bad.json"
    prompt_path.write_text("{}", encoding="utf-8")

    def fake_open(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("builtins.open", fake_open)
    result = prompts_routes._load_prompt("bad")
    assert result is None


def test_save_prompt_io_error(workspace_base, monkeypatch):
    """_save_prompt should raise HTTP 500 on IO failure."""
    prompt = PromptTemplate(
        id="save-test",
        title="Save",
        description=None,
        category=PromptCategory.CODING,
        content="content",
        variables=[],
        tags=[],
        is_favorite=False,
        usage_count=0,
    )

    def fake_open(*args, **kwargs):
        raise OSError("disk error")

    monkeypatch.setattr("builtins.open", fake_open)
    with pytest.raises(HTTPException) as exc:
        prompts_routes._save_prompt(prompt)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_delete_prompt_file_error(workspace_base, monkeypatch):
    """_delete_prompt_file should raise HTTP 500 when unlink fails."""
    prompts_dir = workspace_base / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompts_dir / "delete.json"
    prompt_path.write_text("{}", encoding="utf-8")

    def fake_unlink(self):
        raise OSError("cannot unlink")

    monkeypatch.setattr(Path, "unlink", fake_unlink, raising=False)
    with pytest.raises(HTTPException) as exc:
        prompts_routes._delete_prompt_file("delete")
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_render_prompt_not_found(test_client):
    response = test_client.post(
        "/api/prompts/render", json={"prompt_id": "missing", "variables": {}}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_track_prompt_usage_not_found(test_client):
    response = test_client.post("/api/prompts/missing/use")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_prompt_not_found(test_client):
    response = test_client.delete("/api/prompts/missing")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_list_prompts_handles_exception(test_client):
    with patch.object(
        prompts_routes, "_load_all_prompts", side_effect=RuntimeError("boom")
    ):
        response = test_client.get("/api/prompts/")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_search_prompts_handles_exception(test_client):
    with patch.object(
        prompts_routes, "_load_all_prompts", side_effect=RuntimeError("boom")
    ):
        response = test_client.post("/api/prompts/search", json={"query": "x"})
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_prompt_stats_handles_exception(test_client):
    with patch.object(
        prompts_routes, "_load_all_prompts", side_effect=RuntimeError("boom")
    ):
        response = test_client.get("/api/prompts/stats")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_export_prompts_filtered(test_client):
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Export Coding",
            "content": "content",
            "category": "coding",
            "is_favorite": True,
        },
    )
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Export Debug",
            "content": "content",
            "category": "debugging",
            "is_favorite": False,
        },
    )

    response = test_client.get(
        "/api/prompts/export", params={"category": "coding", "is_favorite": True}
    )
    assert response.status_code == 200
    export_data = response.json()
    assert len(export_data["prompts"]) == 1
    assert export_data["prompts"][0]["category"] == "coding"


def test_import_prompts_updates_existing(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Import Original", "content": "Content", "category": "coding"},
    )
    prompt_data = create_response.json()
    prompt_data["content"] = "Updated Content"
    collection = {
        "name": "collection",
        "description": "desc",
        "version": "1.0",
        "prompts": [prompt_data],
        "metadata": {},
    }

    import_response = test_client.post("/api/prompts/import", json=collection)
    assert import_response.status_code == 200
    result = import_response.json()
    assert result["updated"] >= 1


def test_import_prompts_creates_new(test_client):
    collection = {
        "name": "collection",
        "description": "desc",
        "version": "1.0",
        "prompts": [
            {
                "id": "new-prompt",
                "title": "New Prompt",
                "content": "Content",
                "category": "coding",
                "variables": [],
                "tags": [],
                "is_favorite": False,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        ],
        "metadata": {},
    }

    response = test_client.post("/api/prompts/import", json=collection)
    assert response.status_code == 200
    result = response.json()
    assert result["imported"] >= 1


@pytest.mark.asyncio
async def test_update_prompt_with_full_payload(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Full Update", "content": "Original", "category": "coding"},
    )
    prompt_id = create_response.json()["id"]
    update_payload = {
        "description": "updated description",
        "category": "debugging",
        "content": "New content",
        "variables": [
            {"name": "var", "description": "desc", "required": False},
        ],
        "tags": ["tagged"],
        "is_favorite": True,
    }

    response = test_client.patch(f"/api/prompts/{prompt_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "updated description"
    assert data["category"] == "debugging"
    assert data["content"] == "New content"
    assert data["variables"][0]["name"] == "var"
    assert data["tags"] == ["tagged"]
    assert data["is_favorite"] is True


def test_validate_single_tag_length():
    with pytest.raises(HTTPException):
        prompts_routes._validate_single_tag("a" * (prompts_routes.MAX_TAG_LENGTH + 1))


def test_filter_prompts_query_none():
    now = datetime.now()
    prompts = [
        PromptTemplate(
            id="p1",
            title="Alpha",
            description=None,
            category=PromptCategory.CODING,
            content="Alpha",
            variables=[],
            tags=["alpha"],
            updated_at=now,
            created_at=now,
            is_favorite=False,
            usage_count=0,
        )
    ]
    assert prompts_routes._filter_prompts_by_query(prompts, None) == prompts


def test_load_all_prompts_skips_invalid_files(workspace_base):
    prompts_dir = workspace_base / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    (prompts_dir / "bad.json").write_text("{invalid}", encoding="utf-8")
    valid_prompt = PromptTemplate(
        id="good",
        title="Good",
        description=None,
        category=PromptCategory.CODING,
        content="Content",
        variables=[],
        tags=[],
        is_favorite=False,
        usage_count=0,
    )
    (prompts_dir / "good.json").write_text(
        valid_prompt.model_dump_json(), encoding="utf-8"
    )

    prompts = prompts_routes._load_all_prompts()
    assert len(prompts) == 1
    assert prompts[0].id == "good"


def test_list_prompts_applies_filters(test_client):
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Coding Prompt",
            "content": "c",
            "category": "coding",
            "is_favorite": False,
        },
    )
    test_client.post(
        "/api/prompts/",
        json={
            "title": "Debug Prompt",
            "content": "d",
            "category": "debugging",
            "is_favorite": True,
        },
    )

    response = test_client.get(
        "/api/prompts/",
        params={"category": "debugging", "is_favorite": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "debugging"
    assert data[0]["is_favorite"] is True


def test_create_prompt_handles_save_error(test_client):
    prompt_data = {"title": "Fail Create", "content": "Body", "category": "coding"}
    with patch.object(prompts_routes, "_save_prompt", side_effect=Exception("boom")):
        response = test_client.post("/api/prompts/", json=prompt_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_export_prompts_handles_exception(test_client):
    with patch.object(
        prompts_routes, "_load_all_prompts", side_effect=Exception("boom")
    ):
        response = test_client.get("/api/prompts/export")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_import_prompts_handles_exception(test_client):
    collection = {
        "name": "collection",
        "description": "desc",
        "version": "1.0",
        "prompts": [
            {
                "id": "err",
                "title": "Err",
                "content": "Content",
                "category": "coding",
                "variables": [],
                "tags": [],
                "is_favorite": False,
                "usage_count": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        ],
        "metadata": {},
    }

    with patch.object(prompts_routes, "_save_prompt", side_effect=Exception("boom")):
        response = test_client.post("/api/prompts/import", json=collection)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_render_prompt_internal_error(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Render Err", "content": "{{var}}", "category": "coding"},
    )
    prompt_id = create_response.json()["id"]
    with patch.object(PromptTemplate, "render", side_effect=Exception("boom")):
        response = test_client.post(
            "/api/prompts/render",
            json={"prompt_id": prompt_id, "variables": {"var": "value"}},
        )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_track_prompt_usage_internal_error(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Track Err", "content": "content", "category": "coding"},
    )
    prompt_id = create_response.json()["id"]
    with patch.object(prompts_routes, "_save_prompt", side_effect=Exception("boom")):
        response = test_client.post(f"/api/prompts/{prompt_id}/use")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_prompt_internal_error(test_client):
    with patch.object(prompts_routes, "_load_prompt", side_effect=Exception("boom")):
        response = test_client.get("/api/prompts/problem")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_update_prompt_not_found(test_client):
    with patch.object(prompts_routes, "_load_prompt", return_value=None):
        response = test_client.patch("/api/prompts/missing", json={"title": "new"})
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_prompt_handles_exception(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Update Err", "content": "content", "category": "coding"},
    )
    prompt_id = create_response.json()["id"]
    with patch.object(prompts_routes, "_save_prompt", side_effect=Exception("boom")):
        response = test_client.patch(f"/api/prompts/{prompt_id}", json={"title": "new"})
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_delete_prompt_handles_exception(test_client):
    create_response = test_client.post(
        "/api/prompts/",
        json={"title": "Delete Err", "content": "content", "category": "coding"},
    )
    prompt_id = create_response.json()["id"]
    with patch.object(
        prompts_routes, "_delete_prompt_file", side_effect=Exception("boom")
    ):
        response = test_client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
