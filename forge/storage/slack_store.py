"""Storage operations for Slack integration data."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from forge.core.logger import forge_logger as logger
from forge.storage.data_models.slack_integration import (
    SlackConversationLink,
    SlackOAuthState,
    SlackUserLink,
    SlackWorkspace,
)

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig


class SlackStore:
    """Store for Slack integration data."""

    def __init__(self, config: ForgeConfig) -> None:
        """Initialize Slack store.

        Args:
            config: Application configuration

        """
        self.config = config
        self.storage_path = Path(config.workspace_base or ".") / ".Forge" / "slack"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.workspaces_file = self.storage_path / "workspaces.json"
        self.user_links_file = self.storage_path / "user_links.json"
        self.conversation_links_file = self.storage_path / "conversation_links.json"
        self.oauth_states_file = self.storage_path / "oauth_states.json"

    def _read_json_file(self, file_path: Path) -> dict:
        """Read JSON file safely."""
        if not file_path.exists():
            return {}
        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Failed to read {file_path}, returning empty dict")
            return {}

    def _write_json_file(self, file_path: Path, data: dict) -> None:
        """Write JSON file safely."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to write {file_path}: {e}")
            raise

    # Workspace operations
    def save_workspace(self, workspace: SlackWorkspace) -> None:
        """Save Slack workspace configuration."""
        workspaces = self._read_json_file(self.workspaces_file)
        workspaces[workspace.team_id] = workspace.model_dump(mode="json")
        self._write_json_file(self.workspaces_file, workspaces)
        logger.info(f"Saved workspace {workspace.team_name} ({workspace.team_id})")

    def get_workspace(self, team_id: str) -> SlackWorkspace | None:
        """Get workspace by team ID."""
        workspaces = self._read_json_file(self.workspaces_file)
        workspace_data = workspaces.get(team_id)
        return SlackWorkspace(**workspace_data) if workspace_data else None

    def list_workspaces(self) -> list[SlackWorkspace]:
        """List all registered workspaces."""
        workspaces = self._read_json_file(self.workspaces_file)
        return [SlackWorkspace(**data) for data in workspaces.values()]

    def delete_workspace(self, team_id: str) -> bool:
        """Delete workspace configuration."""
        workspaces = self._read_json_file(self.workspaces_file)
        if team_id in workspaces:
            del workspaces[team_id]
            self._write_json_file(self.workspaces_file, workspaces)
            logger.info(f"Deleted workspace {team_id}")
            return True
        return False

    # User link operations
    def save_user_link(self, user_link: SlackUserLink) -> None:
        """Save Slack user to Forge user link."""
        user_links = self._read_json_file(self.user_links_file)
        key = f"{user_link.slack_workspace_id}:{user_link.slack_user_id}"
        user_links[key] = user_link.model_dump(mode="json")
        self._write_json_file(self.user_links_file, user_links)
        logger.info(
            f"Linked Slack user {user_link.slack_user_id} to Forge user {user_link.FORGE_user_id}",
        )

    def get_user_link(
        self,
        workspace_id: str,
        slack_user_id: str,
    ) -> SlackUserLink | None:
        """Get user link."""
        user_links = self._read_json_file(self.user_links_file)
        key = f"{workspace_id}:{slack_user_id}"
        link_data = user_links.get(key)
        return SlackUserLink(**link_data) if link_data else None

    def get_user_links_by_FORGE_user(
        self,
        FORGE_user_id: str,
    ) -> list[SlackUserLink]:
        """Get all Slack links for an Forge user."""
        user_links = self._read_json_file(self.user_links_file)
        return [
            SlackUserLink(**data) for data in user_links.values() if data.get("FORGE_user_id") == FORGE_user_id
        ]

    def delete_user_link(self, workspace_id: str, slack_user_id: str) -> bool:
        """Delete user link."""
        user_links = self._read_json_file(self.user_links_file)
        key = f"{workspace_id}:{slack_user_id}"
        if key in user_links:
            del user_links[key]
            self._write_json_file(self.user_links_file, user_links)
            logger.info(f"Deleted user link for {slack_user_id}")
            return True
        return False

    # Conversation link operations
    def save_conversation_link(self, conv_link: SlackConversationLink) -> None:
        """Save Slack thread to Forge conversation link."""
        conv_links = self._read_json_file(self.conversation_links_file)
        key = f"{conv_link.slack_workspace_id}:{conv_link.slack_channel_id}:{conv_link.slack_thread_ts}"
        conv_links[key] = conv_link.model_dump(mode="json")
        self._write_json_file(self.conversation_links_file, conv_links)
        logger.info(
            f"Linked Slack thread {conv_link.slack_thread_ts} to conversation {conv_link.conversation_id}",
        )

    def get_conversation_link(
        self,
        workspace_id: str,
        channel_id: str,
        thread_ts: str,
    ) -> SlackConversationLink | None:
        """Get conversation link."""
        conv_links = self._read_json_file(self.conversation_links_file)
        key = f"{workspace_id}:{channel_id}:{thread_ts}"
        link_data = conv_links.get(key)
        return SlackConversationLink(**link_data) if link_data else None

    def get_conversation_links_by_conversation_id(
        self,
        conversation_id: str,
    ) -> list[SlackConversationLink]:
        """Get all Slack links for an Forge conversation."""
        conv_links = self._read_json_file(self.conversation_links_file)
        return [
            SlackConversationLink(**data)
            for data in conv_links.values()
            if data.get("conversation_id") == conversation_id
        ]

    def delete_conversation_link(
        self,
        workspace_id: str,
        channel_id: str,
        thread_ts: str,
    ) -> bool:
        """Delete conversation link."""
        conv_links = self._read_json_file(self.conversation_links_file)
        key = f"{workspace_id}:{channel_id}:{thread_ts}"
        if key in conv_links:
            del conv_links[key]
            self._write_json_file(self.conversation_links_file, conv_links)
            logger.info(f"Deleted conversation link for thread {thread_ts}")
            return True
        return False

    # OAuth state operations
    def save_oauth_state(self, oauth_state: SlackOAuthState) -> None:
        """Save OAuth state for verification."""
        oauth_states = self._read_json_file(self.oauth_states_file)
        oauth_states[oauth_state.state] = oauth_state.model_dump(mode="json")
        self._write_json_file(self.oauth_states_file, oauth_states)

    def get_oauth_state(self, state: str) -> SlackOAuthState | None:
        """Get OAuth state."""
        oauth_states = self._read_json_file(self.oauth_states_file)
        state_data = oauth_states.get(state)
        return SlackOAuthState(**state_data) if state_data else None

    def delete_oauth_state(self, state: str) -> bool:
        """Delete OAuth state after use."""
        oauth_states = self._read_json_file(self.oauth_states_file)
        if state in oauth_states:
            del oauth_states[state]
            self._write_json_file(self.oauth_states_file, oauth_states)
            return True
        return False

    def cleanup_expired_oauth_states(self, expiry_minutes: int = 10) -> int:
        """Clean up expired OAuth states."""
        oauth_states = self._read_json_file(self.oauth_states_file)
        now = datetime.utcnow()
        expired_keys = []

        for key, data in oauth_states.items():
            created_at = datetime.fromisoformat(data["created_at"])
            if now - created_at > timedelta(minutes=expiry_minutes):
                expired_keys.append(key)

        for key in expired_keys:
            del oauth_states[key]

        if expired_keys:
            self._write_json_file(self.oauth_states_file, oauth_states)
            logger.info(f"Cleaned up {len(expired_keys)} expired OAuth states")

        return len(expired_keys)

    def generate_oauth_state(
        self,
        user_id: str,
        redirect_url: str | None = None,
    ) -> str:
        """Generate and save a new OAuth state."""
        state = uuid.uuid4().hex
        oauth_state = SlackOAuthState(
            state=state,
            user_id=user_id,
            redirect_url=redirect_url,
        )
        self.save_oauth_state(oauth_state)
        return state
