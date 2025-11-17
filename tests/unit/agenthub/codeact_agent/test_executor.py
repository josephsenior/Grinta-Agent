from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Iterable

import pytest

import forge.controller  # ensure controller module is fully initialized before agenthub imports
import forge.agenthub.codeact_agent.executor as executor_module
from forge.agenthub.codeact_agent.executor import (
    CodeActExecutor,
    ExecutionResult,
    _FunctionCallingProxy,
)
from forge.events.action import MessageAction


class StubLLM:
    def __init__(self, responses: Iterable[Any]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def completion(self, **params):
        self.calls.append(params)
        if not self.responses:
            raise AssertionError("No more responses configured")
        behavior = self.responses.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


class StubPlanner:
    def __init__(self):
        self.tool_calls: list[list[MessageAction]] = []

    def track_tool_usage(self, actions):
        self.tool_calls.append(list(actions))


class StubSafety:
    def __init__(self):
        self.calls: list[tuple[str, list[MessageAction]]] = []

    def apply(self, response_text, actions):
        self.calls.append((response_text, list(actions)))
        return True, actions


class DummyEventStream:
    def __init__(self):
        self.events: list[Any] = []

    def add_event(self, event, source):
        self.events.append((event, source))


class Chunk:
    def __init__(self, token: str):
        delta = SimpleNamespace(content=token)
        message = SimpleNamespace(content="")
        self.choices = [SimpleNamespace(delta=delta, message=message)]


@pytest.fixture(autouse=True)
def reset_proxy(monkeypatch):
    # Ensure each test sees a clean proxy instance.
    proxy = _FunctionCallingProxy("forge.agenthub.codeact_agent.function_calling")
    monkeypatch.setattr(executor_module, "codeact_function_calling", proxy, raising=False)


@pytest.fixture
def executor_factory(monkeypatch):
    def factory(responses: Iterable[Any]):
        llm = StubLLM(responses)
        planner = StubPlanner()
        safety = StubSafety()
        executor = CodeActExecutor(
            llm=llm,
            safety_manager=safety,
            planner=planner,
            mcp_tool_name_provider=lambda: ["tool-a"],
        )
        monkeypatch.setattr(
            executor_module,
            "codeact_function_calling",
            SimpleNamespace(
                response_to_actions=lambda resp, mcp_tool_names: [MessageAction("action")]
            ),
            raising=False,
        )
        return executor, llm, planner, safety

    return factory


def test_function_calling_proxy_tracks_overrides(monkeypatch):
    fake_mod = ModuleType("tests.fake_module")
    fake_mod.value = 1
    monkeypatch.setitem(sys.modules, "tests.fake_module", fake_mod)

    proxy = _FunctionCallingProxy("tests.fake_module")
    assert proxy.value == 1
    proxy.value = 2
    assert proxy.value == 2
    assert fake_mod.value == 2


def test_execute_streaming_success(executor_factory):
    chunks = [Chunk("Hello "), Chunk("world")]
    executor, llm, planner, safety = executor_factory([chunks])
    stream = DummyEventStream()
    result = executor.execute({"stream": True}, stream)

    assert isinstance(result, ExecutionResult)
    assert result.error is None
    assert stream.events  # streaming actions recorded
    assert planner.tool_calls  # track_tool_usage invoked
    assert safety.calls and safety.calls[0][0] == "Hello world"


def test_execute_fallback_on_stream_error(executor_factory, monkeypatch):
    def failing_stream():
        raise RuntimeError("boom")
        yield  # pragma: no cover

    non_stream_response = SimpleNamespace()
    executor, _, _, _ = executor_factory([failing_stream(), non_stream_response])
    executor._mcp_tool_name_provider = lambda: []
    monkeypatch.setattr(
        executor_module,
        "codeact_function_calling",
        SimpleNamespace(
            response_to_actions=lambda resp, mcp_tool_names=None: []
        ),
        raising=False,
    )
    # Dummy stream optional
    result = executor.execute({"stream": True}, None)
    assert result.error == "boom"
    assert result.response is not None
    # fallback should have synthesized id/choices
    assert hasattr(result.response, "choices")


def test_execute_warns_when_no_chunks(executor_factory, monkeypatch):
    empty_stream = []
    fallback_response = SimpleNamespace()
    executor, _, _, _ = executor_factory([empty_stream, fallback_response])
    executor._mcp_tool_name_provider = lambda: []
    monkeypatch.setattr(
        executor_module,
        "codeact_function_calling",
        SimpleNamespace(response_to_actions=lambda resp, mcp_tool_names=None: []),
        raising=False,
    )
    result = executor.execute({"stream": True}, None)
    assert result.response is not None and getattr(result.response, "id", "") == "fallback"


def test_build_final_response_returns_none(executor_factory):
    executor, _, _, _ = executor_factory([])
    assert executor._build_final_response([], "") is None


def test_response_to_actions_invokes_safety_and_planner(executor_factory, monkeypatch):
    executor, _, planner, safety = executor_factory([[]])
    dummy_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="text"))]
    )
    actions = executor._response_to_actions(dummy_response)
    assert planner.tool_calls and safety.calls
    assert actions == safety.calls[-1][1]


def test_extract_response_text_handles_missing_message(executor_factory):
    executor, _, _, _ = executor_factory([[]])
    response = SimpleNamespace(choices=[SimpleNamespace()])
    assert executor._extract_response_text(response) == ""


def test_extract_response_text_returns_empty_without_choices(executor_factory):
    executor, _, _, _ = executor_factory([])
    response = SimpleNamespace()
    assert executor._extract_response_text(response) == ""


def test_fallback_non_streaming_synthesizes_response(executor_factory):
    executor, _, _, _ = executor_factory([])
    # Simulate llm returning None
    executor._llm = StubLLM([None])
    response = executor._fallback_non_streaming({"foo": "bar"})
    assert getattr(response, "id", "") == "fallback"
    assert response.choices[0].message.content == ""


def test_fallback_non_streaming_augments_existing_response(executor_factory):
    class Response:
        def __init__(self):
            self.choices = []

    executor, _, _, _ = executor_factory([])
    executor._llm = StubLLM([Response()])
    response = executor._fallback_non_streaming({})
    assert response.choices and hasattr(response.choices[0].message, "content")


def test_fallback_non_streaming_preserves_existing_id(executor_factory):
    class Response:
        def __init__(self):
            self.choices = []
            self.id = "existing"

    executor, _, _, _ = executor_factory([])
    executor._llm = StubLLM([Response()])
    response = executor._fallback_non_streaming({})
    assert response.id == "existing"


def test_fallback_non_streaming_with_valid_response(executor_factory):
    class Response:
        def __init__(self):
            msg = SimpleNamespace(content="done")
            delta = SimpleNamespace(content="done")
            self.choices = [SimpleNamespace(message=msg, delta=delta)]
            self.id = "real"

    executor, _, _, _ = executor_factory([])
    executor._llm = StubLLM([Response()])
    response = executor._fallback_non_streaming({})
    assert response.choices[0].message.content == "done"


def test_stream_llm_response_adds_final_chunk(executor_factory):
    executor, _, _, _ = executor_factory([])
    chunks = [Chunk("token")]
    executor._llm = StubLLM([chunks])
    stream = DummyEventStream()
    content, recorded = executor._stream_llm_response({}, stream)
    assert content == "token"
    assert len(recorded) == 1 and recorded[0].choices[0].delta.content == "token"
    assert stream.events  # final chunk emitted when accumulated_content non-empty


def test_stream_llm_response_skips_empty_chunks(executor_factory):
    class EmptyChoices:
        choices: list[Any] = []

    class NoToken:
        def __init__(self):
            self.choices = [SimpleNamespace(delta=SimpleNamespace(content=None))]

    executor, _, _, _ = executor_factory([])
    executor._llm = StubLLM([[EmptyChoices(), NoToken()]])
    content, recorded = executor._stream_llm_response({}, None)
    assert content == ""
    assert recorded == []


def test_stream_llm_response_without_event_stream(executor_factory):
    executor, _, _, _ = executor_factory([])
    executor._llm = StubLLM([[Chunk("token")]])
    content, recorded = executor._stream_llm_response({}, None)
    assert content == "token"


def test_build_final_response_merges_chunks():
    executor = CodeActExecutor(
        llm=StubLLM([]),
        safety_manager=StubSafety(),
        planner=StubPlanner(),
        mcp_tool_name_provider=lambda: [],
    )
    chunks = [Chunk("Hello "), Chunk("world")]
    response = executor._build_final_response(chunks, "combined")
    assert response.choices[0].delta.content == "combined"


def test_extract_response_text_returns_message(executor_factory):
    executor, _, _, _ = executor_factory([])
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="text"))]
    )
    assert executor._extract_response_text(response) == "text"


def test_extract_response_text_handles_message_without_content(executor_factory):
    executor, _, _, _ = executor_factory([])
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))]
    )
    assert executor._extract_response_text(response) == ""

