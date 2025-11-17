import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def chroma_and_sentence_stubs(monkeypatch):
    collection_store = {}

    class DummyCollection:
        def __init__(self, name):
            self._name = name
            self._docs: dict[str, dict] = {}

        def count(self):
            return len(self._docs)

        def add(self, ids, embeddings, documents, metadatas):
            for point_id, doc, meta in zip(ids, documents, metadatas):
                self._docs[point_id] = {"document": doc, "metadata": meta}

        def query(self, query_embeddings, n_results, where, include):
            ids = list(self._docs.keys())[:n_results]
            metadatas = [self._docs[i]["metadata"] for i in ids]
            documents = [self._docs[i]["document"] for i in ids]
            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [[0.1 for _ in ids]],
            }

    class PersistentClient:
        def __init__(self, path, settings):
            self.path = path
            self.settings = settings

        def get_collection(self, name):
            if name not in collection_store:
                raise Exception("missing")
            return collection_store[name]

        def create_collection(self, name, metadata):
            collection_store[name] = DummyCollection(name)
            return collection_store[name]

    chromadb = ModuleType("chromadb")
    chromadb.PersistentClient = PersistentClient
    config_module = ModuleType("chromadb.config")

    class Settings:
        def __init__(self, anonymized_telemetry):
            self.anonymized_telemetry = anonymized_telemetry

    config_module.Settings = Settings

    sentence_transformers = ModuleType("sentence_transformers")

    class Vector(list):
        def tolist(self):
            return list(self)

    class SentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, text, show_progress_bar=False):
            if isinstance(text, list):
                return [Vector([0.1] * 3) for _ in text]
            return Vector([0.1, 0.2, 0.3])

        def get_sentence_embedding_dimension(self):
            return 3

    sentence_transformers.SentenceTransformer = SentenceTransformer

    monkeypatch.setitem(sys.modules, "chromadb", chromadb)
    monkeypatch.setitem(sys.modules, "chromadb.config", config_module)
    monkeypatch.setitem(sys.modules, "sentence_transformers", sentence_transformers)

    yield


@pytest.fixture
def qdrant_stub(monkeypatch, chroma_and_sentence_stubs):
    class DummyClient:
        def __init__(self):
            self._collections = {}
            self._points = {}

        def get_collection(self, name):
            if name not in self._collections:
                raise Exception("missing")
            return SimpleNamespace(points_count=len(self._points.get(name, [])))

        def create_collection(self, collection_name, vectors_config):
            self._collections[collection_name] = vectors_config

        def upsert(self, collection_name, points):
            self._points.setdefault(collection_name, []).extend(points)

        def search(self, collection_name, query_vector, limit, query_filter):
            points = self._points.get(collection_name, [])
            return [
                SimpleNamespace(
                    score=0.5,
                    payload=point.payload
                    if hasattr(point, "payload")
                    else {"step_id": "0", "text": "content"},
                )
                for point in points[:limit]
            ]

    models_module = ModuleType("qdrant_client.http.models")

    class VectorParams:
        def __init__(self, size, distance):
            self.size = size
            self.distance = distance

    class Distance:
        COSINE = "cosine"

    class MatchValue:
        def __init__(self, value):
            self.value = value

    class FieldCondition:
        def __init__(self, key, match):
            self.key = key
            self.match = match

    class Filter:
        def __init__(self, must):
            self.must = must

    class PointStruct:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload

    models_module.VectorParams = VectorParams
    models_module.Distance = SimpleNamespace(COSINE=Distance.COSINE)
    models_module.MatchValue = MatchValue
    models_module.FieldCondition = FieldCondition
    models_module.Filter = Filter
    models_module.PointStruct = PointStruct

    qdrant_client_module = ModuleType("qdrant_client")
    qdrant_client_module.QdrantClient = lambda **kwargs: DummyClient()
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_client_module)
    monkeypatch.setitem(
        sys.modules, "qdrant_client.http", ModuleType("qdrant_client.http")
    )
    monkeypatch.setitem(sys.modules, "qdrant_client.http.models", models_module)
    monkeypatch.setitem(sys.modules, "requests", ModuleType("requests"))

    yield


@pytest.mark.parametrize(
    "rationale,content,expected",
    [
        ("reasoning", "main content", "reasoning\nmain content"),
        (None, "main content", "main content"),
        ("why", "", "why"),
    ],
)
def test_prepare_text_static_method(rationale, content, expected):
    from forge.memory.cloud_vector_store import ChromaDBBackend

    text = ChromaDBBackend._prepare_text(rationale, content)
    assert text == expected


def test_chromadb_backend_add_search_stats(chroma_and_sentence_stubs, monkeypatch):
    from forge.memory.cloud_vector_store import ChromaDBBackend

    backend = ChromaDBBackend(collection_name="test")
    backend.add("1", "user", None, "reason", "content text", metadata={"foo": "bar"})
    results = backend.search("query", k=1)
    assert results[0]["step_id"] == "1"
    stats = backend.stats()
    assert stats["num_documents"] == 1
    assert stats["backend"] == "ChromaDB (Local)"


def test_adaptive_vector_store_force_backend(chroma_and_sentence_stubs, monkeypatch):
    from forge.memory.cloud_vector_store import AdaptiveVectorStore

    store = AdaptiveVectorStore(collection_name="c1", force_backend="chromadb")
    store.add("1", "user", None, "rationale", "content")
    assert store.stats()["backend"].startswith("ChromaDB")


def test_vector_memory_store_wrapper(chroma_and_sentence_stubs):
    from forge.memory.cloud_vector_store import VectorMemoryStore

    wrapper = VectorMemoryStore()
    wrapper.add("1", "user", None, "why", "content")
    results = wrapper.search("content")
    assert isinstance(results, list)
    stats = wrapper.stats()
    assert "backend" in stats


def test_qdrant_backend_creation(qdrant_stub, monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "https://example")
    monkeypatch.setenv("QDRANT_API_KEY", "key")
    monkeypatch.setenv("HF_API_KEY", "")

    from forge.memory.cloud_vector_store import QdrantCloudBackend

    backend = QdrantCloudBackend(collection_name="q")
    backend.add("1", "user", None, "why", "text")
    backend.search("text")
    stats = backend.stats()
    assert stats["backend"].startswith("Qdrant")


def test_chromadb_backend_search_handles_empty_collection(chroma_and_sentence_stubs):
    from forge.memory.cloud_vector_store import ChromaDBBackend

    backend = ChromaDBBackend(collection_name="empty")
    assert backend.search("nothing") == []


def test_chromadb_backend_add_includes_artifact_metadata(chroma_and_sentence_stubs):
    from forge.memory.cloud_vector_store import ChromaDBBackend

    backend = ChromaDBBackend(collection_name="meta")
    backend.add(
        "step-42",
        "assistant",
        artifact_hash="abc123",
        rationale="Reason",
        content_text="Longer content chunk",
        metadata={"topic": "testing"},
    )
    results = backend.search("content", k=1)
    assert results
    doc = results[0]
    assert doc["artifact_hash"] == "abc123"
    assert doc["topic"] == "testing"


def test_chromadb_backend_missing_dependencies(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("chromadb") or name.startswith("sentence_transformers"):
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from forge.memory.cloud_vector_store import ChromaDBBackend

    with pytest.raises(ImportError) as exc:
        ChromaDBBackend(collection_name="will-fail")
    assert "chromadb" in str(exc.value).lower()


def test_qdrant_backend_missing_dependency(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("qdrant_client"):
            raise ImportError("no qdrant")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    from forge.memory.cloud_vector_store import QdrantCloudBackend

    with pytest.raises(ImportError):
        QdrantCloudBackend(collection_name="missing")


def test_qdrant_backend_requires_env(qdrant_stub, monkeypatch):
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    from forge.memory.cloud_vector_store import QdrantCloudBackend

    with pytest.raises(ValueError):
        QdrantCloudBackend(collection_name="no-env")


def test_qdrant_backend_hf_api_fallback(qdrant_stub, monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "https://example")
    monkeypatch.setenv("QDRANT_API_KEY", "key")
    monkeypatch.setenv("HF_API_KEY", "token")

    import sys

    class Response:
        status_code = 500

        def json(self):
            return []

    monkeypatch.setattr(
        sys.modules["requests"],
        "post",
        lambda *args, **kwargs: Response(),
        raising=False,
    )

    from forge.memory.cloud_vector_store import QdrantCloudBackend

    backend = QdrantCloudBackend(collection_name="hf-fallback")
    vector = backend._get_embedding("text to embed")
    assert isinstance(vector, list)
    assert vector


def test_qdrant_backend_hf_api_exception_fallback(qdrant_stub, monkeypatch):
    monkeypatch.setenv("QDRANT_URL", "https://example")
    monkeypatch.setenv("QDRANT_API_KEY", "key")
    monkeypatch.setenv("HF_API_KEY", "token")

    import sys

    def boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(sys.modules["requests"], "post", boom, raising=False)

    from forge.memory.cloud_vector_store import QdrantCloudBackend

    backend = QdrantCloudBackend(collection_name="hf-exception")
    vector = backend._get_embedding("another text")
    assert isinstance(vector, list)
    assert vector


def test_adaptive_vector_store_falls_back_to_chromadb(
    monkeypatch, chroma_and_sentence_stubs
):
    import forge.memory.cloud_vector_store as module

    class FailingQdrant:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("qdrant unavailable")

    class StubChroma:
        def __init__(self, *args, **kwargs):
            self.docs = []

        def add(self, *args, **kwargs):
            self.docs.append(kwargs)

        def search(self, *args, **kwargs):
            return []

        def stats(self):
            return {"backend": "stub chroma"}

    monkeypatch.setenv("QDRANT_URL", "https://example")
    monkeypatch.setenv("QDRANT_API_KEY", "key")
    monkeypatch.setattr(module, "QdrantCloudBackend", FailingQdrant)
    monkeypatch.setattr(module, "ChromaDBBackend", StubChroma)

    store = module.AdaptiveVectorStore(collection_name="fallback")
    assert isinstance(store.backend, StubChroma)

    # cleanup env
    monkeypatch.delenv("QDRANT_URL", raising=False)
    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
