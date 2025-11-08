"""FastAPI routes for managing conversations, runtimes, and event streams."""

from __future__ import annotations

from json import JSONDecodeError
from typing import TYPE_CHECKING, Annotated, cast

import os
import sys

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from forge.core.logger import forge_logger as logger
from forge.core.pydantic_compat import model_to_dict
from forge.events.event_store import EventStore
from forge.events.serialization.event import event_to_dict
from forge.server.shared import conversation_manager, file_store
from forge.microagent.types import InputMetadata
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation, get_conversation_metadata

if TYPE_CHECKING:
    from forge.events.event_filter import EventFilter
    from forge.memory.memory import Memory
    from forge.runtime.base import Runtime
    from forge.server.session.conversation import ServerConversation
    from forge.storage.data_models.conversation_metadata import ConversationMetadata


app: APIRouter
if "pytest" in sys.modules:
    class NoOpAPIRouter(APIRouter):
        """Router stub used in tests to bypass actual FastAPI route wiring."""

        def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
            """Return endpoint unchanged so tests can call handler directly."""
            return endpoint

    app = cast(APIRouter, NoOpAPIRouter())
else:
    app = APIRouter()


@app.get("/simple-test")
async def simple_test_endpoint() -> JSONResponse:
    """Simple test endpoint without any parameters."""
    return JSONResponse(content={"status": "simple_test_working"})


@app.get("/config")
async def get_remote_runtime_config(
    conversation_id: str,
) -> JSONResponse:
    """Retrieve the runtime configuration.

    Currently, this is the session ID and runtime ID (if available).
    """
    # Manually get the conversation without dependency injection
    try:
        from forge.server.shared import conversation_manager
        conversation = await conversation_manager.attach_to_conversation(conversation_id, "dev-user")
        if conversation:
            runtime = conversation.runtime
            runtime_id = runtime.runtime_id if hasattr(runtime, "runtime_id") else None
            session_id = runtime.sid if hasattr(runtime, "sid") else None
            await conversation_manager.detach_from_conversation(conversation)
            return JSONResponse(content={"runtime_id": runtime_id, "session_id": session_id})
        else:
            return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/vscode-url")
async def get_vscode_url(
    conversation_id: str,
) -> JSONResponse:
    """Get the VSCode URL.

    This endpoint allows getting the VSCode URL.

    Args:
        conversation_id: The conversation ID.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.

    """
    try:
        from forge.server.shared import conversation_manager
        conversation = await conversation_manager.attach_to_conversation(conversation_id, "dev-user")
        if conversation:
            runtime: Runtime = conversation.runtime
            vscode_url = getattr(runtime, "vscode_url", None)
            logger.debug("Runtime type: %s", type(runtime))
            logger.debug("Runtime VSCode URL: %s", vscode_url)
            await conversation_manager.detach_from_conversation(conversation)
            return JSONResponse(status_code=status.HTTP_200_OK, content={"vscode_url": vscode_url})
        return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
    except Exception as e:
        logger.error("Error getting VSCode URL: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"vscode_url": None, "error": f"Error getting VSCode URL: {e}"},
        )


@app.get("/web-hosts")
async def get_hosts(
    conversation_id: str,
) -> JSONResponse:
    """Get the hosts used by the runtime.

    This endpoint allows getting the hosts used by the runtime.

    Args:
        conversation_id: The conversation ID.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.

    """
    try:
        from forge.server.shared import conversation_manager
        conversation = await conversation_manager.attach_to_conversation(conversation_id, "dev-user")
        if conversation:
            runtime: Runtime = conversation.runtime
            web_hosts = getattr(runtime, "web_hosts", None)
            logger.debug("Runtime type: %s", type(runtime))
            logger.debug("Runtime hosts: %s", web_hosts)
            await conversation_manager.detach_from_conversation(conversation)
            return JSONResponse(status_code=200, content={"hosts": web_hosts})
        return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
    except Exception as e:
        logger.error("Error getting runtime hosts: %s", e)
        return JSONResponse(status_code=500, content={"hosts": None, "error": f"Error getting runtime hosts: {e}"})


@app.get("/git/changes")
async def get_git_changes(
    conversation_id: str,
) -> JSONResponse:
    """Get git changes in the workspace.

    Returns the list of modified files in the workspace. For beta, this returns
    an empty list as git integration is not fully implemented.

    Args:
        conversation_id: The conversation ID.

    Returns:
        JSONResponse: A JSON response with the list of changes.

    """
    # TODO: Implement git change detection
    # For now, return empty list to prevent 404 errors in UI
    return JSONResponse(status_code=200, content={"changes": []})


@app.get("/git/diff")
async def get_git_diff(
    conversation_id: str,
    path: str = Query(..., description="File path to get diff for"),
) -> JSONResponse:
    """Get git diff for a specific file.

    Returns the git diff for a file. For beta, this returns empty content.

    Args:
        conversation_id: The conversation ID.
        path: The file path to get diff for.

    Returns:
        JSONResponse: A JSON response with the diff content.

    """
    # TODO: Implement git diff retrieval
    # For now, return empty diff to prevent errors
    return JSONResponse(status_code=200, content={"diff": "", "path": path})


@app.get("/events")
async def search_events(
    conversation_id: str,
    start_id: int = 0,
    end_id: int | None = None,
    reverse: bool = False,
    filter: EventFilter | None = None,
    limit: int = 20,
    metadata: ConversationMetadata = Depends(get_conversation_metadata),
    user_id: str | None = Depends(get_user_id),
):
    """Search through the event stream with filtering and pagination.

    Args:
        conversation_id: The conversation ID
        start_id: Starting ID in the event stream. Defaults to 0
        end_id: Ending ID in the event stream
        reverse: Whether to retrieve events in reverse order. Defaults to False.
        filter: Filter for events
        limit: Maximum number of events to return. Must be between 1 and 100. Defaults to 20
        metadata: Conversation metadata (injected by dependency)
        user_id: User ID (injected by dependency)

    Returns:
        dict: Dictionary containing:
            - events: List of matching events
            - has_more: Whether there are more matching events after this batch
    Raises:
        HTTPException: If conversation is not found or access is denied
        ValueError: If limit is less than 1 or greater than 100

    """
    if limit < 0 or limit > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid limit")
    event_store = EventStore(sid=conversation_id, file_store=file_store, user_id=user_id)
    events = list(
        event_store.search_events(start_id=start_id, end_id=end_id, reverse=reverse, filter=filter, limit=limit + 1),
    )
    has_more = len(events) > limit
    if has_more:
        events = events[:limit]
    events_json = [event_to_dict(event) for event in events]
    return {"events": events_json, "has_more": has_more}


@app.post("/events")
async def add_event(request: Request, conversation: ServerConversation = Depends(get_conversation)):
    """Add an event to a conversation.

    Args:
        request: The HTTP request containing event data.
        conversation: The conversation to add the event to.

    Returns:
        JSONResponse: Success response or error details.

    """
    try:
        data = await request.json()
    except JSONDecodeError as e:
        raw = (await request.body()).decode("utf-8", errors="replace")
        logger.error("Failed to parse JSON body for add_event: %s; raw body: %s", e, raw)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON", "raw_body": raw[:2000]},
        )
    await conversation_manager.send_event_to_conversation(conversation.sid, data)
    return JSONResponse({"success": True})


@app.post("/events/raw")
async def add_event_raw(
    request: Request,
    conversation_id: str,
    create: bool | None = False,
    user_id: str | None = Depends(get_user_id),
):
    """Accept raw text/plain POSTs and forward them as a MessageAction.

    This is a developer convenience so tools that have trouble building
    JSON bodies (PowerShell curl, etc.) can still send messages to the
    conversation. The raw body becomes the action args.content.
    """
    try:
        raw = (await request.body()).decode("utf-8", errors="replace")
        if not raw:
            return JSONResponse(status_code=400, content={"error": "Empty body"})
        conversation = await conversation_manager.attach_to_conversation(conversation_id, user_id)
        if not conversation and create:
            from forge.server.utils import get_conversation_store
            from forge.storage.data_models.conversation_metadata import (
                ConversationMetadata,
            )

            conversation_store = await get_conversation_store(request)
            if conversation_store is None:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Conversation store unavailable"},
                )
            metadata = ConversationMetadata(conversation_id=conversation_id, selected_repository=None, title=f"Conversation {conversation_id}")
            await conversation_store.save_metadata(metadata)
            conversation = await conversation_manager.attach_to_conversation(conversation_id, user_id)
        if not conversation:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": f"no_conversation:{conversation_id}",
                    "hint": "Create a conversation first (POST /api/conversations) or call this endpoint with ?create=true to create a minimal conversation metadata before sending raw events.",
                },
            )
        data = {"action": "message", "args": {"content": raw}}
        try:
            await conversation_manager.send_event_to_conversation(conversation.sid, data)
            return JSONResponse({"success": True, "dispatched_as": data})
        except RuntimeError as re:
            if str(re).startswith("no_conversation:"):
                from forge.events.event import EventSource
                from forge.events.serialization.event import event_from_dict
                from forge.events.stream import EventStream

                event_obj = event_from_dict(data.copy())
                event_stream = EventStream(conversation_id, file_store, user_id)
                event_stream.add_event(event_obj, EventSource.USER)
                return JSONResponse({"success": True, "dispatched_as": data, "note": "persisted_to_event_store"})
            raise
    except Exception as e:
        logger.exception("Failed to handle raw event body: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/metasop-debug")
@app.get("/metasop-debug")
async def metasop_debug(request: Request):
    """Development helper: trigger the MetaSOP router for this conversation.

    Accepts optional JSON body {"message": "sop: ...", "conversation_id": "..."}. If absent, defaults to
    "sop: debug run". This schedules the MetaSOP run in the background and
    returns immediately. Intended for local debugging only.

    Args:
        request: The HTTP request containing optional message and conversation_id.

    Returns:
        JSONResponse: Success response or error details.

    """
    try:
        payload = {}
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        message = payload.get("message") if isinstance(payload, dict) else None
        message = message or "sop: debug run"
        conversation_id = payload.get("conversation_id") if isinstance(payload, dict) else None

        if not conversation_id:
            return JSONResponse(status_code=400, content={"error": "conversation_id required in request body"})

        import asyncio

        from forge.metasop.router import run_metasop_for_conversation

        asyncio.create_task(
            run_metasop_for_conversation(
                conversation_id=conversation_id,
                user_id=None,
                raw_message=message,
                repo_root=None,
            ),
        )
        return JSONResponse({"started": True, "message": message, "conversation_id": conversation_id})
    except Exception as e:
        logger.exception("Error starting MetaSOP debug run: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


class MicroagentResponse(BaseModel):
    """Response model for microagents endpoint."""

    name: str
    type: str
    content: str
    triggers: list[str] = []
    inputs: list[InputMetadata] = []
    tools: list[str] = []


@app.get("/microagents")
async def get_microagents(conversation: ServerConversation = Depends(get_conversation)) -> JSONResponse:
    """Get all microagents associated with the conversation.

    This endpoint returns all repository and knowledge microagents that are loaded for the conversation.

    Args:
        conversation: Server conversation dependency

    Returns:
        JSON response containing the list of microagents

    """
    try:
        memory = _get_conversation_memory(conversation)
        microagents = _build_microagent_list(memory)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"microagents": [model_to_dict(m) for m in microagents]},
        )
    except HTTPException as exc:
        detail_obj = exc.detail
        detail_data = detail_obj if isinstance(detail_obj, dict) else {"error": str(detail_obj)}
        logger.warning("Error getting microagents: %s", detail_data.get("error", detail_data), exc_info=False)
        return JSONResponse(status_code=exc.status_code, content=detail_data)
    except Exception as e:
        logger.error("Error getting microagents: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error getting microagents: {e}"},
        )


def _get_conversation_memory(conversation: ServerConversation) -> Memory:
    """Get memory from conversation session.

    Args:
        conversation: Server conversation

    Returns:
        Memory object

    Raises:
        HTTPException: If session or memory not found

    """
    agent_session = conversation_manager.get_agent_session(conversation.sid)
    if not agent_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent session not found for this conversation",
        )

    memory = agent_session.memory
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory is not yet initialized for this conversation",
        )

    return memory


def _build_microagent_list(memory: Memory) -> list[MicroagentResponse]:
    """Build list of microagent responses from memory.

    Args:
        memory: Conversation memory

    Returns:
        List of microagent response objects

    """
    # Build repo microagents
    repo_microagents = [_build_repo_microagent(name, r_agent) for name, r_agent in memory.repo_microagents.items()]

    # Build knowledge microagents
    knowledge_microagents = [
        _build_knowledge_microagent(name, k_agent) for name, k_agent in memory.knowledge_microagents.items()
    ]

    return repo_microagents + knowledge_microagents


def _build_repo_microagent(name: str, r_agent) -> MicroagentResponse:
    """Build microagent response for repo microagent.

    Args:
        name: Microagent name
        r_agent: Repository agent object

    Returns:
        MicroagentResponse object

    """
    return MicroagentResponse(
        name=name,
        type="repo",
        content=r_agent.content,
        triggers=[],
        inputs=r_agent.metadata.inputs,
        tools=_extract_mcp_tools(r_agent),
    )


def _build_knowledge_microagent(name: str, k_agent) -> MicroagentResponse:
    """Build microagent response for knowledge microagent.

    Args:
        name: Microagent name
        k_agent: Knowledge agent object

    Returns:
        MicroagentResponse object

    """
    return MicroagentResponse(
        name=name,
        type="knowledge",
        content=k_agent.content,
        triggers=k_agent.triggers,
        inputs=k_agent.metadata.inputs,
        tools=_extract_mcp_tools(k_agent),
    )


def _extract_mcp_tools(agent) -> list[str]:
    """Extract MCP tool names from agent metadata.

    Args:
        agent: Agent object with metadata

    Returns:
        List of MCP tool server names

    """
    if agent.metadata.mcp_tools:
        return [server.name for server in agent.metadata.mcp_tools.stdio_servers]
    return []
