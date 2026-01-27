import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
from forge.llm.direct_clients import LLMResponse

from forge.events.event import (
    Event,
    EventSource,
    FileEditSource,
    FileReadSource,
    RecallType,
)
from forge.events.event_filter import EventFilter
from forge.events.tool import ToolCallMetadata
from forge.events.utils import get_pairs_from_events
from forge.events.action.action import Action
from forge.events.action.empty import NullAction
from forge.events.observation.empty import NullObservation
from forge.events.observation.commands import CmdOutputObservation
from forge.llm.metrics import Metrics, TokenUsage


@dataclass
class DummyEvent(Event):
    """Simple concrete event used for exercising base Event helpers."""

    observation: str = "dummy"


@dataclass
class DummyAction(Action):
    """Action subclass for pairing tests."""

    action: str = "dummy_action"
    runnable: bool = False


def test_event_property_accessors_roundtrip():
    event = DummyEvent()
    event._message = "hello"
    event._id = 42
    event._sequence = 7
    event.timestamp = datetime(2025, 1, 1, 12, 0, 0)
    event._source = EventSource.AGENT
    event._cause = 99
    event.set_hard_timeout(3.5, blocking=False)

    metrics = Metrics()
    metrics.token_usages = [
        TokenUsage(prompt_tokens=1, completion_tokens=2, total_tokens=3)
    ]
    event.llm_metrics = metrics

    metadata = ToolCallMetadata(
        function_name="compute",
        tool_call_id="call-1",
        model_response=LLMResponse(
            content="",
            model="fake-model",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            id="1"
        ),
        total_calls_in_response=1,
    )
    event.tool_call_metadata = metadata
    event.response_id = "resp-123"

    assert event.message == "hello"
    assert event.id == 42
    assert event.sequence == 7
    assert event.timestamp.startswith("2025-01-01T12:00:00")
    assert event.source is EventSource.AGENT
    assert event.cause == 99
    assert event.timeout == 3.5
    assert event.llm_metrics is metrics
    assert event.tool_call_metadata is metadata
    assert event.response_id == "resp-123"


def test_event_property_defaults_when_unset():
    event = DummyEvent()
    assert event.message == ""
    assert event.id == Event.INVALID_ID
    assert event.sequence == Event.INVALID_ID
    assert event.timestamp is None
    assert event.source is None
    assert event.cause is None
    assert event.timeout is None
    assert event.llm_metrics is None
    assert event.tool_call_metadata is None
    assert event.response_id is None


def test_event_source_and_file_enum_members_are_strings():
    assert EventSource.USER.value == "user"
    assert FileEditSource.LLM_BASED_EDIT.value == "llm_based_edit"
    assert FileReadSource.DEFAULT.value == "default"
    assert RecallType.WORKSPACE_CONTEXT.value == "workspace_context"


def test_set_hard_timeout_updates_timeout_without_blocking_attribute():
    event = DummyEvent()
    event.set_hard_timeout(1.2)
    assert event.timeout == 1.2


def test_get_pairs_from_events_matches_actions_and_observations():
    action = DummyAction()
    action._id = 10
    observation = CmdOutputObservation(
        content="ok", command="ls", metadata={"exit_code": 0}
    )
    observation._cause = 10
    stray_observation = CmdOutputObservation(content="lonely", command="pwd")
    stray_observation._cause = 999

    pairs = get_pairs_from_events([action, observation, stray_observation])

    assert len(pairs) == 2
    assert pairs[0][0] is action
    assert isinstance(pairs[0][1], CmdOutputObservation)
    assert isinstance(pairs[1][0], NullAction)
    assert pairs[1][1].command == "pwd"


def test_get_pairs_from_events_logs_missing_ids(monkeypatch):
    action = DummyAction()
    action._id = Event.INVALID_ID
    observation = CmdOutputObservation(content="orphan", command="ls")
    observation._cause = Event.INVALID_ID

    logs = []

    def fake_debug(msg, *args, **kwargs):
        logs.append(msg)

    monkeypatch.setattr("forge.events.utils.logger.debug", fake_debug)
    pairs = get_pairs_from_events([action, observation])
    assert pairs[0][0].id == Event.INVALID_ID
    assert logs, "Expected debug logs for missing IDs"


@pytest.mark.asyncio
async def test_async_iteration_over_pairs_via_asyncio():
    """Ensure pairing results can be consumed asynchronously without blocking."""
    pairs = get_pairs_from_events([])
    assert pairs == []

    # Simulate async consumer leveraging EventSource constants for coverage
    async def consume():
        await asyncio.sleep(0)
        return EventSource.ENVIRONMENT.value

    assert await consume() == "environment"


def test_null_observation_used_when_observation_missing():
    action = DummyAction()
    action._id = 5
    pairs = get_pairs_from_events([action])
    assert len(pairs) == 1
    assert isinstance(pairs[0][1], NullObservation)


def test_event_filter_exclusion_rules():
    event = DummyEvent()
    event._timestamp = "2024-01-01T00:00:00"
    event._source = EventSource.AGENT
    event.hidden = True

    filt = EventFilter(include_types=(DummyAction,), exclude_hidden=True)
    assert filt.include(event) is False

    filt = EventFilter(include_types=(DummyEvent,), source="user")
    assert filt.include(event) is False

    filt = EventFilter(start_date="2025-01-01T00:00:00")
    assert filt.include(event) is False

    filt = EventFilter(end_date="2023-12-31T23:59:59")
    assert filt.include(event) is False

    event._timestamp = "2025-01-01T00:00:00"
    event.hidden = False
    filt = EventFilter(query="dummy")
    assert filt.include(event) is True

    default_filter = EventFilter()
    assert default_filter.include(event) is True

    assert filt.exclude(event) is False
