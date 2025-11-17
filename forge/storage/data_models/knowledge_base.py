"""Knowledge Base data models for document storage and retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class KnowledgeBaseCollection(BaseModel):
    """A collection of related documents in the knowledge base."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str
    description: str | None = None
    document_count: int = 0
    total_size_bytes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeBaseDocument(BaseModel):
    """A document stored in the knowledge base."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    collection_id: str
    filename: str
    content_hash: str  # SHA256 hash for deduplication
    file_size_bytes: int
    mime_type: str
    content_preview: str | None = None  # First 500 chars for display
    chunk_count: int = 0  # Number of chunks in vector store
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(BaseModel):
    """A chunk of a document for vector storage."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class KnowledgeBaseSearchResult(BaseModel):
    """A search result from the knowledge base."""

    document_id: str
    collection_id: str
    filename: str
    chunk_content: str
    relevance_score: float
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class KnowledgeBaseSettings(BaseModel):
    """User settings for knowledge base feature."""

    enabled: bool = True
    active_collection_ids: list[str] = Field(default_factory=list)
    search_top_k: int = 5  # Number of results to return
    relevance_threshold: float = 0.7  # Minimum relevance score
    auto_search: bool = True  # Auto-search KB in chat
    search_strategy: str = "hybrid"  # "hybrid", "semantic", "keyword"
