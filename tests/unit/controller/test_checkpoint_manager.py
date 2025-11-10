from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json
import shutil

import pytest

from forge.controller.checkpoint_manager import CheckpointManager
from forge.core.schema import AgentState


class _DummyFlag:
    def __init__(self, current_value: int) -> None:
        self.current_value = current_value


class _DummyState:
    def __init__(self, iteration: int, agent_state: AgentState, last_error: str = "") -> None:
        self.iteration_flag = _DummyFlag(iteration)
        self.agent_state = agent_state
        self.last_error = last_error


@pytest.mark.asyncio
async def test_create_and_restore_checkpoint(tmp_path):
    manager = CheckpointManager(tmp_path, max_checkpoints=3, retention_hours=24)
    state = _DummyState(iteration=7, agent_state=AgentState.RUNNING, last_error="boom")

    checkpoint_id = await manager.create_checkpoint(
        state,
        reason="pre-run snapshot",
        description="initial state",
        include_filesystem=True,
    )

    snapshot_path = tmp_path / checkpoint_id / "state.json"
    assert snapshot_path.exists()
    with snapshot_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    assert data["iteration"] == 7
    assert data["agent_state"] == AgentState.RUNNING.value
    assert data["last_error"] == "boom"

    restored = await manager.restore_checkpoint(checkpoint_id)
    assert restored is not None
    assert restored["iteration"] == 7

    # Metadata is persisted and discoverable on a fresh manager instance
    reloaded = CheckpointManager(tmp_path)
    listed = reloaded.list_checkpoints()
    assert listed
    assert listed[0].description == "initial state"


@pytest.mark.asyncio
async def test_restore_checkpoint_missing_returns_none(tmp_path):
    manager = CheckpointManager(tmp_path)
    assert await manager.restore_checkpoint("missing-id") is None


@pytest.mark.asyncio
async def test_restore_checkpoint_handles_read_error(tmp_path):
    manager = CheckpointManager(tmp_path)
    state = _DummyState(3, AgentState.RUNNING)
    checkpoint_id = await manager.create_checkpoint(state, reason="with-state")

    # Remove the underlying state file to trigger the exception branch.
    snapshot_path = tmp_path / checkpoint_id / "state.json"
    snapshot_path.unlink()
    assert await manager.restore_checkpoint(checkpoint_id) is None


@pytest.mark.asyncio
async def test_save_snapshot_and_metadata_error_handling(monkeypatch, tmp_path):
    manager = CheckpointManager(tmp_path)
    state = _DummyState(1, AgentState.RUNNING)

    original_dump = json.dump

    def failing_dump(obj, fp, *args, **kwargs):
        if fp.name.endswith("state.json"):
            raise TypeError("cannot serialize")
        return original_dump(obj, fp, *args, **kwargs)

    monkeypatch.setattr("json.dump", failing_dump)

    original_open = open

    def failing_open(path, *args, **kwargs):
        if str(path).endswith("_metadata.json"):
            raise OSError("cannot write metadata")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", failing_open)

    await manager.create_checkpoint(state, reason="error paths")


def test_load_checkpoints_with_invalid_metadata(tmp_path, monkeypatch):
    metadata_file = tmp_path / "bad_metadata.json"
    metadata_file.write_text("{not json")

    manager = CheckpointManager(tmp_path)
    assert manager.checkpoints == []


def test_load_checkpoints_handles_glob_errors(tmp_path, monkeypatch):
    def failing_glob(self, pattern):
        raise OSError("fail glob")

    monkeypatch.setattr(Path, "glob", failing_glob)
    manager = CheckpointManager(tmp_path)
    assert manager.checkpoints == []


@pytest.mark.asyncio
async def test_cleanup_removes_expired_checkpoints(tmp_path):
    manager = CheckpointManager(tmp_path, max_checkpoints=5, retention_hours=1)
    recent_state = _DummyState(1, AgentState.RUNNING)

    old_id = await manager.create_checkpoint(recent_state, reason="old")
    new_id = await manager.create_checkpoint(recent_state, reason="newer")

    # Force the first checkpoint to appear expired.
    for checkpoint in manager.checkpoints:
        if checkpoint.id == old_id:
            checkpoint.created_at = datetime.now() - timedelta(hours=5)

    await manager._cleanup_old_checkpoints()
    remaining_ids = {cp.id for cp in manager.checkpoints}
    assert remaining_ids == {new_id}
    assert not (tmp_path / old_id).exists()


@pytest.mark.asyncio
async def test_cleanup_respects_max_checkpoints(tmp_path):
    manager = CheckpointManager(tmp_path, max_checkpoints=1, retention_hours=100)
    state = _DummyState(0, AgentState.RUNNING)

    first_id = await manager.create_checkpoint(state, reason="first")
    second_id = await manager.create_checkpoint(state, reason="second")

    remaining_ids = {cp.id for cp in manager.checkpoints}
    assert remaining_ids == {second_id}
    assert not (tmp_path / first_id).exists()


@pytest.mark.asyncio
async def test_delete_checkpoint_error_is_handled(monkeypatch, tmp_path):
    manager = CheckpointManager(tmp_path)
    state = _DummyState(0, AgentState.RUNNING)
    checkpoint_id = await manager.create_checkpoint(state, reason="to-delete")
    checkpoint = manager._find_checkpoint(checkpoint_id)
    assert checkpoint is not None

    def failing_rmtree(path):
        raise OSError("cannot delete")

    monkeypatch.setattr(shutil, "rmtree", failing_rmtree)
    await manager._delete_checkpoint(checkpoint)

