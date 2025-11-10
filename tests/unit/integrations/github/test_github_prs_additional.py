from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr

from forge.integrations.github.github_service import GitHubService
from forge.integrations.service_types import RequestMethod


class StubGitHubService(GitHubService):
    def __init__(self, responses: list[tuple[dict, dict]], token_value: str = "token") -> None:
        super().__init__(token=SecretStr(token_value))
        self._responses = list(responses)
        self.calls: list[tuple[str, dict | None, RequestMethod]] = []

    async def _make_request(
        self,
        url: str,
        params: dict | None = None,
        method: RequestMethod = RequestMethod.GET,
    ) -> tuple[dict, dict]:
        self.calls.append((url, params, method))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_github_create_pr_with_labels() -> None:
    responses = [
        ({"html_url": "https://github/pr/1", "number": 99}, {}),
        ({}, {}),
    ]
    service = StubGitHubService(responses)
    url = await service.create_pr(
        repo_name="owner/repo",
        source_branch="feature",
        target_branch="main",
        title="Add feature",
        body=None,
        draft=False,
        labels=["ready"],
    )
    assert url.endswith("/1")
    assert len(service.calls) == 2
    first_call = service.calls[0]
    assert first_call[2] == RequestMethod.POST
    assert first_call[1]["body"] == "Merging changes from feature into main"


@pytest.mark.asyncio
async def test_github_get_pr_details_and_state_checks() -> None:
    responses = [
        ({"state": "open"}, {}),
        ({"state": "closed"}, {}),
        ({"merged": True, "closed_at": "2024-01-01T00:00:00Z"}, {}),
        ({}, {}),
    ]
    service = StubGitHubService(responses)
    assert (await service.get_pr_details("owner/repo", 1))["state"] == "open"
    assert await service.is_pr_open("owner/repo", 1) is False  # state closed
    assert await service.is_pr_open("owner/repo", 1) is False  # merged true
    assert await service.is_pr_open("owner/repo", 1) is True  # missing keys defaults to True


@pytest.mark.asyncio
async def test_github_is_pr_open_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GitHubService(token=SecretStr("token"))
    monkeypatch.setattr(service, "get_pr_details", AsyncMock(side_effect=RuntimeError("boom")))
    assert await service.is_pr_open("owner/repo", 123) is True

