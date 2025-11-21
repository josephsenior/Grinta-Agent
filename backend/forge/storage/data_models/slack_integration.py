"""Data models for Slack integration."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SlackMessageType(str, Enum):
    """Types of Slack messages."""

    APP_MENTION = "app_mention"
    MESSAGE = "message"
    THREAD_REPLY = "thread_reply"


class SlackWorkspace(BaseModel):
    """Slack workspace configuration."""

    id: str = Field(..., description="Workspace ID")
    team_id: str = Field(..., description="Slack team ID")
    team_name: str = Field(..., description="Slack team name")
    bot_token: str = Field(..., description="Bot OAuth token")
    bot_user_id: str = Field(..., description="Bot user ID")
    installed_at: datetime = Field(default_factory=datetime.utcnow)
    installed_by_user_id: str | None = Field(
        None,
        description="Forge user who installed",
    )


class SlackUserLink(BaseModel):
    """Link between Slack user and Forge user."""

    slack_user_id: str = Field(..., description="Slack user ID")
    slack_workspace_id: str = Field(..., description="Slack workspace ID")
    FORGE_user_id: str = Field(..., description="Forge user ID")
    user_token: str | None = Field(None, description="User OAuth token (if needed)")
    linked_at: datetime = Field(default_factory=datetime.utcnow)


class SlackConversationLink(BaseModel):
    """Link between Slack thread and Forge conversation."""

    slack_channel_id: str = Field(..., description="Slack channel ID")
    slack_thread_ts: str = Field(..., description="Slack thread timestamp")
    slack_workspace_id: str = Field(..., description="Slack workspace ID")
    conversation_id: str = Field(..., description="Forge conversation ID")
    repository: str | None = Field(None, description="Repository being worked on")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_slack_user_id: str = Field(
        ...,
        description="Slack user who started conversation",
    )


class SlackIncomingMessage(BaseModel):
    """Incoming Slack message for processing."""

    type: SlackMessageType = Field(..., description="Message type")
    team_id: str = Field(..., description="Slack team ID")
    channel_id: str = Field(..., description="Channel ID")
    user_id: str = Field(..., description="Slack user ID")
    text: str = Field(..., description="Message text")
    ts: str = Field(..., description="Message timestamp")
    thread_ts: str | None = Field(None, description="Thread timestamp (if reply)")
    event_ts: str = Field(..., description="Event timestamp")


class SlackOutgoingMessage(BaseModel):
    """Outgoing Slack message to send."""

    channel: str = Field(..., description="Channel ID")
    text: str = Field(..., description="Message text")
    thread_ts: str | None = Field(None, description="Thread timestamp (for replies)")
    blocks: list[dict] | None = Field(None, description="Slack block kit blocks")


class SlackOAuthState(BaseModel):
    """OAuth state for verification."""

    state: str = Field(..., description="Random state token")
    user_id: str = Field(..., description="Forge user ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    redirect_url: str | None = Field(None, description="URL to redirect after OAuth")
