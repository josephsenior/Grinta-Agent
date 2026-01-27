"""Knowledge Base module for document storage and retrieval."""

from forge.knowledge_base.manager import KnowledgeBaseManager
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
    KnowledgeBaseSearchResult,
    KnowledgeBaseSettings,
)

__all__ = [
    "KnowledgeBaseManager",
    "KnowledgeBaseCollection",
    "KnowledgeBaseDocument",
    "KnowledgeBaseSearchResult",
    "KnowledgeBaseSettings",
]
