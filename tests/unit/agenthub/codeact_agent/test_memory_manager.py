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


class DummyEnhancedContextManager:
    def __init__(self, *args, **kwargs):
        self.saved = []
        self.loaded = []
        self.added_payloads: list[dict[str, Any]] = []

    def load_from_file(self, path):
        self.loaded.append(path)

    def save_to_file(self, path):
        self.saved.append(path)

    def add_to_short_term(self, payload):
        self.added_payloads.append(payload)


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


class DummyACEFramework:
    def __init__(self, llm, context_playbook, config):
        self.llm = llm
        self.context_playbook = context_playbook
        self.config = config


class DummyContextPlaybook:
    def __init__(self, max_bullets, enable_grow_and_refine):
        self.max_bullets = max_bullets
        self.enable_grow_and_refine = enable_grow_and_refine
        self.import_calls: list[Any] = []
        self.next_content: str | None = "Strategies"

    def import_playbook(self, data):
        self.import_calls.append(data)

    def get_playbook_content(self, max_bullets):
        return self.next_content


class DummyLLMRegistry:
    def __init__(self):
        self.active_llm = object()

    def get_active_llm(self):
        return self.active_llm


@pytest.fixture
def config(tmp_path):
    return SimpleNamespace(
        enable_enhanced_context=True,
        context_short_term_window=2,
        context_working_size=10,
        context_long_term_size=20,
        context_contradiction_threshold=0.6,
        context_persistence_path=str(tmp_path / "ctx.json"),
        condenser_config={"model": "fake"},
        enable_ace=True,
        ace_max_bullets=3,
        ace_multi_epoch=False,
        ace_num_epochs=1,
        ace_reflector_max_iterations=1,
        ace_enable_online_adaptation=False,
        ace_playbook_path=str(tmp_path / "playbook.json"),
        ace_min_helpfulness_threshold=0.1,
        ace_max_playbook_content_length=5,
        ace_enable_grow_and_refine=False,
        ace_cleanup_interval_days=7,
        ace_redundancy_threshold=0.5,
    )


@pytest.fixture(autouse=True)
def stub_conversation_memory(monkeypatch):
    monkeypatch.setattr(module, "ConversationMemory", DummyConversationMemory)


def install_enhanced_context_stub(monkeypatch, *, raise_on_load=False):
    stub_module = ModuleType("forge.memory.enhanced_context_manager")
    instance_container = {"instance": None}

    class StubManager(DummyEnhancedContextManager):
        def __init__(self, *args, **kwargs):
            super().__init__()
            instance_container["instance"] = self

        def load_from_file(self, path):
            if raise_on_load:
                raise RuntimeError("load error")
            return super().load_from_file(path)

    stub_module.EnhancedContextManager = StubManager
    monkeypatch.setitem(
        sys.modules,
        "forge.memory.enhanced_context_manager",
        stub_module,
    )
    return instance_container


def install_ace_stubs(monkeypatch, context_playbook_content="Strategies"):
    stub_module = ModuleType("forge.metasop.ace")
    container = {"playbook": None}

    class ACEConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ContextPlaybook(DummyContextPlaybook):
        def __init__(self, max_bullets, enable_grow_and_refine):
            super().__init__(max_bullets, enable_grow_and_refine)
            self.next_content = context_playbook_content
            container["playbook"] = self

    stub_module.ACEConfig = ACEConfig
    stub_module.ContextPlaybook = ContextPlaybook
    stub_module.ACEFramework = DummyACEFramework
    monkeypatch.setitem(sys.modules, "forge.metasop.ace", stub_module)
    return container


def test_initialize_sets_conversation_memory_and_context_manager(monkeypatch, config):
    ecm_container = install_enhanced_context_stub(monkeypatch)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    install_ace_stubs(monkeypatch)
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    manager.initialize(prompt_manager=object())

    assert isinstance(manager.conversation_memory, DummyConversationMemory)
    assert ecm_container["instance"] is not None


def test_initialize_enhanced_context_manager_loads_existing_state(monkeypatch, config, tmp_path):
    ecm_container = install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    config.context_persistence_path = str(tmp_path / "state.json")
    config.enable_enhanced_context = True
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert ecm_container["instance"].loaded == [config.context_persistence_path]


def test_initialize_enhanced_context_manager_disabled_sets_none(config):
    config.enable_enhanced_context = False
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_enhanced_context_manager()
    assert manager.enhanced_context_manager is None


def test_initialize_enhanced_context_manager_handles_load_errors(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch, raise_on_load=True)
    install_ace_stubs(monkeypatch)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_enhanced_context_manager()
    assert manager.enhanced_context_manager is not None


def test_initialize_enhanced_context_manager_skips_when_no_persistence(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch)
    config.context_persistence_path = None
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_enhanced_context_manager()
    assert manager.enhanced_context_manager is not None


def test_initialize_condenser_sets_instance(monkeypatch, config):
    dummy = DummyCondenser()
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: dummy))
    install_ace_stubs(monkeypatch)
    install_enhanced_context_stub(monkeypatch)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert manager.condenser is dummy


def test_initialize_condenser_handles_failure(monkeypatch, config):
    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=raise_error))
    install_ace_stubs(monkeypatch)
    install_enhanced_context_stub(monkeypatch)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert manager.condenser is None


def test_initialize_condenser_without_config(monkeypatch, config):
    config.condenser_config = None
    config.condenser = None
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_condenser()
    assert manager.condenser is None


def test_initialize_ace_framework_imports_playbook(monkeypatch, config, tmp_path):
    content_path = tmp_path / "playbook.json"
    content_path.write_text('{"bullets": []}', encoding="utf-8")
    config.ace_playbook_path = str(content_path)
    install_enhanced_context_stub(monkeypatch)
    playbook_container = install_ace_stubs(monkeypatch)
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    assert isinstance(manager.ace_framework, DummyACEFramework)
    assert playbook_container["playbook"].import_calls == [{"bullets": []}]


def test_initialize_ace_framework_disabled(monkeypatch, config):
    config.enable_ace = False
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_ace_framework()
    assert manager.ace_framework is None


def test_initialize_ace_framework_without_playbook(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
    config.ace_playbook_path = None
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager._initialize_ace_framework()
    assert manager.ace_framework is not None


def test_save_context_state_and_update_context(monkeypatch, config):
    ecm_container = install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())
    manager.save_context_state()
    assert ecm_container["instance"].saved == [config.context_persistence_path]

    class DummyEvent:
        def __init__(self, action=None):
            self.action = action
            self.timestamp = 1
            self.source = "USER"

    state = SimpleNamespace(history=[DummyEvent(action="file-edit")])
    manager.update_context(state)
    assert ecm_container["instance"].added_payloads[0]["has_decision"] is True


def test_save_context_state_no_manager(config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.enhanced_context_manager = None
    manager.save_context_state()


def test_save_context_state_without_path(monkeypatch, config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.enhanced_context_manager = DummyEnhancedContextManager()
    config.context_persistence_path = None
    manager.save_context_state()
    assert manager.enhanced_context_manager.saved == []


def test_update_context_without_manager(config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.enhanced_context_manager = None
    manager.update_context(SimpleNamespace(history=[]))


def test_update_context_without_file_actions(monkeypatch, config):
    ecm_container = install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
    monkeypatch.setattr(module, "Condenser", SimpleNamespace(from_config=lambda *a, **k: None))
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.initialize(prompt_manager=object())

    class DummyEvent:
        action = "read"
        timestamp = None

    manager.update_context(SimpleNamespace(history=[DummyEvent()]))
    assert "has_decision" not in ecm_container["instance"].added_payloads[-1]


def test_condense_history_without_condenser(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.condenser = None
    state = SimpleNamespace(history=[1, 2])
    condensed = manager.condense_history(state)
    assert condensed.events == [1, 2]
    assert condensed.pending_action is None


def test_condense_history_with_view(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)

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
    install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch)
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


def test_get_ace_playbook_context_returns_text(monkeypatch, config):
    install_enhanced_context_stub(monkeypatch)
    install_ace_stubs(monkeypatch, context_playbook_content="Playbook data")
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.ace_framework = DummyACEFramework(
        llm=None,
        context_playbook=DummyContextPlaybook(1, True),
        config=None,
    )
    context = manager.get_ace_playbook_context(SimpleNamespace())
    assert context and "ACE PLAYBOOK" in context


def test_get_ace_playbook_context_returns_none_on_no_content(monkeypatch, config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.ace_framework = DummyACEFramework(
        llm=None,
        context_playbook=SimpleNamespace(
            get_playbook_content=lambda max_bullets: "No relevant strategies found"
        ),
        config=None,
    )
    assert manager.get_ace_playbook_context(SimpleNamespace()) is None


def test_get_ace_playbook_context_none_when_framework_missing(config):
    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.ace_framework = None
    assert manager.get_ace_playbook_context(SimpleNamespace()) is None


def test_get_ace_playbook_context_handles_exception(config):
    class BadPlaybook:
        def get_playbook_content(self, max_bullets):
            raise RuntimeError("fail")

    manager = CodeActMemoryManager(config, DummyLLMRegistry())
    manager.ace_framework = DummyACEFramework(
        llm=None,
        context_playbook=BadPlaybook(),
        config=None,
    )
    assert manager.get_ace_playbook_context(SimpleNamespace()) is None

