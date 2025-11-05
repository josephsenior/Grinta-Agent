"""Data models for prompt templates."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PromptCategory(str, Enum):
    """Categories for organizing prompts."""

    CODING = "coding"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    WRITING = "writing"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    BRAINSTORMING = "brainstorming"
    CUSTOM = "custom"


class PromptVariable(BaseModel):
    """Represents a variable in a prompt template."""

    name: str = Field(..., description="Variable name (e.g., 'language', 'task')")
    description: str | None = Field(
        None,
        description="Description of what this variable is for",
    )
    default_value: str | None = Field(
        None,
        description="Default value for the variable",
    )
    required: bool = Field(True, description="Whether this variable is required")


class PromptTemplate(BaseModel):
    """Represents a reusable prompt template."""

    id: str = Field(..., description="Unique identifier for the prompt")
    title: str = Field(..., description="Human-readable title")
    description: str | None = Field(
        None,
        description="Description of what this prompt does",
    )
    category: PromptCategory = Field(
        PromptCategory.CUSTOM,
        description="Category for organization",
    )
    content: str = Field(..., description="The actual prompt text with {{variables}}")
    variables: list[PromptVariable] = Field(
        default_factory=list,
        description="Variables used in this prompt",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and search",
    )
    is_favorite: bool = Field(
        False,
        description="Whether this prompt is marked as favorite",
    )
    usage_count: int = Field(0, description="How many times this prompt has been used")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def render(self, variables: dict[str, str] | None = None) -> str:
        """Render the prompt template with provided variables.

        Args:
            variables: Dictionary of variable names to values

        Returns:
            Rendered prompt string with variables replaced
        """
        variables = variables or {}
        rendered = self.content

        # Replace variables in {{variable}} format
        for var in self.variables:
            placeholder = f"{{{{{var.name}}}}}"
            value = variables.get(var.name, var.default_value or "")
            rendered = rendered.replace(placeholder, value)

        return rendered


class CreatePromptRequest(BaseModel):
    """Request model for creating a new prompt template."""

    title: str
    description: str | None = None
    category: PromptCategory = PromptCategory.CUSTOM
    content: str
    variables: list[PromptVariable] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False


class UpdatePromptRequest(BaseModel):
    """Request model for updating an existing prompt template."""

    title: str | None = None
    description: str | None = None
    category: PromptCategory | None = None
    content: str | None = None
    variables: list[PromptVariable] | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None


class SearchPromptsRequest(BaseModel):
    """Request model for searching prompts."""

    query: str | None = None
    category: PromptCategory | None = None
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class PromptStats(BaseModel):
    """Statistics about the prompt library."""

    total_prompts: int
    prompts_by_category: dict[str, int]
    total_favorites: int
    most_used_prompts: list[tuple[str, int]]  # (prompt_id, usage_count)
    total_tags: int


class PromptCollection(BaseModel):
    """A collection of prompts for import/export."""

    name: str = Field(..., description="Name of this prompt collection")
    description: str | None = Field(None, description="Description of the collection")
    version: str = Field("1.0.0", description="Version of the collection format")
    prompts: list[PromptTemplate] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RenderPromptRequest(BaseModel):
    """Request to render a prompt with variables."""

    prompt_id: str
    variables: dict[str, str] = Field(default_factory=dict)
