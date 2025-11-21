from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from forge.utils import conversation_summary


class DummyAction:
    def __init__(self, content: str) -> None:
        self.content = content
        self.source = conversation_summary.EventSource.USER


class DummyEventStore:
    def __init__(self, conversation_id, file_store, user_id) -> None:
        self.events = [DummyAction("Hello world from user")]

    def search_events(self):
        return self.events


class DummyLLMRegistry:
    def __init__(self, result: str = "Conversation Title") -> None:
        self.result = result
        self.calls = []

    def request_extraneous_completion(self, *args, **kwargs) -> str:
        self.calls.append((args, kwargs))
        return self.result


class DummySettings(SimpleNamespace):
    pass


class DummyLLMConfig:
    def __init__(self, model, api_key, base_url):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.aws_region_name = None
        self.aws_access_key_id = None
        self.aws_secret_access_key = None


@pytest.mark.asyncio
async def test_generate_conversation_title_truncates(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(conversation_summary, "LLMConfig", DummyLLMConfig)
    registry = DummyLLMRegistry(
        result="Title that is definitely longer than five characters"
    )
    long_message = "x" * 1100
    title = await conversation_summary.generate_conversation_title(
        long_message, DummyLLMConfig("model", None, None), registry, max_length=10
    )
    assert len(title) <= 10

    registry = DummyLLMRegistry()
    registry.result = "Title"
    monkeypatch.setattr(
        registry,
        "request_extraneous_completion",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    assert (
        await conversation_summary.generate_conversation_title(
            "hello", DummyLLMConfig("m", None, None), registry
        )
        is None
    )
    assert (
        await conversation_summary.generate_conversation_title(
            "", DummyLLMConfig("m", None, None), registry
        )
        is None
    )


@pytest.mark.asyncio
async def test_auto_generate_title_with_llm(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(conversation_summary, "LLMConfig", DummyLLMConfig)
    monkeypatch.setattr(conversation_summary, "EventStore", DummyEventStore)
    monkeypatch.setattr(conversation_summary, "MessageAction", DummyAction)

    llm_registry = DummyLLMRegistry("Great Title")
    settings = DummySettings(llm_model="model", llm_api_key=None, llm_base_url=None)
    title = await conversation_summary.auto_generate_title(
        "cid", "user", object(), settings, llm_registry
    )
    assert title == "Great Title"


@pytest.mark.asyncio
async def test_auto_generate_title_fallback(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(conversation_summary, "LLMConfig", DummyLLMConfig)
    monkeypatch.setattr(conversation_summary, "EventStore", DummyEventStore)
    monkeypatch.setattr(conversation_summary, "MessageAction", DummyAction)
    llm_registry = DummyLLMRegistry()
    settings = DummySettings(llm_model=None, llm_api_key=None, llm_base_url=None)
    title = await conversation_summary.auto_generate_title(
        "cid", "user", object(), settings, llm_registry
    )
    assert title.startswith("Hello")


def test_generate_truncated_title() -> None:
    assert (
        conversation_summary._generate_truncated_title("  spaced  ", max_length=4)
        == "spac..."
    )
    assert (
        conversation_summary._generate_truncated_title("short", max_length=10)
        == "short"
    )


def test_get_default_conversation_title() -> None:
    assert (
        conversation_summary.get_default_conversation_title("abcdef")
        == "Conversation abcde"
    )


@pytest.mark.asyncio
async def test_auto_generate_title_handles_missing(monkeypatch: pytest.MonkeyPatch):
    class EmptyEventStore:
        def __init__(self, *args, **kwargs) -> None:
            self.events = []

        def search_events(self):
            return self.events

    monkeypatch.setattr(conversation_summary, "EventStore", EmptyEventStore)
    result = await conversation_summary.auto_generate_title(
        "cid", "user", object(), DummySettings(), DummyLLMRegistry()
    )
    assert result == ""


@pytest.mark.asyncio
async def test_auto_generate_title_logs_error(monkeypatch: pytest.MonkeyPatch):
    async def bad_try(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        conversation_summary, "_get_first_user_message", lambda *args: "hello"
    )
    monkeypatch.setattr(conversation_summary, "_try_llm_title_generation", bad_try)
    result = await conversation_summary.auto_generate_title(
        "cid", "user", object(), DummySettings(), DummyLLMRegistry()
    )
    assert result == ""


@pytest.mark.asyncio
async def test_try_llm_title_generation_handles_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        conversation_summary,
        "generate_conversation_title",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    settings = DummySettings(llm_model="model", llm_api_key=None, llm_base_url=None)
    result = await conversation_summary._try_llm_title_generation(
        "message", settings, DummyLLMRegistry("ignored")
    )
    assert result is None
