"""Data models for code snippets."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SnippetLanguage(str, Enum):
    """Programming languages supported for syntax highlighting."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    R = "r"
    MATLAB = "matlab"
    SQL = "sql"
    HTML = "html"
    CSS = "css"
    SCSS = "scss"
    LESS = "less"
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    MARKDOWN = "markdown"
    BASH = "bash"
    SHELL = "shell"
    POWERSHELL = "powershell"
    DOCKERFILE = "dockerfile"
    MAKEFILE = "makefile"
    GRAPHQL = "graphql"
    LUA = "lua"
    PERL = "perl"
    HASKELL = "haskell"
    ELIXIR = "elixir"
    CLOJURE = "clojure"
    VUE = "vue"
    REACT = "react"
    ANGULAR = "angular"
    PLAINTEXT = "plaintext"


class SnippetCategory(str, Enum):
    """Categories for organizing code snippets."""

    ALGORITHM = "algorithm"
    DATA_STRUCTURE = "data_structure"
    DATABASE = "database"
    API = "api"
    UI_COMPONENT = "ui_component"
    UTILITY = "utility"
    CONFIGURATION = "configuration"
    TEST = "test"
    DEBUGGING = "debugging"
    ERROR_HANDLING = "error_handling"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BOILERPLATE = "boilerplate"
    CUSTOM = "custom"


class CodeSnippet(BaseModel):
    """Represents a reusable code snippet."""

    id: str = Field(..., description="Unique identifier for the snippet")
    title: str = Field(..., description="Human-readable title")
    description: str | None = Field(
        None,
        description="Description of what this snippet does",
    )
    language: SnippetLanguage = Field(
        SnippetLanguage.PLAINTEXT,
        description="Programming language",
    )
    category: SnippetCategory = Field(
        SnippetCategory.CUSTOM,
        description="Category for organization",
    )
    code: str = Field(..., description="The actual code snippet")
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering and search",
    )
    is_favorite: bool = Field(
        False,
        description="Whether this snippet is marked as favorite",
    )
    usage_count: int = Field(0, description="How many times this snippet has been used")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )
    # Optional fields for advanced features
    dependencies: list[str] = Field(
        default_factory=list,
        description="External dependencies or imports needed",
    )
    related_snippets: list[str] = Field(
        default_factory=list,
        description="IDs of related snippets",
    )
    source_url: str | None = Field(
        None,
        description="Original source URL (if imported)",
    )
    license: str | None = Field(None, description="License information")


class CreateSnippetRequest(BaseModel):
    """Request model for creating a new code snippet."""

    title: str
    description: str | None = None
    language: SnippetLanguage = SnippetLanguage.PLAINTEXT
    category: SnippetCategory = SnippetCategory.CUSTOM
    code: str
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    dependencies: list[str] = Field(default_factory=list)
    source_url: str | None = None
    license: str | None = None


class UpdateSnippetRequest(BaseModel):
    """Request model for updating an existing code snippet."""

    title: str | None = None
    description: str | None = None
    language: SnippetLanguage | None = None
    category: SnippetCategory | None = None
    code: str | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None
    dependencies: list[str] | None = None
    source_url: str | None = None
    license: str | None = None


class SearchSnippetsRequest(BaseModel):
    """Request model for searching code snippets."""

    query: str | None = None
    language: SnippetLanguage | None = None
    category: SnippetCategory | None = None
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool | None = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class SnippetStats(BaseModel):
    """Statistics about the code snippet library."""

    total_snippets: int
    snippets_by_language: dict[str, int]
    snippets_by_category: dict[str, int]
    total_favorites: int
    most_used_snippets: list[tuple[str, int]]  # (snippet_id, usage_count)
    total_tags: int


class SnippetCollection(BaseModel):
    """A collection of code snippets for import/export."""

    name: str = Field(..., description="Name of this snippet collection")
    description: str | None = Field(None, description="Description of the collection")
    version: str = Field("1.0.0", description="Version of the collection format")
    snippets: list[CodeSnippet] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
