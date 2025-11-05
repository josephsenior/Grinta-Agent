"""Unit tests for ConversationWindowCondenser.

These tests mirror the tests for `_apply_conversation_window` in the AgentController,
but adapted to test the condenser implementation. The ConversationWindowCondenser
copies the functionality of the `_apply_conversation_window` function as closely as possible.

The tests verify that the condenser:
1. Identifies essential initial events (System Message, First User Message, Recall Action/Observation)
2. Keeps roughly half of the non-essential events from recent history
3. Handles dangling observations properly
4. Returns appropriate CondensationAction objects specifying which events to forget
"""

from unittest.mock import patch
import pytest
from openhands.events import EventSource
from openhands.events.action import CmdRunAction, MessageAction, RecallAction
from openhands.events.action.agent import CondensationAction
from openhands.events.action.message import SystemMessageAction
from openhands.events.event import RecallType
from openhands.events.observation import CmdOutputObservation, RecallObservation
from openhands.memory.condenser.condenser import Condensation, View
from openhands.memory.condenser.impl.conversation_window_condenser import ConversationWindowCondenser


def create_events(event_data):
    events = []
    from openhands.events.action import CmdRunAction, RecallAction
    from openhands.events.observation import CmdOutputObservation, RecallObservation

    for i, data in enumerate(event_data):
        event_type = data["type"]
        source = data.get("source", EventSource.AGENT)
        kwargs = {}
        if event_type == RecallAction:
            kwargs["query"] = data.get("query", "")
            kwargs["recall_type"] = data.get("recall_type", RecallType.KNOWLEDGE)
        elif event_type == RecallObservation:
            kwargs["content"] = data.get("content", "")
            kwargs["recall_type"] = data.get("recall_type", RecallType.KNOWLEDGE)
        elif event_type == CmdRunAction:
            kwargs["command"] = data.get("command", "")
        elif event_type == CmdOutputObservation:
            kwargs["content"] = data.get("content", "")
            kwargs["command"] = data.get("command", "")
            if "command_id" in data:
                kwargs["command_id"] = data["command_id"]
            if "metadata" in data:
                kwargs["metadata"] = data["metadata"]
        else:
            kwargs["content"] = data.get("content", "")
        event = event_type(**kwargs)
        event._id = i + 1
        event._source = source
        if "cause_id" in data:
            event._cause = data["cause_id"]
        if event_type == CmdOutputObservation:
            if "command_id" not in kwargs and "cause_id" in data:
                kwargs["command_id"] = data["cause_id"]
            if "command_id" in kwargs and event.command_id != kwargs["command_id"]:
                event = event_type(**kwargs)
                event._id = i + 1
                event._source = source
        if "cause_id" in data:
            event._cause = data["cause_id"]
        events.append(event)
    return events


@pytest.fixture
def condenser_fixture():
    return ConversationWindowCondenser()


def test_basic_truncation(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 3},
            {"type": CmdRunAction, "command": "ls"},
            {"type": CmdOutputObservation, "content": "file1", "command": "ls", "cause_id": 5},
            {"type": CmdRunAction, "command": "pwd"},
            {"type": CmdOutputObservation, "content": "/dir", "command": "pwd", "cause_id": 7},
            {"type": CmdRunAction, "command": "cat file1"},
            {"type": CmdOutputObservation, "content": "content", "command": "cat file1", "cause_id": 9},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [5, 6, 7, 8]
    assert sorted(forgotten_ids) == expected_forgotten


def test_no_system_message(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 2},
            {"type": CmdRunAction, "command": "ls"},
            {"type": CmdOutputObservation, "content": "file1", "command": "ls", "cause_id": 4},
            {"type": CmdRunAction, "command": "pwd"},
            {"type": CmdOutputObservation, "content": "/dir", "command": "pwd", "cause_id": 6},
            {"type": CmdRunAction, "command": "cat file1"},
            {"type": CmdOutputObservation, "content": "content", "command": "cat file1", "cause_id": 8},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [4, 5, 6, 7]
    assert sorted(forgotten_ids) == expected_forgotten


def test_no_recall_observation(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": CmdRunAction, "command": "ls"},
            {"type": CmdOutputObservation, "content": "file1", "command": "ls", "cause_id": 4},
            {"type": CmdRunAction, "command": "pwd"},
            {"type": CmdOutputObservation, "content": "/dir", "command": "pwd", "cause_id": 6},
            {"type": CmdRunAction, "command": "cat file1"},
            {"type": CmdOutputObservation, "content": "content", "command": "cat file1", "cause_id": 8},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [4, 5, 6, 7]
    assert sorted(forgotten_ids) == expected_forgotten


def test_short_history_no_truncation(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 3},
            {"type": CmdRunAction, "command": "ls"},
            {"type": CmdOutputObservation, "content": "file1", "command": "ls", "cause_id": 5},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [5, 6]
    assert sorted(forgotten_ids) == expected_forgotten


def test_only_essential_events(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 3},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = []
    assert forgotten_ids == expected_forgotten


def test_dangling_observations_at_cut_point(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 3},
            {"type": CmdOutputObservation, "content": "dangle1", "command": "cmd_unknown"},
            {"type": CmdOutputObservation, "content": "dangle2", "command": "cmd_unknown"},
            {"type": CmdRunAction, "command": "cmd1"},
            {"type": CmdOutputObservation, "content": "obs1", "command": "cmd1", "cause_id": 7},
            {"type": CmdRunAction, "command": "cmd2"},
            {"type": CmdOutputObservation, "content": "obs2", "command": "cmd2", "cause_id": 9},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [5, 6, 7, 8]
    assert sorted(forgotten_ids) == expected_forgotten


def test_only_dangling_observations_in_recent_slice(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result", "cause_id": 3},
            {"type": CmdOutputObservation, "content": "dangle1", "command": "cmd_unknown"},
            {"type": CmdOutputObservation, "content": "dangle2", "command": "cmd_unknown"},
        ]
    )
    view = View(events=events)
    with patch("openhands.memory.condenser.impl.conversation_window_condenser.logger.warning") as mock_log_warning:
        condensation = condenser.get_condensation(view)
        assert isinstance(condensation, Condensation)
        assert isinstance(condensation.action, CondensationAction)
        forgotten_ids = condensation.action.forgotten
        expected_forgotten = [5, 6]
        assert sorted(forgotten_ids) == expected_forgotten
        assert mock_log_warning.call_count == 1
        call_args, call_kwargs = mock_log_warning.call_args
        expected_message_substring = "All recent events are dangling observations, which we truncate. This means the agent has only the essential first events. This should not happen."
        assert expected_message_substring in call_args[0]


def test_empty_history(condenser_fixture):
    condenser = condenser_fixture
    view = View(events=[])
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    assert condensation.action.forgotten == []


def test_multiple_user_messages(condenser_fixture):
    condenser = condenser_fixture
    events = create_events(
        [
            {"type": SystemMessageAction, "content": "System Prompt"},
            {"type": MessageAction, "content": "User Task 1", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 1"},
            {"type": RecallObservation, "content": "Recall result 1", "cause_id": 3},
            {"type": CmdRunAction, "command": "cmd1"},
            {"type": CmdOutputObservation, "content": "obs1", "command": "cmd1", "cause_id": 5},
            {"type": MessageAction, "content": "User Task 2", "source": EventSource.USER},
            {"type": RecallAction, "query": "User Task 2"},
            {"type": RecallObservation, "content": "Recall result 2", "cause_id": 8},
            {"type": CmdRunAction, "command": "cmd2"},
            {"type": CmdOutputObservation, "content": "obs2", "command": "cmd2", "cause_id": 10},
        ]
    )
    view = View(events=events)
    condensation = condenser.get_condensation(view)
    assert isinstance(condensation, Condensation)
    assert isinstance(condensation.action, CondensationAction)
    forgotten_ids = condensation.action.forgotten
    expected_forgotten = [5, 6, 7, 8, 9]
    assert sorted(forgotten_ids) == expected_forgotten
    kept_event_ids = set(range(1, 12)) - set(forgotten_ids)
    assert 2 in kept_event_ids
    assert 7 not in kept_event_ids
