"""Slack API client wrapper for OpenHands integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from openhands.core.logger import openhands_logger as logger

if TYPE_CHECKING:
    from openhands.storage.data_models.slack_integration import SlackOutgoingMessage

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    logger.warning("slack_sdk not installed. Install with: pip install slack-sdk")


class SlackClient:
    """Wrapper for Slack API operations."""

    def __init__(self, bot_token: str) -> None:
        """Initialize Slack client.

        Args:
            bot_token: Slack bot OAuth token

        Raises:
            ImportError: If slack_sdk is not installed
        """
        if not SLACK_SDK_AVAILABLE:
            msg = "slack_sdk is required for Slack integration. Install with: pip install slack-sdk"
            raise ImportError(
                msg,
            )

        self.bot_token = bot_token
        self.client = WebClient(token=bot_token)

    def post_message(self, message: SlackOutgoingMessage) -> dict[str, Any]:
        """Post a message to Slack.

        Args:
            message: Message to send

        Returns:
            Slack API response

        Raises:
            SlackApiError: If API call fails
        """
        try:
            response = self.client.chat_postMessage(
                channel=message.channel,
                text=message.text,
                thread_ts=message.thread_ts,
                blocks=message.blocks,
            )
            logger.info(f"Posted message to Slack channel {message.channel}")
            return response.data  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to post Slack message: {e.response['error']}")
            raise

    def post_ephemeral_message(
        self,
        channel: str,
        user: str,
        text: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        """Post an ephemeral message (only visible to one user).

        Args:
            channel: Channel ID
            user: User ID to show message to
            text: Message text
            thread_ts: Thread timestamp (optional)

        Returns:
            Slack API response
        """
        try:
            response = self.client.chat_postEphemeral(
                channel=channel,
                user=user,
                text=text,
                thread_ts=thread_ts,
            )
            return response.data  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to post ephemeral message: {e.response['error']}")
            raise

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Update an existing message.

        Args:
            channel: Channel ID
            ts: Message timestamp
            text: New message text
            blocks: New blocks (optional)

        Returns:
            Slack API response
        """
        try:
            response = self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks,
            )
            return response.data  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to update message: {e.response['error']}")
            raise

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information.

        Args:
            user_id: Slack user ID

        Returns:
            User info from Slack API
        """
        try:
            response = self.client.users_info(user=user_id)
            return response.data["user"]  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to get user info: {e.response['error']}")
            raise

    def get_conversation_info(self, channel_id: str) -> dict[str, Any]:
        """Get channel/conversation information.

        Args:
            channel_id: Channel ID

        Returns:
            Channel info from Slack API
        """
        try:
            response = self.client.conversations_info(channel=channel_id)
            return response.data["channel"]  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to get conversation info: {e.response['error']}")
            raise

    def add_reaction(self, channel: str, timestamp: str, emoji: str) -> dict[str, Any]:
        """Add a reaction emoji to a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name (without colons)

        Returns:
            Slack API response
        """
        try:
            response = self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=emoji,
            )
            return response.data  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to add reaction: {e.response['error']}")
            raise

    def remove_reaction(
        self,
        channel: str,
        timestamp: str,
        emoji: str,
    ) -> dict[str, Any]:
        """Remove a reaction emoji from a message.

        Args:
            channel: Channel ID
            timestamp: Message timestamp
            emoji: Emoji name (without colons)

        Returns:
            Slack API response
        """
        try:
            response = self.client.reactions_remove(
                channel=channel,
                timestamp=timestamp,
                name=emoji,
            )
            return response.data  # type: ignore
        except SlackApiError as e:
            logger.error(f"Failed to remove reaction: {e.response['error']}")
            raise

    @staticmethod
    def extract_repo_from_text(text: str) -> str | None:
        """Extract repository name from Slack message text.

        Supports formats like:
        - "in the openhands repo"
        - "in All-Hands-AI/OpenHands"

        Args:
            text: Message text

        Returns:
            Repository name if found, None otherwise
        """
        # Pattern 1: "in the <repo-name> repo"
        match = re.search(r"in\s+the\s+([a-zA-Z0-9_-]+)\s+repo", text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Pattern 2: "in <owner>/<repo>"
        match = re.search(r"in\s+([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def remove_bot_mention(text: str, bot_user_id: str) -> str:
        """Remove bot mention from message text.

        Args:
            text: Message text
            bot_user_id: Bot user ID

        Returns:
            Text with bot mention removed
        """
        # Remove <@U123ABC> style mentions
        mention_pattern = f"<@{bot_user_id}>"
        return text.replace(mention_pattern, "").strip()

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """Format code as Slack code block.

        Args:
            code: Code content
            language: Programming language (optional)

        Returns:
            Formatted Slack code block
        """
        if language:
            return f"```{language}\n{code}\n```"
        return f"```\n{code}\n```"

    @staticmethod
    def create_loading_message(text: str = "Working on it...") -> dict:
        """Create a loading message block.

        Args:
            text: Loading message text

        Returns:
            Slack blocks for loading message
        """
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":hourglass_flowing_sand: {text}",
                    },
                },
            ],
        }

    @staticmethod
    def create_error_message(error: str) -> dict:
        """Create an error message block.

        Args:
            error: Error message

        Returns:
            Slack blocks for error message
        """
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f":x: *Error:* {error}"},
                },
            ],
        }

    @staticmethod
    def create_success_message(text: str, details: str | None = None) -> dict:
        """Create a success message block.

        Args:
            text: Success message
            details: Additional details (optional)

        Returns:
            Slack blocks for success message
        """
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":white_check_mark: {text}"},
            },
        ]

        if details:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": details}},
            )

        return {"blocks": blocks}
