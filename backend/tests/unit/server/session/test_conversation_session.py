"""Tests for `ServerConversation` wrapper."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import logging

import pytest

from forge.server.session.conversation import ServerConversation, logger as convo_logger


class DummyRuntime:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.connected = False
        self.closed = False
        self.security_analyzer = "analyzer"

    async def connect(self):
        self.connected = True

    def close(self):
        self.closed = True


class DummyEventStream:
    def __init__(self, sid, file_store, user_id):
        self.sid = sid
        self.file_store = file_store
        self.user_id = user_id
        self.closed = False

    def close(self):
        self.closed = True


class DummyLLMRegistry:
    call_count = 0

    def __init__(self, config):
        DummyLLMRegistry.call_count += 1
        if DummyLLMRegistry.call_count == 1 and getattr(config, "fail_first", False):
            raise ValueError("config not ready")
        self.config = config


@pytest.fixture(autouse=True)
def reset_llm_registry():
    DummyLLMRegistry.call_count = 0
    yield
    DummyLLMRegistry.call_count = 0


def make_config():
    return SimpleNamespace(runtime="dummy-runtime", fail_first=False)


def test_conversation_init_with_existing_runtime(monkeypatch):
    runtime = DummyRuntime()
    event_stream = DummyEventStream("sid", "fs", "user")
    config = make_config()

    convo = ServerConversation(
        sid="sid",
        file_store="fs",
        config=config,
        user_id="user",
        event_stream=event_stream,
        runtime=runtime,
    )

    assert convo.runtime is runtime
    assert convo.event_stream is event_stream
    assert convo.security_analyzer == "analyzer"


@pytest.mark.asyncio
async def test_conversation_init_creates_runtime(monkeypatch):
    monkeypatch.setattr(
        "forge.server.session.conversation.EventStream", DummyEventStream
    )
    monkeypatch.setattr(
        "forge.server.session.conversation.LLMRegistry", DummyLLMRegistry
    )
    monkeypatch.setattr(
        "forge.server.session.conversation.get_runtime_cls",
        lambda runtime: DummyRuntime,
    )
    config = make_config()

    convo = ServerConversation(
        sid="sid",
        file_store="fs",
        config=config,
        user_id=None,
        event_stream=None,
        runtime=None,
    )

    assert isinstance(convo.runtime, DummyRuntime)
    assert isinstance(convo.event_stream, DummyEventStream)

    await convo.connect()
    assert convo.runtime.connected is True


@pytest.mark.asyncio
async def test_conversation_connect_skips_existing(monkeypatch):
    runtime = DummyRuntime()
    convo = ServerConversation(
        "sid",
        "fs",
        make_config(),
        "user",
        event_stream=DummyEventStream("sid", "fs", "user"),
        runtime=runtime,
    )
    await convo.connect()
    assert runtime.connected is False


@pytest.mark.asyncio
async def test_disconnect_closes_runtime(monkeypatch):
    created_tasks = []

    async def fake_call_sync(fn):
        fn()

    monkeypatch.setattr(
        "forge.server.session.conversation.call_sync_from_async", fake_call_sync
    )
    monkeypatch.setattr("asyncio.create_task", lambda coro: created_tasks.append(coro))

    monkeypatch.setattr(
        "forge.server.session.conversation.EventStream", DummyEventStream
    )
    monkeypatch.setattr(
        "forge.server.session.conversation.LLMRegistry", DummyLLMRegistry
    )
    monkeypatch.setattr(
        "forge.server.session.conversation.get_runtime_cls",
        lambda runtime: DummyRuntime,
    )

    convo = ServerConversation("sid", "fs", make_config(), "user")
    assert convo.runtime.closed is False
    await convo.disconnect()
    assert convo.event_stream.closed is True
    assert created_tasks  # ensure close scheduled


@pytest.mark.asyncio
async def test_disconnect_skips_when_attached():
    runtime = DummyRuntime()
    event_stream = DummyEventStream("sid", "fs", "user")
    convo = ServerConversation(
        "sid", "fs", make_config(), "user", event_stream=event_stream, runtime=runtime
    )
    await convo.disconnect()
    assert event_stream.closed is False
    assert runtime.closed is False


@pytest.mark.asyncio
async def test_llm_registry_failure_logs_warning(monkeypatch, caplog):
    monkeypatch.setattr(
        "forge.server.session.conversation.EventStream", DummyEventStream
    )
    monkeypatch.setattr(
        "forge.server.session.conversation.get_runtime_cls",
        lambda runtime: DummyRuntime,
    )
    config = make_config()
    config.fail_first = True
    monkeypatch.setattr(
        "forge.server.session.conversation.LLMRegistry", DummyLLMRegistry
    )

    records = []

    class Handler(logging.Handler):
        def emit(self, record):
            records.append(record)

    handler = Handler()
    convo_logger.addHandler(handler)
    try:
        convo = ServerConversation("sid", "fs", config, None)
    finally:
        convo_logger.removeHandler(handler)

    assert any("LLM config not ready" in record.getMessage() for record in records)
    assert isinstance(convo.runtime, DummyRuntime)
