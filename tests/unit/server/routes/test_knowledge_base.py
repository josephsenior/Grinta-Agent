"""Unit tests for knowledge base routes."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from forge.server.routes import knowledge_base as kb_routes
from forge.storage.data_models.knowledge_base import (
    KnowledgeBaseCollection,
    KnowledgeBaseDocument,
    KnowledgeBaseSearchResult,
)


class StubKBManager:
    def __init__(self, **methods):
        for name, value in methods.items():
            setattr(self, name, value)


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(kb_routes.router)
    return TestClient(app)


def _collection(**overrides) -> KnowledgeBaseCollection:
    base = {
        "user_id": "user",
        "name": "Collection",
        "description": "desc",
        "document_count": 3,
        "total_size_bytes": 5_242_880,  # 5 MB
        "created_at": datetime(2024, 1, 1, 12, 0, 0),
        "updated_at": datetime(2024, 1, 2, 12, 0, 0),
    }
    base.update(overrides)
    return KnowledgeBaseCollection(**base)


def _document(**overrides) -> KnowledgeBaseDocument:
    base = {
        "collection_id": "col-1",
        "filename": "doc.txt",
        "content_hash": "hash",
        "file_size_bytes": 4096,
        "mime_type": "text/plain",
        "chunk_count": 2,
        "uploaded_at": datetime(2024, 1, 3, 12, 0, 0),
    }
    base.update(overrides)
    return KnowledgeBaseDocument(**base)


def _search_result(**overrides) -> KnowledgeBaseSearchResult:
    base = {
        "document_id": "doc-1",
        "collection_id": "col-1",
        "filename": "doc.txt",
        "chunk_content": "content",
        "relevance_score": 0.87654,
    }
    base.update(overrides)
    return KnowledgeBaseSearchResult(**base)


def test_get_kb_manager_uses_manager_class(monkeypatch):
    captured = {}

    class FakeManager:
        def __init__(self, user_id: str):
            captured["user_id"] = user_id

    monkeypatch.setattr(kb_routes, "KnowledgeBaseManager", FakeManager)
    manager = kb_routes._get_kb_manager("user123")
    assert isinstance(manager, FakeManager)
    assert captured["user_id"] == "user123"


def test_collection_to_response_formats_fields():
    response = kb_routes._collection_to_response(_collection())
    assert response.total_size_mb == 5.0
    assert response.created_at.endswith("00:00")


def test_document_to_response_formats_fields():
    response = kb_routes._document_to_response(_document())
    assert response.file_size_kb == 4.0
    assert response.uploaded_at.endswith("00:00")


def test_search_result_to_response_rounds_score():
    response = kb_routes._search_result_to_response(_search_result())
    assert response.relevance_score == pytest.approx(0.877, rel=1e-3)


def test_create_collection_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(create_collection=lambda **kwargs: _collection())
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/collections",
        json={"name": "New", "description": "desc"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Collection"


def test_create_collection_failure(monkeypatch):
    client = _make_client()

    def raising(**kwargs):
        raise RuntimeError("boom")

    stub = StubKBManager(create_collection=raising)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/collections",
        json={"name": "New"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_list_collections_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(list_collections=lambda: [_collection(name="A"), _collection(name="B")])
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections")
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["A", "B"]


def test_list_collections_failure(monkeypatch):
    client = _make_client()
    stub = StubKBManager(list_collections=lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_collection_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_collection=lambda collection_id: _collection(id=collection_id))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections/col-1")
    assert response.status_code == 200
    assert response.json()["id"] == "col-1"


def test_get_collection_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_collection=lambda collection_id: None)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections/col-404")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_collection_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_collection=lambda collection_id: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections/col-1")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_update_collection_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(update_collection=lambda **kwargs: _collection(**{"id": kwargs["collection_id"]}))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.patch(
        "/api/knowledge-base/collections/col-1",
        json={"name": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "col-1"


def test_update_collection_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(update_collection=lambda **kwargs: None)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.patch(
        "/api/knowledge-base/collections/col-404",
        json={},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_collection_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(update_collection=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.patch(
        "/api/knowledge-base/collections/col-1",
        json={},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_delete_collection_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_collection=lambda collection_id: True)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/collections/col-1")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_collection_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_collection=lambda collection_id: False)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/collections/col-404")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_collection_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_collection=lambda collection_id: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/collections/col-1")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_upload_document_too_large(monkeypatch):
    client = _make_client()
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": StubKBManager())

    large_content = BytesIO(b"a" * (10 * 1024 * 1024 + 1))
    response = client.post(
        "/api/knowledge-base/collections/col-1/documents",
        files={"file": ("large.txt", large_content, "text/plain")},
    )
    assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_upload_document_invalid_encoding(monkeypatch):
    client = _make_client()
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": StubKBManager())

    response = client.post(
        "/api/knowledge-base/collections/col-1/documents",
        files={"file": ("binary.bin", BytesIO(b"\xff"), "application/octet-stream")},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_upload_document_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(add_document=lambda **kwargs: None)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/collections/col-404/documents",
        files={"file": ("doc.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_document_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(add_document=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/collections/col-1/documents",
        files={"file": ("doc.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_upload_document_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(add_document=lambda **kwargs: _document())
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/collections/col-1/documents",
        files={"file": ("doc.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["filename"] == "doc.txt"


def test_list_documents_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(list_documents=lambda collection_id: [_document(id="doc-1"), _document(id="doc-2")])
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections/col-1/documents")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_documents_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(list_documents=lambda collection_id: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/collections/col-1/documents")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_document_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_document=lambda document_id: _document(id=document_id))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/documents/doc-1")
    assert response.status_code == 200
    assert response.json()["id"] == "doc-1"


def test_get_document_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_document=lambda document_id: None)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/documents/doc-404")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_document_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_document=lambda document_id: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/documents/doc-1")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_delete_document_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_document=lambda document_id: True)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/documents/doc-1")
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_document_not_found(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_document=lambda document_id: False)
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/documents/doc-404")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_document_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(delete_document=lambda document_id: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.delete("/api/knowledge-base/documents/doc-1")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_search_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(search=lambda **kwargs: [_search_result(), _search_result(document_id="doc-2")])
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/search",
        json={"query": "hello", "top_k": 2},
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(search=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.post(
        "/api/knowledge-base/search",
        json={"query": "hello"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_get_stats_success(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_stats=lambda: {"documents": 5})
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/stats")
    assert response.status_code == 200
    assert response.json()["documents"] == 5


def test_get_stats_error(monkeypatch):
    client = _make_client()
    stub = StubKBManager(get_stats=lambda: (_ for _ in ()).throw(RuntimeError("fail")))
    monkeypatch.setattr(kb_routes, "_get_kb_manager", lambda user_id="default": stub)

    response = client.get("/api/knowledge-base/stats")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
