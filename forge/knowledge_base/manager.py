"""Knowledge Base Manager - Integrates document storage with vector search."""

from __future__ import annotations

import hashlib
import logging
import asyncio
from typing import Any

from forge.memory.enhanced_vector_store import EnhancedVectorStore
from forge.storage.data_models.knowledge_base import (
    DocumentChunk,
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
    KnowledgeBaseSearchResult,
)
from forge.storage.knowledge_base_store import get_knowledge_base_store

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Manages knowledge base collections, documents, and vector search."""

    def __init__(self, user_id: str):
        """Initialize the knowledge base manager.

        Args:
            user_id: The user ID for this knowledge base

        """
        self.user_id = user_id
        self.store = get_knowledge_base_store()
        self._vector_stores: dict[str, EnhancedVectorStore] = {}

    def _get_vector_store(self, collection_id: str) -> EnhancedVectorStore:
        """Get or create a vector store for a collection."""
        if collection_id not in self._vector_stores:
            self._vector_stores[collection_id] = EnhancedVectorStore(
                collection_name=f"kb_{collection_id}",
                enable_cache=True,
                enable_reranking=True,
            )
        return self._vector_stores[collection_id]

    # Collection operations

    def create_collection(
        self, name: str, description: str | None = None
    ) -> KnowledgeBaseCollection:
        """Create a new knowledge base collection."""
        return self.store.create_collection(
            user_id=self.user_id,
            name=name,
            description=description,
        )

    def get_collection(self, collection_id: str) -> KnowledgeBaseCollection | None:
        """Get a collection by ID."""
        collection = self.store.get_collection(collection_id)
        if collection and collection.user_id != self.user_id:
            return None  # Access control
        return collection

    def list_collections(self) -> list[KnowledgeBaseCollection]:
        """List all collections for this user."""
        return self.store.list_collections(self.user_id)

    def update_collection(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBaseCollection | None:
        """Update a collection."""
        collection = self.get_collection(collection_id)
        if not collection:
            return None
        return self.store.update_collection(collection_id, name, description)

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and all its documents."""
        collection = self.get_collection(collection_id)
        if not collection:
            return False

        # Delete from vector store
        # Note: EnhancedVectorStore doesn't have a delete_collection method yet
        # but we can handle this by just removing our reference
        self._vector_stores.pop(collection_id, None)

        return self.store.delete_collection(collection_id)

    # Document operations

    def add_document(
        self,
        collection_id: str,
        filename: str,
        content: str,
        mime_type: str = "text/plain",
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeBaseDocument | None:
        """Add a document to a collection.

        Args:
            collection_id: The collection to add to
            filename: The document filename
            content: The document content
            mime_type: MIME type of the document
            metadata: Optional metadata

        Returns:
            The created document, or None if collection doesn't exist

        """
        # Verify collection exists and user has access
        collection = self.get_collection(collection_id)
        if not collection:
            logger.error(f"Collection {collection_id} not found or access denied")
            return None

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Check if document already exists
        existing = self.store.get_document_by_hash(content_hash)
        if existing and existing.collection_id == collection_id:
            logger.info(f"Document with hash {content_hash} already exists")
            return existing

        # Create document
        document = KnowledgeBaseDocument(
            collection_id=collection_id,
            filename=filename,
            content_hash=content_hash,
            file_size_bytes=len(content.encode()),
            mime_type=mime_type,
            content_preview=content[:500] if len(content) > 500 else content,
        )

        # Chunk the content
        chunks = self._chunk_content(content, document.id, metadata)
        document.chunk_count = len(chunks)

        # Store document
        document = self.store.add_document(document)

        # Add chunks to vector store
        vector_store = self._get_vector_store(collection_id)
        for chunk in chunks:
            vector_store.add(
                step_id=chunk.id,
                role="document",
                artifact_hash=document.content_hash,
                rationale=f"Document: {filename}",
                content_text=chunk.content,
                metadata={
                    "document_id": document.id,
                    "collection_id": collection_id,
                    "filename": filename,
                    "chunk_index": chunk.chunk_index,
                    **(chunk.metadata or {}),
                },
            )

        logger.info(
            f"Added document '{filename}' to collection {collection_id} "
            f"({len(chunks)} chunks)"
        )
        return document

    async def async_add_document(
        self,
        collection_id: str,
        filename: str,
        content: str,
        mime_type: str = "text/plain",
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeBaseDocument | None:
        """Async wrapper for adding a document without blocking.

        Performs chunking and vector insertion in a thread to keep the event loop responsive.
        """
        return await asyncio.to_thread(
            self.add_document,
            collection_id,
            filename,
            content,
            mime_type,
            metadata,
        )

    def _chunk_content(
        self,
        content: str,
        document_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Split content into chunks for vector storage.

        Uses a simple sliding window approach with overlap.
        """
        chunk_size = 1000  # characters
        chunk_overlap = 200  # overlap between chunks

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = start + chunk_size
            chunk_text = content[start:end]

            if chunk_text.strip():  # Skip empty chunks
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    metadata=metadata or {},
                )
                chunks.append(chunk)
                chunk_index += 1

            start = end - chunk_overlap

        return chunks

    def get_document(self, document_id: str) -> KnowledgeBaseDocument | None:
        """Get a document by ID."""
        document = self.store.get_document(document_id)
        if document:
            # Verify user has access
            collection = self.get_collection(document.collection_id)
            if not collection:
                return None
        return document

    def list_documents(self, collection_id: str) -> list[KnowledgeBaseDocument]:
        """List all documents in a collection."""
        collection = self.get_collection(collection_id)
        if not collection:
            return []
        return self.store.list_documents(collection_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from its collection."""
        document = self.get_document(document_id)
        if not document:
            return False

        # Note: We don't delete from vector store yet as EnhancedVectorStore
        # doesn't have a delete method. The chunks will remain but won't be
        # associated with any document metadata.

        return self.store.delete_document(document_id)

    # Search operations

    def search(
        self,
        query: str,
        collection_ids: list[str] | None = None,
        top_k: int = 5,
        relevance_threshold: float = 0.7,
    ) -> list[KnowledgeBaseSearchResult]:
        """Search across knowledge base collections.

        Args:
            query: The search query
            collection_ids: List of collection IDs to search (or None for all)
            top_k: Number of results to return per collection
            relevance_threshold: Minimum relevance score (0-1)

        Returns:
            List of search results, sorted by relevance

        """
        if collection_ids is None:
            collections = self.list_collections()
            collection_ids = [c.id for c in collections]

        all_results = []

        for collection_id in collection_ids:
            # Verify access
            collection = self.get_collection(collection_id)
            if not collection:
                continue

            # Search in vector store
            vector_store = self._get_vector_store(collection_id)
            try:
                raw_results = vector_store.search(
                    query=query,
                    k=top_k,
                    filter_metadata={"collection_id": collection_id},
                )

                # Convert to search results
                for result in raw_results:
                    score = result.get("score", 0.0)
                    if score < relevance_threshold:
                        continue

                    search_result = KnowledgeBaseSearchResult(
                        document_id=result.get("metadata", {}).get("document_id", ""),
                        collection_id=collection_id,
                        filename=result.get("metadata", {}).get("filename", ""),
                        chunk_content=result.get("content", ""),
                        relevance_score=score,
                        metadata=result.get("metadata", {}),
                    )
                    all_results.append(search_result)

            except Exception as e:
                logger.error(f"Error searching collection {collection_id}: {e}")
                continue

        # Sort by relevance
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Return top results
        return all_results[:top_k]

    async def async_search(
        self,
        query: str,
        collection_ids: list[str] | None = None,
        top_k: int = 5,
        relevance_threshold: float = 0.7,
    ) -> list[KnowledgeBaseSearchResult]:
        """Async wrapper for search, offloading blocking work to a thread."""
        return await asyncio.to_thread(
            self.search,
            query,
            collection_ids,
            top_k,
            relevance_threshold,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        collections = self.list_collections()
        total_docs = sum(c.document_count for c in collections)
        total_size = sum(c.total_size_bytes for c in collections)

        return {
            "total_collections": len(collections),
            "total_documents": total_docs,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "collections": [
                {
                    "id": c.id,
                    "name": c.name,
                    "document_count": c.document_count,
                    "size_mb": round(c.total_size_bytes / (1024 * 1024), 2),
                }
                for c in collections
            ],
        }
