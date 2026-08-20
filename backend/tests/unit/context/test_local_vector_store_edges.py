"""Edge-case tests for ChromaDB and SQLite FTS5 vector backends."""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import types
from unittest.mock import MagicMock, patch

import pytest

from backend.context.vector_store import ChromaDBBackend, SQLiteBM25Backend


@pytest.fixture
def chroma_env():
    collection = MagicMock()
    collection.metadata = {}
    collection.count.return_value = 0
    client = MagicMock()
    client.get_collection.return_value = collection
    client.create_collection.return_value = collection
    chromadb_mod = types.ModuleType('chromadb')
    chromadb_mod.PersistentClient = MagicMock(return_value=client)
    config_mod = types.ModuleType('chromadb.config')
    config_mod.Settings = lambda **kwargs: kwargs
    ef_mod = types.ModuleType('chromadb.utils.embedding_functions')
    ef_mod.FastEmbedEmbeddingFunction = MagicMock(return_value=MagicMock())
    utils_mod = types.ModuleType('chromadb.utils')
    utils_mod.embedding_functions = ef_mod
    with patch.dict(
        sys.modules,
        {
            'chromadb': chromadb_mod,
            'chromadb.config': config_mod,
            'chromadb.utils': utils_mod,
            'chromadb.utils.embedding_functions': ef_mod,
        },
    ):
        yield client, collection


def make_chroma_backend(collection=None) -> ChromaDBBackend:
    backend = object.__new__(ChromaDBBackend)
    backend.collection = collection or MagicMock()
    backend._model = MagicMock()
    backend._model_name = 'BAAI/bge-small-en-v1.5'
    backend._model_lock = threading.Lock()
    backend._model_loader_thread = None
    backend._collection_name = 'test-collection'
    return backend


def make_sqlite_backend(tmp_path) -> SQLiteBM25Backend:
    return SQLiteBM25Backend('test-collection', persist_directory=tmp_path)


class TestChromaInit:
    def test_raises_without_chromadb(self, tmp_path) -> None:
        with patch.dict(sys.modules, {'chromadb': None}):
            with pytest.raises(
                RuntimeError, match='Vector memory requires the optional'
            ):
                ChromaDBBackend(persist_directory=tmp_path)

    def test_recreates_on_model_change(self, chroma_env, tmp_path, monkeypatch) -> None:
        client, collection = chroma_env
        collection.metadata = {'embedding_model': 'old-model'}
        collection.count.return_value = 7
        monkeypatch.setenv('EMBEDDING_MODEL', 'new-model')
        backend = ChromaDBBackend(persist_directory=tmp_path)
        client.delete_collection.assert_called_once_with(name='APP_memory')
        client.create_collection.assert_called_once()
        assert backend.collection is collection

    def test_loads_existing_collection(self, chroma_env, tmp_path) -> None:
        client, collection = chroma_env
        collection.metadata = {'embedding_model': 'BAAI/bge-small-en-v1.5'}
        collection.count.return_value = 3
        backend = ChromaDBBackend(persist_directory=tmp_path)
        client.get_collection.assert_called_once()
        client.create_collection.assert_not_called()
        assert backend.collection is collection

    def test_creates_when_collection_missing(self, chroma_env, tmp_path) -> None:
        client, collection = chroma_env
        client.get_collection.side_effect = Exception('missing')
        backend = ChromaDBBackend(persist_directory=tmp_path)
        client.create_collection.assert_called_once()
        assert backend.collection is collection

    def test_default_persist_directory(self, chroma_env, tmp_path) -> None:
        with patch(
            'backend.context.vector_store._local_vector_store.get_active_local_data_root',
            return_value=str(tmp_path),
        ):
            ChromaDBBackend(warm_model_in_background=False)
        assert (tmp_path / 'memory' / 'chroma').exists()


class TestChromaModelLifecycle:
    def test_warm_model_skips_when_loaded(self) -> None:
        backend = make_chroma_backend()
        backend._model_loader_thread = MagicMock()
        with patch.object(backend, '_load_model') as load:
            backend.warm_model_in_background()
            load.assert_not_called()

    def test_warm_model_skips_when_thread_alive(self) -> None:
        backend = make_chroma_backend()
        backend._model = None
        backend._model_loader_thread = MagicMock()
        backend._model_loader_thread.is_alive.return_value = True
        with patch(
            'backend.context.vector_store._local_vector_store.threading.Thread'
        ) as thread_cls:
            backend.warm_model_in_background()
            thread_cls.assert_not_called()

    def test_warm_model_starts_thread(self) -> None:
        backend = make_chroma_backend()
        backend._model = None
        backend._model_loader_thread = None
        fake_thread = MagicMock()
        with patch(
            'backend.context.vector_store._local_vector_store.threading.Thread',
            return_value=fake_thread,
        ) as thread_cls:
            backend.warm_model_in_background()
        thread_cls.assert_called_once()
        fake_thread.start.assert_called_once()
        assert backend._model_loader_thread is fake_thread

    def test_load_model_early_return(self, chroma_env) -> None:
        backend = make_chroma_backend()
        backend._model = MagicMock()
        with patch('backend.context.vector_store._local_vector_store.threading.Lock'):
            backend._load_model()
        assert backend._model is not None

    def test_load_model_loads(self, chroma_env) -> None:
        backend = make_chroma_backend()
        backend._model = None
        backend._load_model()
        assert backend._model is not None

    def test_model_property_loads(self, chroma_env) -> None:
        backend = make_chroma_backend()
        backend._model = None
        assert backend.model is not None


class TestChromaAdd:
    def test_add_short_text_single_insert(self) -> None:
        backend = make_chroma_backend()
        backend.add('s1', 'user', None, None, 'short text')
        backend.collection.add.assert_called_once()
        args = backend.collection.add.call_args
        assert args.kwargs['ids'] == ['s1']

    def test_add_long_text_parent_and_children(self) -> None:
        backend = make_chroma_backend()
        backend.add('s1', 'user', 'hash1', 'rationale', 'x' * 900)
        assert backend.collection.add.call_count == 2
        parent_call, child_call = backend.collection.add.call_args_list
        assert parent_call.kwargs['ids'] == ['s1']
        assert child_call.kwargs['ids'][0] == 's1_child_1'
        assert child_call.kwargs['metadatas'][0]['is_child'] is True
        assert child_call.kwargs['metadatas'][0]['parent_id'] == 's1'

    def test_add_batch_empty_returns(self) -> None:
        backend = make_chroma_backend()
        backend.add_batch([], [], [], [], [])
        backend.collection.add.assert_not_called()

    def test_add_batch_parents_and_children(self) -> None:
        backend = make_chroma_backend()
        backend.add_batch(
            ['s1', 's2'],
            ['user', 'assistant'],
            [None, 'h2'],
            [None, None],
            ['y' * 750, 'short'],
            [None, None],
        )
        assert backend.collection.add.call_count == 2
        parent_call, child_call = backend.collection.add.call_args_list
        assert parent_call.kwargs['ids'] == ['s1', 's2']
        assert child_call.kwargs['ids'] == [
            's1_child_1',
            's1_child_2',
            's1_child_3',
        ]


class TestChromaSearch:
    def test_build_search_filter(self) -> None:
        assert ChromaDBBackend._build_search_filter(None) == {'is_child': True}
        assert ChromaDBBackend._build_search_filter({'role': 'user'}) == {
            'is_child': True,
            'role': 'user',
        }

    def test_build_parent_filter(self) -> None:
        assert ChromaDBBackend._build_parent_filter(None) == {'is_child': False}
        assert ChromaDBBackend._build_parent_filter({'role': 'user'}) == {
            'is_child': False,
            'role': 'user',
        }

    def test_has_results(self) -> None:
        assert ChromaDBBackend._has_results({'ids': [['a']]}) is True
        assert ChromaDBBackend._has_results({'ids': [[]]}) is False
        assert ChromaDBBackend._has_results({'ids': []}) is False

    def test_query_children(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        backend._query_children('q', 2, {'is_child': True})
        backend.collection.query.assert_called_once()
        call = backend.collection.query.call_args
        assert call.kwargs['n_results'] == 6
        assert call.kwargs['where'] == {'is_child': True}

    def test_query_parents(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        backend._query_parents('q', 2, {'is_child': False})
        call = backend.collection.query.call_args
        assert call.kwargs['n_results'] == 2

    def test_query_with_fallback_children_hit(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        children = {'ids': [['c1']]}
        backend.collection.query.return_value = children
        assert (
            backend._query_with_fallback('q', 2, {'is_child': True}, None) is children
        )
        backend.collection.query.assert_called_once()

    def test_query_with_fallback_parents(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        empty: dict = {'ids': [[]]}
        parents = {'ids': [['p1']]}
        backend.collection.query.side_effect = [empty, parents]
        result = backend._query_with_fallback('q', 2, {'is_child': True}, None)
        assert result is parents

    def test_query_with_fallback_none(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        empty: dict = {'ids': [[]]}
        backend.collection.query.return_value = empty
        assert backend._query_with_fallback('q', 2, {'is_child': True}, None) is None

    def test_process_single_match_child(self) -> None:
        backend = make_chroma_backend()
        parent_ids: list[str] = []
        scores: dict[str, float] = {}
        parent_texts: dict[str, str] = {}
        parent_metas: dict[str, dict] = {}
        backend._process_single_match(
            'p1',
            {'parent_id': 'p1', 'is_child': True, 'role': 'user'},
            0.25,
            'child text',
            parent_ids,
            scores,
            parent_texts,
            parent_metas,
        )
        assert parent_ids == ['p1']
        assert scores['p1'] == 0.75
        assert 'parent_id' not in parent_metas['p1']
        assert 'is_child' not in parent_metas['p1']
        assert parent_metas['p1']['role'] == 'user'

    def test_process_single_match_parent(self) -> None:
        backend = make_chroma_backend()
        parent_ids: list[str] = []
        scores: dict[str, float] = {}
        parent_texts: dict[str, str] = {}
        parent_metas: dict[str, dict] = {}
        backend._process_single_match(
            'p1',
            {'is_child': False, 'role': 'user'},
            0.4,
            'parent text',
            parent_ids,
            scores,
            parent_texts,
            parent_metas,
        )
        assert parent_texts['p1'] == 'parent text'
        assert parent_metas['p1']['role'] == 'user'

    def test_process_single_match_duplicate_takes_max(self) -> None:
        backend = make_chroma_backend()
        parent_ids: list[str] = []
        scores: dict[str, float] = {}
        parent_texts: dict[str, str] = {}
        parent_metas: dict[str, dict] = {}
        backend._process_single_match(
            'p1',
            {'is_child': True, 'parent_id': 'p1'},
            0.1,
            't',
            parent_ids,
            scores,
            parent_texts,
            parent_metas,
        )
        backend._process_single_match(
            'p1',
            {'is_child': True, 'parent_id': 'p1'},
            0.05,
            't',
            parent_ids,
            scores,
            parent_texts,
            parent_metas,
        )
        assert parent_ids == ['p1']
        assert scores['p1'] == 0.95

    def test_resolve_parent_matches(self) -> None:
        backend = make_chroma_backend()
        results = {
            'ids': [['c1', 'c2']],
            'metadatas': [
                [
                    {'parent_id': 'p1', 'is_child': True, 'role': 'user'},
                    {'parent_id': 'p2', 'is_child': True, 'role': 'assistant'},
                ]
            ],
            'distances': [[0.1, 0.3]],
            'documents': [['child 1', 'child 2']],
        }
        parent_ids, scores, parent_texts, parent_metas = (
            backend._resolve_parent_matches(results)
        )
        assert parent_ids == ['p1', 'p2']
        assert scores['p1'] == 0.9
        assert scores['p2'] == 0.7
        assert parent_texts == {}

    def test_fetch_missing_parents_none_needed(self) -> None:
        backend = make_chroma_backend()
        parent_texts = {'p1': 'text'}
        parent_metas = {'p1': {'role': 'user'}}
        backend._fetch_missing_parents(['p1'], 5, parent_texts, parent_metas)
        backend.collection.get.assert_not_called()

    def test_fetch_missing_parents_gets(self) -> None:
        backend = make_chroma_backend()
        backend.collection.get.return_value = {
            'ids': ['p1', 'p2'],
            'documents': ['parent text 1', 'parent text 2'],
            'metadatas': [
                {'step_id': 'p1', 'role': 'user'},
                {'step_id': 'p2', 'role': 'assistant'},
            ],
        }
        parent_texts: dict[str, str] = {}
        parent_metas: dict[str, dict] = {}
        backend._fetch_missing_parents(['p1', 'p2'], 2, parent_texts, parent_metas)
        assert parent_texts == {'p1': 'parent text 1', 'p2': 'parent text 2'}
        assert parent_metas['p1']['role'] == 'user'

    def test_assemble_and_sort(self) -> None:
        backend = make_chroma_backend()
        result = backend._assemble_and_sort(
            ['p1', 'p2'],
            2,
            {'p1': 0.9, 'p2': 0.8},
            {'p1': 't1', 'p2': 't2'},
            {'p1': {'role': 'user'}, 'p2': {'role': 'assistant'}},
        )
        assert [r['step_id'] for r in result] == ['p1', 'p2']
        assert result[0]['score'] == 0.9
        assert result[0]['excerpt'] == 't1'

    def test_search_empty_collection(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 0
        assert backend.search('q') == []

    def test_search_full_flow(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        backend.collection.query.return_value = {
            'ids': [['p1', 'p2']],
            'metadatas': [
                [
                    {'parent_id': 'p1', 'is_child': True, 'role': 'user'},
                    {'parent_id': 'p2', 'is_child': True, 'role': 'assistant'},
                ]
            ],
            'distances': [[0.1, 0.2]],
            'documents': [['child 1', 'child 2']],
        }
        backend.collection.get.return_value = {
            'ids': ['p1', 'p2'],
            'documents': ['full text 1', 'full text 2'],
            'metadatas': [
                {'step_id': 'p1', 'role': 'user'},
                {'step_id': 'p2', 'role': 'assistant'},
            ],
        }
        results = backend.search('q', k=2)
        assert len(results) == 2
        assert results[0]['step_id'] == 'p1'
        assert results[0]['excerpt'] == 'full text 1'
        assert results[0]['role'] == 'user'

    def test_search_falls_back_to_parents(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        empty: dict = {
            'ids': [[]],
            'metadatas': [[]],
            'distances': [[]],
            'documents': [[]],
        }
        parent_hit = {
            'ids': [['p1']],
            'metadatas': [[{'is_child': False, 'role': 'user'}]],
            'distances': [[0.2]],
            'documents': [['parent text']],
        }
        backend.collection.query.side_effect = [empty, parent_hit]
        results = backend.search('q', k=2)
        assert results == [
            {
                'step_id': 'p1',
                'score': 0.8,
                'excerpt': 'parent text',
                'is_child': False,
                'role': 'user',
            }
        ]

    def test_search_no_results(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 10
        empty: dict = {
            'ids': [[]],
            'metadatas': [[]],
            'distances': [[]],
            'documents': [[]],
        }
        backend.collection.query.return_value = empty
        assert backend.search('q') == []


class TestChromaAsync:
    async def test_async_add(self) -> None:
        backend = make_chroma_backend()
        await backend.async_add('s1', 'user', None, None, 'hello')
        backend.collection.add.assert_called_once()

    async def test_async_search(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 0
        assert await backend.async_search('q') == []


class TestChromaDelete:
    def test_delete_by_metadata_success(self) -> None:
        backend = make_chroma_backend()
        assert backend.delete_by_metadata({'role': 'user'}) == 1
        backend.collection.delete.assert_called_once_with(where={'role': 'user'})

    def test_delete_by_metadata_failure(self) -> None:
        backend = make_chroma_backend()
        backend.collection.delete.side_effect = Exception('boom')
        assert backend.delete_by_metadata({'role': 'user'}) == 0

    def test_delete_by_ids_success(self) -> None:
        backend = make_chroma_backend()
        assert backend.delete_by_ids(['a', 'b']) == 2
        backend.collection.delete.assert_called_once_with(ids=['a', 'b'])

    def test_delete_by_ids_failure(self) -> None:
        backend = make_chroma_backend()
        backend.collection.delete.side_effect = Exception('boom')
        assert backend.delete_by_ids(['a']) == 0


class TestChromaStats:
    def test_stats_with_model_loaded(self) -> None:
        backend = make_chroma_backend()
        backend.collection.count.return_value = 3
        stats = backend.stats()
        assert stats['embedding_dim'] == 384
        assert stats['model_loaded'] is True

    def test_prepare_text(self) -> None:
        assert ChromaDBBackend._prepare_text('r', 'c') == 'r\nc'
        assert ChromaDBBackend._prepare_text(None, 'c') == 'c'
        assert ChromaDBBackend._prepare_text('r', None) == 'r'
        assert ChromaDBBackend._prepare_text(None, None) == ''


class TestSQLiteBasics:
    def test_default_persist_directory(self, tmp_path) -> None:
        with patch(
            'backend.context.vector_store._local_vector_store.get_active_local_data_root',
            return_value=str(tmp_path),
        ):
            backend = SQLiteBM25Backend('my-coll')
        assert backend.db_path == tmp_path / 'memory' / 'sqlite' / 'my-coll_fts.db'
        backend._close_conn()

    def test_close_conn(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        conn = backend._get_conn()
        assert conn is backend._get_conn()
        backend._close_conn()
        assert getattr(backend._local, 'conn', None) is None

    def test_close_conn_ignores_close_error(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend._get_conn()

        class BadConn:
            def close(self) -> None:
                raise OSError('boom')

        backend._local.conn = BadConn()
        backend._close_conn()
        assert getattr(backend._local, 'conn', None) is None

    def test_meta_string(self) -> None:
        assert SQLiteBM25Backend._meta_string(None) is None
        assert SQLiteBM25Backend._meta_string('x') == 'x'
        assert SQLiteBM25Backend._meta_string(42) == '42'
        assert SQLiteBM25Backend._meta_string(4.2) == '4.2'
        assert SQLiteBM25Backend._meta_string(True) == 'True'
        assert SQLiteBM25Backend._meta_string('') is None
        assert SQLiteBM25Backend._meta_string(['a']) is None

    def test_prepare_text(self) -> None:
        assert SQLiteBM25Backend._prepare_text('r', 'c') == 'r\nc'
        assert SQLiteBM25Backend._prepare_text(None, 'c') == 'c'
        assert SQLiteBM25Backend._prepare_text('r', None) == 'r'
        assert SQLiteBM25Backend._prepare_text(None, None) == ''

    def test_load_row_metadata(self) -> None:
        assert SQLiteBM25Backend._load_row_metadata('{"a": 1}') == {'a': 1}
        assert SQLiteBM25Backend._load_row_metadata('[1, 2]') == {}
        assert SQLiteBM25Backend._load_row_metadata('not json') == {}

    def test_metadata_matches_filter(self) -> None:
        assert SQLiteBM25Backend._metadata_matches_filter({'a': 1}, {'a': 1}) is True
        assert SQLiteBM25Backend._metadata_matches_filter({'a': 1}, {'a': 2}) is False
        assert SQLiteBM25Backend._metadata_matches_filter({'a': 1}, {'b': 1}) is False

    def test_append_fts_row(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        results: list[dict] = []
        added = backend._append_fts_row(
            results,
            step_id='s1',
            content='text',
            meta_json=json.dumps({'role': 'user'}),
            score=-0.5,
            filter_metadata={'role': 'assistant'},
            k=5,
        )
        assert added is False
        assert results == []
        added = backend._append_fts_row(
            results,
            step_id='s1',
            content='text',
            meta_json=json.dumps({'role': 'user'}),
            score=-0.5,
            filter_metadata=None,
            k=1,
        )
        assert added is True
        assert results[0]['step_id'] == 's1'
        assert results[0]['score'] == 0.5

    def test_build_fts_match_query(self) -> None:
        assert (
            SQLiteBM25Backend._build_fts_match_query('hello world')
            == '"hello" OR "world"'
        )
        assert SQLiteBM25Backend._build_fts_match_query('a b') is None
        assert SQLiteBM25Backend._build_fts_match_query('   ') is None
        assert (
            SQLiteBM25Backend._build_fts_match_query('say "hi"') == '"say" OR """hi"""'
        )

    def test_indexed_filter_clause(self) -> None:
        assert SQLiteBM25Backend._indexed_filter_clause(None) == ('', [])
        assert SQLiteBM25Backend._indexed_filter_clause({'session_id': 's'}) == (
            ' AND meta.session_id = ?',
            ['s'],
        )
        clause, params = SQLiteBM25Backend._indexed_filter_clause(
            {'session_id': 's', 'artifact_hash': 'h', 'role': 'r'}
        )
        assert clause == (
            ' AND meta.session_id = ? AND meta.artifact_hash = ? AND meta.role = ?'
        )
        assert params == ['s', 'h', 'r']
        assert SQLiteBM25Backend._indexed_filter_clause({'kind': 'x'}) == ('', [])


class TestSQLiteAdd:
    def test_add_and_stats(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add(
            's1', 'user', 'hash1', 'rationale', 'apple banana', {'session_id': 'sess'}
        )
        assert backend.stats()['num_documents'] == 1
        assert backend.db_path.exists()

    def test_add_batch_empty(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add_batch([], [], [], [], [])
        assert backend.stats()['num_documents'] == 0

    def test_add_batch_with_metadatas(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add_batch(
            ['s1', 's2'],
            ['user', 'assistant'],
            [None, 'h2'],
            [None, None],
            ['apple pie', 'orange juice'],
            [{'session_id': 'a'}, None],
        )
        assert backend.stats()['num_documents'] == 2
        results = backend.search('apple')
        assert results[0]['step_id'] == 's1'

    def test_add_batch_default_metadatas(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add_batch(
            ['s1', 's2'],
            ['user', 'user'],
            [None, None],
            [None, None],
            ['apple', 'orange'],
        )
        assert backend.stats()['num_documents'] == 2


class TestSQLiteSearch:
    def test_search_basic(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add(
            's1', 'user', None, None, 'apple banana cherry', {'session_id': 'a'}
        )
        backend.add(
            's2', 'assistant', None, None, 'apple pie recipe', {'session_id': 'b'}
        )
        results = backend.search('apple', k=2)
        assert len(results) == 2

    def test_search_indexed_filter(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple banana', {'session_id': 'a'})
        backend.add('s2', 'user', None, None, 'apple pie', {'session_id': 'b'})
        results = backend.search('apple', k=5, filter_metadata={'session_id': 'a'})
        assert [r['step_id'] for r in results] == ['s1']

    def test_search_residual_filter(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple tart', {'kind': 'dessert'})
        backend.add('s2', 'user', None, None, 'apple crisp', {'kind': 'other'})
        results = backend.search('apple', k=5, filter_metadata={'kind': 'dessert'})
        assert [r['step_id'] for r in results] == ['s1']

    def test_search_no_match_query(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', None)
        assert backend.search('a') == []

    def test_search_operational_error(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend._get_conn = MagicMock(side_effect=sqlite3.OperationalError('boom'))
        assert backend.search('apple') == []


class TestSQLiteDelete:
    def test_delete_by_metadata_empty_filter(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', None)
        assert backend.delete_by_metadata({}) == 0

    def test_delete_by_metadata_pure_indexed(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', {'session_id': 'a'})
        backend.add('s2', 'user', None, None, 'orange', {'session_id': 'b'})
        assert backend.delete_by_metadata({'session_id': 'a'}) == 1
        assert backend.stats()['num_documents'] == 1
        assert backend.search('apple') == []

    def test_delete_by_metadata_mixed(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', {'session_id': 'a', 'kind': 'x'})
        backend.add(
            's2', 'user', None, None, 'orange', {'session_id': 'a', 'kind': 'y'}
        )
        assert backend.delete_by_metadata({'session_id': 'a', 'kind': 'x'}) == 1
        assert backend.stats()['num_documents'] == 1

    def test_delete_by_metadata_python_scan(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', {'kind': 'x'})
        backend.add('s2', 'user', None, None, 'orange', {'kind': 'y'})
        assert backend.delete_by_metadata({'kind': 'x'}) == 1
        assert backend.stats()['num_documents'] == 1

    def test_delete_by_metadata_no_match(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', {'kind': 'x'})
        assert backend.delete_by_metadata({'kind': 'zzz'}) == 0

    def test_delete_by_ids(self, tmp_path) -> None:
        backend = make_sqlite_backend(tmp_path)
        backend.add('s1', 'user', None, None, 'apple', None)
        backend.add('s2', 'user', None, None, 'orange', None)
        assert backend.delete_by_ids([]) == 0
        assert backend.delete_by_ids(['s1']) == 1
        assert backend.stats()['num_documents'] == 1
        assert backend.delete_by_ids(['nope']) == 0
