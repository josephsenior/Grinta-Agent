"""Tests for `forge.knowledge_base.manager.KnowledgeBaseManager`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from forge.knowledge_base import manager as kb_manager_module
from forge.knowledge_base.manager import KnowledgeBaseManager
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
)


@dataclass
class StubVectorStore:
    """Minimal stand-in for EnhancedVectorStore used in tests."""

    collection_id: str
    enable_cache: bool = True
    enable_reranking: bool = True

    def __post_init__(self) -> None:
        self.add_calls: list[dict[str, Any]] = []
        self.search_calls: list[dict[str, Any]] = []
        self._search_results: list[dict[str, Any]] = []

    def add(self, **kwargs: Any) -> None:
        self.add_calls.append(kwargs)

    def search(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.search_calls.append(kwargs)
        return list(self._search_results)

    def set_search_results(self, results: list[dict[str, Any]]) -> None:
        self._search_results = results


class StubStore:
    """In-memory shim for the knowledge base store API."""

    def __init__(self) -> None:
        self.collections: dict[str, KnowledgeBaseCollection] = {}
        self.documents: dict[str, KnowledgeBaseDocument] = {}
        self.collection_documents: dict[str, list[str]] = {}
        self.documents_by_hash: dict[str, KnowledgeBaseDocument] = {}

    # Collection operations -------------------------------------------------
    def create_collection(
        self, user_id: str, name: str, description: str | None = None
    ) -> KnowledgeBaseCollection:
        collection = KnowledgeBaseCollection(
            user_id=user_id, name=name, description=description
        )
        self.collections[collection.id] = collection
        self.collection_documents[collection.id] = []
        return collection

    def get_collection(self, collection_id: str) -> KnowledgeBaseCollection | None:
        return self.collections.get(collection_id)

    def list_collections(self, user_id: str) -> list[KnowledgeBaseCollection]:
        return [c for c in self.collections.values() if c.user_id == user_id]

    def update_collection(
        self,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
    ):
        collection = self.collections.get(collection_id)
        if not collection:
            return None
        if name is not None:
            collection.name = name
        if description is not None:
            collection.description = description
        return collection

    def delete_collection(self, collection_id: str) -> bool:
        if collection_id not in self.collections:
            return False
        for doc_id in self.collection_documents.get(collection_id, []):
            self.documents.pop(doc_id, None)
        self.collection_documents.pop(collection_id, None)
        self.collections.pop(collection_id)
        return True

    # Document operations ---------------------------------------------------
    def add_document(self, document: KnowledgeBaseDocument) -> KnowledgeBaseDocument:
        self.documents[document.id] = document
        self.collection_documents.setdefault(document.collection_id, []).append(
            document.id
        )
        self.documents_by_hash[document.content_hash] = document

        collection = self.collections[document.collection_id]
        collection.document_count += 1
        collection.total_size_bytes += document.file_size_bytes
        return document

    def get_document(self, document_id: str) -> KnowledgeBaseDocument | None:
        return self.documents.get(document_id)

    def list_documents(self, collection_id: str) -> list[KnowledgeBaseDocument]:
        doc_ids = self.collection_documents.get(collection_id, [])
        return [
            self.documents[doc_id] for doc_id in doc_ids if doc_id in self.documents
        ]

    def delete_document(self, document_id: str) -> bool:
        document = self.documents.pop(document_id, None)
        if not document:
            return False
        doc_list = self.collection_documents.get(document.collection_id, [])
        if document_id in doc_list:
            doc_list.remove(document_id)
        collection = self.collections.get(document.collection_id)
        if collection:
            collection.document_count -= 1
            collection.total_size_bytes -= document.file_size_bytes
        self.documents_by_hash.pop(document.content_hash, None)
        return True

    def get_document_by_hash(self, content_hash: str) -> KnowledgeBaseDocument | None:
        return self.documents_by_hash.get(content_hash)


def create_manager(monkeypatch: pytest.MonkeyPatch):
    """Create KnowledgeBaseManager with stubbed dependencies for testing."""
    store = StubStore()
    vector_stores: dict[str, StubVectorStore] = {}

    def fake_get_store():
        return store

    def fake_vector_store(**kwargs):
        collection_name = kwargs.get("collection_name", "")
        collection_id = collection_name.removeprefix("kb_")
        vector = StubVectorStore(collection_id=collection_id)
        vector_stores[collection_id] = vector
        return vector

    monkeypatch.setattr(kb_manager_module, "get_knowledge_base_store", fake_get_store)
    monkeypatch.setattr(kb_manager_module, "EnhancedVectorStore", fake_vector_store)
    manager = KnowledgeBaseManager(user_id="user-1")
    return manager, store, vector_stores


def test_create_and_list_collections(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)

    collection = kb.create_collection("Docs")
    assert collection in store.collections.values()

    listed = kb.list_collections()
    assert [c.id for c in listed] == [collection.id]

    updated = kb.update_collection(collection.id, name="New Name", description="desc")
    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "desc"


def test_delete_collection_removes_vector_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    coll = kb.create_collection("Coll")

    store.collections[coll.id] = coll
    vector = kb._get_vector_store(coll.id)
    assert vector_stores[coll.id] is vector

    assert kb.delete_collection(coll.id) is True
    assert coll.id not in kb._vector_stores


def test_add_document_chunks_and_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    collection = kb.create_collection("Docs")

    content = "A" * 1200  # ensures two chunks with overlap
    document = kb.add_document(collection.id, filename="doc.txt", content=content)
    assert document is not None
    assert document.chunk_count == 2
    assert store.get_document(document.id) is document

    vector_store = vector_stores[collection.id]
    assert len(vector_store.add_calls) == 2
    assert {call["metadata"]["chunk_index"] for call in vector_store.add_calls} == {
        0,
        1,
    }

    # Deduplication with identical content hash should return the original document
    duplicate = kb.add_document(
        collection.id, filename="duplicate.txt", content=content
    )
    assert duplicate is document


def test_add_document_missing_collection_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kb, store, _ = create_manager(monkeypatch)
    assert kb.add_document("missing", filename="a.txt", content="hi") is None


def test_search_returns_ranked_results(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    first = kb.create_collection("First")
    second = kb.create_collection("Second")

    kb._get_vector_store(first.id)
    kb._get_vector_store(second.id)

    # Prime vector store search results
    vector_stores[first.id].set_search_results(
        [
            {
                "score": 0.9,
                "metadata": {"document_id": "doc-1", "filename": "one"},
                "content": "chunk-one",
            },
            {
                "score": 0.6,
                "metadata": {"document_id": "doc-2", "filename": "two"},
                "content": "chunk-two",
            },
        ]
    )
    vector_stores[second.id].set_search_results(
        [
            {
                "score": 0.8,
                "metadata": {"document_id": "doc-3", "filename": "three"},
                "content": "chunk-three",
            }
        ]
    )

    results = kb.search("query", top_k=2, relevance_threshold=0.7)
    assert len(results) == 2
    assert results[0].document_id == "doc-1"
    assert results[1].document_id == "doc-3"


def test_update_collection_missing_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kb, store, _ = create_manager(monkeypatch)
    assert kb.update_collection("missing", name="noop") is None


def test_get_list_and_delete_document(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)
    collection = kb.create_collection("Docs")

    document = kb.add_document(collection.id, filename="doc.txt", content="hello")
    assert document is not None

    retrieved = kb.get_document(document.id)
    assert retrieved is document

    docs = kb.list_documents(collection.id)
    assert [doc.id for doc in docs] == [document.id]

    assert kb.delete_document(document.id) is True
    assert kb.get_document(document.id) is None


def test_get_document_respects_user_access(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)
    other_collection = store.create_collection(user_id="other", name="Other")
    store.collections[other_collection.id] = other_collection

    foreign_doc = KnowledgeBaseDocument(
        collection_id=other_collection.id,
        filename="other.txt",
        content_hash="hash",
        file_size_bytes=10,
        mime_type="text/plain",
    )
    store.add_document(foreign_doc)
    assert kb.get_document(foreign_doc.id) is None


def test_get_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    collection = kb.create_collection("Stats")
    kb.add_document(collection.id, filename="doc.txt", content="data")

    stats = kb.get_stats()
    assert stats["total_collections"] == 1
    assert stats["total_documents"] == 1
    assert stats["collections"][0]["document_count"] == 1


def test_search_handles_vector_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    collection = kb.create_collection("Error")
    vector = kb._get_vector_store(collection.id)

    def failing_search(**kwargs):
        raise RuntimeError("boom")

    vector.search = failing_search  # type: ignore[assignment]
    results = kb.search("query", collection_ids=[collection.id])
    assert results == []


def test_delete_collection_missing_or_foreign(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)
    assert kb.delete_collection("does-not-exist") is False

    foreign = store.create_collection(user_id="other", name="Other")
    store.collections[foreign.id] = foreign
    assert kb.delete_collection(foreign.id) is False


def test_list_documents_requires_access(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)
    collection = store.create_collection(user_id="other", name="Other")
    store.collections[collection.id] = collection

    assert kb.list_documents(collection.id) == []


def test_delete_document_missing_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    kb, store, _ = create_manager(monkeypatch)
    collection = kb.create_collection("Docs")
    document = kb.add_document(collection.id, filename="doc.txt", content="hello")
    assert document is not None

    assert kb.delete_document("unknown-id") is False

    foreign_collection = store.create_collection(user_id="other", name="Other")
    foreign_doc = KnowledgeBaseDocument(
        collection_id=foreign_collection.id,
        filename="foreign.txt",
        content_hash="hash",
        file_size_bytes=4,
        mime_type="text/plain",
    )
    store.add_document(foreign_doc)
    assert kb.delete_document(foreign_doc.id) is False


def test_search_skips_collections_without_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kb, store, vector_stores = create_manager(monkeypatch)
    owned = kb.create_collection("Owned")
    foreign = store.create_collection(user_id="other", name="Other")
    store.collections[foreign.id] = foreign

    kb._get_vector_store(owned.id)
    vector_stores[owned.id].set_search_results(
        [
            {
                "score": 0.9,
                "metadata": {"document_id": "doc", "filename": "file"},
                "content": "chunk",
            }
        ]
    )

    results = kb.search("query", collection_ids=[owned.id, foreign.id])
    assert len(results) == 1
    assert results[0].collection_id == owned.id
