import os
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from openhands.core.logger import openhands_logger as logger
from openhands.events.async_event_store_wrapper import AsyncEventStoreWrapper
from openhands.events.event_filter import EventFilter
from openhands.events.serialization import event_to_trajectory
from openhands.server.dependencies import get_dependencies
from openhands.server.session.conversation import ServerConversation
from openhands.server.utils import get_conversation

app = APIRouter(prefix="/api/conversations/{conversation_id}/trajectory", dependencies=get_dependencies())


@app.get("/")
async def get_trajectory(conversation_id: str) -> JSONResponse:
    """Get trajectory.

    This function retrieves the current trajectory and returns it.

    Args:
        conversation_id: Conversation ID from URL path

    Returns:
        JSONResponse: A JSON response containing the trajectory as a list of
        events.
    """
    # Return empty trajectory for now
    logger.info("Returning empty trajectory for %s", conversation_id)
    return JSONResponse(status_code=status.HTTP_200_OK, content={"trajectory": []})
