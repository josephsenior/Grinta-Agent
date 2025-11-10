from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from forge.integrations.gitlab.gitlab_service import GitLabService
from forge.integrations.service_types import (
    BaseGitService,
    MicroagentParseError,
    MicroagentResponse,
    ProviderType,
    ResourceNotFoundError,
)


class BrokenService(BaseGitService):
    async def _make_request(self, url: str, params: dict | None = None, method=None):  # pragma: no cover - unused
        return ({}, {})

    async def _get_cursorrules_url(self, repository: str) -> str:  # pragma: no cover - unused
        return ""

    async def _get_microagents_directory_url(self, repository: str, microagents_path: str) -> str:  # pragma: no cover
        return ""

    def _get_microagents_directory_params(self, microagents_path: str) -> dict | None:  # pragma: no cover - unused
        return None

    def _is_valid_microagent_file(self, item: dict) -> bool:  # pragma: no cover - unused
        return False

    def _get_file_name_from_item(self, item: dict) -> str:  # pragma: no cover - unused
        return ""

    def _get_file_path_from_item(self, item: dict, microagents_path: str) -> str:  # pragma: no cover - unused
        return ""


def test_base_git_service_provider_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        _ = BrokenService().provider


def _make_service() -> GitLabService:
    return GitLabService(token=SecretStr("token"))


def test_determine_microagents_path_and_response_creation() -> None:
    service = _make_service()
    assert service._determine_microagents_path("owner/repo") == ".Forge/microagents"
    assert service._determine_microagents_path("owner/.Forge") == "microagents"
    response = service._create_microagent_response("agent.cursorrules", "path")
    assert response.name == "agentcursorrules"
    assert response.path == "path"


def test_parse_microagent_content_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()
    dummy_microagent = SimpleNamespace(content="body", metadata=SimpleNamespace(triggers=["on_push"]))
    with patch("forge.integrations.service_types.BaseMicroagent.load", return_value=dummy_microagent):
        result = service._parse_microagent_content("text", "path.md")
        assert result.content == "body"
        assert result.triggers == ["on_push"]
        assert result.git_provider == ProviderType.GITLAB.value
    with patch("forge.integrations.service_types.BaseMicroagent.load", side_effect=RuntimeError("boom")):
        with pytest.raises(MicroagentParseError):
            service._parse_microagent_content("text", "path.md")


@pytest.mark.asyncio
async def test_fetch_and_check_cursorrules(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()
    monkeypatch.setattr(service, "_get_cursorrules_url", AsyncMock(return_value="url"))
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=("content", {})))
    content = await service._fetch_cursorrules_content("repo")
    assert content == "content"

    monkeypatch.setattr(service, "_fetch_cursorrules_content", AsyncMock(return_value="data"))
    response = await service._check_cursorrules_file("repo")
    assert isinstance(response, MicroagentResponse)

    monkeypatch.setattr(service, "_fetch_cursorrules_content", AsyncMock(side_effect=ResourceNotFoundError("missing")))
    assert await service._check_cursorrules_file("repo") is None

    monkeypatch.setattr(service, "_fetch_cursorrules_content", AsyncMock(side_effect=RuntimeError("boom")))
    assert await service._check_cursorrules_file("repo") is None


@pytest.mark.asyncio
async def test_process_microagents_directory_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()
    monkeypatch.setattr(service, "_get_microagents_directory_url", AsyncMock(return_value="dir"))

    values_response = (
        {"values": [{"type": "blob", "name": "agent.md", "path": "dir/agent.md"}]},
        {},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=values_response))
    microagents = await service._process_microagents_directory("repo", ".Forge/microagents")
    assert len(microagents) == 1

    nodes_response = (
        {"nodes": [{"type": "blob", "name": "agent2.md", "path": "dir/agent2.md"}]},
        {},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=nodes_response))
    microagents = await service._process_microagents_directory("repo", ".Forge/microagents")
    assert len(microagents) == 1

    invalid_response = (
        {"values": [{"type": "blob", "name": "invalid.md", "path": "dir/invalid.md"}]},
        {},
    )
    monkeypatch.setattr(service, "_make_request", AsyncMock(return_value=invalid_response))
    monkeypatch.setattr(service, "_get_file_name_from_item", lambda item: (_ for _ in ()).throw(RuntimeError("bad")))
    microagents = await service._process_microagents_directory("repo", ".Forge/microagents")
    assert microagents == []

    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=ResourceNotFoundError("missing")))
    microagents = await service._process_microagents_directory("repo", ".Forge/microagents")
    assert microagents == []

    monkeypatch.setattr(service, "_make_request", AsyncMock(side_effect=RuntimeError("fail")))
    microagents = await service._process_microagents_directory("repo", ".Forge/microagents")
    assert microagents == []


@pytest.mark.asyncio
async def test_get_microagents_combines_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _make_service()
    now = datetime.utcnow()
    cursorrules_resp = MicroagentResponse(name="rules", path=".cursorrules", created_at=now)
    directory_resp = [MicroagentResponse(name="agent", path="agent.md", created_at=now)]
    monkeypatch.setattr(service, "_check_cursorrules_file", AsyncMock(return_value=cursorrules_resp))
    monkeypatch.setattr(service, "_process_microagents_directory", AsyncMock(return_value=directory_resp))
    responses = await service.get_microagents("owner/repo")
    assert [r.name for r in responses] == ["rules", "agent"]


def test_truncate_comment_helper() -> None:
    service = _make_service()
    short = "hello"
    long = "x" * 600
    assert service._truncate_comment(short) == short
    assert service._truncate_comment(long).endswith("...")
