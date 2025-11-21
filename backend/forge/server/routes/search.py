"""Global search API endpoints.

Provides search across conversations, files, snippets, and other resources.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation_store
from forge.server.utils.responses import success, error
from forge.server.routes.manage_conversations import _search_conversations_impl
from forge.storage.data_models.conversation_metadata import ConversationMetadata

if TYPE_CHECKING:
    from forge.storage.conversation.conversation_store import ConversationStore
else:
    ConversationStore = Any

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    """Search result item."""

    id: str
    type: str
    title: str
    description: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response."""

    query: str
    results: dict[str, list[SearchResult]] = Field(default_factory=dict)
    total: int = 0


async def _search_conversations(
    conversation_store: ConversationStore | None,
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[SearchResult]:
    """Search conversations.

    Args:
        conversation_store: Conversation storage
        user_id: User identifier
        query: Search query
        limit: Maximum results

    Returns:
        List of search results
    """
    if not conversation_store:
        return []

    try:
        # Get all conversations and filter by query
        result_set = await conversation_store.search(page_id=None, limit=1000)
        conversations = result_set.results

        query_lower = query.lower()
        results = []

        for conv in conversations:
            if _matches_search_query(conv, query_lower):
                results.append(_create_search_result(conv))
                if len(results) >= limit:
                    break

        return results

    except Exception as e:
        logger.error(f"Error searching conversations: {e}", exc_info=True)
        return []


def _matches_search_query(conv: ConversationMetadata, query_lower: str) -> bool:
    """Check if conversation matches search query."""
    title = (conv.title or "").lower()
    repo = (conv.selected_repository or "").lower()
    return query_lower in title or query_lower in repo


def _create_search_result(conv: ConversationMetadata) -> SearchResult:
    """Create a SearchResult from conversation metadata."""
    return SearchResult(
        id=conv.id,
        type="conversation",
        title=conv.title or "Untitled Conversation",
        description=f"Repository: {conv.selected_repository or 'N/A'}",
        url=f"/conversations/{conv.id}",
        metadata={
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
        },
    )


async def _search_snippets(
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[SearchResult]:
    """Search code snippets.

    Args:
        user_id: User identifier
        query: Search query
        limit: Maximum results

    Returns:
        List of search results
    """
    # TODO: Implement snippet search when snippet storage is available
    # For now, return empty list
    return []


async def _search_files(
    user_id: str,
    query: str,
    limit: int = 10,
) -> list[SearchResult]:
    """Search files.

    Args:
        user_id: User identifier
        query: Search query
        limit: Maximum results

    Returns:
        List of search results
    """
    # TODO: Implement file search when file indexing is available
    # For now, return empty list
    return []


@router.get("")
async def global_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    type: str = Query("all", description="Search type: conversations, snippets, files, all"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results per type"),
    user_id: str = Depends(get_user_id),
    conversation_store: ConversationStore | None = Depends(get_conversation_store),
) -> JSONResponse:
    """Global search across all resources.

    Args:
        request: FastAPI request
        q: Search query
        type: Type of resources to search (conversations, snippets, files, all)
        limit: Maximum results per type
        user_id: User identifier (from dependency)
        conversation_store: Conversation store (from dependency)

    Returns:
        Search results
    """
    try:
        if not q or len(q.strip()) == 0:
            return error(
                message="Search query is required",
                error_code="INVALID_QUERY",
                request=request,
                status_code=400,
            )

        query = q.strip()
        results: dict[str, list[SearchResult]] = {}
        total = 0

        # Search conversations
        if type in ("conversations", "all"):
            conversation_results = await _search_conversations(
                conversation_store, user_id, query, limit=limit
            )
            results["conversations"] = conversation_results
            total += len(conversation_results)

        # Search snippets
        if type in ("snippets", "all"):
            snippet_results = await _search_snippets(user_id, query, limit=limit)
            results["snippets"] = snippet_results
            total += len(snippet_results)

        # Search files
        if type in ("files", "all"):
            file_results = await _search_files(user_id, query, limit=limit)
            results["files"] = file_results
            total += len(file_results)

        search_response = SearchResponse(
            query=query,
            results=results,
            total=total,
        )

        return success(
            data=search_response.model_dump(),
            request=request,
        )

    except Exception as e:
        logger.error(f"Error performing global search: {e}", exc_info=True)
        return error(
            message="Search failed",
            error_code="SEARCH_ERROR",
            request=request,
            status_code=500,
        )

