"""Dashboard API endpoints.

Provides quick stats, recent conversations, and activity feed for the dashboard page.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation_store
from forge.server.utils.responses import success, error
from forge.server.shared import file_store

if TYPE_CHECKING:
    from forge.storage.conversation.conversation_store import ConversationStore
else:
    ConversationStore = Any

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class QuickStats(BaseModel):
    """Quick statistics for dashboard."""

    total_conversations: int = 0
    active_conversations: int = 0
    total_cost: float = 0.0
    success_rate: float = 0.0


class RecentConversation(BaseModel):
    """Recent conversation summary."""

    id: str
    title: str | None = None
    status: str
    created_at: str
    updated_at: str
    cost: float = 0.0
    preview: str | None = None


class ActivityItem(BaseModel):
    """Activity feed item."""

    id: str
    type: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardStats(BaseModel):
    """Complete dashboard statistics."""

    quick_stats: QuickStats
    recent_conversations: list[RecentConversation] = Field(default_factory=list)
    activity_feed: list[ActivityItem] = Field(default_factory=list)


async def _get_quick_stats(
    conversation_store: ConversationStore | None,
    user_id: str,
) -> QuickStats:
    """Calculate quick statistics for dashboard.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier

    Returns:
        QuickStats object
    """
    if not conversation_store:
        return QuickStats()

    try:
        # Get all conversations
        result_set = await conversation_store.search(page_id=None, limit=1000)
        conversations = result_set.results

        total_conversations = len(conversations)

        # Note: ConversationMetadata doesn't have a status field
        # Active conversations cannot be determined from metadata alone
        active_conversations = 0

        # Calculate total cost from conversation stats
        total_cost = 0.0
        successful_conversations = 0

        for conv in conversations:
            # Try to load conversation stats
            try:
                from forge.storage.locations import get_conversation_stats_filename

                stats_filename = get_conversation_stats_filename(conv.id)
                stats_data = file_store.read(stats_filename)

                if stats_data:
                    import base64
                    import json

                    try:
                        decoded = base64.b64decode(stats_data).decode("utf-8")
                        stats = json.loads(decoded)
                        cost = stats.get("accumulated_cost", 0.0)
                        if isinstance(cost, (int, float)):
                            total_cost += cost

                        # Note: ConversationMetadata doesn't have a status field
                        # Consider all conversations with stats as successful for now
                        successful_conversations += 1
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        pass
            except Exception:
                # Skip if stats can't be loaded
                pass

        # Calculate success rate
        success_rate = (
            successful_conversations / total_conversations
            if total_conversations > 0
            else 0.0
        )

        return QuickStats(
            total_conversations=total_conversations,
            active_conversations=active_conversations,
            total_cost=round(total_cost, 2),
            success_rate=round(success_rate, 2),
        )

    except Exception as e:
        logger.error(f"Error calculating quick stats: {e}", exc_info=True)
        return QuickStats()


async def _get_recent_conversations(
    conversation_store: ConversationStore | None,
    user_id: str,
    limit: int = 5,
) -> list[RecentConversation]:
    """Get recent conversations for dashboard.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier
        limit: Maximum number of conversations to return

    Returns:
        List of recent conversations
    """
    if not conversation_store:
        return []

    try:
        result_set = await conversation_store.search(page_id=None, limit=limit)
        conversations = result_set.results

        # Sort by last_updated_at descending
        conversations.sort(
            key=lambda c: c.last_updated_at if c.last_updated_at else datetime.min,
            reverse=True,
        )

        recent = []
        for conv in conversations[:limit]:
            cost = _get_conversation_cost(conv.id)
            recent.append(
                RecentConversation(
                    id=conv.id,
                    title=conv.title,
                    status="unknown",  # ConversationMetadata doesn't have a status field
                    created_at=conv.created_at.isoformat() if conv.created_at else datetime.now().isoformat(),
                    updated_at=conv.last_updated_at.isoformat() if conv.last_updated_at else datetime.now().isoformat(),
                    cost=round(cost, 2),
                    preview=None,  # Could be extracted from first message
                )
            )

        return recent

    except Exception as e:
        logger.error(f"Error getting recent conversations: {e}", exc_info=True)
        return []


def _get_conversation_cost(conversation_id: str) -> float:
    """Get cost from conversation stats if available."""
    try:
        from forge.storage.locations import get_conversation_stats_filename

        stats_filename = get_conversation_stats_filename(conversation_id)
        stats_data = file_store.read(stats_filename)

        if stats_data:
            import base64
            import json

            try:
                decoded = base64.b64decode(stats_data).decode("utf-8")
                stats = json.loads(decoded)
                cost = stats.get("accumulated_cost", 0.0)
                if isinstance(cost, (int, float)):
                    return float(cost)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
    except Exception:
        pass
    return 0.0


async def _get_activity_feed(
    conversation_store: ConversationStore | None,
    user_id: str,
    limit: int = 10,
) -> list[ActivityItem]:
    """Get activity feed for dashboard.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier
        limit: Maximum number of activities to return

    Returns:
        List of activity items
    """
    if not conversation_store:
        return []

    try:
        result_set = await conversation_store.search(page_id=None, limit=100)
        conversations = result_set.results

        activities = []

        # Create activities from recent conversations
        for conv in conversations[:limit]:
            activities.append(
                ActivityItem(
                    id=f"conv_{conv.id}",
                    type="conversation_created",
                    description=f"Created conversation: {conv.title or 'Untitled'}",
                    timestamp=conv.created_at.isoformat() if conv.created_at else datetime.now().isoformat(),
                    metadata={
                        "conversation_id": conv.id,
                    },
                )
            )

            if conv.last_updated_at and conv.last_updated_at != conv.created_at:
                activities.append(
                    ActivityItem(
                        id=f"conv_updated_{conv.id}",
                        type="conversation_updated",
                        description=f"Updated conversation: {conv.title or 'Untitled'}",
                        timestamp=conv.last_updated_at.isoformat(),
                        metadata={
                            "conversation_id": conv.id,
                        },
                    )
                )

        # Sort by timestamp descending
        activities.sort(key=lambda a: a.timestamp, reverse=True)

        return activities[:limit]

    except Exception as e:
        logger.error(f"Error getting activity feed: {e}", exc_info=True)
        return []


@router.get("/stats")
async def get_dashboard_stats(
    request: Request,
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
    recent_limit: int = Query(5, ge=1, le=20, description="Number of recent conversations"),
    activity_limit: int = Query(10, ge=1, le=50, description="Number of activity items"),
) -> JSONResponse:
    """Get dashboard statistics including quick stats, recent conversations, and activity feed.

    Args:
        request: FastAPI request
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)
        recent_limit: Maximum number of recent conversations
        activity_limit: Maximum number of activity items

    Returns:
        Dashboard statistics
    """
    try:
        # Get quick stats
        quick_stats = await _get_quick_stats(conversation_store, user_id)

        # Get recent conversations
        recent_conversations = await _get_recent_conversations(
            conversation_store, user_id, limit=recent_limit
        )

        # Get activity feed
        activity_feed = await _get_activity_feed(
            conversation_store, user_id, limit=activity_limit
        )

        dashboard_stats = DashboardStats(
            quick_stats=quick_stats,
            recent_conversations=recent_conversations,
            activity_feed=activity_feed,
        )

        return success(
            data=dashboard_stats.model_dump(),
            request=request,
        )

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}", exc_info=True)
        return error(
            message="Failed to load dashboard statistics",
            error_code="DASHBOARD_ERROR",
            request=request,
            status_code=500,
        )

