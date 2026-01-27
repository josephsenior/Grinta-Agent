from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable

import pytest

import forge.agenthub.codeact_agent.memory_manager as module
from forge.agenthub.codeact_agent.memory_manager import (
    CodeActMemoryManager,
    CondensedHistory,
)
from forge.core.message import ImageContent, Message, TextContent
from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.core.schemas import ActionType


class DummyConversationMemory:
    def __init__(self, *args, **kwargs):
        self.process_calls: list[dict[str, Any]] = []

    def process_events(
        self,
        condensed_history,
        initial_user_action,
        max_message_chars,
        vision_is_active,
    ):
        self.process_calls.append(
            {
                "history": list(condensed_history),
                "initial": initial_user_action,
                "max_chars": max_message_chars,
                "vision": vision_is_active,
            }
        )
        return [
            Message(role="system", content=[TextContent(text="sys")]),
            Message(role="assistant", content=[TextContent(text="answer")]),
            Message(role="user", content=[TextContent(text="user")]),
        ]


class DummyCondenser:
    def __init__(self, view_to_return=None, action=None):
        self.view_to_return = view_to_return
        self.action = action
        self.calls = 0

    def condensed_history(self, state):
        self.calls += 1
        if self.view_to_return is not None:
            return self.view_to_return
        return SimpleNamespace(action=self.action)


class DummyLLMRegistry:
    def __init__(self):
        self.active_llm = object()

    def get_active_llm(self):
        return self.active_llm


@pytest.fixture
def config(tmp_path):
    return SimpleNamespace(
        condenser={"model": "fake"},
    )


@pytest.fixture(autouse=True)
def stub_conversation_memory(monkeypatch):
    monkeypatch.setattr(module, "ConversationMemory", DummyConversationMemory)


def test_initialize_sets_conversation_memory(monkeypatch, config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    manager.initialize(prompt_manager=object())

    assert isinstance(manager.conversation_memory, DummyConversationMemory)


def test_initialize_condenser_sets_instance(monkeypatch, config):
    dummy = DummyCondenser()
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: dummy))
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert manager.condenser is dummy


def test_initialize_condenser_handles_failure(monkeypatch, config):
    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=raise_error))
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert manager.condenser is None


def test_condense_history_without_condenser(monkeypatch, config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.condenser = None
    state = SimpleNamespace(history=[1, 2])
    condensed = manager.condense_history(state)
    assert condensed.events == [1, 2]
    assert condensed.pending_action is None


def test_condense_history_with_view(monkeypatch, config):
    class DummyView:
        def __init__(self, events):
            self.events = events

    monkeypatch.setattr(module, "View", DummyView)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.condenser = DummyCondenser(view_to_return=DummyView([MessageAction("hi")]))
    condensed = manager.condense_history(SimpleNamespace())
    assert isinstance(condensed, CondensedHistory)
    assert condensed.events[0].content == "hi"


def test_condense_history_with_action(monkeypatch, config):
    action = MessageAction("do-it")
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.condenser = DummyCondenser(action=action)
    condensed = manager.condense_history(SimpleNamespace())
    assert condensed.pending_action is action


def test_get_initial_user_message_returns_existing_message():
    user_msg = MessageAction("hello")
    user_msg.source = EventSource.USER
    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    assert manager.get_initial_user_message([user_msg]) is user_msg


def test_get_initial_user_message_clones_non_message_action():
    class DummyEvent:
        source = EventSource.USER
        action = ActionType.MESSAGE
        content = "payload"
        wait_for_response = True
        id = 42
        timestamp = 123

    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    cloned = manager.get_initial_user_message([DummyEvent()])
    assert isinstance(cloned, MessageAction)
    assert cloned.content == "payload"
    assert cloned.id == 42


def test_get_initial_user_message_skips_non_user_sources():
    class AgentEvent:
        source = EventSource.AGENT

    user_msg = MessageAction("user")
    user_msg.source = EventSource.USER
    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    result = manager.get_initial_user_message([AgentEvent(), user_msg])
    assert result is user_msg


def test_get_initial_user_message_raises_when_missing():
    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    with pytest.raises(ValueError):
        manager.get_initial_user_message([])


def test_get_initial_user_message_handles_bad_event():
    class BadEvent:
        source = EventSource.USER

        @property
        def action(self):
            raise RuntimeError("bad")

    user_msg = MessageAction("ok")
    user_msg.source = EventSource.USER
    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    result = manager.get_initial_user_message([BadEvent(), user_msg])
    assert result is user_msg


def test_get_initial_user_message_without_ids():
    class DummyEvent:
        source = EventSource.USER
        action = ActionType.MESSAGE
        content = "payload"

    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    cloned = manager.get_initial_user_message([DummyEvent()])
    assert isinstance(cloned, MessageAction)
    assert cloned.content == "payload"


def test_get_initial_user_message_ignores_non_message_user_events():
    class OtherEvent:
        source = EventSource.USER
        action = "not-message"

    user_msg = MessageAction("real")
    user_msg.source = EventSource.USER
    manager = CodeActMemoryManager(SimpleNamespace(), DummyLLMRegistry())
    result = manager.get_initial_user_message([OtherEvent(), user_msg])
    assert result is user_msg


def test_build_messages_marks_cache_prompts(monkeypatch, config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.conversation_memory = DummyConversationMemory()
    llm_config = SimpleNamespace(max_message_chars=100, vision_is_active=True)
    messages = manager.build_messages([], MessageAction("hi"), llm_config)
    assert messages[0].content[0].cache_prompt is True
    assert any(item.cache_prompt for item in messages[-1].content)


def test_build_messages_raises_when_uninitialized(config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    with pytest.raises(RuntimeError):
        manager.build_messages([], MessageAction("x"), SimpleNamespace())


def test_build_messages_returns_immediately_when_empty(monkeypatch, config):
    class EmptyConversationMemory(DummyConversationMemory):
        def process_events(self, *args, **kwargs):
            return []

    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.conversation_memory = EmptyConversationMemory()
    result = manager.build_messages([], MessageAction("x"), SimpleNamespace())
    assert result == []


def test_build_messages_handles_non_text_content(monkeypatch, config):
    class NoTextConversationMemory(DummyConversationMemory):
        def process_events(self, *args, **kwargs):
            return [
                Message(role="system", content=[ImageContent(image_urls=["img"])]),
                Message(role="assistant", content=[ImageContent(image_urls=["img2"])]),
            ]

    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.conversation_memory = NoTextConversationMemory()
    messages = manager.build_messages([], MessageAction("x"), SimpleNamespace())
    assert all(not isinstance(item, TextContent) for msg in messages for item in msg.content)


def test_build_messages_handles_missing_user_message(monkeypatch, config):
    class AssistantOnlyMemory(DummyConversationMemory):
        def process_events(self, *args, **kwargs):
            return [Message(role="assistant", content=[TextContent(text="assistant")])]

    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.conversation_memory = AssistantOnlyMemory()
    messages = manager.build_messages([], MessageAction("x"), SimpleNamespace())
    assert messages[0].content[0].cache_prompt is True


def test_build_messages_user_without_text_content(monkeypatch, config):
    class UserImageMemory(DummyConversationMemory):
        def process_events(self, *args, **kwargs):
            return [Message(role="user", content=[ImageContent(image_urls=["img"])])]

    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.conversation_memory = UserImageMemory()
    messages = manager.build_messages([], MessageAction("x"), SimpleNamespace())
    assert isinstance(messages[0].content[0], ImageContent)

