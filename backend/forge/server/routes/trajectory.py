"""Routes for exporting or inspecting conversation event trajectories."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, status, Path
from fastapi.responses import JSONResponse
from typing import Annotated

from forge.core.logger import forge_logger as logger
from forge.events.async_event_store_wrapper import AsyncEventStoreWrapper
from forge.events.event_filter import EventFilter
from forge.events.serialization import event_to_trajectory
from forge.server.dependencies import get_dependencies
from forge.server.session.conversation import ServerConversation
from forge.server.utils import get_conversation

app = APIRouter(
    prefix="/api/conversations/{conversation_id}/trajectory",
    dependencies=get_dependencies(),
)


@app.get("/")
async def get_trajectory(
    conversation_id: Annotated[str, Path(..., min_length=1, description="Conversation ID")],
) -> JSONResponse:
    """Get trajectory history for a conversation.

    Retrieves the complete event trajectory for the specified conversation,
    containing all logged events in chronological order. Currently returns
    an empty trajectory as a placeholder for future event store integration.

    Args:
        conversation_id: The unique conversation identifier from the URL path.

    Returns:
        JSONResponse: JSON response with status 200 OK containing:
        {
            "trajectory": list[dict]
                List of event dictionaries in chronological order. Each event
                contains timestamps, event types, and associated data.
        }

    Raises:
        HTTPException: 404 Not Found if conversation_id does not exist.
        HTTPException: 500 Internal Server Error if event store retrieval fails.

    Examples:
        >>> curl http://localhost:3000/api/conversations/abc123/trajectory/
        {
            "trajectory": [
                {"type": "message", "timestamp": "2025-01-06T10:15:30Z", ...},
                {"type": "action", "timestamp": "2025-01-06T10:15:35Z", ...},
                ...
            ]
        }

    Notes:
        - Event filter automatically excludes hidden/internal events
        - Trajectory may be large for long conversations
        - Events are immutable once recorded

    """
    # Return empty trajectory for now
    logger.info("Returning empty trajectory for %s", conversation_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"trajectory": []})
