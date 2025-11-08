"""API routes for managing prompt templates."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from forge.server.shared import config
from forge.storage.data_models.prompt_template import (
    CreatePromptRequest,
    PromptCategory,
    PromptCollection,
    PromptStats,
    PromptTemplate,
    RenderPromptRequest,
    SearchPromptsRequest,
    UpdatePromptRequest,
)

app = APIRouter(prefix="/api/prompts")
logger = logging.getLogger(__name__)

# Validation constants
MAX_PROMPT_CONTENT_LENGTH = 50_000  # 50KB
MAX_PROMPT_TITLE_LENGTH = 200
MAX_PROMPT_DESCRIPTION_LENGTH = 1000
MAX_TAGS_PER_PROMPT = 20
MAX_TAG_LENGTH = 50
MAX_VARIABLE_NAME_LENGTH = 50


def _validate_prompt_input(title: str, content: str, tags: list[str], variables: list) -> None:
    """Validate prompt input for security and sanity.

    Args:
        title: Prompt title
        content: Prompt content
        tags: List of tags
        variables: List of variables

    Raises:
        HTTPException: If validation fails

    """
    _validate_prompt_title(title)
    _validate_prompt_content(content)
    _validate_prompt_tags(tags)
    _validate_prompt_variables(variables)


def _validate_prompt_title(title: str) -> None:
    """Validate prompt title.

    Args:
        title: The title to validate

    Raises:
        HTTPException: If validation fails

    """
    if len(title) > MAX_PROMPT_TITLE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Title too long. Maximum length is {MAX_PROMPT_TITLE_LENGTH} characters.",
        )

    if not title.strip():
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty.",
        )


def _validate_prompt_content(content: str) -> None:
    """Validate prompt content.

    Args:
        content: The content to validate

    Raises:
        HTTPException: If validation fails

    """
    if len(content) > MAX_PROMPT_CONTENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Content too long. Maximum length is {MAX_PROMPT_CONTENT_LENGTH} characters.",
        )

    if not content.strip():
        raise HTTPException(
            status_code=400,
            detail="Content cannot be empty.",
        )


def _validate_prompt_tags(tags: list[str]) -> None:
    """Validate prompt tags.

    Args:
        tags: List of tags to validate

    Raises:
        HTTPException: If validation fails

    """
    if len(tags) > MAX_TAGS_PER_PROMPT:
        raise HTTPException(
            status_code=400,
            detail=f"Too many tags. Maximum is {MAX_TAGS_PER_PROMPT}.",
        )

    for tag in tags:
        _validate_single_tag(tag)


def _validate_single_tag(tag: str) -> None:
    """Validate a single tag.

    Args:
        tag: Tag string to validate

    Raises:
        HTTPException: If validation fails

    """
    if len(tag) > MAX_TAG_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Tag '{tag}' too long. Maximum length is {MAX_TAG_LENGTH} characters.",
        )

    # Sanitize tag (alphanumeric, hyphens, underscores, spaces only)
    if not all(c.isalnum() or c in ["-", "_", " "] for c in tag):
        raise HTTPException(
            status_code=400,
            detail=f"Tag '{tag}' contains invalid characters. Use only letters, numbers, hyphens, and underscores.",
        )


def _validate_prompt_variables(variables: list) -> None:
    """Validate prompt variables.

    Args:
        variables: List of variables to validate

    Raises:
        HTTPException: If validation fails

    """
    for var in variables:
        var_name = var.get("name", "") if isinstance(var, dict) else var.name
        _validate_variable_name(var_name)


def _validate_variable_name(var_name: str) -> None:
    """Validate a single variable name.

    Args:
        var_name: Variable name to validate

    Raises:
        HTTPException: If validation fails

    """
    if len(var_name) > MAX_VARIABLE_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Variable name '{var_name}' too long. Maximum length is {MAX_VARIABLE_NAME_LENGTH}.",
        )

    # Sanitize variable name (alphanumeric and underscores only)
    if not var_name.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail=f"Variable name '{var_name}' contains invalid characters. Use only letters, numbers, and underscores.",
        )


def _get_prompts_dir() -> Path:
    """Get the directory where prompts are stored."""
    workspace_base = Path(config.workspace_base or ".")
    prompts_dir = workspace_base / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir


def _get_prompt_file_path(prompt_id: str) -> Path:
    """Get the file path for a specific prompt."""
    return _get_prompts_dir() / f"{prompt_id}.json"


def _load_prompt(prompt_id: str) -> PromptTemplate | None:
    """Load a prompt from disk."""
    try:
        prompt_file = _get_prompt_file_path(prompt_id)
        if not prompt_file.exists():
            return None

        with open(prompt_file, encoding="utf-8") as f:
            data = json.load(f)
            return PromptTemplate(**data)
    except Exception as e:
        logger.exception(f"Error loading prompt {prompt_id}: {e}")
        return None


def _save_prompt(prompt: PromptTemplate) -> None:
    """Save a prompt to disk."""
    try:
        prompt_file = _get_prompt_file_path(prompt.id)
        with open(prompt_file, "w", encoding="utf-8") as f:
            json.dump(prompt.model_dump(), f, indent=2, default=str)
    except Exception as e:
        logger.exception(f"Error saving prompt {prompt.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save prompt: {e!s}",
        ) from e


def _delete_prompt_file(prompt_id: str) -> None:
    """Delete a prompt file from disk."""
    try:
        prompt_file = _get_prompt_file_path(prompt_id)
        if prompt_file.exists():
            prompt_file.unlink()
    except Exception as e:
        logger.exception(f"Error deleting prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete prompt: {e!s}",
        ) from e


def _load_all_prompts() -> list[PromptTemplate]:
    """Load all prompts from disk."""
    prompts = []
    prompts_dir = _get_prompts_dir()

    for prompt_file in prompts_dir.glob("*.json"):
        try:
            with open(prompt_file, encoding="utf-8") as f:
                data = json.load(f)
                prompts.append(PromptTemplate(**data))
        except Exception as e:
            logger.exception(f"Error loading prompt from {prompt_file}: {e}")
            continue

    return prompts


@app.get("/")
async def list_prompts(
    category: PromptCategory | None = None,
    is_favorite: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PromptTemplate]:
    """List all prompt templates with optional filtering.

    Args:
        category: Filter by category
        is_favorite: Filter by favorite status
        limit: Maximum number of prompts to return
        offset: Number of prompts to skip

    Returns:
        List of prompt templates

    """
    try:
        prompts = _load_all_prompts()

        # Apply filters
        if category:
            prompts = [p for p in prompts if p.category == category]

        if is_favorite is not None:
            prompts = [p for p in prompts if p.is_favorite == is_favorite]

        # Sort by most recently updated
        prompts.sort(key=lambda p: p.updated_at, reverse=True)

        # Apply pagination
        return prompts[offset: offset + limit]

    except Exception as e:
        logger.exception(f"Error listing prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompts: {e!s}",
        ) from e


@app.post("/", status_code=status.HTTP_201_CREATED)
async def create_prompt(request: CreatePromptRequest) -> PromptTemplate:
    """Create a new prompt template.

    Args:
        request: Prompt creation request

    Returns:
        Created prompt template

    """
    try:
        # Validate input
        _validate_prompt_input(
            title=request.title,
            content=request.content,
            tags=request.tags,
            variables=request.variables,
        )

        prompt = PromptTemplate(
            id=str(uuid4()),
            title=request.title,
            description=request.description,
            category=request.category,
            content=request.content,
            variables=request.variables,
            tags=request.tags,
            is_favorite=request.is_favorite,
            usage_count=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        _save_prompt(prompt)
        logger.info(f"Created prompt: {prompt.id} - {prompt.title}")
        return prompt

    except Exception as e:
        logger.exception(f"Error creating prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prompt: {e!s}",
        ) from e


@app.post("/search")
async def search_prompts(request: SearchPromptsRequest) -> list[PromptTemplate]:
    """Search prompts with advanced filtering.

    Args:
        request: Search request with filters

    Returns:
        List of matching prompts

    """
    try:
        prompts = _load_all_prompts()
        prompts = _filter_prompts(prompts, request)
        prompts = _sort_prompts(prompts, getattr(request, "sort_by", "usage"))
        return _paginate_prompt_results(prompts, request.offset, request.limit)

    except Exception as e:
        logger.exception(f"Error searching prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search prompts: {e!s}",
        ) from e


def _filter_prompts(prompts: list[PromptTemplate], request: SearchPromptsRequest) -> list[PromptTemplate]:
    """Apply all filters to prompt list.

    Args:
        prompts: List of prompts to filter
        request: Search request with filter criteria

    Returns:
        Filtered list of prompts

    """
    prompts = _filter_prompts_by_category(prompts, request.category)
    prompts = _filter_prompts_by_favorite(prompts, request.is_favorite)
    prompts = _filter_prompts_by_tags(prompts, request.tags)
    return _filter_prompts_by_query(prompts, request.query)


def _filter_prompts_by_category(prompts: list[PromptTemplate], category: PromptCategory | None) -> list[PromptTemplate]:
    """Filter prompts by category.

    Args:
        prompts: List of prompts to filter
        category: Category to filter by, or None for no filter

    Returns:
        Filtered prompts

    """
    if not category:
        return prompts
    return [p for p in prompts if p.category == category]


def _filter_prompts_by_favorite(prompts: list[PromptTemplate], is_favorite: bool | None) -> list[PromptTemplate]:
    """Filter prompts by favorite status.

    Args:
        prompts: List of prompts to filter
        is_favorite: Favorite status to filter by, or None for no filter

    Returns:
        Filtered prompts

    """
    if is_favorite is None:
        return prompts
    return [p for p in prompts if p.is_favorite == is_favorite]


def _filter_prompts_by_tags(prompts: list[PromptTemplate], tags: list[str] | None) -> list[PromptTemplate]:
    """Filter prompts by tags.

    Args:
        prompts: List of prompts to filter
        tags: Tags to filter by (any match), or None for no filter

    Returns:
        Filtered prompts

    """
    if not tags:
        return prompts
    return [p for p in prompts if any(tag in p.tags for tag in tags)]


def _filter_prompts_by_query(prompts: list[PromptTemplate], query: str | None) -> list[PromptTemplate]:
    """Filter prompts by text search query.

    Args:
        prompts: List of prompts to filter
        query: Search query string, or None for no filter

    Returns:
        Prompts matching the query

    """
    if not query:
        return prompts

    query_lower = query.lower()
    return [
        p
        for p in prompts
        if query_lower in p.title.lower()
        or (p.description and query_lower in p.description.lower())
        or query_lower in p.content.lower()
        or any(query_lower in tag.lower() for tag in p.tags)
    ]


def _sort_prompts(prompts: list[PromptTemplate], sort_by: str) -> list[PromptTemplate]:
    """Sort prompts by specified criteria.

    Args:
        prompts: List of prompts to sort
        sort_by: Sort criteria ('usage', 'date', 'title')

    Returns:
        Sorted list of prompts

    """
    sort_keys = {
        "usage": lambda p: p.usage_count,
        "date": lambda p: p.updated_at,
        "title": lambda p: p.title.lower(),
    }
    key_func = sort_keys.get(sort_by, sort_keys["usage"])
    return sorted(prompts, key=key_func, reverse=(sort_by != "title"))


def _paginate_prompt_results(prompts: list[PromptTemplate], offset: int, limit: int) -> list[PromptTemplate]:
    """Paginate prompt results.

    Args:
        prompts: List of prompts to paginate
        offset: Starting index
        limit: Maximum number of results

    Returns:
        Paginated slice of prompts

    """
    return prompts[offset: offset + limit]


@app.get("/stats")
async def get_prompt_stats() -> PromptStats:
    """Get statistics about the prompt library.

    Returns:
        Prompt library statistics

    """
    try:
        prompts = _load_all_prompts()

        # Count by category
        prompts_by_category = {}
        for category in PromptCategory:
            count = len([p for p in prompts if p.category == category])
            if count > 0:
                prompts_by_category[category.value] = count

        # Get most used prompts
        most_used = sorted(prompts, key=lambda p: p.usage_count, reverse=True)[:5]
        most_used_prompts = [(p.id, p.usage_count) for p in most_used]

        # Count unique tags
        all_tags = set()
        for p in prompts:
            all_tags.update(p.tags)

        return PromptStats(
            total_prompts=len(prompts),
            prompts_by_category=prompts_by_category,
            total_favorites=len([p for p in prompts if p.is_favorite]),
            most_used_prompts=most_used_prompts,
            total_tags=len(all_tags),
        )

    except Exception as e:
        logger.exception(f"Error getting prompt stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt stats: {e!s}",
        ) from e


@app.get("/export")
async def export_prompts(
    category: PromptCategory | None = None,
    is_favorite: bool | None = None,
) -> JSONResponse:
    """Export prompts as a collection.

    Args:
        category: Only export prompts from this category
        is_favorite: Only export favorite prompts

    Returns:
        JSON response with prompt collection

    """
    try:
        prompts = _load_all_prompts()

        # Apply filters
        if category:
            prompts = [p for p in prompts if p.category == category]

        if is_favorite is not None:
            prompts = [p for p in prompts if p.is_favorite == is_favorite]

        collection = PromptCollection(
            name="Forge Prompt Collection",
            description=f"Exported {len(prompts)} prompts",
            version="1.0.0",
            prompts=prompts,
            metadata={
                "exported_at": datetime.now().isoformat(),
                "total_prompts": len(prompts),
            },
        )

        return JSONResponse(
            content=json.loads(collection.model_dump_json(indent=2)),
            headers={
                "Content-Disposition": f'attachment; filename="prompts_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"',
            },
        )

    except Exception as e:
        logger.exception(f"Error exporting prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export prompts: {e!s}",
        ) from e


@app.post("/import")
async def import_prompts(collection: PromptCollection) -> dict[str, int]:
    """Import prompts from a collection.

    Args:
        collection: Prompt collection to import

    Returns:
        Dictionary with import statistics

    """
    try:
        imported = 0
        skipped = 0
        updated = 0

        for prompt in collection.prompts:
            existing = _load_prompt(prompt.id)
            if existing:
                # Update existing prompt
                prompt.updated_at = datetime.now()
                _save_prompt(prompt)
                updated += 1
            else:
                # Create new prompt
                prompt.created_at = datetime.now()
                prompt.updated_at = datetime.now()
                _save_prompt(prompt)
                imported += 1

        logger.info(
            f"Imported prompts: {imported} new, {updated} updated, {skipped} skipped",
        )

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "total": imported + updated,
        }

    except Exception as e:
        logger.exception(f"Error importing prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import prompts: {e!s}",
        ) from e


@app.post("/render")
async def render_prompt(request: RenderPromptRequest) -> dict[str, str]:
    """Render a prompt template with variables.

    Args:
        request: Render request with prompt ID and variables

    Returns:
        Dictionary with rendered prompt

    """
    try:
        prompt = _load_prompt(request.prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt not found: {request.prompt_id}",
            )

        rendered = prompt.render(request.variables)

        # Increment usage count
        prompt.usage_count += 1
        prompt.updated_at = datetime.now()
        _save_prompt(prompt)

        return {"rendered": rendered}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error rendering prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render prompt: {e!s}",
        ) from e


@app.post("/{prompt_id}/use")
async def track_prompt_usage(prompt_id: str) -> PromptTemplate:
    """Track usage of a prompt (increment usage count).

    Args:
        prompt_id: ID of the prompt

    Returns:
        Updated prompt template

    """
    try:
        prompt = _load_prompt(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt not found: {prompt_id}",
            )

        prompt.usage_count += 1
        prompt.updated_at = datetime.now()
        _save_prompt(prompt)

        return prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error tracking prompt usage: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track prompt usage: {e!s}",
        ) from e


@app.get("/{prompt_id}")
async def get_prompt(prompt_id: str) -> PromptTemplate:
    """Get a specific prompt by ID.

    Args:
        prompt_id: ID of the prompt

    Returns:
        Prompt template

    """
    try:
        if prompt := _load_prompt(prompt_id):
            return prompt

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt not found: {prompt_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompt: {e!s}",
        ) from e


@app.patch("/{prompt_id}")
async def update_prompt(prompt_id: str, request: UpdatePromptRequest) -> PromptTemplate:
    """Update an existing prompt.

    Args:
        prompt_id: ID of the prompt to update
        request: Update request with new values

    Returns:
        Updated prompt template

    """
    try:
        prompt = _load_prompt(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt not found: {prompt_id}",
            )

        _apply_prompt_updates(prompt, request)
        prompt.updated_at = datetime.now()
        _save_prompt(prompt)

        logger.info(f"Updated prompt: {prompt_id}")
        return prompt

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt: {e!s}",
        ) from e


def _apply_prompt_updates(prompt: PromptTemplate, request: UpdatePromptRequest) -> None:
    """Apply update request fields to prompt.

    Args:
        prompt: Prompt to update (modified in place)
        request: Update request with new values

    """
    if request.title is not None:
        prompt.title = request.title
    if request.description is not None:
        prompt.description = request.description
    if request.category is not None:
        prompt.category = request.category
    if request.content is not None:
        prompt.content = request.content
    if request.variables is not None:
        prompt.variables = request.variables
    if request.tags is not None:
        prompt.tags = request.tags
    if request.is_favorite is not None:
        prompt.is_favorite = request.is_favorite


@app.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_prompt(prompt_id: str) -> None:
    """Delete a prompt.

    Args:
        prompt_id: ID of the prompt to delete

    """
    try:
        prompt = _load_prompt(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prompt not found: {prompt_id}",
            )

        _delete_prompt_file(prompt_id)
        logger.info(f"Deleted prompt: {prompt_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete prompt: {e!s}",
        ) from e
