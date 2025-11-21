"""Activity feed API endpoints.

Provides user activity timeline and feed.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation_store
from forge.server.utils.responses import success, error
from forge.server.utils.pagination import PaginatedResponse, parse_pagination_params
from forge.storage.data_models.conversation_metadata import ConversationMetadata

if TYPE_CHECKING:
    from forge.storage.conversation.conversation_store import ConversationStore
else:
    ConversationStore = Any

router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityItem(BaseModel):
    """Activity item."""

    id: str
    type: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


async def _get_user_activities(
    conversation_store: ConversationStore | None,
    user_id: str,
    activity_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ActivityItem], int]:
    """Get user activities.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier
        activity_type: Filter by activity type (optional)
        limit: Maximum number of activities
        offset: Offset for pagination

    Returns:
        Tuple of (activities list, total count)
    """
    if not conversation_store:
        return [], 0

    try:
        result_set = await conversation_store.search(page_id=None, limit=1000)
        conversations = result_set.results

        activities: list[ActivityItem] = []

        # Create activities from conversations
        for conv in conversations:
            _add_conversation_activities(conv, activities, activity_type)

        # Filter by type if specified
        if activity_type:
            activities = [a for a in activities if a.type == activity_type]

        # Sort by timestamp descending
        activities.sort(key=lambda a: a.timestamp, reverse=True)

        total = len(activities)

        # Apply pagination
        paginated_activities = activities[offset : offset + limit]

        return paginated_activities, total

    except Exception as e:
        logger.error(f"Error getting user activities: {e}", exc_info=True)
        return [], 0


def _add_conversation_activities(
    conv: ConversationMetadata, activities: list[ActivityItem], activity_type: Optional[str]
) -> None:
    """Add conversation activities to the activities list."""
    # Conversation created
    if activity_type is None or activity_type == "conversation_created":
        activities.append(
            ActivityItem(
                id=f"conv_created_{conv.id}",
                type="conversation_created",
                description=f"Created conversation: {conv.title or 'Untitled'}",
                timestamp=conv.created_at.isoformat() if conv.created_at else datetime.now().isoformat(),
                metadata={
                    "conversation_id": conv.id,
                    "repository": conv.selected_repository,
                },
            )
        )

    # Conversation updated
    if (
        conv.last_updated_at
        and conv.last_updated_at != conv.created_at
        and (activity_type is None or activity_type == "conversation_updated")
    ):
        activities.append(
            ActivityItem(
                id=f"conv_updated_{conv.id}",
                type="conversation_updated",
                description=f"Updated conversation: {conv.title or 'Untitled'}",
                timestamp=conv.last_updated_at.isoformat(),
                metadata={
                    "conversation_id": conv.id,
                    "repository": conv.selected_repository,
                },
            )
        )


@router.get("", response_model=None)
async def get_activity_feed(
    request: Request,
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
    type: Optional[str] = Query(None, description="Filter by activity type"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> JSONResponse | PaginatedResponse[dict]:
    """Get activity feed for the current user.

    Args:
        request: FastAPI request
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)
        type: Filter by activity type (optional)
        page: Page number
        limit: Items per page

    Returns:
        Paginated activity feed
    """
    try:
        params = parse_pagination_params(page=page, limit=limit)

        activities, total = await _get_user_activities(
            conversation_store,
            user_id,
            activity_type=type,
            limit=params.limit,
            offset=params.offset,
        )

        paginated = PaginatedResponse.create(
            items=[a.model_dump() for a in activities],
            page=params.page,
            limit=params.limit,
            total=total,
        )
        # PaginatedResponse is a Pydantic model, FastAPI can serialize it directly
        return paginated

    except Exception as e:
        logger.error(f"Error getting activity feed: {e}", exc_info=True)
        return error(
            message="Failed to load activity feed",
            error_code="ACTIVITY_ERROR",
            request=request,
            status_code=500,
        )

