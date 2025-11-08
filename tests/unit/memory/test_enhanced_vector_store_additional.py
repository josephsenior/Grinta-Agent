from types import SimpleNamespace


def test_query_cache_hit_and_expiration(monkeypatch):
    from forge.memory.enhanced_vector_store import QueryCache

    cache = QueryCache(max_size=2, ttl=5)
    monkeypatch.setattr("time.time", lambda: 100.0)
    cache.set("hello", [{"id": 1}])
    assert cache.get("hello") == [{"id": 1}]

    monkeypatch.setattr("time.time", lambda: 200.0)
    assert cache.get("hello") is None


def test_reranker_handles_missing_dependency(monkeypatch):
    from forge.memory.enhanced_vector_store import ReRanker

    reranker = ReRanker()

    def failing_import(*args, **kwargs):
        raise ImportError("fail")

    monkeypatch.setattr("forge.memory.enhanced_vector_store.CrossEncoder", failing_import, raising=False)
    results = reranker.rerank("query", [{"excerpt": "text"}], top_k=1)
    assert results == [{"excerpt": "text"}]


def test_enhanced_vector_store_search_with_cache(monkeypatch):
    from forge.memory.enhanced_vector_store import EnhancedVectorStore

    class DummyBackend:
        def __init__(self, *args, **kwargs):
            self.records = []

        def add(self, step_id, role, artifact_hash, rationale, content_text, metadata=None):
            self.records.append({"step_id": step_id, "role": role, "excerpt": content_text, **(metadata or {})})

        def search(self, query, k, filter_metadata=None):
            return self.records[:k]

        def stats(self):
            return {"backend": "dummy", "num_documents": len(self.records)}

    import forge.memory.enhanced_vector_store as evs

    monkeypatch.setattr("forge.memory.cloud_vector_store.AdaptiveVectorStore", lambda *args, **kwargs: DummyBackend(), raising=False)
    monkeypatch.setattr(evs, "ReRanker", lambda *args, **kwargs: SimpleNamespace(enabled=False), raising=False)

    store = EnhancedVectorStore(collection_name="test", enable_cache=True, enable_reranking=False)
    store.add("1", "user", None, None, "hello world", metadata={"role": "user"})
    first = store.search("hello", k=1)
    assert first and first[0]["step_id"] == "1"

    # cached call with filter
    filtered = store.search("hello", k=1, filter_metadata={"role": "system"})
    assert filtered == []


def test_enhanced_vector_store_stats(monkeypatch):
    from forge.memory.enhanced_vector_store import EnhancedVectorStore

    backend = SimpleNamespace(
        add=lambda *args, **kwargs: None,
        search=lambda *args, **kwargs: [],
        stats=lambda: {"backend": "dummy"},
    )

    import forge.memory.enhanced_vector_store as evs

    monkeypatch.setattr("forge.memory.cloud_vector_store.AdaptiveVectorStore", lambda *a, **k: backend, raising=False)
    monkeypatch.setattr(evs, "ReRanker", lambda *args, **kwargs: SimpleNamespace(enabled=True, model_name="stub"), raising=False)

    store = EnhancedVectorStore(enable_cache=True, enable_reranking=True)
    stats = store.stats()
    assert stats["backend"] == "dummy"
    assert stats["cache"]["size"] == 0
    assert stats["reranker"]["enabled"] is True

