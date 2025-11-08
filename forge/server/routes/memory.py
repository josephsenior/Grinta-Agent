"""Memory management API endpoints.

Allows users to store, retrieve, and manage persistent memories.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.user_auth import get_user_settings_store

if TYPE_CHECKING:
    from forge.storage.settings.settings_store import SettingsStore

app = APIRouter(prefix="/api/memory")


class MemoryCategory(str, Enum):
    """Memory categories."""

    TECHNICAL = "technical"
    PREFERENCE = "preference"
    PROJECT = "project"
    FACT = "fact"
    CUSTOM = "custom"


class MemorySource(str, Enum):
    """Memory source."""

    MANUAL = "manual"
    AI_SUGGESTED = "ai-suggested"


class MemoryImportance(str, Enum):
    """Memory importance level."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemoryModel(BaseModel):
    """Memory data model."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    category: MemoryCategory
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    usage_count: int = Field(default=0)
    last_used: str | None = None
    source: MemorySource = Field(default=MemorySource.MANUAL)
    conversation_id: str | None = None
    importance: MemoryImportance = Field(default=MemoryImportance.MEDIUM)


class CreateMemoryRequest(BaseModel):
    """Request to create a new memory."""

    title: str
    content: str
    category: MemoryCategory
    tags: list[str] = Field(default_factory=list)
    importance: MemoryImportance = Field(default=MemoryImportance.MEDIUM)
    conversation_id: str | None = None


class UpdateMemoryRequest(BaseModel):
    """Request to update a memory."""

    title: str | None = None
    content: str | None = None
    category: MemoryCategory | None = None
    tags: list[str] | None = None
    importance: MemoryImportance | None = None


class SearchMemoriesRequest(BaseModel):
    """Request to search memories."""

    query: str
    category: MemoryCategory | None = None
    tags: list[str] | None = None
    min_usage_count: int | None = None
    importance: MemoryImportance | None = None


class MemoryStats(BaseModel):
    """Memory statistics."""

    total: int
    by_category: dict[str, int]
    used_today: int
    most_used: list[dict]
    recently_used: list[dict]


@app.get("/")
async def list_memories(
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> list[dict]:
    """List all memories for the current user."""
    settings = await settings_store.load()

    return getattr(settings, "MEMORIES", []) if settings else []


@app.post("/")
async def create_memory(
    memory: CreateMemoryRequest,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Create a new memory."""
    settings = await settings_store.load()

    if not settings:
        raise HTTPException(status_code=500, detail="Settings not found")

    # Initialize MEMORIES if it doesn't exist
    if not hasattr(settings, "MEMORIES"):
        settings.MEMORIES = []

    # Create memory model
    memory_model = MemoryModel(
        title=memory.title,
        content=memory.content,
        category=memory.category,
        tags=memory.tags,
        importance=memory.importance,
        conversation_id=memory.conversation_id,
    )

    # Add new memory
    settings.MEMORIES.append(memory_model.model_dump())

    # Save settings
    await settings_store.save(settings)

    logger.info(f"Created memory: {memory.title} ({memory.category})")

    return {"status": "success", "memory": memory_model.model_dump()}


@app.post("/search")
async def search_memories(
    search: SearchMemoriesRequest,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> list[dict]:
    """Search memories based on criteria."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        return []

    memories = settings.MEMORIES
    return _filter_memories(memories, search)


def _filter_memories(memories: list[dict], search: SearchMemoriesRequest) -> list[dict]:
    """Apply all filters to memory list.

    Args:
        memories: List of memories to filter
        search: Search request with filter criteria

    Returns:
        Filtered list of memories

    """
    results = []
    for memory in memories:
        if not _memory_matches_filters(memory, search):
            continue
        results.append(memory)
    return results


def _memory_matches_filters(memory: dict, search: SearchMemoriesRequest) -> bool:
    """Check if a memory matches all search filters.

    Args:
        memory: Memory dict to check
        search: Search criteria

    Returns:
        True if memory matches all filters

    """
    if not _memory_matches_query(memory, search.query):
        return False

    if not _memory_matches_category(memory, search.category):
        return False

    if not _memory_matches_tags(memory, search.tags):
        return False

    if not _memory_matches_usage_count(memory, search.min_usage_count):
        return False

    return _memory_matches_importance(memory, search.importance)


def _memory_matches_query(memory: dict, query: str | None) -> bool:
    """Check if memory matches text search query.

    Args:
        memory: Memory dict to check
        query: Search query string, or None for no filter

    Returns:
        True if memory matches query

    """
    if not query:
        return True

    query_lower = query.lower()
    title_match = query_lower in memory.get("title", "").lower()
    content_match = query_lower in memory.get("content", "").lower()
    tag_match = any(query_lower in tag.lower() for tag in memory.get("tags", []))

    return title_match or content_match or tag_match


def _memory_matches_category(memory: dict, category: str | None) -> bool:
    """Check if memory matches category filter.

    Args:
        memory: Memory dict to check
        category: Category to match, or None for no filter

    Returns:
        True if memory matches category

    """
    if not category:
        return True
    return memory.get("category") == category


def _memory_matches_tags(memory: dict, tags: list[str] | None) -> bool:
    """Check if memory matches tags filter.

    Args:
        memory: Memory dict to check
        tags: Tags to match (any), or None for no filter

    Returns:
        True if memory has any of the specified tags

    """
    if not tags:
        return True
    memory_tags = memory.get("tags", [])
    return any(tag in memory_tags for tag in tags)


def _memory_matches_usage_count(memory: dict, min_usage_count: int | None) -> bool:
    """Check if memory meets minimum usage count.

    Args:
        memory: Memory dict to check
        min_usage_count: Minimum usage count, or None for no filter

    Returns:
        True if memory meets minimum usage

    """
    if not min_usage_count:
        return True
    return memory.get("usage_count", 0) >= min_usage_count


def _memory_matches_importance(memory: dict, importance: str | None) -> bool:
    """Check if memory matches importance level.

    Args:
        memory: Memory dict to check
        importance: Importance level to match, or None for no filter

    Returns:
        True if memory matches importance

    """
    if not importance:
        return True
    return memory.get("importance") == importance


@app.get("/stats")
async def get_memory_stats(
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> MemoryStats:
    """Get memory statistics."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        return MemoryStats(
            total=0,
            by_category={},
            used_today=0,
            most_used=[],
            recently_used=[],
        )

    memories = settings.MEMORIES

    by_category = {
        category.value: sum(bool(m.get("category") == category.value) for m in memories) for category in MemoryCategory
    }
    # Used today
    today = datetime.now().date()
    used_today = sum(
        bool(
            m.get("last_used") and datetime.fromisoformat(m["last_used"]).date() == today,
        )
        for m in memories
    )

    # Most used
    most_used = sorted(memories, key=lambda m: m.get("usage_count", 0), reverse=True)[:5]

    # Recently used
    recently_used = sorted(
        [m for m in memories if m.get("last_used")],
        key=lambda m: m.get("last_used", ""),
        reverse=True,
    )[:5]

    return MemoryStats(
        total=len(memories),
        by_category=by_category,
        used_today=used_today,
        most_used=most_used,
        recently_used=recently_used,
    )


@app.post("/{memory_id}/track-usage")
async def track_memory_usage(
    memory_id: str,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Track memory usage (increment usage count and update last used)."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        raise HTTPException(status_code=404, detail="Memory not found")

    # Find and update usage
    found = False
    for memory in settings.MEMORIES:
        if memory["id"] == memory_id:
            memory["usage_count"] = memory.get("usage_count", 0) + 1
            memory["last_used"] = datetime.now().isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Memory not found")

    await settings_store.save(settings)

    return {"status": "success"}


@app.get("/export")
async def export_memories(
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Export all memories to JSON."""
    settings = await settings_store.load()

    memories = []
    if settings and hasattr(settings, "MEMORIES"):
        memories = settings.MEMORIES

    # Get stats
    stats_data = await get_memory_stats(settings_store)

    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "memories": memories,
        "stats": stats_data.model_dump(),
    }


@app.post("/import")
async def import_memories(
    import_data: dict,
    merge: bool = False,
    settings_store: Any = Depends(get_user_settings_store),
) -> dict:
    """Import memories from JSON file."""
    settings = await settings_store.load()

    if not settings:
        raise HTTPException(status_code=500, detail="Settings not found")

    # Validate import data
    if "memories" not in import_data:
        raise HTTPException(status_code=400, detail="Invalid import data")

    imported_memories = import_data["memories"]

    # Initialize MEMORIES if it doesn't exist
    if not hasattr(settings, "MEMORIES"):
        settings.MEMORIES = []

    if merge:
        # Merge with existing memories (avoid duplicates by ID)
        existing_ids = {m["id"] for m in settings.MEMORIES}
        new_memories = [m for m in imported_memories if m["id"] not in existing_ids]
        settings.MEMORIES.extend(new_memories)
        imported_count = len(new_memories)
    else:
        # Replace all memories
        settings.MEMORIES = imported_memories
        imported_count = len(imported_memories)

    await settings_store.save(settings)

    logger.info(f"Imported {imported_count} memories (merge={merge})")

    return {
        "status": "success",
        "imported": imported_count,
        "total": len(settings.MEMORIES),
    }


# ============================================================================
# PARAMETERIZED ROUTES (must be at the end to avoid catching specific routes)
# ============================================================================


@app.get("/{memory_id}")
async def get_memory(
    memory_id: str,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Get a single memory by ID."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        raise HTTPException(status_code=404, detail="Memory not found")

    # Find the memory
    for memory in settings.MEMORIES:
        if memory["id"] == memory_id:
            return memory

    raise HTTPException(status_code=404, detail="Memory not found")


@app.patch("/{memory_id}")
async def update_memory(
    memory_id: str,
    updates: UpdateMemoryRequest,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Update an existing memory.

    Args:
        memory_id: Memory ID to update
        updates: Update request
        settings_store: Settings store dependency

    Returns:
        Success status dict

    """
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        raise HTTPException(status_code=404, detail="Memory not found")

    _find_and_update_memory(settings.MEMORIES, memory_id, updates)
    await settings_store.save(settings)

    logger.info(f"Updated memory: {memory_id}")
    return {"status": "success"}


def _find_and_update_memory(memories: list[dict], memory_id: str, updates: UpdateMemoryRequest) -> dict:
    """Find memory by ID and apply updates.

    Args:
        memories: List of memory dicts
        memory_id: Memory ID to find
        updates: Updates to apply

    Returns:
        Updated memory dict

    Raises:
        HTTPException: If memory not found

    """
    for memory in memories:
        if memory["id"] == memory_id:
            _apply_memory_updates(memory, updates)
            memory["updated_at"] = datetime.now().isoformat()
            return memory

    raise HTTPException(status_code=404, detail="Memory not found")


def _apply_memory_updates(memory: dict, updates: UpdateMemoryRequest) -> None:
    """Apply update request fields to memory.

    Args:
        memory: Memory dict to update (modified in place)
        updates: Update request with new values

    """
    if updates.title is not None:
        memory["title"] = updates.title
    if updates.content is not None:
        memory["content"] = updates.content
    if updates.category is not None:
        memory["category"] = updates.category
    if updates.tags is not None:
        memory["tags"] = updates.tags
    if updates.importance is not None:
        memory["importance"] = updates.importance


@app.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    settings_store: Annotated[Any, Depends(get_user_settings_store)],
) -> dict:
    """Delete a memory."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "MEMORIES"):
        raise HTTPException(status_code=404, detail="Memory not found")

    # Filter out the memory to delete
    original_count = len(settings.MEMORIES)
    settings.MEMORIES = [m for m in settings.MEMORIES if m["id"] != memory_id]

    if len(settings.MEMORIES) == original_count:
        raise HTTPException(status_code=404, detail="Memory not found")

    await settings_store.save(settings)

    logger.info(f"Deleted memory: {memory_id}")

    return {"status": "success"}
