import pytest
from unittest.mock import MagicMock, patch
from forge.memory.memory import Memory
from forge.events.action.agent import RecallAction
from forge.events.event import EventSource, RecallType
from forge.storage.data_models.knowledge_base import KnowledgeBaseSearchResult, KnowledgeBaseSettings

@pytest.fixture
def mock_event_stream():
    return MagicMock()

@pytest.fixture
def memory(mock_event_stream):
    with patch('forge.memory.memory.KnowledgeBaseManager'):
        with patch('forge.memory.memory.Memory._load_global_microagents'):
            with patch('forge.memory.memory.Memory._load_user_microagents'):
                return Memory(event_stream=mock_event_stream, sid="test-sid", user_id="test-user")

def test_on_microagent_recall_searches_kb(memory):
    # Setup
    query = "test query"
    event = RecallAction(query=query, recall_type=RecallType.KNOWLEDGE)
    event.source = EventSource.USER
    
    mock_result = KnowledgeBaseSearchResult(
        document_id="doc1",
        collection_id="col1",
        filename="test.txt",
        chunk_content="test content",
        relevance_score=0.9,
        metadata={}
    )
    memory._kb_manager.search.return_value = [mock_result]
    
    # Execute
    observation = memory._on_microagent_recall(event)
    
    # Verify
    assert observation is not None
    assert observation.recall_type == RecallType.KNOWLEDGE
    assert len(observation.knowledge_base_results) == 1
    assert observation.knowledge_base_results[0].document_id == "doc1"
    memory._kb_manager.search.assert_called_once_with(
        query=query,
        relevance_threshold=0.7,
        top_k=5,
        collection_ids=None
    )

def test_on_microagent_recall_respects_settings(memory):
    # Setup
    settings = KnowledgeBaseSettings(
        auto_search=True,
        relevance_threshold=0.5,
        search_top_k=10,
        active_collection_ids=["col1"]
    )
    memory.set_knowledge_base_settings(settings)
    
    query = "test query"
    event = RecallAction(query=query, recall_type=RecallType.KNOWLEDGE)
    event.source = EventSource.USER
    
    memory._kb_manager.search.return_value = []
    
    # Execute
    memory._on_microagent_recall(event)
    
    # Verify
    memory._kb_manager.search.assert_called_once_with(
        query=query,
        relevance_threshold=0.5,
        top_k=10,
        collection_ids=["col1"]
    )

def test_on_microagent_recall_respects_disabled_auto_search(memory):
    # Setup
    settings = KnowledgeBaseSettings(
        auto_search=False
    )
    memory.set_knowledge_base_settings(settings)
    
    query = "test query"
    event = RecallAction(query=query, recall_type=RecallType.KNOWLEDGE)
    event.source = EventSource.USER
    
    # Execute
    observation = memory._on_microagent_recall(event)
    
    # Verify
    assert observation is None
    memory._kb_manager.search.assert_not_called()
