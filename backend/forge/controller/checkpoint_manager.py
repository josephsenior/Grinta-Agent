"""Checkpoint management for autonomous agent recovery.

Provides automatic checkpointing and rollback capabilities:
- Create checkpoints before risky operations
- Restore from checkpoints on failures
- Manage checkpoint lifecycle and retention
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from forge.controller.state.state import State

from forge.core.logger import forge_logger as logger


@dataclass
class Checkpoint:
    """Represents a checkpoint of agent state."""

    id: str
    created_at: datetime
    iteration: int
    reason: str
    state_snapshot_path: str
    filesystem_snapshot_path: str | None = None
    git_commit_hash: str | None = None
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "iteration": self.iteration,
            "reason": self.reason,
            "state_snapshot_path": self.state_snapshot_path,
            "filesystem_snapshot_path": self.filesystem_snapshot_path,
            "git_commit_hash": self.git_commit_hash,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Checkpoint:
        """Create from dictionary."""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class CheckpointManager:
    """Manages checkpoints for autonomous agent recovery.

    Checkpoints include:
    - Agent state (state.json)
    - Filesystem snapshot (optional)
    - Git commit hash (optional)
    """

    def __init__(
        self,
        checkpoint_dir: str | Path,
        max_checkpoints: int = 20,
        retention_hours: int = 168,  # 7 days
    ) -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_dir: Directory to store checkpoints
            max_checkpoints: Maximum number of checkpoints to keep
            retention_hours: How long to keep checkpoints (hours)

        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.max_checkpoints = max_checkpoints
        self.retention_hours = retention_hours

        self.checkpoints: list[Checkpoint] = []
        self._load_checkpoints()

        logger.info(
            f"CheckpointManager initialized: dir={checkpoint_dir}, "
            f"max={max_checkpoints}, retention={retention_hours}h",
        )

    async def create_checkpoint(
        self,
        state: State,
        reason: str,
        description: str = "",
        include_filesystem: bool = False,
    ) -> str:
        """Create a new checkpoint.

        Args:
            state: Current agent state
            reason: Reason for checkpoint
            description: Optional description
            include_filesystem: Whether to snapshot filesystem

        Returns:
            Checkpoint ID

        """
        checkpoint_id = str(uuid4())[:8]  # Short ID

        logger.info(f"Creating checkpoint {checkpoint_id}: {reason}")

        # Create checkpoint directory
        checkpoint_path = self.checkpoint_dir / checkpoint_id
        checkpoint_path.mkdir(parents=True, exist_ok=True)

        # Save state snapshot
        state_snapshot_path = checkpoint_path / "state.json"
        self._save_state_snapshot(state, state_snapshot_path)

        # Optional: Save filesystem snapshot
        filesystem_snapshot_path = None
        if include_filesystem:
            filesystem_snapshot_path = str(checkpoint_path / "filesystem")
            # In production, you'd use something like rsync or tar
            # For now, we just mark it as available
            logger.debug(
                f"Filesystem snapshot would be created at: {filesystem_snapshot_path}"
            )

        # Create checkpoint record
        checkpoint = Checkpoint(
            id=checkpoint_id,
            created_at=datetime.now(),
            iteration=state.iteration_flag.current_value,
            reason=reason,
            state_snapshot_path=str(state_snapshot_path),
            filesystem_snapshot_path=filesystem_snapshot_path,
            description=description,
        )

        # Add to list and save metadata
        self.checkpoints.append(checkpoint)
        self._save_checkpoint_metadata(checkpoint)

        # Clean up old checkpoints
        await self._cleanup_old_checkpoints()

        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> dict | None:
        """Restore state from a checkpoint.

        Args:
            checkpoint_id: ID of checkpoint to restore

        Returns:
            Restored state dictionary or None if checkpoint not found

        """
        checkpoint = self._find_checkpoint(checkpoint_id)

        if not checkpoint:
            logger.error(f"Checkpoint {checkpoint_id} not found")
            return None

        logger.info(f"Restoring checkpoint {checkpoint_id}: {checkpoint.reason}")

        # Load state snapshot
        try:
            with open(checkpoint.state_snapshot_path, encoding="utf-8") as f:
                state_data = json.load(f)

            logger.info(f"Successfully restored checkpoint {checkpoint_id}")
            return state_data

        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return None

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all available checkpoints.

        Returns:
            List of checkpoints sorted by creation time

        """
        return sorted(self.checkpoints, key=lambda c: c.created_at, reverse=True)

    def _save_state_snapshot(self, state: State, path: Path) -> None:
        """Save state to JSON file.

        Args:
            state: State to save
            path: File path

        """
        try:
            # Convert state to dictionary
            state_dict = {
                "iteration": state.iteration_flag.current_value,
                "agent_state": state.agent_state.value,
                "last_error": state.last_error,
                # Add other relevant state fields
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to save state snapshot: {e}")

    def _save_checkpoint_metadata(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint metadata.

        Args:
            checkpoint: Checkpoint to save

        """
        metadata_path = self.checkpoint_dir / f"{checkpoint.id}_metadata.json"

        try:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save checkpoint metadata: {e}")

    def _load_checkpoints(self) -> None:
        """Load existing checkpoints from disk."""
        try:
            if not self.checkpoint_dir.exists():
                return

            # Load all metadata files
            for metadata_file in self.checkpoint_dir.glob("*_metadata.json"):
                try:
                    with open(metadata_file, encoding="utf-8") as f:
                        data = json.load(f)

                    checkpoint = Checkpoint.from_dict(data)
                    self.checkpoints.append(checkpoint)

                except Exception as e:
                    logger.warning(
                        f"Failed to load checkpoint metadata {metadata_file}: {e}"
                    )

            logger.info(f"Loaded {len(self.checkpoints)} existing checkpoints")

        except Exception as e:
            logger.error(f"Failed to load checkpoints: {e}")

    def _find_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Find checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint or None

        """
        return next((c for c in self.checkpoints if c.id == checkpoint_id), None)

    async def _cleanup_old_checkpoints(self) -> None:
        """Clean up old checkpoints based on retention policy."""
        now = datetime.now()
        retention_delta = timedelta(hours=self.retention_hours)

        # Remove expired checkpoints
        expired = [c for c in self.checkpoints if now - c.created_at > retention_delta]

        for checkpoint in expired:
            await self._delete_checkpoint(checkpoint)

        # Remove excess checkpoints (keep only max_checkpoints most recent)
        if len(self.checkpoints) > self.max_checkpoints:
            sorted_checkpoints = sorted(
                self.checkpoints, key=lambda c: c.created_at, reverse=True
            )
            to_delete = sorted_checkpoints[self.max_checkpoints :]

            for checkpoint in to_delete:
                await self._delete_checkpoint(checkpoint)

    async def _delete_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Delete a checkpoint and its files.

        Args:
            checkpoint: Checkpoint to delete

        """
        try:
            # Remove checkpoint directory
            checkpoint_path = self.checkpoint_dir / checkpoint.id
            if checkpoint_path.exists():
                shutil.rmtree(checkpoint_path)

            # Remove metadata file
            metadata_path = self.checkpoint_dir / f"{checkpoint.id}_metadata.json"
            if metadata_path.exists():
                metadata_path.unlink()

            # Remove from list
            self.checkpoints = [c for c in self.checkpoints if c.id != checkpoint.id]

            logger.debug(f"Deleted checkpoint {checkpoint.id}")

        except Exception as e:
            logger.error(f"Failed to delete checkpoint {checkpoint.id}: {e}")
