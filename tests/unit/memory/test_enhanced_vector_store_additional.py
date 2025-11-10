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


def test_query_cache_eviction_and_stats(monkeypatch):
    from forge.memory.enhanced_vector_store import QueryCache

    cache = QueryCache(max_size=1, ttl=10)
    monkeypatch.setattr("time.time", lambda: 0.0)
    cache.set("first", [{"id": 1}])
    cache.set("second", [{"id": 2}])
    assert cache.get("first") is None
    assert cache.get("second") == [{"id": 2}]
    stats = cache.stats()
    assert stats["misses"] >= 1
    assert stats["size"] == 1


def test_reranker_handles_generic_exception(monkeypatch):
    from forge.memory.enhanced_vector_store import ReRanker

    reranker = ReRanker()
    reranker._model = SimpleNamespace(predict=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    reranker.enabled = True
    results = reranker.rerank("query", [{"excerpt": "a"}], top_k=1)
    assert results == [{"excerpt": "a"}]


def test_reranker_success_path(monkeypatch):
    from forge.memory.enhanced_vector_store import ReRanker

    scores = [0.3, 0.8]

    reranker = ReRanker()
    reranker._model = SimpleNamespace(predict=lambda pairs: scores)
    reranker.enabled = True
    candidates = [{"excerpt": "low"}, {"excerpt": "high"}]
    ranked = reranker.rerank("query", candidates, top_k=1)
    assert ranked[0]["excerpt"] == "high"
    assert "rerank_score" in ranked[0]


def test_enhanced_vector_store_search_no_cache(monkeypatch):
    from forge.memory.enhanced_vector_store import EnhancedVectorStore

    backend = SimpleNamespace(
        add=lambda *args, **kwargs: None,
        search=lambda *args, **kwargs: [],
        stats=lambda: {"backend": "dummy"},
    )

    import forge.memory.enhanced_vector_store as evs

    monkeypatch.setattr("forge.memory.cloud_vector_store.AdaptiveVectorStore", lambda *a, **k: backend, raising=False)
    monkeypatch.setattr(evs, "ReRanker", lambda *args, **kwargs: SimpleNamespace(enabled=False), raising=False)

    store = EnhancedVectorStore(enable_cache=False, enable_reranking=False)
    assert store.search("query") == []


def test_vector_memory_store_wrapper(monkeypatch):
    from forge.memory.enhanced_vector_store import VectorMemoryStore

    class StubStore:
        def __init__(self, *args, **kwargs):
            self.add_called = False

        def add(self, *args, **kwargs):
            self.add_called = True

        def search(self, *args, **kwargs):
            return [{"step_id": "1"}]

        def stats(self):
            return {"backend": "stub"}

    monkeypatch.setattr("forge.memory.enhanced_vector_store.EnhancedVectorStore", lambda *a, **k: StubStore())

    wrapper = VectorMemoryStore()
    wrapper.add("1", "user", None, "why", "content")
    assert wrapper.search("query")[0]["step_id"] == "1"
    assert wrapper.stats()["backend"] == "stub"
