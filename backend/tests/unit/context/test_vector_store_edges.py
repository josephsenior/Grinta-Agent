"""Edge-case tests for QueryCache and EnhancedVectorStore."""

from __future__ import annotations

import sys
import time
import types
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

from backend.context.vector_store import EnhancedVectorStore, QueryCache
from backend.context.vector_store import _vector_store as vs

TENANT_METADATA_KEY = vs.TENANT_METADATA_KEY


def make_store() -> EnhancedVectorStore:
    store = object.__new__(EnhancedVectorStore)
    store.cache = None
    store.config = {'initial_k': 20, 'final_k': 5}
    store.enable_reranking = False
    store.reranker = None
    store.backend = MagicMock()
    store.bm25_backend = MagicMock()
    store._search_pool = ThreadPoolExecutor(max_workers=2)
    return store


def shutdown_pool(store: EnhancedVectorStore) -> None:
    pool = getattr(store, '_search_pool', None)
    if pool is not None:
        pool.shutdown(wait=True)


class TestResolveCurrentTenant:
    def test_returns_session_id(self) -> None:
        with (
            patch(
                'backend.context.memory.session_context.bind_session_context',
                return_value=None,
            ),
            patch(
                'backend.engine.tools.working_memory.get_current_session_id',
                return_value='  sess-1  ',
            ),
        ):
            assert vs._resolve_current_tenant() == 'sess-1'

    def test_returns_none_when_not_string(self) -> None:
        with (
            patch(
                'backend.context.memory.session_context.bind_session_context',
                return_value=None,
            ),
            patch(
                'backend.engine.tools.working_memory.get_current_session_id',
                return_value=None,
            ),
        ):
            assert vs._resolve_current_tenant() is None

    def test_returns_none_on_error(self) -> None:
        with patch(
            'backend.context.memory.session_context.bind_session_context',
            side_effect=RuntimeError('boom'),
        ):
            assert vs._resolve_current_tenant() is None


class TestQueryCacheInvalidate:
    def test_invalidate_by_step_ids(self) -> None:
        cache = QueryCache()
        cache.store('q1', [{'step_id': 'a'}])
        cache.store('q2', [{'step_id': 'b'}])
        cache.store('q3', [{'step_id': 'c'}])
        assert cache.invalidate_by_step_ids({'a', 'c'}) == 2
        assert cache.get('q1') is None
        assert cache.get('q2') == [{'step_id': 'b'}]
        assert cache.get('q3') is None

    def test_invalidate_by_step_ids_no_match(self) -> None:
        cache = QueryCache()
        cache.store('q1', [{'step_id': 'a'}])
        assert cache.invalidate_by_step_ids({'zzz'}) == 0

    def test_hash_query_json_error_falls_back_to_repr(self) -> None:
        class BadStr:
            def __str__(self) -> str:
                raise ValueError('boom')

        key = QueryCache._hash_query('q', filter_metadata={'k': BadStr()})
        assert len(key) == 24


class TestQueryCacheExtra:
    def test_get_expired_entry(self) -> None:
        cache = QueryCache(ttl=0)
        cache.store('q', [{'step_id': 'a'}])
        assert cache.get('q') is None

    def test_store_evicts_lru(self) -> None:
        cache = QueryCache(max_size=1)
        cache.store('a', [{'step_id': 'a'}])
        cache.store('b', [{'step_id': 'b'}])
        assert cache.get('a') is None
        assert cache.get('b') == [{'step_id': 'b'}]

    def test_clear_drops_entries(self) -> None:
        cache = QueryCache()
        cache.store('a', [{'step_id': 'a'}])
        cache.store('b', [{'step_id': 'b'}])
        cache.clear()
        assert cache.stats()['size'] == 0
        assert cache.get('a') is None


class TestEnhancedInit:
    def test_reranking_enabled_creates_ranker(self, tmp_path) -> None:
        fake_ranker = MagicMock()
        flashrank_mod = types.ModuleType('flashrank')
        flashrank_mod.Ranker = MagicMock(return_value=fake_ranker)
        with (
            patch.dict(sys.modules, {'flashrank': flashrank_mod}),
            patch(
                'backend.context.vector_store._local_vector_store.ChromaDBBackend',
                return_value=MagicMock(),
            ),
            patch(
                'backend.context.vector_store._vector_store.SQLiteBM25Backend',
                return_value=MagicMock(),
            ),
            patch(
                'backend.context.vector_store._local_vector_store.get_active_local_data_root',
                return_value=str(tmp_path),
            ),
        ):
            store = EnhancedVectorStore(
                collection_name='demo',
                enable_reranking=True,
                warm_embeddings_in_background=False,
            )
        assert store.reranker is fake_ranker
        store.shutdown()

    def test_reranking_enabled_without_flashrank(self) -> None:
        fake_backend = MagicMock()
        fake_backend.backend_name = 'Fake'
        with (
            patch(
                'backend.context.vector_store._local_vector_store.ChromaDBBackend',
                return_value=fake_backend,
            ),
            patch(
                'backend.context.vector_store._vector_store.SQLiteBM25Backend',
                return_value=MagicMock(),
            ),
        ):
            store = EnhancedVectorStore(
                collection_name='demo',
                enable_reranking=True,
                warm_embeddings_in_background=False,
            )
        assert store.reranker is None
        store.shutdown()

    def test_shutdown(self) -> None:
        store = make_store()
        store.shutdown()
        assert store._search_pool is None

    def test_shutdown_idempotent(self) -> None:
        store = make_store()
        store._search_pool = None
        store.shutdown()

    def test_start_background_warmup(self) -> None:
        store = make_store()
        store.backend.warm_model_in_background = MagicMock()
        store.start_background_warmup()
        store.backend.warm_model_in_background.assert_called_once()

    def test_start_background_warmup_without_support(self) -> None:
        store = make_store()
        del store.backend.warm_model_in_background
        store.start_background_warmup()


class TestAttachTenant:
    def test_adds_tenant_when_missing(self) -> None:
        assert EnhancedVectorStore._attach_tenant_metadata({'role': 'user'}, 's1') == {
            'role': 'user',
            TENANT_METADATA_KEY: 's1',
        }

    def test_none_metadata_creates_dict(self) -> None:
        assert EnhancedVectorStore._attach_tenant_metadata(None, 's1') == {
            TENANT_METADATA_KEY: 's1'
        }

    def test_existing_tenant_not_overwritten(self) -> None:
        assert EnhancedVectorStore._attach_tenant_metadata(
            {TENANT_METADATA_KEY: 's2'}, 's1'
        ) == {TENANT_METADATA_KEY: 's2'}

    def test_no_tenant_returns_copy(self) -> None:
        merged = EnhancedVectorStore._attach_tenant_metadata({'role': 'user'}, None)
        assert merged == {'role': 'user'}


class TestEnhancedAdd:
    def test_add_both_backends(self) -> None:
        store = make_store()
        store.add('s1', 'user', 'h', 'r', 'text', {'role': 'user'}, tenant_id='sess')
        store.backend.add.assert_called_once()
        call = store.backend.add.call_args
        assert call.args[0] == 's1'
        assert call.args[5][TENANT_METADATA_KEY] == 'sess'
        store.bm25_backend.add.assert_called_once()
        shutdown_pool(store)

    def test_add_batch_default_metadatas(self) -> None:
        store = make_store()
        store.add_batch(
            ['s1', 's2'],
            ['user', 'user'],
            [None, None],
            [None, None],
            ['a', 'b'],
            tenant_id='sess',
        )
        store.backend.add_batch.assert_called_once()
        call = store.backend.add_batch.call_args
        assert call.args[5][0][TENANT_METADATA_KEY] == 'sess'
        assert call.args[5][1][TENANT_METADATA_KEY] == 'sess'
        store.bm25_backend.add_batch.assert_called_once()
        shutdown_pool(store)

    async def test_async_add(self) -> None:
        store = make_store()
        await store.async_add('s1', 'user', None, None, 'text', tenant_id='sess')
        store.backend.add.assert_called_once()
        shutdown_pool(store)

    async def test_async_add_batch(self) -> None:
        store = make_store()
        await store.async_add_batch(
            ['s1'], ['user'], [None], [None], ['text'], tenant_id='sess'
        )
        store.backend.add_batch.assert_called_once()
        shutdown_pool(store)


class TestEffectiveInitialK:
    def test_default(self) -> None:
        store = make_store()
        assert store._effective_initial_k(5) == 20

    def test_bool_coerced(self) -> None:
        store = make_store()
        store.config['initial_k'] = True
        assert store._effective_initial_k(5) == 20

    def test_float_coerced(self) -> None:
        store = make_store()
        store.config['initial_k'] = 30.7
        assert store._effective_initial_k(5) == 30

    def test_int_larger_than_k_double(self) -> None:
        store = make_store()
        store.config['initial_k'] = 30
        assert store._effective_initial_k(5) == 30

    def test_k_double_dominates(self) -> None:
        store = make_store()
        store.config['initial_k'] = 3
        assert store._effective_initial_k(5) == 10


class TestDedupe:
    def test_deduplicates_by_step_id(self) -> None:
        candidates = EnhancedVectorStore._dedupe_candidates_by_step_id(
            [{'step_id': 'a'}, {'step_id': 'b'}],
            [{'step_id': 'b'}, {'step_id': 'c'}],
        )
        assert [c['step_id'] for c in candidates] == ['a', 'b', 'c']


class TestFinalizeHybrid:
    def test_no_reranker_truncates(self) -> None:
        store = make_store()
        candidates = [{'step_id': 'a'}, {'step_id': 'b'}, {'step_id': 'c'}]
        assert store._finalize_hybrid_results('q', 2, candidates) == candidates[:2]

    def test_no_candidates_returns_empty(self) -> None:
        store = make_store()
        assert store._finalize_hybrid_results('q', 5, []) == []

    def test_rerank_maps_scores(self) -> None:
        store = make_store()
        fake_ranker = MagicMock()
        fake_ranker.rerank.return_value = [
            {'id': 'a', 'score': 0.9},
            {'id': 'b', 'score': 0.7},
        ]
        store.reranker = fake_ranker
        candidates = [
            {'step_id': 'a', 'excerpt': 'ta', 'score': 0.1},
            {'step_id': 'b', 'excerpt': 'tb', 'score': 0.2},
        ]
        flashrank_mod = types.ModuleType('flashrank')
        flashrank_mod.RerankRequest = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {'flashrank': flashrank_mod}):
            result = store._finalize_hybrid_results('q', 5, candidates)
        assert result[0]['score'] == 0.9
        assert result[1]['score'] == 0.7

    def test_rerank_appends_dropped_candidates(self) -> None:
        store = make_store()
        fake_ranker = MagicMock()
        fake_ranker.rerank.return_value = [{'id': 'a', 'score': 0.9}]
        store.reranker = fake_ranker
        candidates = [
            {'step_id': 'a', 'excerpt': 'ta', 'score': 0.1},
            {'step_id': 'b', 'excerpt': 'tb', 'score': 0.2},
        ]
        flashrank_mod = types.ModuleType('flashrank')
        flashrank_mod.RerankRequest = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {'flashrank': flashrank_mod}):
            result = store._finalize_hybrid_results('q', 5, candidates)
        assert len(result) == 2
        assert result[1]['step_id'] == 'b'

    def test_rerank_failure_falls_back(self) -> None:
        store = make_store()
        fake_ranker = MagicMock()
        fake_ranker.rerank.side_effect = RuntimeError('boom')
        store.reranker = fake_ranker
        candidates = [{'step_id': 'a'}, {'step_id': 'b'}]
        flashrank_mod = types.ModuleType('flashrank')
        flashrank_mod.RerankRequest = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {'flashrank': flashrank_mod}):
            result = store._finalize_hybrid_results('q', 5, candidates)
        assert result == candidates


class TestTryCachedSearch:
    def test_no_cache(self) -> None:
        store = make_store()
        assert (
            store._try_cached_search('q', 5, None, time.time(), tenant_id='t') is None
        )

    def test_cache_miss(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        assert (
            store._try_cached_search('q', 5, None, time.time(), tenant_id='t') is None
        )

    def test_cache_hit(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.cache.store('q', [{'step_id': 'a', 'score': 1.0}], tenant_id='t')
        result = store._try_cached_search('q', 5, None, time.time(), tenant_id='t')
        assert result == [{'step_id': 'a', 'score': 1.0}]


class TestParallelSearch:
    def test_both_backends_return(self) -> None:
        store = make_store()
        store.backend.search.return_value = [{'step_id': 'a'}]
        store.bm25_backend.search.return_value = [{'step_id': 'b'}]
        semantic, lexical = store._search_backends_in_parallel(
            'q', 10, None, tenant_id='t'
        )
        assert semantic == [{'step_id': 'a'}]
        assert lexical == [{'step_id': 'b'}]
        store.backend.search.assert_called_once_with(
            'q', k=10, filter_metadata={TENANT_METADATA_KEY: 't'}
        )
        shutdown_pool(store)

    def test_semantic_failure_falls_back_to_lexical(self) -> None:
        store = make_store()
        store.backend.search.side_effect = RuntimeError('boom')
        store.bm25_backend.search.return_value = [{'step_id': 'b'}]
        semantic, lexical = store._search_backends_in_parallel(
            'q', 10, None, tenant_id='t'
        )
        assert semantic == []
        assert lexical == [{'step_id': 'b'}]
        shutdown_pool(store)

    def test_lexical_failure_falls_back_to_semantic(self) -> None:
        store = make_store()
        store.backend.search.return_value = [{'step_id': 'a'}]
        store.bm25_backend.search.side_effect = RuntimeError('boom')
        semantic, lexical = store._search_backends_in_parallel(
            'q', 10, None, tenant_id='t'
        )
        assert semantic == [{'step_id': 'a'}]
        assert lexical == []
        shutdown_pool(store)


class TestSearch:
    def test_tenant_resolved_when_missing(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.backend.search.return_value = [{'step_id': 'a', TENANT_METADATA_KEY: 't'}]
        store.bm25_backend.search.return_value = []
        with patch.object(vs, '_resolve_current_tenant', return_value='t'):
            results = store.search('q', tenant_id=None)
        assert results == [{'step_id': 'a', TENANT_METADATA_KEY: 't'}]
        shutdown_pool(store)

    def test_cache_hit_short_circuits(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.cache.store(
            'q', [{'step_id': 'a', TENANT_METADATA_KEY: 't'}], tenant_id='t'
        )
        results = store.search('q', tenant_id='t')
        assert results == [{'step_id': 'a', TENANT_METADATA_KEY: 't'}]
        store.backend.search.assert_not_called()
        shutdown_pool(store)

    def test_full_flow_with_cache_store(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.backend.search.return_value = [
            {'step_id': 'a', TENANT_METADATA_KEY: 't', 'score': 0.9}
        ]
        store.bm25_backend.search.return_value = []
        results = store.search('q', tenant_id='t')
        assert results == [{'step_id': 'a', TENANT_METADATA_KEY: 't', 'score': 0.9}]
        assert store.cache.get('q', tenant_id='t') == results
        shutdown_pool(store)

    def test_tenant_filter_drops_foreign_docs(self) -> None:
        store = make_store()
        store.backend.search.return_value = [
            {'step_id': 'a', TENANT_METADATA_KEY: 't1'},
            {'step_id': 'b', TENANT_METADATA_KEY: 't2'},
            {'step_id': 'c'},
        ]
        store.bm25_backend.search.return_value = []
        results = store.search('q', tenant_id='t1')
        assert [r['step_id'] for r in results] == ['a', 'c']
        shutdown_pool(store)

    def test_no_candidates_returns_empty(self) -> None:
        store = make_store()
        store.backend.search.return_value = []
        store.bm25_backend.search.return_value = []
        assert store.search('q', tenant_id='t') == []
        shutdown_pool(store)

    def test_search_without_cache(self) -> None:
        store = make_store()
        store.backend.search.return_value = [{'step_id': 'a'}]
        store.bm25_backend.search.return_value = []
        assert store.search('q', tenant_id='t') == [{'step_id': 'a'}]
        shutdown_pool(store)

    async def test_async_search(self) -> None:
        store = make_store()
        store.backend.search.return_value = []
        store.bm25_backend.search.return_value = []
        assert await store.async_search('q', tenant_id='t') == []
        shutdown_pool(store)


class TestDelete:
    def test_delete_by_metadata(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.backend.delete_by_metadata.return_value = 3
        store.bm25_backend.delete_by_metadata.return_value = 2
        store.cache.store('q', [{'step_id': 'a', 'role': 'user'}])
        assert store.delete_by_metadata({'role': 'user'}) == 3
        store.backend.delete_by_metadata.assert_called_once_with({'role': 'user'})
        assert store.cache.get('q') is None
        shutdown_pool(store)

    def test_delete_by_ids(self) -> None:
        store = make_store()
        store.cache = QueryCache()
        store.backend.delete_by_ids.return_value = 2
        store.bm25_backend.delete_by_ids.return_value = 2
        store.cache.store('q', [{'step_id': 'a'}])
        assert store.delete_by_ids(['a']) == 2
        store.backend.delete_by_ids.assert_called_once_with(['a'])
        assert store.cache.get('q') is None
        shutdown_pool(store)

    def test_delete_backends_in_parallel_both_fail(self) -> None:
        store = make_store()
        store.backend.delete_by_ids.side_effect = RuntimeError('boom')
        store.bm25_backend.delete_by_ids.side_effect = RuntimeError('boom')
        assert (
            store._delete_backends_in_parallel(
                store.backend.delete_by_ids, store.bm25_backend.delete_by_ids, ['a']
            )
            == 0
        )
        shutdown_pool(store)


class TestStats:
    def test_stats_with_cache(self) -> None:
        store = make_store()
        store.backend.stats.return_value = {'backend': 'x', 'num_documents': 5}
        store.cache = QueryCache()
        stats = store.stats()
        assert stats['backend'] == 'x'
        assert stats['cache']['size'] == 0
        shutdown_pool(store)

    def test_stats_without_cache(self) -> None:
        store = make_store()
        store.backend.stats.return_value = {'backend': 'x'}
        assert 'cache' not in store.stats()
        shutdown_pool(store)


class TestApplyFilters:
    def test_no_filter_returns_first_k(self) -> None:
        results = [{'step_id': '1'}, {'step_id': '2'}, {'step_id': '3'}]
        assert EnhancedVectorStore._apply_filters(results, 2, None) == results[:2]

    def test_filter_keeps_matching(self) -> None:
        results = [
            {'step_id': '1', 'role': 'user'},
            {'step_id': '2', 'role': 'assistant'},
        ]
        filtered = EnhancedVectorStore._apply_filters(results, 5, {'role': 'user'})
        assert [r['step_id'] for r in filtered] == ['1']

    def test_tenant_filter(self) -> None:
        results = [
            {'step_id': '1', TENANT_METADATA_KEY: 't1'},
            {'step_id': '2', TENANT_METADATA_KEY: 't2'},
            {'step_id': '3'},
        ]
        filtered = EnhancedVectorStore._apply_filters(results, 5, None, tenant_id='t1')
        assert [r['step_id'] for r in filtered] == ['1', '3']

    def test_empty_results(self) -> None:
        assert EnhancedVectorStore._apply_filters([], 5, None) == []
