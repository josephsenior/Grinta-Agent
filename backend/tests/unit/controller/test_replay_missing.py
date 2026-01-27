"""Tests for replay.py missing coverage."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from forge.controller.replay import ReplayManager
from forge.events.action.empty import NullAction
from forge.events.action.message import MessageAction
from forge.events.event import EventSource
from forge.events.observation.empty import NullObservation
from forge.events.serialization.event import event_from_dict


def test_replay_manager_init_with_events():
    """Test ReplayManager initialization with events."""
    action = NullAction()
    action._source = EventSource.AGENT
    events = [action]
    manager = ReplayManager(events)
    assert manager.replay_mode is True
    assert len(manager.replay_events) == 1
    assert manager.replay_index == 0


def test_replay_manager_init_with_none():
    """Test ReplayManager initialization with None."""
    manager = ReplayManager(None)
    assert manager.replay_mode is False
    assert manager.replay_events == []
    assert manager.replay_index == 0


def test_replay_manager_init_with_empty_list():
    """Test ReplayManager initialization with empty list."""
    manager = ReplayManager([])
    assert manager.replay_mode is False
    assert manager.replay_events == []
    assert manager.replay_index == 0


def test_replay_manager_filters_environment_events():
    """Test that ReplayManager filters out environment events."""
    action = NullAction()
    action._source = EventSource.AGENT
    env_action = NullAction()
    env_action._source = EventSource.ENVIRONMENT
    events = [action, env_action]
    manager = ReplayManager(events)
    assert len(manager.replay_events) == 1
    assert manager.replay_events[0] == action


def test_replay_manager_filters_null_observations():
    """Test that ReplayManager filters out NullObservations."""
    action = NullAction()
    action._source = EventSource.AGENT
    null_obs = NullObservation(content="none")
    null_obs._source = EventSource.AGENT
    events = [action, null_obs]
    manager = ReplayManager(events)
    assert len(manager.replay_events) == 1
    assert manager.replay_events[0] == action


def test_replay_manager_sets_wait_for_response_false():
    """Test that ReplayManager sets wait_for_response to False for MessageActions."""
    message_action = MessageAction(content="test", wait_for_response=True)
    message_action._source = EventSource.AGENT
    action = NullAction()
    action._source = EventSource.AGENT
    events = [message_action, action]
    manager = ReplayManager(events)
    assert manager.replay_events[0].wait_for_response is False


def test_replay_manager_should_replay_false_when_not_in_replay_mode():
    """Test should_replay returns False when not in replay mode."""
    manager = ReplayManager(None)
    assert manager.should_replay() is False


def test_replay_manager_should_replay_false_when_index_out_of_bounds():
    """Test should_replay returns False when replay_index is out of bounds."""
    action = NullAction()
    action.source = EventSource.AGENT
    manager = ReplayManager([action])
    manager.replay_index = 10  # Out of bounds
    assert manager.should_replay() is False


def test_replay_manager_should_replay_skips_non_actions():
    """Test should_replay skips non-action events."""
    from forge.events.observation.commands import CmdOutputObservation

    action = NullAction()
    action._source = EventSource.AGENT
    obs = CmdOutputObservation(command="ls", exit_code=0, content="")
    obs._source = EventSource.AGENT
    events = [obs, action]
    manager = ReplayManager(events)
    # Should skip the observation and return True for the action
    assert manager.should_replay() is True
    assert manager.replay_index == 1  # Should have advanced past the observation


def test_replay_manager_step():
    """Test step method returns next action."""
    action1 = NullAction()
    action1._source = EventSource.AGENT
    action2 = NullAction()
    action2._source = EventSource.AGENT
    manager = ReplayManager([action1, action2])
    manager.replay_index = 0
    result = manager.step()
    assert result == action1
    assert manager.replay_index == 1


def test_replay_manager_step_raises_on_non_action():
    """Test step raises RuntimeError when event is not an Action."""
    from forge.events.observation.commands import CmdOutputObservation

    obs = CmdOutputObservation(command="ls", exit_code=0, content="")
    obs._source = EventSource.AGENT
    # Manually set replay_index to point to observation
    manager = ReplayManager([obs])
    manager.replay_index = 0
    # Manually set replay_events to include non-action
    manager.replay_events = [obs]
    with pytest.raises(RuntimeError, match="Unexpected non-action event"):
        manager.step()


def test_get_replay_events():
    """Test get_replay_events converts trajectory to events."""
    trajectory = [
        {
            "action": "null",
            "args": {},
            "source": "agent",
        }
    ]
    events = ReplayManager.get_replay_events(trajectory)
    assert len(events) == 1
    assert isinstance(events[0], NullAction)


def test_get_replay_events_filters_environment():
    """Test get_replay_events filters out environment events."""
    trajectory = [
        {
            "action": "null",
            "args": {},
            "source": "agent",
        },
        {
            "action": "null",
            "args": {},
            "source": "environment",
        },
    ]
    events = ReplayManager.get_replay_events(trajectory)
    assert len(events) == 1
    assert events[0].source == EventSource.AGENT


def test_get_replay_events_resets_ids():
    """Test get_replay_events resets event IDs."""
    trajectory = [
        {
            "action": "null",
            "args": {},
            "source": "agent",
            "_id": "test-id-123",
        }
    ]
    events = ReplayManager.get_replay_events(trajectory)
    assert events[0]._id is None

