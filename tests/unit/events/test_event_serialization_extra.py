"""Additional tests exercising event serialization utilities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from litellm import ModelResponse
import pytest

from forge.events.action.action import ActionSecurityRisk
from forge.events.action.commands import CmdRunAction
from forge.events.action.empty import NullAction
from forge.events.event import Event, EventSource, RecallType
from forge.events.observation.commands import CmdOutputMetadata, CmdOutputObservation
from forge.events.serialization.event import event_from_dict, event_to_dict, event_to_trajectory, truncate_content
from forge.events.tool import ToolCallMetadata
from forge.llm.metrics import Metrics


def test_event_to_dict_includes_timeout_and_security_risk() -> None:
    action = CmdRunAction(command="ls")
    action.security_risk = ActionSecurityRisk.HIGH
    action.set_hard_timeout(2.5)
    action._id = 7
    action._source = EventSource.AGENT
    action._timestamp = "2024-01-01T00:00:00"

    metrics = Metrics()
    metrics.add_cost(0.01)
    action.llm_metrics = metrics
    action.tool_call_metadata = ToolCallMetadata(
        function_name="fn",
        tool_call_id="call-1",
        model_response=ModelResponse(id="1", choices=[], created=0, model="gpt-4", object="chat.completion"),
        total_calls_in_response=1,
    )

    serialized = event_to_dict(action)

    assert serialized["args"]["security_risk"] == ActionSecurityRisk.HIGH.value
    assert serialized["timeout"] == pytest.approx(2.5)
    assert serialized["source"] == EventSource.AGENT.value
    assert serialized["tool_call_metadata"]["function_name"] == "fn"
    assert serialized["llm_metrics"]["accumulated_cost"] == pytest.approx(0.01)


def test_event_to_dict_observation_converts_extras() -> None:
    obs = CmdOutputObservation(
        content="output",
        command="ls",
        metadata=CmdOutputMetadata(exit_code=0, prefix="[", suffix="]"),
    )
    obs._id = 11
    obs._sequence = 12
    obs._source = EventSource.ENVIRONMENT
    obs._timestamp = datetime.now(timezone.utc).isoformat()

    serialized = event_to_dict(obs)

    assert "sequence" not in serialized
    assert serialized["source"] == EventSource.ENVIRONMENT.value
    assert serialized["extras"]["metadata"]["exit_code"] == 0
    assert serialized["success"] is True


class DemoEnum(Enum):
    FOO = "foo"


@dataclass
class ScreenshotObservation(Event):
    content: str
    screenshot: str | None = None
    dom_object: str | None = None
    keep_field: DemoEnum = DemoEnum.FOO
    observation: str = "custom"


def test_event_to_trajectory_filters_extras() -> None:
    observation = ScreenshotObservation(
        content="body",
        screenshot="imgdata",
        dom_object="div",
    )
    observation._id = 9

    without_shots = event_to_trajectory(observation, include_screenshots=False)
    with_shots = event_to_trajectory(observation, include_screenshots=True)

    assert without_shots["extras"]["keep_field"] == DemoEnum.FOO.value
    assert "screenshot" not in without_shots["extras"]
    assert "dom_object" not in without_shots["extras"]

    assert with_shots["extras"]["screenshot"] == "imgdata"
    assert "dom_object" not in with_shots["extras"]


def test_event_to_trajectory_returns_none_for_null_action() -> None:
    action = NullAction()
    assert event_to_trajectory(action) is None


def test_event_to_dict_for_non_dataclass_event() -> None:
    class FakeEvent:
        def __init__(self) -> None:
            self.id = 5
            self.sequence = 6
            self.timestamp = "2024-02-02T00:00:00"
            self.source = EventSource.AGENT

        def __str__(self) -> str:
            return "non-dataclass event"

    event = FakeEvent()
    data = event_to_dict(event)

    assert data["id"] == 5
    assert data["sequence"] == 6
    assert data["timestamp"] == "2024-02-02T00:00:00"
    assert data["source"] == EventSource.AGENT.value
    assert data["content"] == "non-dataclass event"
    assert data["observation"] == "fallback"


def test_truncate_content_midpoint() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    truncated = truncate_content(text, max_chars=10)
    assert truncated.startswith("abcde")
    assert truncated.endswith("vwxyz")
    assert "[... Observation truncated due to length ...]" in truncated
    assert truncate_content(text, max_chars=-1) == text


def test_event_from_dict_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        event_from_dict({"foo": "bar"})


def test_event_from_dict_populates_llm_metrics_and_metadata() -> None:
    data = {
        "action": "finish",
        "llm_metrics": {
            "accumulated_cost": 1.25,
            "max_budget_per_task": 3.0,
            "costs": [{"model": "gpt", "cost": 0.5, "prompt_tokens": 10, "timestamp": 0.0}],
            "response_latencies": [{"model": "gpt", "latency": 0.7, "response_id": "resp"}],
            "token_usages": [{"model": "gpt", "prompt_tokens": 5, "completion_tokens": 7}],
            "accumulated_token_usage": {"model": "gpt", "prompt_tokens": 5, "completion_tokens": 7},
        },
        "tool_call_metadata": {"function_name": "fn"},
    }

    event = event_from_dict(data)

    metrics = event.llm_metrics
    assert metrics.accumulated_cost == 1.25
    assert metrics.max_budget_per_task == 3.0
    assert metrics.costs[-1].cost == 0.5
    assert metrics.response_latencies[-1].latency == 0.7
    assert metrics.token_usages[-1].prompt_tokens == 5
    assert metrics.accumulated_token_usage.prompt_tokens == 5
    # tool_call_metadata should be None when required fields missing
    assert event.tool_call_metadata is None

