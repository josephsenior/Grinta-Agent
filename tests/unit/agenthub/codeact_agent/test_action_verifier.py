"""Tests for the action verification utilities that guard against hallucinations."""

from __future__ import annotations

import pytest

from forge.agenthub.codeact_agent.action_verifier import ActionVerifier
from forge.events.action import CmdRunAction, FileEditAction
from forge.events.observation import CmdOutputObservation, ErrorObservation


class StubRuntime:
    def __init__(self, observations):
        self.observations = list(observations)
        self.calls = []

    async def run_action(self, action):
        self.calls.append(action)
        if not self.observations:
            raise RuntimeError("No more observations")
        return self.observations.pop(0)


@pytest.mark.asyncio
async def test_verify_action_disabled() -> None:
    verifier = ActionVerifier(runtime=StubRuntime([]))
    verifier.verification_enabled = False

    success, message, obs = await verifier.verify_action(FileEditAction(path="file.txt"))
    assert success is True
    assert message == "Verification disabled"
    assert obs is None


@pytest.mark.asyncio
async def test_verify_action_non_file_returns_no_verification() -> None:
    verifier = ActionVerifier(runtime=StubRuntime([]))
    success, message, obs = await verifier.verify_action(CmdRunAction(command="echo hi"))
    assert success is True
    assert message == "No verification needed"
    assert obs is None


@pytest.mark.asyncio
async def test_verify_file_edit_successful_verification() -> None:
    runtime = StubRuntime([
        CmdOutputObservation(content="FILE_EXISTS\n", command="verify"),
        CmdOutputObservation(content="5 file.txt\n", command="wc"),
    ])
    verifier = ActionVerifier(runtime=runtime)
    action = FileEditAction(path="/tmp/file.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is True
    assert "Verified" in message
    assert isinstance(obs, CmdOutputObservation)


@pytest.mark.asyncio
async def test_verify_file_edit_missing_file(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime([
        CmdOutputObservation(content="FILE_MISSING\n", command="verify"),
    ])
    verifier = ActionVerifier(runtime=runtime)
    action = FileEditAction(path="/tmp/missing.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is False
    assert "NOT created" in message
    assert isinstance(obs, CmdOutputObservation)


@pytest.mark.asyncio
async def test_verify_file_edit_unexpected_observation_type() -> None:
    runtime = StubRuntime([
        ErrorObservation(content="failure"),
    ])
    verifier = ActionVerifier(runtime=runtime)
    action = FileEditAction(path="/tmp/file.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is False
    assert "unexpected observation type" in message
    assert isinstance(obs, ErrorObservation)


@pytest.mark.asyncio
async def test_verify_file_edit_empty_file_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = StubRuntime([
        CmdOutputObservation(content="FILE_EXISTS\n", command="verify"),
        CmdOutputObservation(content="0 file.txt\n", command="wc"),
    ])
    verifier = ActionVerifier(runtime=runtime)
    action = FileEditAction(path="/tmp/file.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is True
    assert "empty" in message
    assert isinstance(obs, CmdOutputObservation)


@pytest.mark.asyncio
async def test_verify_file_edit_skips_content_check_when_unexpected_type() -> None:
    runtime = StubRuntime([
        CmdOutputObservation(content="FILE_EXISTS\n", command="verify"),
        ErrorObservation(content="not a cmd output"),
    ])
    verifier = ActionVerifier(runtime=runtime)
    action = FileEditAction(path="/tmp/file.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is True
    assert "content check skipped" in message
    assert isinstance(obs, ErrorObservation)


@pytest.mark.asyncio
async def test_verify_file_edit_handles_runtime_exception() -> None:
    class ExplodingRuntime(StubRuntime):
        async def run_action(self, action):
            raise RuntimeError("boom")

    verifier = ActionVerifier(runtime=ExplodingRuntime([]))
    action = FileEditAction(path="/tmp/file.txt")

    success, message, obs = await verifier.verify_action(action)
    assert success is False
    assert "Verification error" in message
    assert isinstance(obs, ErrorObservation)


def test_should_verify_only_file_edits() -> None:
    verifier = ActionVerifier(runtime=StubRuntime([]))
    assert verifier.should_verify(FileEditAction(path="file.txt")) is True
    assert verifier.should_verify(CmdRunAction(command="echo hi")) is False

