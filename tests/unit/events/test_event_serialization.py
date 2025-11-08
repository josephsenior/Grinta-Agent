from forge.events.action import CmdRunAction, MessageAction
from forge.events.action.action import ActionSecurityRisk
from forge.events.observation import CmdOutputMetadata, CmdOutputObservation
from forge.events.serialization import event_from_dict, event_to_dict
from forge.llm.metrics import Cost, Metrics, ResponseLatency, TokenUsage


def test_command_output_success_serialization():
    obs = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt", metadata=CmdOutputMetadata(exit_code=0))
    serialized = event_to_dict(obs)
    assert serialized["success"] is True
    obs = CmdOutputObservation(
        command="ls", content="No such file or directory", metadata=CmdOutputMetadata(exit_code=1)
    )
    serialized = event_to_dict(obs)
    assert serialized["success"] is False


def test_metrics_basic_serialization():
    action = MessageAction(content="Hello, world!")
    metrics = Metrics()
    metrics.accumulated_cost = 0.03
    action._llm_metrics = metrics
    serialized = event_to_dict(action)
    assert "llm_metrics" in serialized
    assert serialized["llm_metrics"]["accumulated_cost"] == 0.03
    assert serialized["llm_metrics"]["costs"] == []
    assert serialized["llm_metrics"]["response_latencies"] == []
    assert serialized["llm_metrics"]["token_usages"] == []
    deserialized = event_from_dict(serialized)
    assert deserialized.llm_metrics is not None
    assert deserialized.llm_metrics.accumulated_cost == 0.03
    assert len(deserialized.llm_metrics.costs) == 0
    assert len(deserialized.llm_metrics.response_latencies) == 0
    assert len(deserialized.llm_metrics.token_usages) == 0


def test_metrics_full_serialization():
    """Test full serialization and deserialization of metrics."""
    # Setup test data
    obs = _create_test_observation()
    metrics = _create_test_metrics()
    obs._llm_metrics = metrics

    # Test serialization
    serialized = event_to_dict(obs)
    _verify_serialized_metrics(serialized)

    # Test deserialization
    deserialized = event_from_dict(serialized)
    _verify_deserialized_metrics(deserialized)


def _create_test_observation():
    """Create a test observation for metrics testing."""
    return CmdOutputObservation(command="ls", content="test.txt", metadata=CmdOutputMetadata(exit_code=0))


def _create_test_metrics():
    """Create test metrics with various components."""
    metrics = Metrics(model_name="test-model")
    metrics.accumulated_cost = 0.03

    # Add cost
    cost = Cost(model="test-model", cost=0.02)
    metrics._costs.append(cost)

    # Add latency
    latency = ResponseLatency(model="test-model", latency=0.5, response_id="test-id")
    metrics.response_latencies = [latency]

    # Add token usage
    usage = TokenUsage(
        model="test-model",
        prompt_tokens=10,
        completion_tokens=20,
        cache_read_tokens=0,
        cache_write_tokens=0,
        response_id="test-id",
    )
    metrics.token_usages = [usage]

    return metrics


def _verify_serialized_metrics(serialized: dict):
    """Verify serialized metrics contain expected data."""
    assert "llm_metrics" in serialized
    metrics_dict = serialized["llm_metrics"]

    # Verify accumulated cost
    assert metrics_dict["accumulated_cost"] == 0.03

    # Verify costs
    assert len(metrics_dict["costs"]) == 1
    assert metrics_dict["costs"][0]["cost"] == 0.02

    # Verify response latencies
    assert len(metrics_dict["response_latencies"]) == 1
    assert metrics_dict["response_latencies"][0]["latency"] == 0.5

    # Verify token usages
    assert len(metrics_dict["token_usages"]) == 1
    assert metrics_dict["token_usages"][0]["prompt_tokens"] == 10
    assert metrics_dict["token_usages"][0]["completion_tokens"] == 20


def _verify_deserialized_metrics(deserialized):
    """Verify deserialized metrics contain expected data."""
    assert deserialized.llm_metrics is not None

    # Verify accumulated cost
    assert deserialized.llm_metrics.accumulated_cost == 0.03

    # Verify costs
    assert len(deserialized.llm_metrics.costs) == 1
    assert deserialized.llm_metrics.costs[0].cost == 0.02

    # Verify response latencies
    assert len(deserialized.llm_metrics.response_latencies) == 1
    assert deserialized.llm_metrics.response_latencies[0].latency == 0.5

    # Verify token usages
    assert len(deserialized.llm_metrics.token_usages) == 1
    assert deserialized.llm_metrics.token_usages[0].prompt_tokens == 10
    assert deserialized.llm_metrics.token_usages[0].completion_tokens == 20


def test_metrics_none_serialization():
    obs = CmdOutputObservation(command="ls", content="test.txt", metadata=CmdOutputMetadata(exit_code=0))
    obs._llm_metrics = None
    serialized = event_to_dict(obs)
    assert "llm_metrics" not in serialized
    deserialized = event_from_dict(serialized)
    assert deserialized.llm_metrics is None


def test_action_risk_serialization():
    action = CmdRunAction(command="rm -rf /tmp/test")
    action.security_risk = ActionSecurityRisk.HIGH
    serialized = event_to_dict(action)
    assert "security_risk" in serialized["args"]
    assert serialized["args"]["security_risk"] == ActionSecurityRisk.HIGH.value
    deserialized = event_from_dict(serialized)
    assert deserialized.security_risk == ActionSecurityRisk.HIGH
    action = CmdRunAction(command="ls")
    serialized = event_to_dict(action)
    assert "security_risk" in serialized["args"]
    assert serialized["args"]["security_risk"] == ActionSecurityRisk.UNKNOWN.value
    deserialized = event_from_dict(serialized)
    assert deserialized.security_risk == ActionSecurityRisk.UNKNOWN
