"""Cloud-ready vector store that works locally AND in production.

This implementation automatically detects the environment and uses:
- Local: ChromaDB embedded (for development on weak PCs)
- Cloud: Qdrant Cloud / Weaviate (for production)

No code changes needed - just set environment variables!
"""

from __future__ import annotations

import logging
import os
import time
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VectorBackend(ABC):
    """Abstract base class for vector storage backends."""

    @abstractmethod
    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a document to the vector store."""

    @abstractmethod
    def search(
        self, query: str, k: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar documents."""

    @abstractmethod
    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        """Delete documents matching metadata filters.
        
        Args:
            filter_metadata: Metadata filters to match documents
            
        Returns:
            Number of documents deleted
        """
    
    @abstractmethod
    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by their IDs.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            Number of documents deleted
        """
    
    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""


class ChromaDBBackend(VectorBackend):
    """Local ChromaDB backend - runs on weak PCs, good for development."""

    def __init__(
        self,
        collection_name: str = "FORGE_memory",
        persist_directory: Path | None = None,
    ) -> None:
        """Initialize ChromaDB local vector store with sentence embeddings.

        Sets up ChromaDB persistent client with SentenceTransformer embeddings for local development.
        Auto-creates or loads existing collection from disk.

        Args:
            collection_name: Name of ChromaDB collection, defaults to "FORGE_memory"
            persist_directory: Directory for persistent storage. If None, uses ~/.Forge/memory/chroma

        Returns:
            None

        Side Effects:
            - Creates persist_directory if not exists
            - Loads or creates ChromaDB collection
            - Initializes SentenceTransformer model (downloads if needed)
            - Disables ChromaDB telemetry

        Raises:
            ImportError: If chromadb or sentence-transformers not installed

        Notes:
            - Uses lightweight embedding model (all-MiniLM-L6-v2) for weak PC support
            - Configurable via EMBEDDING_MODEL environment variable
            - Collection uses cosine similarity metric (hnsw:space)
            - Designed for development; use Qdrant/Weaviate for production

        Example:
            >>> backend = ChromaDBBackend()
            >>> # Collection ready for add/search operations
            >>> backend.collection.count()
            0

        """
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            msg = (
                "ChromaDB backend requires: pip install chromadb sentence-transformers\n"
                f"Original error: {e}"
            )
            raise ImportError(
                msg,
            ) from e

        if persist_directory is None:
            persist_directory = Path.home() / ".Forge" / "memory" / "chroma"
        persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Use lightweight model for local development
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(
                f"Loaded ChromaDB collection with {self.collection.count()} documents"
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("Created new ChromaDB collection")

    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert a new document embedding into the local ChromaDB collection."""
        text = self._prepare_text(rationale, content_text)
        embedding = self.model.encode(text, show_progress_bar=False).tolist()

        doc_metadata = {
            "step_id": step_id,
            "role": role,
            "timestamp": time.time(),
            **(metadata or {}),
        }
        if artifact_hash:
            doc_metadata["artifact_hash"] = artifact_hash

        self.collection.add(
            ids=[step_id],
            embeddings=[embedding],
            documents=[text[:2000]],
            metadatas=[doc_metadata],
        )

    def search(
        self, query: str, k: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search the collection for the most similar documents to the query."""
        if self.collection.count() == 0:
            return []

        query_embedding = self.model.encode(query, show_progress_bar=False).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, self.collection.count()),
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )

        return [
            {
                "step_id": results["ids"][0][i],
                "score": 1.0 - results["distances"][0][i],
                "excerpt": results["documents"][0][i],
                **results["metadatas"][0][i],
            }
            for i in range(len(results["ids"][0]))
        ]

    async def async_add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Non-blocking add using a thread to encode and persist."""
        await asyncio.to_thread(
            self.add, step_id, role, artifact_hash, rationale, content_text, metadata
        )

    async def async_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Non-blocking search wrapper."""
        return await asyncio.to_thread(self.search, query, k, filter_metadata)

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        """Delete documents matching metadata filters."""
        try:
            # ChromaDB supports where filters for deletion
            result = self.collection.delete(where=filter_metadata)
            deleted_count = len(result.get("ids", [])) if isinstance(result, dict) else 0
            logger.info(f"Deleted {deleted_count} documents from ChromaDB matching {filter_metadata}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete from ChromaDB: {e}")
            return 0
    
    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by their IDs."""
        try:
            result = self.collection.delete(ids=ids)
            deleted_count = len(result.get("ids", [])) if isinstance(result, dict) else len(ids)
            logger.info(f"Deleted {deleted_count} documents from ChromaDB")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete from ChromaDB: {e}")
            return 0

    def stats(self) -> dict[str, Any]:
        """Return metadata about the local ChromaDB collection and embedding model."""
        return {
            "backend": "ChromaDB (Local)",
            "num_documents": self.collection.count(),
            "embedding_dim": self.model.get_sentence_embedding_dimension(),
        }

    @staticmethod
    def _prepare_text(rationale: str | None, content: str) -> str:
        """Prepare combined text for embedding from rationale and content.

        Args:
            rationale: Step rationale/reasoning (optional)
            content: Step artifact content/output (required)

        Returns:
            str: Combined text with rationale first (if present), then content
                 Content is truncated to 2000 chars for memory efficiency

        Side Effects:
            None - Pure function

        Notes:
            - Rationale provides context for semantic search
            - Content is the primary information being stored
            - 2000 char limit prevents excessive embedding computation
            - Used for vector embedding in ChromaDB

        Example:
            >>> text = ChromaDBBackend._prepare_text(
            ...     "Fixed bug in parsing",
            ...     "def parse_data(): return json.load(...)"
            ... )
            >>> "Fixed bug" in text
            True

        """
        parts = []
        if rationale:
            parts.append(rationale)
        if content:
            parts.append(content[:2000])
        return "\n".join(parts)


class QdrantCloudBackend(VectorBackend):
    """Qdrant Cloud backend - free tier available, production-ready with native async support."""

    def __init__(self, collection_name: str = "FORGE_memory") -> None:
        """Connect to Qdrant Cloud using credentials from the environment and ensure the collection exists."""
        try:
            from qdrant_client import QdrantClient  # type: ignore
            try:
                from qdrant_client import AsyncQdrantClient  # type: ignore
            except Exception:
                AsyncQdrantClient = None  # type: ignore[assignment]
            from qdrant_client.http import models  # type: ignore
        except ImportError as e:
            msg = (
                "Qdrant backend requires: pip install qdrant-client\n"
                f"Original error: {e}"
            )
            raise ImportError(
                msg,
            ) from e

        # Get credentials from environment
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_url or not qdrant_key:
            msg = (
                "Qdrant Cloud requires environment variables:\n"
                "  QDRANT_URL=https://your-cluster.cloud.qdrant.io\n"
                "  QDRANT_API_KEY=your_api_key\n"
                "Sign up for free at: https://cloud.qdrant.io"
            )
            raise ValueError(
                msg,
            )

        # Initialize sync client and async client if available
        self.client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        self.async_client = (
            AsyncQdrantClient(url=qdrant_url, api_key=qdrant_key)
            if "AsyncQdrantClient" in globals() and AsyncQdrantClient is not None
            else None
        )
        self.collection_name = collection_name
        self.models = models

        # Use HuggingFace Inference API for embeddings (free tier available)
        self.hf_api_key = os.getenv("HF_API_KEY")
        if not self.hf_api_key:
            logger.warning("No HF_API_KEY found. Using Qdrant's built-in embeddings.")

        # Check if collection exists, create if not
        try:
            self.client.get_collection(collection_name)
            logger.info(f"Connected to Qdrant Cloud collection: {collection_name}")
        except Exception:
            # Create collection with proper vector configuration
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=768,  # all-mpnet-base-v2 dimension
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"Created new Qdrant Cloud collection: {collection_name}")

    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Insert or update a vector point in the Qdrant collection."""
        text = self._prepare_text(rationale, content_text)
        embedding = self._get_embedding(text)

        payload = {
            "step_id": step_id,
            "role": role,
            "text": text[:2000],
            "timestamp": time.time(),
            **(metadata or {}),
        }
        if artifact_hash:
            payload["artifact_hash"] = artifact_hash

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                self.models.PointStruct(
                    id=hash(step_id) & 0x7FFFFFFF,  # Convert to positive int
                    vector=embedding,
                    payload=payload,
                ),
            ],
        )

    def search(
        self, query: str, k: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a similarity search against the Qdrant collection."""
        query_embedding = self._get_embedding(query)

        # Build filter if provided
        qdrant_filter = None
        if filter_metadata:
            qdrant_filter = self.models.Filter(
                must=[
                    self.models.FieldCondition(
                        key=key,
                        match=self.models.MatchValue(value=value),
                    )
                    for key, value in filter_metadata.items()
                ],
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=k,
            query_filter=qdrant_filter,
        )

        return [
            {
                "step_id": hit.payload.get("step_id"),
                "score": hit.score,
                "excerpt": hit.payload.get("text", ""),
                **{k: v for k, v in hit.payload.items() if k not in ["text"]},
            }
            for hit in results
        ]

    async def async_add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Native async add using AsyncQdrantClient when available; otherwise offload sync call."""
        text = self._prepare_text(rationale, content_text)
        # Use fully async embedding generation with aiohttp
        embedding = await self._get_embedding_async(text)

        payload = {
            "step_id": step_id,
            "role": role,
            "text": text[:2000],
            "timestamp": time.time(),
            **(metadata or {}),
        }
        if artifact_hash:
            payload["artifact_hash"] = artifact_hash

        # If async client available, use it; otherwise offload sync upsert
        if self.async_client is not None:
            await self.async_client.upsert(
                collection_name=self.collection_name,
                points=[
                    self.models.PointStruct(
                        id=hash(step_id) & 0x7FFFFFFF,
                        vector=embedding,
                        payload=payload,
                    ),
                ],
            )
        else:
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[
                    self.models.PointStruct(
                        id=hash(step_id) & 0x7FFFFFFF,
                        vector=embedding,
                        payload=payload,
                    ),
                ],
            )

    async def async_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Native async search using AsyncQdrantClient when available; otherwise offload sync search."""
        # Use fully async embedding generation
        query_embedding = await self._get_embedding_async(query)

        # Build filter if provided
        qdrant_filter = None
        if filter_metadata:
            qdrant_filter = self.models.Filter(
                must=[
                    self.models.FieldCondition(
                        key=key,
                        match=self.models.MatchValue(value=value),
                    )
                    for key, value in filter_metadata.items()
                ],
            )

        # Execute search
        if self.async_client is not None:
            results = await self.async_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k,
                query_filter=qdrant_filter,
            )
        else:
            results = await asyncio.to_thread(
                self.client.search,
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k,
                query_filter=qdrant_filter,
            )

        return [
            {
                "step_id": hit.payload.get("step_id"),
                "score": hit.score,
                "excerpt": hit.payload.get("text", ""),
                **{k: v for k, v in hit.payload.items() if k not in ["text"]},
            }
            for hit in results
        ]

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        """Delete documents matching metadata filters."""
        try:
            # Build Qdrant filter
            qdrant_filter = self.models.Filter(
                must=[
                    self.models.FieldCondition(
                        key=key,
                        match=self.models.MatchValue(value=value),
                    )
                    for key, value in filter_metadata.items()
                ],
            )
            
            # Delete points matching filter
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=self.models.FilterSelector(filter=qdrant_filter),
            )
            deleted_count = result.operation_id if hasattr(result, 'operation_id') else 0
            logger.info(f"Deleted documents from Qdrant matching {filter_metadata}")
            return deleted_count if isinstance(deleted_count, int) else 0
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")
            return 0
    
    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by their IDs."""
        try:
            # Convert string IDs to integer IDs (Qdrant uses int IDs)
            point_ids = [hash(step_id) & 0x7FFFFFFF for step_id in ids]
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=self.models.PointIdsList(
                    points=point_ids,
                ),
            )
            deleted_count = result.operation_id if hasattr(result, 'operation_id') else len(ids)
            logger.info(f"Deleted {len(ids)} documents from Qdrant")
            return deleted_count if isinstance(deleted_count, int) else len(ids)
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")
            return 0

    def stats(self) -> dict[str, Any]:
        """Return summary statistics for the Qdrant collection."""
        info = self.client.get_collection(self.collection_name)
        return {
            "backend": "Qdrant Cloud (Production)",
            "num_documents": info.points_count,
            "embedding_dim": 768,
        }

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding using HuggingFace Inference API or fallback to local.

        Note: This method is CPU/IO-bound and should be called via asyncio.to_thread
        in async contexts to avoid blocking the event loop.
        """
        if self.hf_api_key:
            try:
                import requests

                api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2"
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}
                response = requests.post(
                    api_url, headers=headers, json={"inputs": text[:512]}, timeout=30
                )

                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    f"HF API error: {response.status_code}, falling back to local"
                )
            except Exception as e:
                logger.warning(f"HF API error: {e}, falling back to local")

        # Fallback to local embeddings
        from sentence_transformers import SentenceTransformer

        if not hasattr(self, "_local_model"):
            self._local_model = SentenceTransformer("all-mpnet-base-v2")
        return self._local_model.encode(text[:512], show_progress_bar=False).tolist()

    async def _get_embedding_async(self, text: str) -> list[float]:
        """Async wrapper for embedding generation using aiohttp for HF API calls."""
        if self.hf_api_key:
            try:
                import aiohttp

                api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-mpnet-base-v2"
                headers = {"Authorization": f"Bearer {self.hf_api_key}"}

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url,
                        headers=headers,
                        json={"inputs": text[:512]},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        logger.warning(
                            f"HF API error: {response.status}, falling back to local"
                        )
            except Exception as e:
                logger.warning(f"HF API async error: {e}, falling back to local")

        # Fallback to local embeddings in thread (CPU-bound)
        return await asyncio.to_thread(self._get_embedding_fallback, text)

    def _get_embedding_fallback(self, text: str) -> list[float]:
        """Local fallback for embedding generation (CPU-bound, run in thread)."""
        from sentence_transformers import SentenceTransformer

        if not hasattr(self, "_local_model"):
            self._local_model = SentenceTransformer("all-mpnet-base-v2")
        return self._local_model.encode(text[:512], show_progress_bar=False).tolist()

    @staticmethod
    def _prepare_text(rationale: str | None, content: str) -> str:
        parts = []
        if rationale:
            parts.append(rationale)
        if content:
            parts.append(content[:2000])
        return "\n".join(parts)


class AdaptiveVectorStore:
    """Adaptive vector store that automatically selects the best backend.

    Priority (based on environment):
    1. QDRANT_URL set → Qdrant Cloud (production)
    2. Force local → ChromaDB (development)
    3. Default → ChromaDB (safe fallback)

    Usage:
        # Development (local PC):
        store = AdaptiveVectorStore()  # Uses ChromaDB automatically

        # Production (with env vars):
        # export QDRANT_URL=https://your-cluster.cloud.qdrant.io
        # export QDRANT_API_KEY=your_key
        store = AdaptiveVectorStore()  # Uses Qdrant Cloud automatically
    """

    def __init__(
        self, collection_name: str = "FORGE_memory", force_backend: str | None = None
    ) -> None:
        """Initialize with automatic backend detection.

        Args:
            collection_name: Name of the collection/index
            force_backend: Override detection ("chromadb", "qdrant")

        """
        self.collection_name = collection_name
        self.backend: VectorBackend

        # Determine backend
        if force_backend:
            backend_type = force_backend.lower()
        elif os.getenv("QDRANT_URL"):
            backend_type = "qdrant"
        else:
            backend_type = "chromadb"

        # Initialize backend
        if backend_type == "qdrant":
            try:
                self.backend = QdrantCloudBackend(collection_name)
                logger.info("✅ Using Qdrant Cloud backend (production)")
            except Exception as e:
                logger.warning(f"Failed to initialize Qdrant Cloud: {e}")
                logger.info("Falling back to ChromaDB (local)")
                self.backend = ChromaDBBackend(collection_name)
        else:
            self.backend = ChromaDBBackend(collection_name)
            logger.info("✅ Using ChromaDB backend (development)")

    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a document to the vector store."""
        return self.backend.add(
            step_id, role, artifact_hash, rationale, content_text, metadata
        )

    async def async_add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Async wrapper to add without blocking."""
        if hasattr(self.backend, "async_add"):
            return await self.backend.async_add(
                step_id, role, artifact_hash, rationale, content_text, metadata
            )
        await asyncio.to_thread(
            self.add, step_id, role, artifact_hash, rationale, content_text, metadata
        )

    def search(
        self, query: str, k: int = 5, filter_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar documents."""
        return self.backend.search(query, k, filter_metadata)

    async def async_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Async wrapper for search."""
        if hasattr(self.backend, "async_search"):
            return await self.backend.async_search(query, k, filter_metadata)
        return await asyncio.to_thread(self.search, query, k, filter_metadata)

    def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> int:
        """Delete documents matching metadata filters."""
        return self.backend.delete_by_metadata(filter_metadata)
    
    def delete_by_ids(self, ids: list[str]) -> int:
        """Delete documents by their IDs."""
        return self.backend.delete_by_ids(ids)

    def stats(self) -> dict[str, Any]:
        """Get statistics about the vector store."""
        return self.backend.stats()


# Backward compatibility wrapper for existing MetaSOP code
class VectorMemoryStore:
    """Backward compatible wrapper that uses adaptive cloud-ready backend."""

    def __init__(self, dim: int = 256, max_records: int | None = 500) -> None:
        """Initialize the legacy facade while delegating storage to the adaptive backend."""
        logger.info(
            "Initializing cloud-ready vector store (ignoring legacy params: dim=%d, max_records=%s)",
            dim,
            max_records,
        )
        self._store = AdaptiveVectorStore()

    def add(
        self,
        step_id: str,
        role: str,
        artifact_hash: str | None,
        rationale: str | None,
        content_text: str,
    ) -> None:
        """Add a record (backward compatible interface)."""
        self._store.add(step_id, role, artifact_hash, rationale, content_text)

    def search(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        """Search for similar records (backward compatible interface)."""
        return self._store.search(query, k)

    def stats(self) -> dict[str, Any]:
        """Get statistics (backward compatible interface)."""
        return self._store.stats()


__all__ = [
    "AdaptiveVectorStore",
    "ChromaDBBackend",
    "QdrantCloudBackend",
    "VectorMemoryStore",
]
