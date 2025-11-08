"""API routes for managing code snippets."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from forge.core.config import AppConfig
from forge.server.shared import config
from forge.storage.data_models.code_snippet import (
    CodeSnippet,
    CreateSnippetRequest,
    SearchSnippetsRequest,
    SnippetCategory,
    SnippetCollection,
    SnippetLanguage,
    SnippetStats,
    UpdateSnippetRequest,
)

app = APIRouter(prefix="/api/snippets")
logger = logging.getLogger(__name__)


class SnippetUsageEvent(BaseModel):
    """Analytics payload for tracking snippet usage."""

    snippet_id: str
    action: str | None = None
    metadata: dict[str, str | int | float | bool | None] | None = None


def _get_snippets_dir() -> Path:
    """Get the directory where snippets are stored."""
    base_path = config.workspace_base or getattr(AppConfig, "workspace_base", None)
    if base_path is None:
        base_path = "."
    else:
        # Keep shared config in sync when tests patch AppConfig.workspace_base
        if config.workspace_base != base_path:
            config.workspace_base = base_path
    workspace_base = Path(base_path)
    snippets_dir = workspace_base / "snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)
    return snippets_dir


def _get_snippet_file_path(snippet_id: str) -> Path:
    """Get the file path for a specific snippet."""
    return _get_snippets_dir() / f"{snippet_id}.json"


def _load_snippet(snippet_id: str) -> CodeSnippet | None:
    """Load a snippet from disk."""
    try:
        snippet_file = _get_snippet_file_path(snippet_id)
        logger.info("Loading snippet %s from %s", snippet_id, snippet_file)
        if not snippet_file.exists():
            logger.info("Snippet file not found for %s", snippet_id)
            return None

        with open(snippet_file, encoding="utf-8") as f:
            data = json.load(f)
            return CodeSnippet(**data)
    except Exception as e:
        logger.exception(f"Error loading snippet {snippet_id}: {e}")
        return None


def _save_snippet(snippet: CodeSnippet) -> None:
    """Save a snippet to disk."""
    try:
        snippet_file = _get_snippet_file_path(snippet.id)
        logger.info("Saving snippet %s to %s", snippet.id, snippet_file)
        with open(snippet_file, "w", encoding="utf-8") as f:
            json.dump(snippet.model_dump(), f, indent=2, default=str)
    except Exception as e:
        logger.exception(f"Error saving snippet {snippet.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save snippet: {e!s}",
        ) from e


def _delete_snippet_file(snippet_id: str) -> None:
    """Delete a snippet file from disk."""
    try:
        snippet_file = _get_snippet_file_path(snippet_id)
        if snippet_file.exists():
            snippet_file.unlink()
    except Exception as e:
        logger.exception(f"Error deleting snippet {snippet_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete snippet: {e!s}",
        ) from e


def _load_all_snippets() -> list[CodeSnippet]:
    """Load all snippets from disk."""
    snippets = []
    snippets_dir = _get_snippets_dir()

    for snippet_file in snippets_dir.glob("*.json"):
        try:
            with open(snippet_file, encoding="utf-8") as f:
                data = json.load(f)
                snippets.append(CodeSnippet(**data))
        except Exception as e:
            logger.exception(f"Error loading snippet from {snippet_file}: {e}")
            continue

    return snippets


def _get_usage_events_path() -> Path:
    """Return the path to the usage events log."""
    return _get_snippets_dir() / "usage_events.json"


def _load_usage_events() -> list[dict[str, Any]]:
    """Load snippet usage analytics events from disk."""
    events_file = _get_usage_events_path()
    if not events_file.exists():
        return []

    try:
        with open(events_file, encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                return [event for event in data if isinstance(event, dict)]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to load snippet usage events: %s", exc)
    return []


def _save_usage_events(events: list[dict[str, Any]]) -> None:
    """Persist snippet usage analytics events."""
    events_file = _get_usage_events_path()
    try:
        with open(events_file, "w", encoding="utf-8") as handle:
            json.dump(events, handle, indent=2)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to save snippet usage events: %s", exc)


@app.get("/")
async def list_snippets(
    language: SnippetLanguage | None = None,
    category: SnippetCategory | None = None,
    is_favorite: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CodeSnippet]:
    """List all code snippets with optional filtering.

    Args:
        language: Filter by programming language
        category: Filter by category
        is_favorite: Filter by favorite status
        limit: Maximum number of snippets to return
        offset: Number of snippets to skip

    Returns:
        List of code snippets

    """
    try:
        snippets = _load_all_snippets()
        snippets = _apply_list_filters(snippets, language, category, is_favorite)
        snippets = _sort_by_update_time(snippets)
        return snippets[offset: offset + limit]

    except Exception as e:
        logger.exception(f"Error listing snippets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list snippets: {e!s}",
        ) from e


def _apply_list_filters(
    snippets: list[CodeSnippet],
    language: SnippetLanguage | None,
    category: SnippetCategory | None,
    is_favorite: bool | None,
) -> list[CodeSnippet]:
    """Apply filters for listing snippets.

    Args:
        snippets: Snippets to filter
        language: Language filter
        category: Category filter
        is_favorite: Favorite filter

    Returns:
        Filtered snippets

    """
    snippets = _filter_by_language(snippets, language)
    snippets = _filter_by_category(snippets, category)
    return _filter_by_favorite(snippets, is_favorite)


def _sort_by_update_time(snippets: list[CodeSnippet]) -> list[CodeSnippet]:
    """Sort snippets by most recently updated.

    Args:
        snippets: Snippets to sort

    Returns:
        Sorted snippets

    """
    return sorted(snippets, key=lambda s: s.updated_at, reverse=True)


@app.post("/", status_code=status.HTTP_201_CREATED)
async def create_snippet(request: CreateSnippetRequest) -> CodeSnippet:
    """Create a new code snippet.

    Args:
        request: Snippet creation request

    Returns:
        Created code snippet

    """
    try:
        snippet = CodeSnippet(
            id=str(uuid4()),
            title=request.title,
            description=request.description,
            language=request.language,
            category=request.category,
            code=request.code,
            tags=request.tags,
            is_favorite=request.is_favorite,
            dependencies=request.dependencies,
            source_url=request.source_url,
            license=request.license,
            usage_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        _save_snippet(snippet)
        logger.info(f"Created snippet: {snippet.id} - {snippet.title}")
        return snippet

    except Exception as e:
        logger.exception(f"Error creating snippet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create snippet: {e!s}",
        ) from e


@app.post("/search")
async def search_snippets(request: SearchSnippetsRequest) -> list[CodeSnippet]:
    """Search snippets with advanced filtering.

    Args:
        request: Search request with filters

    Returns:
        List of matching snippets

    """
    try:
        snippets = _load_all_snippets()

        # Apply all filters
        snippets = _filter_snippets(snippets, request)

        # Sort and paginate
        snippets = _sort_snippets(snippets, request.sort_by or "usage")
        return _paginate_results(snippets, request.offset, request.limit)

    except Exception as e:
        logger.exception(f"Error searching snippets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search snippets: {e!s}",
        ) from e


def _filter_snippets(snippets: list[CodeSnippet], request: SearchSnippetsRequest) -> list[CodeSnippet]:
    """Apply all filters to snippet list.

    Args:
        snippets: List of snippets to filter
        request: Search request with filter criteria

    Returns:
        Filtered list of snippets

    """
    snippets = _filter_by_language(snippets, request.language)
    snippets = _filter_by_category(snippets, request.category)
    snippets = _filter_by_favorite(snippets, request.is_favorite)
    snippets = _filter_by_tags(snippets, request.tags)
    return _filter_by_query(snippets, request.query)


def _filter_by_language(snippets: list[CodeSnippet], language: SnippetLanguage | None) -> list[CodeSnippet]:
    """Filter snippets by programming language.

    Args:
        snippets: List of snippets to filter
        language: Language to filter by, or None for no filter

    Returns:
        Filtered snippets

    """
    if not language:
        return snippets
    return [s for s in snippets if s.language == language]


def _filter_by_category(snippets: list[CodeSnippet], category: SnippetCategory | None) -> list[CodeSnippet]:
    """Filter snippets by category.

    Args:
        snippets: List of snippets to filter
        category: Category to filter by, or None for no filter

    Returns:
        Filtered snippets

    """
    if not category:
        return snippets
    return [s for s in snippets if s.category == category]


def _filter_by_favorite(snippets: list[CodeSnippet], is_favorite: bool | None) -> list[CodeSnippet]:
    """Filter snippets by favorite status.

    Args:
        snippets: List of snippets to filter
        is_favorite: Favorite status to filter by, or None for no filter

    Returns:
        Filtered snippets

    """
    if is_favorite is None:
        return snippets
    return [s for s in snippets if s.is_favorite == is_favorite]


def _filter_by_tags(snippets: list[CodeSnippet], tags: list[str] | None) -> list[CodeSnippet]:
    """Filter snippets by tags.

    Args:
        snippets: List of snippets to filter
        tags: Tags to filter by (any match), or None for no filter

    Returns:
        Filtered snippets

    """
    if not tags:
        return snippets
    return [s for s in snippets if any(tag in s.tags for tag in tags)]


def _filter_by_query(snippets: list[CodeSnippet], query: str | None) -> list[CodeSnippet]:
    """Filter snippets by text search query.

    Args:
        snippets: List of snippets to filter
        query: Search query string

    Returns:
        Snippets matching the query

    """
    if not query:
        return snippets

    query_lower = query.lower()
    return [
        s
        for s in snippets
        if query_lower in s.title.lower()
        or (s.description and query_lower in s.description.lower())
        or query_lower in s.code.lower()
        or any(query_lower in tag.lower() for tag in s.tags)
        or any(query_lower in dep.lower() for dep in s.dependencies)
    ]


def _sort_snippets(snippets: list[CodeSnippet], sort_by: str) -> list[CodeSnippet]:
    """Sort snippets by specified criteria.

    Args:
        snippets: List of snippets to sort
        sort_by: Sort criteria ('usage', 'date', 'title')

    Returns:
        Sorted list of snippets

    """
    sort_keys = {
        "usage": lambda s: s.usage_count,
        "date": lambda s: s.updated_at,
        "title": lambda s: s.title.lower(),
    }
    key_func = sort_keys.get(sort_by, sort_keys["usage"])
    return sorted(snippets, key=key_func, reverse=(sort_by != "title"))


def _paginate_results(snippets: list[CodeSnippet], offset: int, limit: int) -> list[CodeSnippet]:
    """Paginate snippet results.

    Args:
        snippets: List of snippets to paginate
        offset: Starting index
        limit: Maximum number of results

    Returns:
        Paginated slice of snippets

    """
    return snippets[offset: offset + limit]


@app.get("/stats")
async def get_snippet_stats() -> SnippetStats:
    """Get statistics about the snippet library.

    Returns:
        Snippet library statistics

    """
    try:
        snippets = _load_all_snippets()

        return SnippetStats(
            total_snippets=len(snippets),
            snippets_by_language=_count_snippets_by_language(snippets),
            snippets_by_category=_count_snippets_by_category(snippets),
            total_favorites=_count_favorites(snippets),
            most_used_snippets=_get_most_used_snippets(snippets),
            total_tags=_count_unique_tags(snippets),
        )

    except Exception as e:
        logger.exception(f"Error getting snippet stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get snippet stats: {e!s}",
        ) from e


def _count_snippets_by_language(snippets: list[CodeSnippet]) -> dict[str, int]:
    """Count snippets grouped by language.

    Args:
        snippets: List of all snippets

    Returns:
        Dictionary mapping language to count

    """
    return {
        lang.value: count for lang in SnippetLanguage if (count := len([s for s in snippets if s.language == lang])) > 0
    }


def _count_snippets_by_category(snippets: list[CodeSnippet]) -> dict[str, int]:
    """Count snippets grouped by category.

    Args:
        snippets: List of all snippets

    Returns:
        Dictionary mapping category to count

    """
    return {
        cat.value: count for cat in SnippetCategory if (count := len([s for s in snippets if s.category == cat])) > 0
    }


def _count_favorites(snippets: list[CodeSnippet]) -> int:
    """Count total favorite snippets.

    Args:
        snippets: List of all snippets

    Returns:
        Number of favorite snippets

    """
    return len([s for s in snippets if s.is_favorite])


def _get_most_used_snippets(snippets: list[CodeSnippet], limit: int = 5) -> list[tuple[str, int]]:
    """Get the most frequently used snippets.

    Args:
        snippets: List of all snippets
        limit: Maximum number of results

    Returns:
        List of (snippet_id, usage_count) tuples

    """
    most_used = sorted(snippets, key=lambda s: s.usage_count, reverse=True)[:limit]
    return [(s.id, s.usage_count) for s in most_used]


def _count_unique_tags(snippets: list[CodeSnippet]) -> int:
    """Count total unique tags across all snippets.

    Args:
        snippets: List of all snippets

    Returns:
        Number of unique tags

    """
    all_tags = set()
    for s in snippets:
        all_tags.update(s.tags)
    return len(all_tags)


def _apply_snippet_updates(snippet: CodeSnippet, request: UpdateSnippetRequest) -> None:
    """Apply update request fields to snippet.

    Args:
        snippet: Snippet to update (modified in place)
        request: Update request with new values

    """
    # Map of fields to update
    updates = {
        "title": request.title,
        "description": request.description,
        "language": request.language,
        "category": request.category,
        "code": request.code,
        "tags": request.tags,
        "is_favorite": request.is_favorite,
        "dependencies": request.dependencies,
        "source_url": request.source_url,
        "license": request.license,
    }

    for field, value in updates.items():
        if value is not None:
            setattr(snippet, field, value)


@app.get("/export")
async def export_snippets(
    language: SnippetLanguage | None = None,
    category: SnippetCategory | None = None,
    is_favorite: bool | None = None,
) -> JSONResponse:
    """Export snippets as a collection.

    Args:
        language: Only export snippets in this language
        category: Only export snippets from this category
        is_favorite: Only export favorite snippets

    Returns:
        JSON response with snippet collection

    """
    try:
        snippets = _load_all_snippets()
        snippets = _apply_list_filters(snippets, language, category, is_favorite)

        collection = _build_snippet_collection(snippets)
        return _create_export_response(collection)

    except Exception as e:
        logger.exception(f"Error exporting snippets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export snippets: {e!s}",
        ) from e


def _build_snippet_collection(snippets: list[CodeSnippet]) -> SnippetCollection:
    """Build snippet collection for export.

    Args:
        snippets: List of snippets to export

    Returns:
        SnippetCollection object

    """
    return SnippetCollection(
        name="Forge Snippet Collection",
        description=f"Exported {len(snippets)} code snippets",
        version="1.0.0",
        snippets=snippets,
        metadata={
            "exported_at": datetime.now().isoformat(),
            "total_snippets": len(snippets),
        },
    )


def _create_export_response(collection: SnippetCollection) -> JSONResponse:
    """Create JSON response for snippet export.

    Args:
        collection: Snippet collection to export

    Returns:
        JSONResponse with download headers

    """
    filename = f'snippets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    return JSONResponse(
        content=json.loads(collection.model_dump_json(indent=2)),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/import")
async def import_snippets(collection: SnippetCollection) -> dict[str, int]:
    """Import snippets from a collection.

    Args:
        collection: Snippet collection to import

    Returns:
        Dictionary with import statistics

    """
    try:
        imported = 0
        skipped = 0
        updated = 0

        for snippet in collection.snippets:
            existing = _load_snippet(snippet.id)
            if existing:
                # Update existing snippet
                snippet.updated_at = datetime.now()
                _save_snippet(snippet)
                updated += 1
            else:
                # Create new snippet
                snippet.created_at = datetime.now()
                snippet.updated_at = datetime.now()
                _save_snippet(snippet)
                imported += 1

        logger.info(
            f"Imported snippets: {imported} new, {updated} updated, {skipped} skipped",
        )

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": imported + updated,
        }

    except Exception as e:
        logger.exception(f"Error importing snippets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import snippets: {e!s}",
        ) from e


@app.post("/{snippet_id}/use")
async def mark_snippet_used(snippet_id: str) -> JSONResponse:
    """Increment usage count for a snippet and persist the change."""
    try:
        snippet = _load_snippet(snippet_id)
        if not snippet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snippet not found: {snippet_id}",
            )

        snippet.usage_count += 1
        snippet.updated_at = datetime.now()
        _save_snippet(snippet)
        logger.info("Tracked usage for snippet %s", snippet_id)
        return JSONResponse({"status": "ok", "usage_count": snippet.usage_count})

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error tracking usage for snippet {snippet_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track snippet usage: {e!s}",
        ) from e


@app.post("/snippets/track_usage")
async def track_snippet_usage(request: SnippetUsageEvent) -> JSONResponse:
    """Record snippet usage analytics event from client request payload."""
    event = request.model_dump()
    events = _load_usage_events()
    event["timestamp"] = datetime.utcnow().isoformat()
    events.append(event)
    _save_usage_events(events)
    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_201_CREATED)


@app.get("/{snippet_id}")
async def get_snippet(snippet_id: str) -> CodeSnippet:
    """Get a specific snippet by ID.

    Args:
        snippet_id: ID of the snippet

    Returns:
        Code snippet

    """
    try:
        if snippet := _load_snippet(snippet_id):
            return snippet

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Snippet not found: {snippet_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting snippet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get snippet: {e!s}",
        ) from e


@app.patch("/{snippet_id}")
async def update_snippet(snippet_id: str, request: UpdateSnippetRequest) -> CodeSnippet:
    """Update an existing snippet.

    Args:
        snippet_id: ID of the snippet to update
        request: Update request with new values

    Returns:
        Updated snippet

    """
    try:
        snippet = _load_snippet(snippet_id)
        if not snippet:
            logger.info(
                "Snippet %s missing. Current workspace_base=%s AppConfig=%s",
                snippet_id,
                config.workspace_base,
                getattr(AppConfig, "workspace_base", None),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snippet not found: {snippet_id}",
            )

        _apply_snippet_updates(snippet, request)
        snippet.updated_at = datetime.now()
        _save_snippet(snippet)

        logger.info(f"Updated snippet: {snippet_id}")
        return snippet

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating snippet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update snippet: {e!s}",
        ) from e


@app.delete("/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_snippet(snippet_id: str) -> None:
    """Delete a snippet.

    Args:
        snippet_id: ID of the snippet to delete

    """
    try:
        snippet = _load_snippet(snippet_id)
        if not snippet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snippet not found: {snippet_id}",
            )

        _delete_snippet_file(snippet_id)
        logger.info(f"Deleted snippet: {snippet_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting snippet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete snippet: {e!s}",
        ) from e


# Export router for inclusion and a FastAPI app for standalone testing
router = app
snippets_test_app = FastAPI()
snippets_test_app.include_router(router)
