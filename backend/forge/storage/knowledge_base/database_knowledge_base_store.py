"""Database-based knowledge base storage implementation using PostgreSQL.

Stores knowledge base collections and documents in PostgreSQL for production use.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any

import asyncpg
from asyncpg import Pool

from forge.core.logger import forge_logger as logger
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
)

# Global connection pool (reuse from user store)
_db_pool: Pool | None = None


async def get_kb_db_pool() -> Pool:
    """Get or create database connection pool for knowledge base.
    
    Reuses the same pool as user store for efficiency.
    """
    global _db_pool
    if _db_pool is None:
        # Try to reuse user store pool if available
        try:
            from forge.storage.user.database_user_store import get_db_pool
            _db_pool = await get_db_pool()
            logger.info("Reusing database connection pool for knowledge base")
        except Exception:
            # Create new pool if user store pool not available
            host = os.getenv("DB_HOST", "localhost")
            port = int(os.getenv("DB_PORT", "5432"))
            database = os.getenv("DB_NAME", "forge")
            user = os.getenv("DB_USER", "forge")
            password = os.getenv("DB_PASSWORD", "forge")
            
            dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            _db_pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
                command_timeout=60,
            )
            logger.info(f"Created database connection pool for knowledge base: {database}@{host}:{port}")
    
    return _db_pool


class DatabaseKnowledgeBaseStore:
    """PostgreSQL-based implementation of knowledge base storage."""

    def __init__(self, pool: Pool | None = None):
        """Initialize database knowledge base store.

        Args:
            pool: Optional asyncpg connection pool (will create one if not provided)
        """
        self._pool = pool

    async def _get_pool(self) -> Pool:
        """Get database connection pool."""
        if self._pool:
            return self._pool
        return await get_kb_db_pool()

    async def create_collection(
        self, user_id: str, name: str, description: str | None = None
    ) -> KnowledgeBaseCollection:
        """Create a new collection."""
        pool = await self._get_pool()
        collection = KnowledgeBaseCollection(
            user_id=user_id,
            name=name,
            description=description,
            document_count=0,
            total_size_bytes=0,
        )
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO knowledge_base_collections (
                        id, user_id, name, description, document_count,
                        total_size_bytes, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    collection.id,
                    collection.user_id,
                    collection.name,
                    collection.description,
                    collection.document_count,
                    collection.total_size_bytes,
                    collection.created_at,
                    collection.updated_at,
                )
        
        logger.info(f"Created collection in database: {collection.name} (ID: {collection.id})")
        return collection

    async def get_collection(self, collection_id: str) -> KnowledgeBaseCollection | None:
        """Get a collection by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM knowledge_base_collections WHERE id = $1",
                collection_id,
            )
            if not row:
                return None
            return self._row_to_collection(row)

    async def list_collections(self, user_id: str) -> list[KnowledgeBaseCollection]:
        """List all collections for a user."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM knowledge_base_collections WHERE user_id = $1 ORDER BY created_at DESC",
                user_id,
            )
            return [self._row_to_collection(row) for row in rows]

    async def update_collection(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> KnowledgeBaseCollection | None:
        """Update a collection."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Build update query dynamically
                updates = []
                params: list[Any] = []
                param_idx = 1
                
                if name is not None:
                    updates.append(f"name = ${param_idx}")
                    params.append(name)
                    param_idx += 1
                
                if description is not None:
                    updates.append(f"description = ${param_idx}")
                    params.append(description)
                    param_idx += 1
                
                if not updates:
                    # No updates, just fetch and return
                    row = await conn.fetchrow(
                        "SELECT * FROM knowledge_base_collections WHERE id = $1",
                        collection_id,
                    )
                    return self._row_to_collection(row) if row else None
                
                updates.append(f"updated_at = ${param_idx}")
                params.append(datetime.utcnow())  # asyncpg handles datetime conversion
                param_idx += 1
                
                params.append(collection_id)
                
                query = f"""
                    UPDATE knowledge_base_collections
                    SET {', '.join(updates)}
                    WHERE id = ${param_idx}
                    RETURNING *
                """
                
                row = await conn.fetchrow(query, *params)
                if not row:
                    return None
                
                return self._row_to_collection(row)

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and all its documents."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Delete documents first (CASCADE should handle this, but explicit is better)
                await conn.execute(
                    "DELETE FROM knowledge_base_documents WHERE collection_id = $1",
                    collection_id,
                )
                
                # Delete collection
                result = await conn.execute(
                    "DELETE FROM knowledge_base_collections WHERE id = $1",
                    collection_id,
                )
                
                deleted = result == "DELETE 1"
                if deleted:
                    logger.info(f"Deleted collection from database: {collection_id}")
                return deleted

    async def add_document(self, document: KnowledgeBaseDocument) -> KnowledgeBaseDocument:
        """Add a document to a collection."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO knowledge_base_documents (
                        id, collection_id, filename, content_hash, file_size_bytes,
                        mime_type, content_preview, chunk_count, uploaded_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    document.id,
                    document.collection_id,
                    document.filename,
                    document.content_hash,
                    document.file_size_bytes,
                    document.mime_type,
                    document.content_preview,
                    document.chunk_count,
                    document.uploaded_at,
                )
                
                # Update collection stats
                await conn.execute(
                    """
                    UPDATE knowledge_base_collections
                    SET document_count = document_count + 1,
                        total_size_bytes = total_size_bytes + $1,
                        updated_at = $2
                    WHERE id = $3
                    """,
                    document.file_size_bytes,
                    datetime.utcnow(),
                    document.collection_id,
                )
        
        logger.info(f"Added document to database: {document.filename} (ID: {document.id})")
        return document

    async def get_document(self, document_id: str) -> KnowledgeBaseDocument | None:
        """Get a document by ID."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM knowledge_base_documents WHERE id = $1",
                document_id,
            )
            if not row:
                return None
            return self._row_to_document(row)

    async def list_documents(self, collection_id: str) -> list[KnowledgeBaseDocument]:
        """List all documents in a collection."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM knowledge_base_documents WHERE collection_id = $1 ORDER BY uploaded_at DESC",
                collection_id,
            )
            return [self._row_to_document(row) for row in rows]

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Get document first to update collection stats
                doc_row = await conn.fetchrow(
                    "SELECT collection_id, file_size_bytes FROM knowledge_base_documents WHERE id = $1",
                    document_id,
                )
                
                if not doc_row:
                    return False
                
                collection_id = doc_row["collection_id"]
                file_size = doc_row["file_size_bytes"]
                
                # Delete document
                result = await conn.execute(
                    "DELETE FROM knowledge_base_documents WHERE id = $1",
                    document_id,
                )
                
                if result == "DELETE 1":
                    # Update collection stats
                    await conn.execute(
                        """
                        UPDATE knowledge_base_collections
                        SET document_count = document_count - 1,
                            total_size_bytes = total_size_bytes - $1,
                            updated_at = $2
                        WHERE id = $3
                        """,
                        file_size,
                        datetime.utcnow(),
                        collection_id,
                    )
                    logger.info(f"Deleted document from database: {document_id}")
                    return True
                
                return False

    async def get_document_by_hash(self, content_hash: str) -> KnowledgeBaseDocument | None:
        """Find a document by its content hash (for deduplication)."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM knowledge_base_documents WHERE content_hash = $1",
                content_hash,
            )
            if not row:
                return None
            return self._row_to_document(row)

    def _row_to_collection(self, row: asyncpg.Record) -> KnowledgeBaseCollection:
        """Convert database row to KnowledgeBaseCollection."""
        return KnowledgeBaseCollection(
            id=str(row["id"]),
            user_id=str(row["user_id"]),
            name=row["name"],
            description=row["description"],
            document_count=row["document_count"],
            total_size_bytes=row["total_size_bytes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_document(self, row: asyncpg.Record) -> KnowledgeBaseDocument:
        """Convert database row to KnowledgeBaseDocument."""
        return KnowledgeBaseDocument(
            id=str(row["id"]),
            collection_id=str(row["collection_id"]),
            filename=row["filename"],
            content_hash=row["content_hash"],
            file_size_bytes=row["file_size_bytes"],
            mime_type=row["mime_type"],
            content_preview=row.get("content_preview"),
            chunk_count=row["chunk_count"],
            uploaded_at=row["uploaded_at"],
        )

