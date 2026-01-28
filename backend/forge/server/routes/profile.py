"""Profile API endpoints.

Provides user profile information, statistics, and activity timeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator

from forge.core.logger import forge_logger as logger
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation_store
from forge.server.utils.responses import success, error
from forge.server.utils.pagination import PaginatedResponse, parse_pagination_params
from forge.storage.user import get_user_store
from forge.storage.data_models.user import User
from forge.server.shared import file_store

if TYPE_CHECKING:
    from forge.storage.conversation.conversation_store import ConversationStore
else:
    ConversationStore = Any

router = APIRouter(prefix="/api/profile", tags=["profile"])


class UserStatistics(BaseModel):
    """User statistics."""

    total_conversations: int = 0
    active_conversations: int = 0
    total_cost: float = 0.0
    success_rate: float = 0.0
    total_tokens: int = 0
    avg_response_time: float = 0.0


class ActivityTimelineItem(BaseModel):
    """Activity timeline item."""

    id: str = Field(..., min_length=1, description="Activity identifier")
    type: str = Field(..., min_length=1, description="Activity type")
    description: str = Field(..., min_length=1, description="Activity description")
    timestamp: str = Field(..., min_length=1, description="ISO timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("id", "type", "description", "timestamp")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate required string fields are non-empty."""
        from forge.core.security.type_safety import validate_non_empty_string
        return validate_non_empty_string(v, name="field")


class ProfileResponse(BaseModel):
    """Complete profile response."""

    user: dict[str, Any]
    statistics: UserStatistics
    recent_activity: list[ActivityTimelineItem] = Field(default_factory=list)


class UpdateProfileRequest(BaseModel):
    """Update profile request."""

    username: Optional[str] = Field(None, min_length=1, max_length=100, description="Username")
    email: Optional[EmailStr] = Field(None, description="Email address")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Validate username if provided."""
        if v is not None:
            from forge.core.security.type_safety import validate_non_empty_string
            return validate_non_empty_string(v, name="username")
        return v


def _load_conversation_stats(conversation_id: str) -> Optional[dict]:
    """Load and parse conversation statistics."""
    try:
        from forge.storage.locations import get_conversation_stats_filename
        import base64
        import json

        stats_filename = get_conversation_stats_filename(conversation_id)
        stats_data = file_store.read(stats_filename)

        if not stats_data:
            return None

        decoded = base64.b64decode(stats_data).decode("utf-8")
        stats = json.loads(decoded)

        cost = stats.get("accumulated_cost", 0.0)
        cost_value = cost if isinstance(cost, (int, float)) else 0.0

        tokens = stats.get("total_tokens", 0)
        tokens_value = int(tokens) if isinstance(tokens, (int, float)) else 0

        response_times = []
        latencies = stats.get("response_latencies", [])
        for latency in latencies:
            if isinstance(latency, dict):
                rt = latency.get("latency", 0)
                if isinstance(rt, (int, float)) and rt > 0:
                    response_times.append(rt)

        return {
            "cost": cost_value,
            "tokens": tokens_value,
            "response_times": response_times,
        }
    except (json.JSONDecodeError, UnicodeDecodeError, Exception):
        return None


async def _calculate_user_statistics(
    conversation_store: ConversationStore | None,
    user_id: str,
) -> UserStatistics:
    """Calculate user statistics.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier

    Returns:
        UserStatistics object
    """
    if not conversation_store:
        return UserStatistics()

    try:
        result_set = await conversation_store.search(page_id=None, limit=1000)
        conversations = result_set.results

        total_conversations = len(conversations)

        # Note: ConversationMetadata doesn't have a status field
        # Active conversations cannot be determined from metadata alone
        active_conversations = 0

        total_cost = 0.0
        total_tokens = 0
        successful_conversations = 0
        response_times: list[float] = []

        for conv in conversations:
            stats = _load_conversation_stats(conv.id)
            if stats:
                total_cost += stats.get("cost", 0.0)
                total_tokens += stats.get("tokens", 0)
                response_times.extend(stats.get("response_times", []))
                successful_conversations += 1

        success_rate = (
            successful_conversations / total_conversations
            if total_conversations > 0
            else 0.0
        )

        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0.0
        )

        return UserStatistics(
            total_conversations=total_conversations,
            active_conversations=active_conversations,
            total_cost=round(total_cost, 2),
            success_rate=round(success_rate, 2),
            total_tokens=total_tokens,
            avg_response_time=round(avg_response_time, 3),
        )

    except Exception as e:
        logger.error(f"Error calculating user statistics: {e}", exc_info=True)
        return UserStatistics()


async def _get_activity_timeline(
    conversation_store: ConversationStore | None,
    user_id: str,
    limit: int = 20,
) -> list[ActivityTimelineItem]:
    """Get activity timeline for user.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier
        limit: Maximum number of activities

    Returns:
        List of activity timeline items
    """
    if not conversation_store:
        return []

    try:
        result_set = await conversation_store.search(page_id=None, limit=100)
        conversations = result_set.results

        activities = []

        for conv in conversations:
            activities.append(
                ActivityTimelineItem(
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
                    ActivityTimelineItem(
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
        logger.error(f"Error getting activity timeline: {e}", exc_info=True)
        return []


@router.get("", name="get_profile")
async def get_profile(
    request: Request,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
    activity_limit: int = Query(20, ge=1, le=100, description="Number of activity items"),
) -> JSONResponse:
    """Get user profile with statistics and activity timeline.

    Args:
        request: FastAPI request
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)
        activity_limit: Maximum number of activity items

    Returns:
        Profile information with statistics and activity
    """
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    
    try:
        user_store = get_user_store()
        user = await user_store.get_user_by_id(user_id)

        if not user:
            return error(
                message="User not found",
                error_code="USER_NOT_FOUND",
                request=request,
                status_code=404,
            )

        # Get statistics
        statistics = await _calculate_user_statistics(conversation_store, user_id)

        # Get activity timeline
        recent_activity = await _get_activity_timeline(
            conversation_store, user_id, limit=activity_limit
        )

        profile = ProfileResponse(
            user=user.to_dict(),
            statistics=statistics,
            recent_activity=recent_activity,
        )

        return success(
            data=profile.model_dump(),
            request=request,
        )

    except Exception as e:
        logger.error(f"Error getting profile: {e}", exc_info=True)
        return error(
            message="Failed to load profile",
            error_code="PROFILE_ERROR",
            request=request,
            status_code=500,
        )


@router.patch("", name="update_profile")
async def update_profile(
    request: Request,
    update_data: UpdateProfileRequest,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
) -> JSONResponse:
    """Update user profile.

    Args:
        request: FastAPI request
        update_data: Profile update data
        user_id: User identifier (from dependency)

    Returns:
        Updated profile information
    """
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    
    try:
        user_store = get_user_store()
        user = await user_store.get_user_by_id(user_id)

        if not user:
            return error(
                message="User not found",
                error_code="USER_NOT_FOUND",
                request=request,
                status_code=404,
            )

        # Update fields
        if update_data.username is not None:
            # Check username uniqueness
            existing = await user_store.get_user_by_username(update_data.username)
            if existing and existing.id != user_id:
                return error(
                    message="Username already taken",
                    error_code="USERNAME_ALREADY_EXISTS",
                    request=request,
                    status_code=409,
                )
            user.username = update_data.username

        if update_data.email is not None:
            # Check email uniqueness
            existing = await user_store.get_user_by_email(update_data.email)
            if existing and existing.id != user_id:
                return error(
                    message="Email already taken",
                    error_code="EMAIL_ALREADY_EXISTS",
                    request=request,
                    status_code=409,
                )
            user.email = update_data.email.lower()

        updated_user = await user_store.update_user(user)

        logger.info(f"Profile updated: {user_id}")

        return success(
            data={"user": updated_user.to_dict()},
            message="Profile updated successfully",
            request=request,
        )

    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return error(
            message="Failed to update profile",
            error_code="PROFILE_UPDATE_ERROR",
            request=request,
            status_code=500,
        )


@router.get("/stats")
async def get_profile_statistics(
    request: Request,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> JSONResponse:
    """Get user statistics only.

    Args:
        request: FastAPI request
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)

    Returns:
        User statistics
    """
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    
    try:
        statistics = await _calculate_user_statistics(conversation_store, user_id)

        return success(
            data=statistics.model_dump(),
            request=request,
        )

    except Exception as e:
        logger.error(f"Error getting profile statistics: {e}", exc_info=True)
        return error(
            message="Failed to load statistics",
            error_code="STATISTICS_ERROR",
            request=request,
            status_code=500,
        )


@router.get("/activity")
async def get_profile_activity(
    request: Request,
    user_id: Annotated[str | None, Depends(get_user_id)] = None,
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
    limit: int = Query(20, ge=1, le=100, description="Number of activity items"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> JSONResponse:
    """Get user activity timeline.

    Args:
        request: FastAPI request
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)
        limit: Maximum number of activities
        offset: Offset for pagination

    Returns:
        Activity timeline
    """
    if not user_id:
        return error(
            message="Authentication required",
            error_code="AUTHENTICATION_REQUIRED",
            request=request,
            status_code=401,
        )
    
    try:
        activities = await _get_activity_timeline(
            conversation_store, user_id, limit=limit + offset
        )

        # Apply offset
        paginated_activities = activities[offset : offset + limit]

        return success(
            data={
                "activities": [a.model_dump() for a in paginated_activities],
                "total": len(activities),
                "limit": limit,
                "offset": offset,
            },
            request=request,
        )

    except Exception as e:
        logger.error(f"Error getting profile activity: {e}", exc_info=True)
        return error(
            message="Failed to load activity",
            error_code="ACTIVITY_ERROR",
            request=request,
            status_code=500,
        )

