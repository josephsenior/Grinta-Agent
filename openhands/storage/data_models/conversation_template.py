"""Data models for conversation templates."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TemplateCategory(str, Enum):
    """Categories for conversation templates."""

    DEBUG = "debug"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    TEST = "test"
    REVIEW = "review"
    EXPLAIN = "explain"
    OPTIMIZE = "optimize"
    FIX_BUG = "fix_bug"
    ADD_FEATURE = "add_feature"
    CUSTOM = "custom"


class ConversationTemplate(BaseModel):
    """Represents a conversation template."""

    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Template title")
    description: str | None = Field(None, description="Template description")
    category: TemplateCategory = Field(TemplateCategory.CUSTOM)
    prompt: str = Field(..., description="The initial prompt/message")
    icon: str | None = Field(None, description="Icon identifier")
    is_favorite: bool = Field(False)
    usage_count: int = Field(0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""

    title: str
    description: str | None = None
    category: TemplateCategory = TemplateCategory.CUSTOM
    prompt: str
    icon: str | None = None
    is_favorite: bool = False


class UpdateTemplateRequest(BaseModel):
    """Request to update a template."""

    title: str | None = None
    description: str | None = None
    category: TemplateCategory | None = None
    prompt: str | None = None
    icon: str | None = None
    is_favorite: bool | None = None
