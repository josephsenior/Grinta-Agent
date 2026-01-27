import base64
import json
import pickle
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from forge.core.config import LLMConfig, ForgeConfig
from forge.llm.llm import LLM
from forge.llm.llm_registry import LLMRegistry, RegistryEvent
from forge.llm.metrics import Metrics
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.memory import InMemoryFileStore


@pytest.fixture
def mock_file_store():
    """Create a mock file store for testing."""
    return InMemoryFileStore({})


@pytest.fixture
def conversation_stats(mock_file_store):
    """Create a ConversationStats instance for testing."""
    return ConversationStats(
        file_store=mock_file_store,
        conversation_id="test-conversation-id",
        user_id="test-user-id",
    )


@pytest.fixture
def mock_llm_registry():
    """Create a mock LLM registry that properly simulates LLM registration."""
    config = ForgeConfig()
    return LLMRegistry(config=config, agent_cls=None, retry_listener=None)


@pytest.fixture
def connected_registry_and_stats(mock_llm_registry, conversation_stats):
    """Connect the LLMRegistry and ConversationStats properly."""
    mock_llm_registry.subscribe(conversation_stats.register_llm)
    return (mock_llm_registry, conversation_stats)


def test_conversation_stats_initialization(conversation_stats):
    """Test that ConversationStats initializes correctly."""
    assert conversation_stats.conversation_id == "test-conversation-id"
    assert conversation_stats.user_id == "test-user-id"
    assert conversation_stats.service_to_metrics == {}
    assert isinstance(conversation_stats.restored_metrics, dict)


def test_save_metrics(conversation_stats, mock_file_store):
    """Test that metrics are saved correctly."""
    service_id = "test-service"
    metrics = Metrics(model_name="gpt-4")
    metrics.add_cost(0.05)
    conversation_stats.service_to_metrics[service_id] = metrics
    conversation_stats.save_metrics()
    try:
        encoded = mock_file_store.read(conversation_stats.metrics_path)
        decoded = base64.b64decode(encoded).decode("utf-8")
        restored = json.loads(decoded)
        assert service_id in restored
        m = Metrics()
        m.__setstate__(restored[service_id])
        assert m.accumulated_cost == 0.05
    except FileNotFoundError:
        pytest.fail(f"File not found: {conversation_stats.metrics_path}")


def test_maybe_restore_metrics(mock_file_store):
    """Test that metrics are restored correctly."""
    service_id = "test-service"
    metrics = Metrics(model_name="gpt-4")
    metrics.add_cost(0.1)
    service_to_metrics = {service_id: metrics}
    pickled = pickle.dumps(service_to_metrics)
    serialized_metrics = base64.b64encode(pickled).decode("utf-8")
    conversation_id = "test-conversation-id"
    user_id = "test-user-id"
    from forge.storage.locations import get_conversation_stats_filename

    metrics_path = get_conversation_stats_filename(conversation_id, user_id)
    mock_file_store.write(metrics_path, serialized_metrics)
    stats = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    assert service_id in stats.restored_metrics
    assert stats.restored_metrics[service_id].accumulated_cost == 0.1


def test_get_combined_metrics(conversation_stats):
    """Test that combined metrics are calculated correctly."""
    service1 = "service1"
    metrics1 = Metrics(model_name="gpt-4")
    metrics1.add_cost(0.05)
    metrics1.add_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=8000,
        response_id="resp1",
    )
    service2 = "service2"
    metrics2 = Metrics(model_name="gpt-3.5")
    metrics2.add_cost(0.02)
    metrics2.add_token_usage(
        prompt_tokens=200,
        completion_tokens=100,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=4000,
        response_id="resp2",
    )
    conversation_stats.service_to_metrics[service1] = metrics1
    conversation_stats.service_to_metrics[service2] = metrics2
    combined = conversation_stats.get_combined_metrics()
    assert combined.accumulated_cost == 0.07
    assert combined.accumulated_token_usage.prompt_tokens == 300
    assert combined.accumulated_token_usage.completion_tokens == 150
    assert combined.accumulated_token_usage.context_window == 8000


def test_get_metrics_for_service(conversation_stats):
    """Test that metrics for a specific service are retrieved correctly."""
    service_id = "test-service"
    metrics = Metrics(model_name="gpt-4")
    metrics.add_cost(0.05)
    conversation_stats.service_to_metrics[service_id] = metrics
    retrieved_metrics = conversation_stats.get_metrics_for_service(service_id)
    assert retrieved_metrics.accumulated_cost == 0.05
    assert retrieved_metrics is metrics
    with pytest.raises(Exception, match="LLM service does not exist"):
        conversation_stats.get_metrics_for_service("non-existent-service")


def test_register_llm_with_new_service(conversation_stats):
    """Test registering a new LLM service."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    with patch("forge.llm.llm.get_direct_client"):
        llm = LLM(service_id="new-service", config=llm_config)
        service_id = "new-service"
        event = RegistryEvent(llm=llm, service_id=service_id)
        conversation_stats.register_llm(event)
        assert service_id in conversation_stats.service_to_metrics
        assert conversation_stats.service_to_metrics[service_id] is llm.metrics


def test_register_llm_with_restored_metrics(conversation_stats):
    """Test registering an LLM service with restored metrics."""
    service_id = "restored-service"
    restored_metrics = Metrics(model_name="gpt-4")
    restored_metrics.add_cost(0.1)
    conversation_stats.restored_metrics = {service_id: restored_metrics}
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    with patch("forge.llm.llm.get_direct_client"):
        llm = LLM(service_id=service_id, config=llm_config)
        event = RegistryEvent(llm=llm, service_id=service_id)
        conversation_stats.register_llm(event)
        assert service_id in conversation_stats.service_to_metrics
        assert conversation_stats.service_to_metrics[service_id] is llm.metrics
        assert llm.metrics.accumulated_cost == 0.1
        assert service_id not in conversation_stats.restored_metrics
        assert hasattr(conversation_stats, "restored_metrics")


def test_llm_registry_notifications(connected_registry_and_stats):
    """Test that LLM registry notifications update conversation stats."""
    mock_llm_registry, conversation_stats = connected_registry_and_stats
    service_id = "test-service"
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    llm = mock_llm_registry.get_llm(service_id, llm_config)
    assert service_id in conversation_stats.service_to_metrics
    assert conversation_stats.service_to_metrics[service_id] is llm.metrics
    llm.metrics.add_cost(0.05)
    llm.metrics.add_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=8000,
        response_id="resp1",
    )
    assert conversation_stats.service_to_metrics[service_id].accumulated_cost == 0.05
    assert (
        conversation_stats.service_to_metrics[
            service_id
        ].accumulated_token_usage.prompt_tokens
        == 100
    )
    assert (
        conversation_stats.service_to_metrics[
            service_id
        ].accumulated_token_usage.completion_tokens
        == 50
    )
    combined = conversation_stats.get_combined_metrics()
    assert combined.accumulated_cost == 0.05
    assert combined.accumulated_token_usage.prompt_tokens == 100
    assert combined.accumulated_token_usage.completion_tokens == 50


def test_multiple_llm_services(connected_registry_and_stats):
    """Test tracking metrics for multiple LLM services."""
    mock_llm_registry, conversation_stats = connected_registry_and_stats
    service1 = "service1"
    service2 = "service2"
    llm_config1 = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    llm_config2 = LLMConfig(
        model="gpt-3.5-turbo",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    llm1 = mock_llm_registry.get_llm(service1, llm_config1)
    llm2 = mock_llm_registry.get_llm(service2, llm_config2)
    llm1.metrics.add_cost(0.05)
    llm1.metrics.add_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=8000,
        response_id="resp1",
    )
    llm2.metrics.add_cost(0.02)
    llm2.metrics.add_token_usage(
        prompt_tokens=200,
        completion_tokens=100,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=4000,
        response_id="resp2",
    )
    assert service1 in conversation_stats.service_to_metrics
    assert service2 in conversation_stats.service_to_metrics
    assert conversation_stats.service_to_metrics[service1].accumulated_cost == 0.05
    assert conversation_stats.service_to_metrics[service2].accumulated_cost == 0.02
    combined = conversation_stats.get_combined_metrics()
    assert combined.accumulated_cost == 0.07
    assert combined.accumulated_token_usage.prompt_tokens == 300
    assert combined.accumulated_token_usage.completion_tokens == 150
    assert combined.accumulated_token_usage.context_window == 8000


def test_register_llm_with_multiple_restored_services_bug(conversation_stats):
    """Test that reproduces the bug where del self.restored_metrics deletes entire dict instead of specific service."""
    service_id_1 = "service-1"
    service_id_2 = "service-2"
    restored_metrics_1 = Metrics(model_name="gpt-4")
    restored_metrics_1.add_cost(0.1)
    restored_metrics_2 = Metrics(model_name="gpt-3.5")
    restored_metrics_2.add_cost(0.05)
    conversation_stats.restored_metrics = {
        service_id_1: restored_metrics_1,
        service_id_2: restored_metrics_2,
    }
    llm_config_1 = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    llm_config_2 = LLMConfig(
        model="gpt-3.5-turbo",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    with patch("forge.llm.llm.get_direct_client"):
        llm_1 = LLM(service_id=service_id_1, config=llm_config_1)
        event_1 = RegistryEvent(llm=llm_1, service_id=service_id_1)
        conversation_stats.register_llm(event_1)
        assert service_id_1 in conversation_stats.service_to_metrics
        assert llm_1.metrics.accumulated_cost == 0.1
        assert service_id_2 in conversation_stats.restored_metrics
        llm_2 = LLM(service_id=service_id_2, config=llm_config_2)
        event_2 = RegistryEvent(llm=llm_2, service_id=service_id_2)
        conversation_stats.register_llm(event_2)
        assert service_id_2 in conversation_stats.service_to_metrics
        assert llm_2.metrics.accumulated_cost == 0.05
        assert not conversation_stats.restored_metrics


def test_save_and_restore_workflow(mock_file_store):
    """Test the full workflow of saving and restoring metrics."""
    conversation_id = "test-conversation-id"
    user_id = "test-user-id"
    stats1 = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    service_id = "test-service"
    metrics = Metrics(model_name="gpt-4")
    metrics.add_cost(0.05)
    metrics.add_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        cache_read_tokens=0,
        cache_write_tokens=0,
        context_window=8000,
        response_id="resp1",
    )
    stats1.service_to_metrics[service_id] = metrics
    stats1.save_metrics()
    stats2 = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    assert service_id in stats2.restored_metrics
    assert stats2.restored_metrics[service_id].accumulated_cost == 0.05
    assert (
        stats2.restored_metrics[service_id].accumulated_token_usage.prompt_tokens == 100
    )
    assert (
        stats2.restored_metrics[service_id].accumulated_token_usage.completion_tokens
        == 50
    )
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    with patch("forge.llm.llm.get_direct_client"):
        llm = LLM(service_id=service_id, config=llm_config)
        event = RegistryEvent(llm=llm, service_id=service_id)
        stats2.register_llm(event)
        assert llm.metrics.accumulated_cost == 0.05
        assert llm.metrics.accumulated_token_usage.prompt_tokens == 100
        assert llm.metrics.accumulated_token_usage.completion_tokens == 50


def test_merge_conversation_stats_success_non_overlapping(mock_file_store):
    """Merging two ConversationStats combines only restored metrics. Active metrics.

    (service_to_metrics) are not merged; if present, an error is logged but
    execution continues. Incoming restored metrics overwrite duplicates.
    """
    stats_a = ConversationStats(
        file_store=mock_file_store, conversation_id="conv-merge-a", user_id="user-x"
    )
    stats_b = ConversationStats(
        file_store=mock_file_store, conversation_id="conv-merge-b", user_id="user-x"
    )
    m_a_active = Metrics(model_name="model-a")
    m_a_active.add_cost(0.1)
    m_a_restored = Metrics(model_name="model-a")
    m_a_restored.add_cost(0.2)
    stats_a.service_to_metrics["a-active"] = m_a_active
    stats_a.restored_metrics = {"a-restored": m_a_restored}
    m_b_active = Metrics(model_name="model-b")
    m_b_active.add_cost(0.3)
    m_b_restored = Metrics(model_name="model-b")
    m_b_restored.add_cost(0.4)
    stats_b.service_to_metrics["b-active"] = m_b_active
    stats_b.restored_metrics = {"b-restored": m_b_restored}
    stats_a.merge_and_save(stats_b)
    assert set(stats_a.service_to_metrics.keys()) == {"a-active"}
    assert set(stats_a.restored_metrics.keys()) == {"a-restored", "b-restored"}
    assert stats_a.service_to_metrics["a-active"] is m_a_active
    assert stats_a.restored_metrics["a-restored"] is m_a_restored
    assert stats_a.restored_metrics["b-restored"] is m_b_restored
    encoded = mock_file_store.read(stats_a.metrics_path)
    restored_dict = json.loads(base64.b64decode(encoded).decode("utf-8"))
    assert set(restored_dict.keys()) == {"a-active", "a-restored", "b-restored"}


@pytest.mark.parametrize(
    "self_side,other_side",
    [
        ("active", "active"),
        ("restored", "active"),
        ("active", "restored"),
        ("restored", "restored"),
    ],
)
def test_merge_conversation_stats_duplicates_overwrite_and_log_errors(
    mock_file_store, self_side, other_side
):
    stats_a = ConversationStats(
        file_store=mock_file_store, conversation_id="conv-merge-a", user_id="user-x"
    )
    stats_b = ConversationStats(
        file_store=mock_file_store, conversation_id="conv-merge-b", user_id="user-x"
    )
    dupe_id = "dupe-service"
    m1 = Metrics(model_name="m")
    m1.add_cost(0.1)
    m2 = Metrics(model_name="m")
    m2.add_cost(0.2)
    if self_side == "active":
        stats_a.service_to_metrics[dupe_id] = m1
    else:
        stats_a.restored_metrics[dupe_id] = m1
    if other_side == "active":
        stats_b.service_to_metrics[dupe_id] = m2
    else:
        stats_b.restored_metrics[dupe_id] = m2
    stats_a.merge_and_save(stats_b)
    if other_side == "restored":
        assert dupe_id in stats_a.restored_metrics
        assert stats_a.restored_metrics[dupe_id] is m2
    elif self_side == "restored":
        assert dupe_id in stats_a.restored_metrics
        assert stats_a.restored_metrics[dupe_id] is m1
    else:
        assert dupe_id not in stats_a.restored_metrics


def _create_test_metrics():
    """Create test metrics for different services."""
    metrics_a = Metrics(model_name="gpt-4")
    metrics_a.add_cost(0.1)
    metrics_b = Metrics(model_name="gpt-3.5")
    metrics_b.add_cost(0.05)
    metrics_c = Metrics(model_name="claude-3")
    metrics_c.add_cost(0.08)
    return metrics_a, metrics_b, metrics_c


def _setup_initial_stats(mock_file_store, conversation_id, user_id):
    """Setup initial conversation stats with test metrics."""
    stats1 = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    service_a, service_b, service_c = "service-a", "service-b", "service-c"
    metrics_a, metrics_b, metrics_c = _create_test_metrics()

    stats1.service_to_metrics[service_a] = metrics_a
    stats1.service_to_metrics[service_b] = metrics_b
    stats1.service_to_metrics[service_c] = metrics_c
    stats1.save_metrics()

    return stats1, service_a, service_b, service_c


def _verify_restored_metrics(stats, service_a, service_b, service_c):
    """Verify that all services are in restored metrics with correct costs."""
    assert service_a in stats.restored_metrics
    assert service_b in stats.restored_metrics
    assert service_c in stats.restored_metrics
    assert stats.restored_metrics[service_a].accumulated_cost == 0.1
    assert stats.restored_metrics[service_b].accumulated_cost == 0.05
    assert stats.restored_metrics[service_c].accumulated_cost == 0.08


def _register_llm_service(stats, service_a):
    """Register an LLM service and verify the transition."""
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    with patch("forge.llm.llm.get_direct_client"):
        llm_a = LLM(service_id=service_a, config=llm_config)
        event_a = RegistryEvent(llm=llm_a, service_id=service_a)
        stats.register_llm(event_a)

    assert service_a in stats.service_to_metrics
    assert service_a not in stats.restored_metrics
    assert stats.service_to_metrics[service_a].accumulated_cost == 0.1


def _verify_remaining_restored_metrics(stats, service_b, service_c):
    """Verify that unregistered services remain in restored metrics."""
    assert service_b in stats.restored_metrics
    assert service_c in stats.restored_metrics
    assert stats.restored_metrics[service_b].accumulated_cost == 0.05
    assert stats.restored_metrics[service_c].accumulated_cost == 0.08


def test_save_metrics_preserves_restored_metrics_fix(mock_file_store):
    """Test that save_metrics correctly preserves restored metrics for unregistered services."""
    conversation_id = "test-conversation-id"
    user_id = "test-user-id"

    # Setup initial stats
    stats1, service_a, service_b, service_c = _setup_initial_stats(
        mock_file_store, conversation_id, user_id
    )

    # Load stats and verify restored metrics
    stats2 = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    _verify_restored_metrics(stats2, service_a, service_b, service_c)

    # Register one service and verify transition
    _register_llm_service(stats2, service_a)
    _verify_remaining_restored_metrics(stats2, service_b, service_c)

    # Save and reload to verify persistence
    stats2.save_metrics()
    stats3 = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    _verify_restored_metrics(stats3, service_a, service_b, service_c)


def test_save_metrics_throws_error_on_duplicate_service_ids(mock_file_store):
    """Test updated: save_metrics should NOT raise on duplicate service IDs; it should prefer service_to_metrics and proceed."""
    conversation_id = "test-conversation-id"
    user_id = "test-user-id"
    stats = ConversationStats(
        file_store=mock_file_store, conversation_id=conversation_id, user_id=user_id
    )
    service_id = "duplicate-service"
    restored_metrics = Metrics(model_name="gpt-4")
    restored_metrics.add_cost(0.1)
    stats.restored_metrics[service_id] = restored_metrics
    service_metrics = Metrics(model_name="gpt-3.5")
    service_metrics.add_cost(0.05)
    stats.service_to_metrics[service_id] = service_metrics
    stats.save_metrics()
    encoded = mock_file_store.read(stats.metrics_path)
    restored = json.loads(base64.b64decode(encoded).decode("utf-8"))
    val = restored[service_id]
    m = Metrics()
    m.__setstate__(val)
    assert service_id in restored
    assert m.accumulated_cost == 0.05
