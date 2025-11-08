"""API routes for Knowledge Base management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from forge.knowledge_base import KnowledgeBaseManager
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
    KnowledgeBaseSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


# Request/Response models

class CreateCollectionRequest(BaseModel):
    """Request to create a new collection."""

    name: str
    description: str | None = None


class UpdateCollectionRequest(BaseModel):
    """Request to update a collection."""

    name: str | None = None
    description: str | None = None


class SearchRequest(BaseModel):
    """Request to search the knowledge base."""

    query: str
    collection_ids: list[str] | None = None
    top_k: int = 5
    relevance_threshold: float = 0.7


class CollectionResponse(BaseModel):
    """Response containing collection data."""

    id: str
    name: str
    description: str | None
    document_count: int
    total_size_bytes: int
    total_size_mb: float
    created_at: str
    updated_at: str


class DocumentResponse(BaseModel):
    """Response containing document data."""

    id: str
    collection_id: str
    filename: str
    file_size_bytes: int
    file_size_kb: float
    mime_type: str
    content_preview: str | None
    chunk_count: int
    uploaded_at: str


class SearchResultResponse(BaseModel):
    """Response containing search result."""

    document_id: str
    collection_id: str
    filename: str
    chunk_content: str
    relevance_score: float


# Helper functions

def _get_kb_manager(user_id: str = "default") -> KnowledgeBaseManager:
    """Create and return a KnowledgeBaseManager instance for a user.

    Factory function to instantiate a knowledge base manager scoped to a specific
    user. Enables isolation of knowledge bases across multiple users in the system.

    Args:
        user_id: User identifier for the knowledge base scope (default: "default")

    Returns:
        KnowledgeBaseManager: Initialized manager for the specified user

    Raises:
        ValueError: If user_id is empty string

    Example:
        kb_manager = _get_kb_manager("user123")
        collections = kb_manager.list_collections()

    """
    return KnowledgeBaseManager(user_id=user_id)


def _collection_to_response(collection: KnowledgeBaseCollection) -> CollectionResponse:
    """Convert KnowledgeBaseCollection model to API response format.

    Transforms internal collection data model into a response object suitable
    for HTTP endpoints, converting timestamps to ISO format and calculating
    size in megabytes from bytes.

    Args:
        collection: Internal KnowledgeBaseCollection model

    Returns:
        CollectionResponse with formatted fields ready for JSON serialization

    Example:
        collection = kb_manager.get_collection("coll123")
        response = _collection_to_response(collection)
        # response.total_size_mb is calculated from bytes

    """
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        document_count=collection.document_count,
        total_size_bytes=collection.total_size_bytes,
        total_size_mb=round(collection.total_size_bytes / (1024 * 1024), 2),
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


def _document_to_response(document: KnowledgeBaseDocument) -> DocumentResponse:
    """Convert KnowledgeBaseDocument model to API response format.

    Transforms internal document data model into a response object suitable
    for HTTP endpoints, converting timestamps to ISO format and calculating
    size in kilobytes from bytes.

    Args:
        document: Internal KnowledgeBaseDocument model

    Returns:
        DocumentResponse with formatted fields ready for JSON serialization

    Example:
        doc = kb_manager.get_document("doc123")
        response = _document_to_response(doc)
        # response.file_size_kb is calculated from bytes

    """
    return DocumentResponse(
        id=document.id,
        collection_id=document.collection_id,
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        file_size_kb=round(document.file_size_bytes / 1024, 2),
        mime_type=document.mime_type,
        content_preview=document.content_preview,
        chunk_count=document.chunk_count,
        uploaded_at=document.uploaded_at.isoformat(),
    )


def _search_result_to_response(result: KnowledgeBaseSearchResult) -> SearchResultResponse:
    """Convert KnowledgeBaseSearchResult to API response format.

    Transforms internal search result into a response object for HTTP endpoints,
    rounding the relevance score to 3 decimal places for clarity.

    Args:
        result: Internal KnowledgeBaseSearchResult from search operation

    Returns:
        SearchResultResponse with relevance_score rounded to 3 decimals

    Example:
        results = kb_manager.search("query")
        response = [_search_result_to_response(r) for r in results]

    """
    return SearchResultResponse(
        document_id=result.document_id,
        collection_id=result.collection_id,
        filename=result.filename,
        chunk_content=result.chunk_content,
        relevance_score=round(result.relevance_score, 3),
    )


# Collection endpoints

@router.post("/collections", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CreateCollectionRequest,
    user_id: str = "default",
) -> CollectionResponse:
    """Create a new knowledge base collection."""
    try:
        kb_manager = _get_kb_manager(user_id)
        collection = kb_manager.create_collection(
            name=request.name,
            description=request.description,
        )
        logger.info(f"Created collection: {collection.name} (ID: {collection.id})")
        return _collection_to_response(collection)
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}",
        )


@router.get("/collections", response_model=list[CollectionResponse])
async def list_collections(user_id: str = "default") -> list[CollectionResponse]:
    """List all collections for the user."""
    try:
        kb_manager = _get_kb_manager(user_id)
        collections = kb_manager.list_collections()
        return [_collection_to_response(c) for c in collections]
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        )


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    user_id: str = "default",
) -> CollectionResponse:
    """Get a collection by ID."""
    try:
        kb_manager = _get_kb_manager(user_id)
        collection = kb_manager.get_collection(collection_id)
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )
        return _collection_to_response(collection)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection: {str(e)}",
        )


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    user_id: str = "default",
) -> CollectionResponse:
    """Update a collection."""
    try:
        kb_manager = _get_kb_manager(user_id)
        collection = kb_manager.update_collection(
            collection_id=collection_id,
            name=request.name,
            description=request.description,
        )
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )
        logger.info(f"Updated collection: {collection.name} (ID: {collection.id})")
        return _collection_to_response(collection)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update collection: {str(e)}",
        )


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: str,
    user_id: str = "default",
):
    """Delete a collection and all its documents."""
    try:
        kb_manager = _get_kb_manager(user_id)
        success = kb_manager.delete_collection(collection_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )
        logger.info(f"Deleted collection: {collection_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}",
        )


# Document endpoints

@router.post("/collections/{collection_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    collection_id: str,
    file: UploadFile = File(...),
    user_id: str = "default",
) -> DocumentResponse:
    """Upload a document to a collection."""
    try:
        # Validate file size (max 10MB for MVP)
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        content = await file.read()
        
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024 * 1024)}MB",
            )

        # Decode content (assume UTF-8 text for MVP)
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a valid UTF-8 text file",
            )

        # Add document
        kb_manager = _get_kb_manager(user_id)
        document = kb_manager.add_document(
            collection_id=collection_id,
            filename=file.filename or "untitled",
            content=text_content,
            mime_type=file.content_type or "text/plain",
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_id} not found",
            )

        logger.info(f"Uploaded document: {document.filename} to collection {collection_id}")
        return _document_to_response(document)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}",
        )


@router.get("/collections/{collection_id}/documents", response_model=list[DocumentResponse])
async def list_documents(
    collection_id: str,
    user_id: str = "default",
) -> list[DocumentResponse]:
    """List all documents in a collection."""
    try:
        kb_manager = _get_kb_manager(user_id)
        documents = kb_manager.list_documents(collection_id)
        return [_document_to_response(d) for d in documents]
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user_id: str = "default",
) -> DocumentResponse:
    """Get a document by ID."""
    try:
        kb_manager = _get_kb_manager(user_id)
        document = kb_manager.get_document(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )
        return _document_to_response(document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document: {str(e)}",
        )


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user_id: str = "default",
):
    """Delete a document."""
    try:
        kb_manager = _get_kb_manager(user_id)
        success = kb_manager.delete_document(document_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )
        logger.info(f"Deleted document: {document_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


# Search endpoint

@router.post("/search", response_model=list[SearchResultResponse])
async def search_knowledge_base(
    request: SearchRequest,
    user_id: str = "default",
) -> list[SearchResultResponse]:
    """Search the knowledge base."""
    try:
        kb_manager = _get_kb_manager(user_id)
        results = kb_manager.search(
            query=request.query,
            collection_ids=request.collection_ids,
            top_k=request.top_k,
            relevance_threshold=request.relevance_threshold,
        )
        return [_search_result_to_response(r) for r in results]
    except Exception as e:
        logger.error(f"Failed to search knowledge base: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search knowledge base: {str(e)}",
        )


# Stats endpoint

@router.get("/stats")
async def get_stats(user_id: str = "default") -> dict[str, Any]:
    """Get knowledge base statistics."""
    try:
        kb_manager = _get_kb_manager(user_id)
        return kb_manager.get_stats()
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {str(e)}",
        )

