from typing import Any, cast

import pytest

from forge.controller.replay import ReplayManager
from forge.events import EventSource
from forge.events.action import CmdRunAction, MessageAction
from forge.events.observation import NullObservation


def _build_events():
    msg = MessageAction(content="hello", wait_for_response=True)
    msg._source = EventSource.AGENT
    action = CmdRunAction(command="ls -la")
    action._source = EventSource.AGENT
    null_obs = NullObservation(content="none")
    null_obs._source = EventSource.AGENT
    env_event = MessageAction(content="ignore")
    env_event._source = EventSource.ENVIRONMENT
    return [env_event, null_obs, msg, action]


def test_replay_manager_filters_and_replays():
    manager = ReplayManager(_build_events())
    assert manager.replay_mode is True
    assert manager.should_replay()
    step = manager.step()
    assert isinstance(step, MessageAction)
    assert manager.should_replay()
    step2 = manager.step()
    assert isinstance(step2, CmdRunAction)
    # Wait for response flag is cleared during initialization
    first_event = manager.replay_events[0]
    if isinstance(first_event, MessageAction):
        assert first_event.wait_for_response is False
    else:
        pytest.fail("First replay event is not a MessageAction")
    assert not manager.should_replay()


def test_replay_manager_from_trajectory():
    trajectory = [
        {"action": "message", "args": {"content": "hi"}, "source": "agent"},
        {"action": "run", "args": {"command": "echo hi"}, "source": "agent"},
    ]
    events = ReplayManager.get_replay_events(trajectory)
    assert len(events) == 2
    assert isinstance(events[0], MessageAction)
    with pytest.raises(ValueError):
        ReplayManager.get_replay_events(cast(Any, "not-a-list"))
