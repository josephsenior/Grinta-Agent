"""Tests for missing coverage in service_types.py."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import (
    BaseGitService,
    MicroagentParseError,
    MicroagentResponse,
    ProviderType,
    ResourceNotFoundError,
)


def _make_service() -> GitHubService:
    return GitHubService(token=SecretStr("token"))


class TestBaseGitServiceCheckCursorrulesFile:
    """Test BaseGitService._check_cursorrules_file missing coverage."""

    @pytest.mark.asyncio
    async def test_check_cursorrules_file_runtime_error_returns_none(self):
        """Test _check_cursorrules_file returns None on RuntimeError."""
        service = _make_service()

        with patch.object(
            service,
            "_fetch_cursorrules_content",
            AsyncMock(side_effect=RuntimeError("error"))
        ):
            result = await service._check_cursorrules_file("repo")
            assert result is None


class TestBaseGitServiceProcessMicroagentsDirectory:
    """Test BaseGitService._process_microagents_directory missing coverage."""

    @pytest.mark.asyncio
    async def test_process_microagents_directory_resource_not_found_returns_empty(self):
        """Test _process_microagents_directory returns empty on ResourceNotFoundError."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            with patch.object(
                service,
                "_make_request",
                AsyncMock(side_effect=ResourceNotFoundError("not found"))
            ):
                result = await service._process_microagents_directory("repo", ".Forge/microagents")
                assert result == []

    @pytest.mark.asyncio
    async def test_process_microagents_directory_runtime_error_returns_empty(self):
        """Test _process_microagents_directory returns empty on RuntimeError."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            with patch.object(
                service,
                "_make_request",
                AsyncMock(side_effect=RuntimeError("error"))
            ):
                result = await service._process_microagents_directory("repo", ".Forge/microagents")
                assert result == []

    @pytest.mark.asyncio
    async def test_process_microagents_directory_invalid_file_skipped(self):
        """Test _process_microagents_directory skips invalid files."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            # Response with invalid file (not a blob or wrong extension)
            invalid_response = (
                {"values": [{"type": "tree", "name": "dir"}]},  # Not a blob
                {},
            )
            with patch.object(
                service,
                "_make_request",
                AsyncMock(return_value=invalid_response)
            ):
                result = await service._process_microagents_directory("repo", ".Forge/microagents")
                assert result == []

    @pytest.mark.asyncio
    async def test_process_microagents_directory_get_file_name_error_skipped(self):
        """Test _process_microagents_directory skips files when _get_file_name_from_item errors."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            response = (
                {"values": [{"type": "blob", "name": "agent.md", "path": "dir/agent.md"}]},
                {},
            )
            with patch.object(
                service,
                "_make_request",
                AsyncMock(return_value=response)
            ):
                with patch.object(
                    service,
                    "_get_file_name_from_item",
                    side_effect=RuntimeError("error")
                ):
                    result = await service._process_microagents_directory("repo", ".Forge/microagents")
                    assert result == []


class TestBaseGitServiceCheckCursorrulesFileAdditional:
    """Test BaseGitService._check_cursorrules_file additional coverage."""

    @pytest.mark.asyncio
    async def test_check_cursorrules_file_with_content_returns_microagent(self):
        """Test _check_cursorrules_file returns microagent when content found."""
        service = _make_service()

        with patch.object(
            service,
            "_fetch_cursorrules_content",
            AsyncMock(return_value="cursorrules content")
        ):
            result = await service._check_cursorrules_file("repo")
            assert result is not None
            assert result.name == "cursorrules"  # .cursorrules becomes cursorrules after replace
            assert result.path == ".cursorrules"


class TestBaseGitServiceProcessMicroagentsDirectoryAdditional:
    """Test BaseGitService._process_microagents_directory additional coverage."""

    @pytest.mark.asyncio
    async def test_process_microagents_directory_with_nodes_key(self):
        """Test _process_microagents_directory handles 'nodes' key in response."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            response = (
                {"nodes": [{"type": "blob", "name": "agent.md", "path": "dir/agent.md"}]},
                {},
            )
            with patch.object(
                service,
                "_make_request",
                AsyncMock(return_value=response)
            ):
                with patch.object(service, "_is_valid_microagent_file", return_value=True):
                    with patch.object(service, "_get_file_name_from_item", return_value="agent.md"):
                        with patch.object(service, "_get_file_path_from_item", return_value="dir/agent.md"):
                            result = await service._process_microagents_directory("repo", ".Forge/microagents")
                            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_process_microagents_directory_with_list_response(self):
        """Test _process_microagents_directory handles list response."""
        service = _make_service()

        with patch.object(
            service,
            "_get_microagents_directory_url",
            AsyncMock(return_value="dir")
        ):
            response = (
                [{"type": "blob", "name": "agent.md", "path": "dir/agent.md"}],
                {},
            )
            with patch.object(
                service,
                "_make_request",
                AsyncMock(return_value=response)
            ):
                with patch.object(service, "_is_valid_microagent_file", return_value=True):
                    with patch.object(service, "_get_file_name_from_item", return_value="agent.md"):
                        with patch.object(service, "_get_file_path_from_item", return_value="dir/agent.md"):
                            result = await service._process_microagents_directory("repo", ".Forge/microagents")
                            assert len(result) == 1


class TestBaseGitServiceGetMicroagents:
    """Test BaseGitService.get_microagents missing coverage."""

    @pytest.mark.asyncio
    async def test_get_microagents_with_cursorrules(self):
        """Test get_microagents includes cursorrules microagent."""
        service = _make_service()

        microagent = MicroagentResponse(
            name=".cursorrules",
            path=".cursorrules",
            git_provider=ProviderType.GITHUB.value,
            created_at=datetime.now()
        )

        with patch.object(service, "_check_cursorrules_file", AsyncMock(return_value=microagent)):
            with patch.object(service, "_process_microagents_directory", AsyncMock(return_value=[])):
                result = await service.get_microagents("repo")
                assert len(result) == 1
                assert result[0].name == ".cursorrules"

