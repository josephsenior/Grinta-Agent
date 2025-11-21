"""Additional tests for forge.controller.checkpoint_manager."""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from forge.controller.checkpoint_manager import CheckpointManager
from forge.core.schemas import AgentState


def build_state(iteration: int, last_error: str = "") -> SimpleNamespace:
    """Create a lightweight state compatible with CheckpointManager."""
    return SimpleNamespace(
        iteration_flag=SimpleNamespace(current_value=iteration),
        agent_state=AgentState.RUNNING,
        last_error=last_error,
    )


@pytest.mark.asyncio
async def test_checkpoint_manager_create_and_restore(tmp_path):
    """Checkpoints should persist state snapshots and allow restoration."""
    manager = CheckpointManager(tmp_path, max_checkpoints=3, retention_hours=24)
    state = build_state(iteration=7)

    checkpoint_id = await manager.create_checkpoint(
        state=state,
        reason="before risky operation",
        description="Test checkpoint",
        include_filesystem=True,
    )

    assert checkpoint_id
    checkpoints = manager.list_checkpoints()
    assert len(checkpoints) == 1
    assert checkpoints[0].reason == "before risky operation"

    restored = await manager.restore_checkpoint(checkpoint_id)
    assert restored["iteration"] == 7
    assert restored["agent_state"] == AgentState.RUNNING.value


@pytest.mark.asyncio
async def test_checkpoint_manager_cleanup_old_entries(tmp_path):
    """Old checkpoints should be pruned based on retention policy and max count."""
    manager = CheckpointManager(tmp_path, max_checkpoints=1, retention_hours=1)
    state = build_state(iteration=1)

    # Create first checkpoint
    first_id = await manager.create_checkpoint(state, reason="first")

    # Force it to be old
    manager.checkpoints[0].created_at = datetime.now() - timedelta(hours=2)

    # Create second checkpoint which should trigger deletion of the first
    second_id = await manager.create_checkpoint(state, reason="second")

    await manager._cleanup_old_checkpoints()
    remaining_ids = {checkpoint.id for checkpoint in manager.checkpoints}
    assert remaining_ids == {second_id}

    # Attempting to restore deleted checkpoint should return None
    assert await manager.restore_checkpoint(first_id) is None
