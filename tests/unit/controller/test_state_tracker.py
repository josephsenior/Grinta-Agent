from __future__ import annotations

from collections import deque
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from forge.controller.state.control_flags import BudgetControlFlag
from forge.controller.state.state import State
from forge.controller.state.state_tracker import StateTracker
from forge.core.schema import AgentState
from forge.events.action.agent import AgentDelegateAction
from forge.events.action.empty import NullAction
from forge.events.event import EventSource
from forge.events.observation.agent import AgentStateChangedObservation
from forge.events.observation.delegate import AgentDelegateObservation
from forge.events.observation.empty import NullObservation
from forge.events.observation.error import ErrorObservation
from forge.events.serialization import event as event_serialization_module


def _assign_meta(event, event_id: int, source: EventSource, hidden: bool = False):
    event._id = event_id  # type: ignore[attr-defined]
    event._source = source  # type: ignore[attr-defined]
    if hidden:
        event.hidden = True  # type: ignore[attr-defined]


class DummyEventStream:
    def __init__(self, events: list):
        self.events = events
        self.calls = deque()

    def get_latest_event_id(self):
        return self.events[-1].id if self.events else -1

    def search_events(self, start_id: int, end_id: int, reverse: bool, filter):
        self.calls.append((start_id, end_id, reverse))
        return [event for event in self.events if start_id <= event.id <= end_id and filter.include(event)]


class DummyFileStore:
    def __init__(self):
        self.saved = None

    def write(self, path, data):
        self.saved = (path, data)


@pytest.fixture
def conversation_stats():
    stats = SimpleNamespace(
        save_metrics=MagicMock(),
        get_combined_metrics=MagicMock(return_value=SimpleNamespace(accumulated_cost=12.5)),
    )
    return stats


def test_set_initial_state_creates_new_state(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id="user")
    tracker.set_initial_state(
        id="sid",
        state=None,
        conversation_stats=conversation_stats,
        max_iterations=5,
        max_budget_per_task=10.0,
        confirmation_mode=True,
    )
    assert tracker.state.session_id == "sid"
    assert tracker.state.iteration_flag.max_value == 5
    assert tracker.state.budget_flag.max_value == 10.0
    assert tracker.state.start_id == 0


def test_set_initial_state_uses_existing_state(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    state = State(start_id=-5)
    tracker.set_initial_state("sid", state, conversation_stats, max_iterations=3, max_budget_per_task=None)
    assert tracker.state is state
    assert tracker.state.start_id == 0
    assert tracker.state.conversation_stats is conversation_stats


def test_validate_history_range_sets_empty_history(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State(history=[1, 2, 3], start_id=10)
    assert not tracker._validate_history_range(5, 2)
    assert tracker.state.history == []


def test_init_history_filters_delegate_ranges(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.set_initial_state("sid", None, conversation_stats, max_iterations=3, max_budget_per_task=None)

    delegate_action = AgentDelegateAction(agent="helper", inputs={})
    _assign_meta(delegate_action, 2, EventSource.AGENT)
    delegate_obs = AgentDelegateObservation(content="done", outputs={})
    _assign_meta(delegate_obs, 5, EventSource.ENVIRONMENT)
    normal_event = ErrorObservation(content="err", error_id="E")
    _assign_meta(normal_event, 6, EventSource.ENVIRONMENT)

    events = [
        delegate_action,
        NullAction(),
        NullObservation(""),
        delegate_obs,
        normal_event,
    ]
    for idx, event in enumerate(events):
        _assign_meta(event, idx + 1, EventSource.ENVIRONMENT)

    stream = DummyEventStream(events)
    tracker._init_history(stream)
    assert tracker.state.history[0].id == 1  # delegate action
    assert tracker.state.history[1].id == 4  # delegate observation
    assert tracker.state.history[-1].id == 5


def test_add_history_respects_filter(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State(history=[])

    normal_event = ErrorObservation(content="err", error_id="E")
    _assign_meta(normal_event, 1, EventSource.ENVIRONMENT)
    hidden_event = ErrorObservation(content="hidden", error_id="E")
    _assign_meta(hidden_event, 2, EventSource.ENVIRONMENT, hidden=True)
    tracker.add_history(normal_event)
    tracker.add_history(hidden_event)
    tracker.add_history(NullObservation(""))
    tracker.add_history(NullAction())
    tracker.add_history(AgentStateChangedObservation(content="", agent_state="RUNNING"))
    assert tracker.state.history == [normal_event]


def test_get_trajectory_uses_event_to_trajectory(monkeypatch):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State(history=[ErrorObservation(content="err", error_id="E")])
    tracker.state.history[0]._id = 1  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "forge.controller.state.state_tracker.event_to_trajectory",
        lambda event, include_screenshots: {"id": event.id, "screenshots": include_screenshots},
    )

    trajectory = tracker.get_trajectory(include_screenshots=True)
    assert trajectory == [{"id": 1, "screenshots": True}]


def test_save_state_persists_state_and_metrics(conversation_stats):
    file_store = DummyFileStore()
    tracker = StateTracker(sid="sid", file_store=file_store, user_id="user")
    tracker.state = State(conversation_stats=conversation_stats, agent_state=AgentState.RUNNING)
    tracker.save_state()
    assert file_store.saved[0] == "users/user/conversations/sid/agent_state.pkl"
    conversation_stats.save_metrics.assert_called_once()


def test_run_control_flags():
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State()
    tracker.state.iteration_flag.max_value = 1
    tracker.run_control_flags()
    with pytest.raises(RuntimeError):
        tracker.run_control_flags()

    tracker.state.iteration_flag.current_value = 0
    tracker.state.iteration_flag.max_value = 100
    tracker.state.budget_flag = BudgetControlFlag(limit_increase_amount=5.0, current_value=3.0, max_value=3.0)
    with pytest.raises(RuntimeError):
        tracker.run_control_flags()

def test_maybe_increase_control_flags_limits():
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State()
    tracker.state.iteration_flag.current_value = tracker.state.iteration_flag.max_value
    tracker.state.iteration_flag.reached_limit()
    tracker.maybe_increase_control_flags_limits(headless_mode=False)
    assert tracker.state.iteration_flag.max_value > tracker.state.iteration_flag.current_value

    tracker.state.budget_flag = BudgetControlFlag(limit_increase_amount=5.0, current_value=4.0, max_value=4.0)
    tracker.state.budget_flag.reached_limit()
    tracker.maybe_increase_control_flags_limits(headless_mode=False)
    assert tracker.state.budget_flag.max_value == 9.0


def test_sync_budget_flag_with_metrics(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State(conversation_stats=conversation_stats)
    tracker.state.budget_flag = BudgetControlFlag(limit_increase_amount=5.0, current_value=0.0, max_value=10.0)
    tracker.sync_budget_flag_with_metrics()
    assert tracker.state.budget_flag.current_value == 12.5


def test_close_rehydrates_history(conversation_stats):
    tracker = StateTracker(sid="sid", file_store=None, user_id=None)
    tracker.state = State()
    tracker.state.start_id = 0

    event = ErrorObservation(content="err", error_id="E")
    _assign_meta(event, 1, EventSource.ENVIRONMENT)
    stream = DummyEventStream([event])
    tracker.close(stream)
    assert tracker.state.history == [event]

