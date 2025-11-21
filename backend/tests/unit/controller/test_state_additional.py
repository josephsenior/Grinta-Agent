from __future__ import annotations

import base64
import os
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from forge.controller.state import state as state_module
from forge.controller.state.state import RESUMABLE_STATES, State
from forge.core.schemas import AgentState
from forge.events.action import MessageAction
from forge.events.action.agent import AgentFinishAction
from forge.events.event import EventSource
from forge.llm.metrics import Metrics
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.files import FileStore


class DummyFileStore:
    def __init__(self):
        self.storage: dict[str, str] = {}
        self.deleted: list[str] = []

    def write(self, path: str, data: str) -> None:
        self.storage[path] = data

    def read(self, path: str) -> str:
        if path not in self.storage:
            raise FileNotFoundError(path)
        return self.storage[path]

    def delete(self, path: str) -> None:
        self.deleted.append(path)
        raise RuntimeError("delete failed")  # Should be suppressed


def _assign_event_meta(event, event_id: int, source: EventSource) -> None:
    event._id = event_id  # type: ignore[attr-defined]
    event._source = source  # type: ignore[attr-defined]


def test_save_and_restore_round_trip(monkeypatch):
    file_store = DummyFileStore()
    conversation_stats = cast(
        ConversationStats, SimpleNamespace(save_metrics=MagicMock())
    )

    state = State(
        session_id="sid",
        agent_state=AgentState.RUNNING,
        conversation_stats=conversation_stats,
    )
    state.history.append(MessageAction(content="hello"))

    state.save_to_session("sid", cast(FileStore, file_store), user_id="user-1")
    assert "users/user-1/conversations/sid/agent_state.pkl" in file_store.storage
    assert file_store.deleted == ["sessions/sid/agent_state.pkl"]
    assert state.conversation_stats is conversation_stats  # restored after save

    restored = State.restore_from_session(
        "sid", cast(FileStore, file_store), user_id="user-1"
    )
    assert restored.agent_state == AgentState.LOADING
    assert restored.resume_state in RESUMABLE_STATES


def test_restore_from_session_with_user_fallback():
    class FallbackFileStore(DummyFileStore):
        def read(self, path: str) -> str:
            if path.startswith("users/user-2"):
                raise FileNotFoundError(path)
            return super().read(path)

    file_store = FallbackFileStore()
    state = State(session_id="sid", agent_state=AgentState.RUNNING)
    state.save_to_session("sid", cast(FileStore, file_store), user_id=None)

    restored = State.restore_from_session(
        "sid", cast(FileStore, file_store), user_id="user-2"
    )
    assert restored.resume_state == AgentState.RUNNING
    assert restored.agent_state == AgentState.LOADING


def test_restore_from_session_propagates_other_errors():
    class ErrorFileStore(DummyFileStore):
        def read(self, path: str) -> str:
            raise ValueError("boom")

    with pytest.raises(ValueError):
        State.restore_from_session("sid", cast(FileStore, ErrorFileStore()))


def test_getstate_and_setstate_strip_transient_fields():
    state = State()
    state.history = [MessageAction(content="hi")]
    state._history_checksum = 1  # type: ignore[attr-defined]
    state.iteration = 5
    state.local_metrics = Metrics()
    serializable = state.__getstate__()
    for key in [
        "_history_checksum",
        "_view",
        "iteration",
        "local_metrics",
        "traffic_control_state",
        "delegates",
    ]:
        assert key not in serializable
    assert serializable["history"] == []

    serializable.update({"iteration": 3, "max_iterations": 3, "iteration_flag": None})
    new_state = State()
    new_state.__setstate__(serializable)
    assert isinstance(new_state.iteration_flag, state_module.IterationControlFlag)
    assert new_state.history == []
    assert new_state.budget_flag is None


def test_user_intent_lookup_with_finish_action():
    state = State()
    user_msg = MessageAction(content="task")
    _assign_event_meta(user_msg, 1, EventSource.USER)
    finish = AgentFinishAction(final_thought="done")
    _assign_event_meta(finish, 2, EventSource.AGENT)
    state.history.extend([user_msg, finish])

    intent, image_urls = state.get_current_user_intent()
    assert intent == "task"
    assert image_urls is None


def test_last_message_helpers():
    state = State()
    agent_msg = MessageAction(content="result")
    user_msg = MessageAction(content="follow up")
    _assign_event_meta(agent_msg, 1, EventSource.AGENT)
    _assign_event_meta(user_msg, 2, EventSource.USER)
    state.history.extend([agent_msg, user_msg])

    assert state.get_last_agent_message() is agent_msg
    assert state.get_last_user_message() is user_msg


def test_to_llm_metadata(monkeypatch):
    state = State(session_id="sid", user_id="user-3")
    monkeypatch.setenv("WEB_HOST", "example.com")

    metadata = state.to_llm_metadata(model_name="gpt", agent_name="agent")
    assert metadata["session_id"] == "sid"
    assert any(tag.startswith("web_host:example.com") for tag in metadata["tags"])


def test_local_metrics_and_step():
    base_metrics = Metrics()
    base_metrics.accumulated_cost = 10.0
    snapshot = base_metrics.copy()

    state = State()
    state.metrics.accumulated_cost = 15.0
    state.parent_iteration = 5
    state.iteration_flag.current_value = 8
    state.parent_metrics_snapshot = snapshot

    assert state.get_local_step() == 3
    diff = state.get_local_metrics()
    assert diff.accumulated_cost == 5.0


def test_view_caching(monkeypatch):
    state = State()
    message = MessageAction(content="cache")
    _assign_event_meta(message, 1, EventSource.USER)
    state.history.append(message)

    calls = []

    def fake_from_events(events):
        calls.append(list(events))
        return state_module.View(events=list(events))

    monkeypatch.setattr(
        state_module.View, "from_events", staticmethod(fake_from_events)
    )

    first_view = state.view
    second_view = state.view
    assert first_view is second_view
    assert len(calls) == 1

    new_msg = MessageAction(content="new")
    _assign_event_meta(new_msg, 2, EventSource.AGENT)
    state.history.append(new_msg)
    third_view = state.view
    assert third_view is not first_view
    assert len(calls) == 2


def test_save_to_session_restores_conversation_stats_on_failure():
    class FailingFileStore(DummyFileStore):
        def write(self, path: str, data: str) -> None:
            raise RuntimeError("write failure")

    state = State(conversation_stats=cast(ConversationStats, SimpleNamespace()))
    with pytest.raises(RuntimeError):
        state.save_to_session("sid", cast(FileStore, FailingFileStore()), user_id=None)


def test_find_user_intent_without_finish():
    state = State()
    message = MessageAction(content="hello", image_urls=["image.png"])
    _assign_event_meta(message, 1, EventSource.USER)
    state.history.append(message)

    intent, images = state.get_current_user_intent()
    assert intent == "hello"
    assert images == ["image.png"]
