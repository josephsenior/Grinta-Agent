"""FastAPI routes for managing conversations, runtimes, and event streams."""

from __future__ import annotations

from json import JSONDecodeError
from typing import TYPE_CHECKING, Annotated, Any, cast

import os
import sys

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.core.constants import COMPLETION_TIMEOUT
from backend.core.logger import forge_logger as logger
from backend.core.pydantic_compat import model_to_dict
from backend.events.event_store import EventStore
from backend.events.serialization.event import event_to_dict
from backend.server.shared import (
    event_service_adapter,
    get_event_service_adapter,
)
from backend.server.shared import (
    conversation_manager,
    file_store,
    get_conversation_manager,
)
from backend.instruction.types import InputMetadata
from backend.server.user_auth import get_user_id, get_user_settings_store
from backend.server.utils import get_conversation, get_conversation_metadata
from backend.server.utils.responses import error
from backend.server.dependencies import get_dependencies
from backend.core.config.llm_config import LLMConfig
from backend.engines.orchestrator.file_verification_guard import FileVerificationGuard
from backend.controller.error_recovery import ErrorRecoveryStrategy, ErrorType
from backend.controller.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerResult,
)
from backend.events.action import ActionSecurityRisk
from backend.core.cache.async_smart_cache import AsyncSmartCache
from backend.models.cost_tracker import record_llm_cost_from_response
from backend.server.session.errors import SessionInvariantError
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time

if TYPE_CHECKING:
    from backend.events.event_filter import EventFilter
    from backend.memory.memory import Memory
    from backend.runtime.base import Runtime
    from backend.server.session.conversation import ServerConversation
    from backend.storage.data_models.conversation_metadata import ConversationMetadata


app: APIRouter
if "pytest" in sys.modules:

    class NoOpAPIRouter(APIRouter):
        """Router stub used in tests to bypass actual FastAPI route wiring."""

        def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
            """Return endpoint unchanged so tests can call handler directly."""
            return endpoint

    app = cast(APIRouter, NoOpAPIRouter())
else:
    app = APIRouter(
        prefix="/api/conversations/{conversation_id}",
        dependencies=get_dependencies(),
    )


def _get_conversation_manager_instance():
    manager: Any = conversation_manager
    if manager is not None:
        return manager
    try:
        return get_conversation_manager()
    except Exception:
        return None


def _require_conversation_manager():
    manager = _get_conversation_manager_instance()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation manager is not initialized",
        )
    return manager


def _get_event_service_adapter_instance():
    adapter: Any = event_service_adapter
    if adapter is not None:
        return adapter
    try:
        return get_event_service_adapter()
    except Exception:
        return None


def _require_event_service_adapter():
    adapter = _get_event_service_adapter_instance()
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event service adapter is not initialized",
        )
    return adapter


@app.get("/simple-test")
async def simple_test_endpoint() -> JSONResponse:
    """Simple test endpoint without any parameters."""
    return JSONResponse(content={"status": "simple_test_working"})


@app.get("/config")
async def get_remote_runtime_config(
    request: Request,
    conversation_id: str,  # Extracted from path by FastAPI
) -> JSONResponse:
    """Retrieve the runtime configuration.

    Currently, this is the session ID and runtime ID (if available).
    """
    manager = _require_conversation_manager()
    user_id = await get_user_id(request)

    try:
        conversation = await manager.attach_to_conversation(
            conversation_id, user_id or "dev-user"
        )
        if conversation:
            runtime = conversation.runtime
            runtime_id = runtime.runtime_id if hasattr(runtime, "runtime_id") else None
            session_id = runtime.sid if hasattr(runtime, "sid") else None
            await manager.detach_from_conversation(conversation)
            return JSONResponse(
                content={"runtime_id": runtime_id, "session_id": session_id}
            )
        else:
            return error(
                message="Conversation not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="CONVERSATION_NOT_FOUND",
                request=request,
            )
    except Exception as e:
        logger.error("Error getting runtime config: %s", e, exc_info=True)
        return error(
            message=f"Error retrieving runtime configuration: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="RUNTIME_CONFIG_ERROR",
            request=request,
        )


@app.get("/web-hosts")
async def get_hosts(
    request: Request,
    conversation_id: str,  # Extracted from path by FastAPI
) -> JSONResponse:
    """Get the hosts used by the runtime.

    This endpoint allows getting the hosts used by the runtime.

    Args:
        request: The FastAPI request object.
        conversation_id: The conversation ID.

    Returns:
        JSONResponse: A JSON response indicating the success of the operation.

    """
    manager = _require_conversation_manager()
    user_id = await get_user_id(request)

    try:
        conversation = await manager.attach_to_conversation(
            conversation_id, user_id or "dev-user"
        )
        if conversation:
            runtime: Runtime = conversation.runtime
            web_hosts = getattr(runtime, "web_hosts", None) or []
            logger.debug("Runtime type: %s", type(runtime))
            logger.debug("Runtime hosts: %s", web_hosts)
            await manager.detach_from_conversation(conversation)
            return JSONResponse(status_code=200, content={"hosts": web_hosts})
        return error(
            message="Conversation not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="CONVERSATION_NOT_FOUND",
            request=request,
        )
    except Exception as e:
        logger.error("Error getting runtime hosts: %s", e, exc_info=True)
        return error(
            message=f"Error retrieving web hosts: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="WEB_HOSTS_ERROR",
            request=request,
        )


@app.get("/git/changes")
async def get_git_changes(
    conversation_id: str,
) -> JSONResponse:
    """Get git changes in the workspace.

    Returns the list of modified, added, and deleted files by running
    ``git status --porcelain`` inside the conversation workspace.

    Args:
        conversation_id: The conversation ID.

    Returns:
        JSONResponse: A JSON response with the list of changes.
    """
    from backend.server.services.git_service import get_changes

    workspace_dir = os.path.join(
        os.path.expanduser(file_store.root), conversation_id
    )
    result = get_changes(workspace_dir)
    if result.error:
        code = 422 if "not installed" in result.error else (504 if "timed out" in result.error else 500)
        return JSONResponse(status_code=code, content={"error": result.error})
    return JSONResponse(
        status_code=200,
        content={"changes": [{"status": c.status, "path": c.path} for c in result.changes]},
    )


@app.get("/git/diff")
async def get_git_diff(
    conversation_id: str,  # Extracted from path by FastAPI
    path: str = Query(..., min_length=1, description="File path to get diff for"),
) -> JSONResponse:
    """Get git diff for a specific file.

    Runs ``git diff`` for the given file path inside the conversation workspace.

    Args:
        conversation_id: The conversation ID.
        path: The file path to get diff for.

    Returns:
        JSONResponse: A JSON response with the diff content.
    """
    from backend.server.services.git_service import get_diff

    workspace_dir = os.path.join(
        os.path.expanduser(file_store.root), conversation_id
    )
    result = get_diff(workspace_dir, path)
    if result.error:
        code = 404 if "not found" in result.error else (422 if "not installed" in result.error else (504 if "timed out" in result.error else 500))
        return JSONResponse(
            status_code=code,
            content={"error": result.error, "path": path},
        )
    return JSONResponse(
        status_code=200,
        content={"diff": result.diff, "path": result.path},
    )


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
    if limit < 1 or limit > 100:
        raise SessionInvariantError("limit must be between 1 and 100")
    if start_id < 0:
        raise SessionInvariantError("start_id must be non-negative")
    if end_id is not None and end_id < start_id:
        raise SessionInvariantError("end_id must be >= start_id")
    event_store = EventStore(
        sid=conversation_id, file_store=file_store, user_id=user_id
    )
    events = list(
        event_store.search_events(
            start_id=start_id,
            end_id=end_id,
            reverse=reverse,
            filter=filter,
            limit=limit + 1,
        ),
    )
    has_more = len(events) > limit
    if has_more:
        events = events[:limit]
    events_json = [event_to_dict(event) for event in events]
    return {"events": events_json, "has_more": has_more}


@app.post("/events")
async def add_event(
    request: Request, conversation: ServerConversation = Depends(get_conversation)
):
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
        logger.error(
            "Failed to parse JSON body for add_event: %s; raw body: %s", e, raw
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON", "raw_body": raw[:2000]},
        )
    manager = _require_conversation_manager()
    await manager.send_event_to_conversation(conversation.sid, data)
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
    manager = _require_conversation_manager()
    adapter = _require_event_service_adapter()
    try:
        raw = (await request.body()).decode("utf-8", errors="replace")
        if not raw:
            return JSONResponse(status_code=400, content={"error": "Empty body"})
        conversation = await manager.attach_to_conversation(conversation_id, user_id)
        if not conversation and create:
            from backend.server.utils import get_conversation_store
            from backend.storage.data_models.conversation_metadata import (
                ConversationMetadata,
            )

            conversation_store = await get_conversation_store(request)
            if conversation_store is None:
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"error": "Conversation store unavailable"},
                )
            metadata = ConversationMetadata(
                conversation_id=conversation_id,
                selected_repository=None,
                title=f"Conversation {conversation_id}",
            )
            await conversation_store.save_metadata(metadata)
            conversation = await manager.attach_to_conversation(
                conversation_id, user_id
            )
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
            await manager.send_event_to_conversation(conversation.sid, data)
            return JSONResponse({"success": True, "dispatched_as": data})
        except RuntimeError as re:
            if str(re).startswith("no_conversation:"):
                from backend.events.event import EventSource
                from backend.events.serialization.event import event_from_dict

                event_obj = event_from_dict(data.copy())
                adapter.start_session(
                    session_id=conversation_id,
                    user_id=user_id,
                    labels={"source": "conversation_route"},
                )
                event_stream = adapter.get_event_stream(conversation_id)
                event_stream.add_event(event_obj, EventSource.USER)
                return JSONResponse(
                    {
                        "success": True,
                        "dispatched_as": data,
                        "note": "persisted_to_event_store",
                    }
                )
            raise
    except Exception as e:
        logger.exception("Failed to handle raw event body: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


class PlaybookResponse(BaseModel):
    """Response model for playbooks endpoint."""

    name: str
    type: str
    content: str
    triggers: list[str] = []
    inputs: list[InputMetadata] = []
    tools: list[str] = []


@app.get("/playbooks")
async def get_playbooks(
    conversation: ServerConversation = Depends(get_conversation),
) -> JSONResponse:
    """Get all playbooks associated with the conversation.

    This endpoint returns all repository and knowledge playbooks that are loaded for the conversation.

    Args:
        conversation: Server conversation dependency

    Returns:
        JSON response containing the list of playbooks

    """
    try:
        memory = _get_conversation_memory(conversation)
        playbooks = _build_playbook_list(memory)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"playbooks": [model_to_dict(m) for m in playbooks]},
        )
    except HTTPException as exc:
        detail_obj: Any = exc.detail
        if not isinstance(detail_obj, dict):
            detail_obj = {"error": str(detail_obj)}
        detail_data = cast(dict[str, Any], detail_obj)
        logger.warning(
            "Error getting playbooks: %s",
            detail_data.get("error", detail_data),
            exc_info=False,
        )
        return JSONResponse(status_code=exc.status_code, content=detail_data)
    except Exception as e:
        logger.error("Error getting playbooks: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error getting playbooks: {e}"},
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
    manager = _require_conversation_manager()
    agent_session = manager.get_agent_session(conversation.sid)
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


def _build_playbook_list(memory: Memory) -> list[PlaybookResponse]:
    """Build list of playbook responses from memory.

    Args:
        memory: Conversation memory

    Returns:
        List of playbook response objects

    """
    # Build repo playbooks
    repo_playbooks = [
        _build_repo_playbook(name, r_agent)
        for name, r_agent in memory.repo_playbooks.items()
    ]

    # Build knowledge playbooks
    knowledge_playbooks = [
        _build_knowledge_playbook(name, k_agent)
        for name, k_agent in memory.knowledge_playbooks.items()
    ]

    return repo_playbooks + knowledge_playbooks


def _build_repo_playbook(name: str, r_agent) -> PlaybookResponse:
    """Build playbook response for repo playbook.

    Args:
        name: Playbook name
        r_agent: Repository agent object

    Returns:
        PlaybookResponse object

    """
    return PlaybookResponse(
        name=name,
        type="repo",
        content=r_agent.content,
        triggers=[],
        inputs=r_agent.metadata.inputs,
        tools=_extract_mcp_tools(r_agent),
    )


def _build_knowledge_playbook(name: str, k_agent) -> PlaybookResponse:
    """Build playbook response for knowledge playbook.

    Args:
        name: Playbook name
        k_agent: Knowledge agent object

    Returns:
        PlaybookResponse object

    """
    return PlaybookResponse(
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


class CodeCompletionRequest(BaseModel):
    """Request model for code completion."""

    filePath: str
    fileContent: str
    language: str
    position: dict[str, int]  # {line: int, character: int}
    prefix: str
    suffix: str


class CodeCompletionResponse(BaseModel):
    """Response model for code completion."""

    completion: str
    stopReason: str | None = None


# Global circuit breaker instances per conversation (lightweight, no State required)
_completion_circuit_breakers: dict[str, CircuitBreaker] = {}
_completion_error_tracking: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "consecutive_errors": 0,
        "recent_errors": [],
        "recent_success": [],
        "last_error_time": None,
    }
)

# Global cache instance for LLM config (Priority 2: SmartConfigCache)
_completion_config_cache: Optional[AsyncSmartCache] = None

# Per-conversation budget tracking (Priority 2: BudgetGuardService)
_completion_budgets: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "total_cost": 0.0,
        "request_count": 0,
        "max_cost_per_request": 0.01,  # $0.01 per completion
        "max_total_cost": 1.0,  # $1.00 per conversation
        "budget_exceeded": False,
    }
)

# Retry tracking per conversation (Priority 2: RetryService)
_completion_retry_tracking: dict[str, dict[str, Any]] = defaultdict(
    lambda: {
        "retry_count": 0,
        "max_retries": 3,
        "last_retry_time": None,
        "retry_backoff": 1.0,  # Start with 1 second
    }
)


def _get_completion_config_cache() -> AsyncSmartCache:
    """Get or create async smart cache for code completion config."""
    global _completion_config_cache
    if _completion_config_cache is None:
        _completion_config_cache = AsyncSmartCache()
    return _completion_config_cache


def _estimate_completion_cost(
    model: str, prompt_tokens: int, completion_tokens: int
) -> float:
    """Estimate cost for code completion.

    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens

    Returns:
        Estimated cost in USD
    """
    from backend.models.cost_tracker import get_completion_cost

    return get_completion_cost(model, prompt_tokens, completion_tokens)


def _track_completion_cost(
    model: str, prompt_tokens: int, completion_tokens: int, user_key: str
) -> float:
    """Track and record completion cost.

    Args:
        model: Model name
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
        user_key: User identifier for cost tracking

    Returns:
        Actual cost in USD
    """
    cost = _estimate_completion_cost(model, prompt_tokens, completion_tokens)

    # Record cost using cost tracker
    try:
        # Create a mock response dict for cost tracking
        mock_response = {
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }
        record_llm_cost_from_response(user_key, mock_response, model)
    except Exception as e:
        logger.debug(f"Failed to record cost via cost tracker: {e}")

    return cost


def _get_completion_circuit_breaker(conversation_id: str) -> CircuitBreaker:
    """Get or create circuit breaker for code completion per conversation."""
    if conversation_id not in _completion_circuit_breakers:
        config = CircuitBreakerConfig(
            enabled=True,
            max_consecutive_errors=5,
            max_high_risk_actions=10,
            max_stuck_detections=3,
        )
        _completion_circuit_breakers[conversation_id] = CircuitBreaker(config)
    return _completion_circuit_breakers[conversation_id]


def _check_completion_circuit_breaker(
    conversation_id: str,
) -> tuple[bool, Optional[str]]:
    """Check if circuit breaker should trip for code completion.

    Returns:
        Tuple of (should_block, reason_if_blocked)
    """
    tracking = _completion_error_tracking[conversation_id]

    # Check consecutive errors
    if tracking["consecutive_errors"] >= 5:
        return (
            True,
            f"Too many consecutive errors ({tracking['consecutive_errors']}). Circuit breaker tripped.",
        )

    # Check error rate in last 10 requests
    recent = tracking["recent_success"][-10:]
    if len(recent) >= 10:
        error_count = sum(1 for success in recent if not success)
        error_rate = error_count / len(recent)
        if error_rate > 0.5:  # 50% error rate
            return (
                True,
                f"Error rate too high ({error_rate:.1%}). Circuit breaker tripped.",
            )

    return False, None


def _record_completion_error(conversation_id: str, error: Exception) -> None:
    """Record an error for code completion circuit breaker."""
    tracking = _completion_error_tracking[conversation_id]
    tracking["consecutive_errors"] += 1
    tracking["recent_errors"].append(str(error))
    tracking["recent_success"].append(False)
    tracking["last_error_time"] = time.time()

    # Keep only last 20 entries
    if len(tracking["recent_success"]) > 20:
        tracking["recent_success"] = tracking["recent_success"][-20:]
    if len(tracking["recent_errors"]) > 20:
        tracking["recent_errors"] = tracking["recent_errors"][-20:]


def _record_completion_success(conversation_id: str) -> None:
    """Record a successful code completion."""
    tracking = _completion_error_tracking[conversation_id]
    tracking["consecutive_errors"] = 0  # Reset on success
    tracking["recent_success"].append(True)

    # Keep only last 20 entries
    if len(tracking["recent_success"]) > 20:
        tracking["recent_success"] = tracking["recent_success"][-20:]


def _analyze_completion_security(
    completion: str, file_path: str, language: str
) -> tuple[ActionSecurityRisk, Optional[str]]:
    """Analyze code completion for security risks.

    Returns:
        Tuple of (risk_level, warning_message_if_high_risk)
    """
    completion_lower = completion.lower()

    # High-risk patterns
    high_risk_patterns = [
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__\s*\(",
        r"compile\s*\(",
        r"subprocess\s*\.(call|run|Popen)",
        r"os\s*\.(system|popen|exec)",
        r"shell\s*=\s*True",
        r"rm\s+-rf",
        r"del\s+/",
        r"format\s*\(.*%",
        r"\.format\s*\(.*\{.*\}",
    ]

    # Medium-risk patterns
    medium_risk_patterns = [
        r"open\s*\(",
        r"file\s*\(",
        r"pickle\s*\.(load|dumps)",
        r"yaml\s*\.(load|safe_load)",
        r"json\s*\.loads",
        r"requests\s*\.(get|post)",
        r"urllib\s*\.(urlopen|request)",
    ]

    import re

    # Check for high-risk patterns
    for pattern in high_risk_patterns:
        if re.search(pattern, completion_lower):
            return ActionSecurityRisk.HIGH, f"High-risk pattern detected: {pattern}"

    # Check for medium-risk patterns
    for pattern in medium_risk_patterns:
        if re.search(pattern, completion_lower):
            return ActionSecurityRisk.MEDIUM, f"Medium-risk pattern detected: {pattern}"

    return ActionSecurityRisk.LOW, None


def _format_completion_error_message(exc: Exception, error_type: ErrorType) -> str:
    """Format user-friendly error message using ErrorRecoveryStrategy patterns.

    Args:
        exc: The exception that occurred
        error_type: Classified error type

    Returns:
        User-friendly error message
    """
    error_str = str(exc)

    # Use ErrorRecoveryStrategy patterns for user-friendly messages
    if error_type == ErrorType.NETWORK_ERROR:
        return (
            f"⚠️ Network Error\n\n"
            f"Unable to connect to the AI service. This usually means:\n\n"
            f"• The AI service is temporarily unavailable\n"
            f"• There's a network connectivity issue\n"
            f"• The service is experiencing high load\n\n"
            f"**What you can do:**\n"
            f"• Wait a moment and try again\n"
            f"• Check your internet connection\n"
            f"• Try using a different AI model\n\n"
            f"**Technical details:** {error_str[:200]}"
        )
    elif error_type == ErrorType.TIMEOUT_ERROR:
        return (
            f"⏱️ Timeout Error\n\n"
            f"The code completion request took too long to complete.\n\n"
            f"**What you can do:**\n"
            f"• Try a simpler completion request\n"
            f"• Wait a moment and try again\n"
            f"• Check if the AI service is responding\n\n"
            f"**Technical details:** {error_str[:200]}"
        )
    elif error_type == ErrorType.PERMISSION_ERROR:
        return (
            f"🔒 Permission Error\n\n"
            f"Operation failed due to insufficient permissions.\n\n"
            f"**What you can do:**\n"
            f"• Check your API key permissions\n"
            f"• Verify your account has access to this feature\n"
            f"• Contact support if the issue persists\n\n"
            f"**Technical details:** {error_str[:200]}"
        )
    elif error_type == ErrorType.MODULE_NOT_FOUND:
        return (
            f"📦 Module Not Found\n\n"
            f"A required module is missing: {error_str}\n\n"
            f"**What you can do:**\n"
            f"• Check backend dependencies\n"
            f"• Verify all required packages are installed\n"
            f"• Contact support if the issue persists\n\n"
            f"**Technical details:** {error_str[:200]}"
        )
    else:
        # Generic error message
        return (
            f"❌ Error\n\n"
            f"An error occurred while getting code completion: {error_str[:200]}\n\n"
            f"**What you can do:**\n"
            f"• Try again in a moment\n"
            f"• Check the error details below\n"
            f"• Contact support if the issue persists\n\n"
            f"**Error type:** {error_type.value}"
        )


@app.post("/completions", response_model=CodeCompletionResponse)
async def get_code_completion(
    request: Request,
    request_body: CodeCompletionRequest,
    conversation: ServerConversation = Depends(get_conversation),
    user_id: str | None = Depends(get_user_id),
) -> JSONResponse:
    r"""Get code completion suggestions for the current position in a file.

    This endpoint uses the conversation's LLM to generate code completion suggestions
    based on the file content, language, and cursor position. Includes:
    - Exponential backoff retry (via LLM class)
    - Anti-hallucination validation
    - Stuck detection and timeout handling
    - Metrics and monitoring

    Args:
        request: FastAPI request object
        request_body: Code completion request containing file info and context
        conversation: Server conversation dependency
        user_id: User ID from authentication

    Returns:
        JSONResponse: Code completion response with suggested text

    Example:
        POST /api/conversations/{id}/completions
        {
            "filePath": "src/main.py",
            "fileContent": "def hello():\n    print(",
            "language": "python",
            "position": {"line": 1, "character": 12},
            "prefix": "def hello():\n    print(",
            "suffix": ")"
        }
    """
    # Initialize anti-hallucination system
    anti_hallucination = AntiHallucinationSystem()

    # Check circuit breaker before processing
    should_block, block_reason = _check_completion_circuit_breaker(conversation.sid)
    if should_block:
        logger.warning(
            f"Code completion blocked by circuit breaker for conversation {conversation.sid}: {block_reason}"
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": block_reason
                or "Service temporarily unavailable due to high error rate.",
                "completion": "",
                "stopReason": "circuit_breaker_tripped",
            },
        )

    try:
        # Priority 2: SmartConfigCache - Cache user settings
        cache = _get_completion_config_cache()
        user_settings_store = await get_user_settings_store(request)

        if not user_settings_store:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "User settings store not available."},
            )

        # Try to get cached settings
        settings = await cache.get_user_settings(
            user_id or "anonymous", user_settings_store
        )

        if not settings or not settings.llm_model:
            # Cache miss or no settings - load directly
            settings = await user_settings_store.load()
            if not settings or not settings.llm_model:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "LLM settings not configured. Please configure your LLM settings first."
                    },
                )

        # Build LLM config from settings
        llm_config = LLMConfig(
            model=settings.llm_model or "",
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        # Get conversation manager
        manager = _require_conversation_manager()

        # Build prompt for code completion with anti-hallucination guidance
        # Format: context + prefix + [CURSOR] + suffix
        prompt = f"""You are a code completion assistant. Complete the code at the cursor position.

File: {request_body.filePath}
Language: {request_body.language}

Code before cursor:
```{request_body.language}
{request_body.prefix}
```

Code after cursor:
```{request_body.language}
{request_body.suffix}
```

IMPORTANT: 
- Provide ONLY the completion text that should appear at the cursor position
- Do NOT repeat the prefix or include the suffix
- Do NOT claim to have created, edited, or modified files
- Return only the code that completes the current statement or expression
- Be concise and accurate"""

        # Prepare messages for LLM
        messages = [
            {
                "role": "system",
                "content": "You are a helpful code completion assistant. Provide concise, accurate code completions. Never claim to have performed file operations.",
            },
            {"role": "user", "content": prompt},
        ]

        # Priority 2: BudgetGuardService - Get budget tracking
        budget = _completion_budgets[conversation.sid]

        # Priority 2: RetryService - Advanced retry with exponential backoff
        retry_tracking = _completion_retry_tracking[conversation.sid]
        completion_text = None
        last_error: Exception | None = None

        for attempt in range(retry_tracking["max_retries"] + 1):
            try:
                # Priority 2: BudgetGuardService - Check cost before request
                prompt_tokens_est = len(str(messages)) // 4  # Rough estimate
                completion_tokens_est = 100  # Estimate
                estimated_cost = _estimate_completion_cost(
                    model=llm_config.model,
                    prompt_tokens=prompt_tokens_est,
                    completion_tokens=completion_tokens_est,
                )

                if budget["total_cost"] + estimated_cost > budget["max_total_cost"]:
                    logger.warning(
                        f"Code completion blocked: would exceed budget (current: ${budget['total_cost']:.4f}, estimated: ${estimated_cost:.4f})"
                    )
                    budget["budget_exceeded"] = True
                    return JSONResponse(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        content={
                            "error": f"Request would exceed budget. Current: ${budget['total_cost']:.4f}, Estimated: ${estimated_cost:.4f}, Max: ${budget['max_total_cost']:.2f}",
                            "completion": "",
                            "stopReason": "budget_exceeded",
                        },
                    )

                # Request completion from LLM with timeout and stuck detection
                # Use asyncio.wait_for for timeout handling
                completion_text = await asyncio.wait_for(
                    manager.request_llm_completion(
                        sid=conversation.sid,
                        service_id="code_completion",
                        llm_config=llm_config,
                        messages=messages,
                    ),
                    timeout=COMPLETION_TIMEOUT,
                )

                # Success - record cost and break retry loop
                actual_prompt_tokens = len(str(messages)) // 4
                actual_completion_tokens = len(completion_text or "") // 4
                actual_cost = _track_completion_cost(
                    model=llm_config.model,
                    prompt_tokens=actual_prompt_tokens,
                    completion_tokens=actual_completion_tokens,
                    user_key=f"user:{user_id or 'anonymous'}:conversation:{conversation.sid}",
                )
                budget["total_cost"] += actual_cost
                budget["request_count"] += 1
                retry_tracking["retry_count"] = 0  # Reset on success
                retry_tracking["retry_backoff"] = 1.0  # Reset backoff
                break

            except asyncio.TimeoutError as e:
                last_error = e
                if attempt < retry_tracking["max_retries"]:
                    retry_tracking["retry_count"] += 1
                    wait_time = retry_tracking["retry_backoff"] * (
                        2**attempt
                    )  # Exponential backoff
                    logger.warning(
                        f"Code completion timeout (attempt {attempt + 1}/{retry_tracking['max_retries'] + 1}), "
                        f"retrying in {wait_time:.1f}s for conversation {conversation.sid}"
                    )
                    await asyncio.sleep(wait_time)
                    retry_tracking["retry_backoff"] = wait_time
                else:
                    logger.warning(
                        f"Code completion timeout after {retry_tracking['max_retries'] + 1} attempts for conversation {conversation.sid}"
                    )
                    _record_completion_error(conversation.sid, e)
                    return JSONResponse(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        content={
                            "error": f"Code completion request timed out after {retry_tracking['max_retries'] + 1} attempts. The request may be too complex or the LLM service is slow.",
                            "completion": "",
                            "stopReason": "timeout",
                        },
                    )
            except Exception as e:
                last_error = e
                # Check if error is retryable
                error_type = ErrorRecoveryStrategy.classify_error(e)
                is_retryable = error_type in [
                    ErrorType.NETWORK_ERROR,
                    ErrorType.TIMEOUT_ERROR,
                    ErrorType.RUNTIME_CRASH,
                ]

                if is_retryable and attempt < retry_tracking["max_retries"]:
                    retry_tracking["retry_count"] += 1
                    wait_time = retry_tracking["retry_backoff"] * (
                        2**attempt
                    )  # Exponential backoff
                    logger.warning(
                        f"Code completion error (type: {error_type.value}, attempt {attempt + 1}/{retry_tracking['max_retries'] + 1}), "
                        f"retrying in {wait_time:.1f}s for conversation {conversation.sid}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                    retry_tracking["retry_backoff"] = wait_time
                else:
                    # Not retryable or max retries reached
                    raise

        if completion_text is None:
            # All retries exhausted
            if last_error:
                raise last_error
            else:
                raise Exception("Code completion failed: unknown error")

        # Clean up the completion (remove any extra formatting)
        completion = completion_text.strip()

        # Remove markdown code blocks if present
        if completion.startswith("```"):
            lines = completion.split("\n")
            if len(lines) > 1:
                completion = "\n".join(lines[1:])
            if completion.endswith("```"):
                completion = completion[:-3].strip()

        # Security validation (Priority 1: SafetyService pattern)
        security_risk, security_warning = _analyze_completion_security(
            completion, request_body.filePath, request_body.language
        )

        if security_risk == ActionSecurityRisk.HIGH:
            logger.warning(
                f"High security risk detected in code completion: {security_warning}"
            )
            _record_completion_error(
                conversation.sid, Exception(f"High security risk: {security_warning}")
            )
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "completion": "",
                    "stopReason": "security_risk_high",
                    "warning": f"Completion blocked due to security risk: {security_warning}",
                },
            )

        # Anti-hallucination validation
        # Check for file operation claims (hallucination pattern)
        is_valid, error_message = anti_hallucination.validate_response(
            response_text=completion,
            actions=[],  # No actions for code completion
        )

        if not is_valid:
            logger.warning(
                f"Anti-hallucination check failed for code completion: {error_message}"
            )
            _record_completion_error(
                conversation.sid, Exception(f"Hallucination detected: {error_message}")
            )
            # Return empty completion if hallucination detected
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "completion": "",
                    "stopReason": "hallucination_detected",
                    "warning": "Completion validation failed. Please try again.",
                },
            )

        # Additional validation: Check for repetitive or stuck patterns
        # Simple check: if completion is too long or contains suspicious patterns
        if len(completion) > 1000:  # Reasonable limit for code completion
            logger.warning(
                f"Code completion too long ({len(completion)} chars), truncating"
            )
            completion = completion[:1000]

        # Check for suspicious patterns that might indicate stuck/hallucination
        suspicious_patterns = [
            "I have created",
            "I have written",
            "I have edited",
            "I've created",
            "I've written",
            "I've edited",
            "The file has been",
            "File created successfully",
        ]

        completion_lower = completion.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in completion_lower:
                logger.warning(f"Suspicious pattern detected in completion: {pattern}")
                # Remove the suspicious part
                idx = completion_lower.find(pattern.lower())
                if idx > 0:
                    completion = completion[:idx].strip()
                else:
                    completion = ""

        # Record success for circuit breaker
        _record_completion_success(conversation.sid)

        # Log metrics
        logger.info(
            f"Code completion successful for {request_body.filePath} "
            f"(language: {request_body.language}, length: {len(completion)}, "
            f"security_risk: {security_risk.value})"
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "completion": completion,
                "stopReason": "stop" if completion else "empty",
                "securityRisk": security_risk.value
                if security_risk != ActionSecurityRisk.LOW
                else None,
            },
        )

    except HTTPException:
        raise
    except asyncio.TimeoutError:
        # Already handled above, but catch here as well
        raise
    except Exception as e:
        # Priority 1: Error Recovery Strategy - Classify error
        error_type = ErrorRecoveryStrategy.classify_error(e)
        logger.error(
            f"Error getting code completion (type: {error_type.value}): {e}",
            exc_info=True,
        )

        # Record error for circuit breaker
        _record_completion_error(conversation.sid, e)

        # Priority 1: RecoveryService pattern - Format user-friendly error message
        error_message = _format_completion_error_message(e, error_type)

        # Determine appropriate status code based on error type
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if error_type == ErrorType.NETWORK_ERROR:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif error_type == ErrorType.TIMEOUT_ERROR:
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
        elif error_type == ErrorType.PERMISSION_ERROR:
            status_code = status.HTTP_403_FORBIDDEN

        return JSONResponse(
            status_code=status_code,
            content={
                "error": error_message,
                "errorType": error_type.value,
                "completion": "",
                "stopReason": "error",
            },
        )
