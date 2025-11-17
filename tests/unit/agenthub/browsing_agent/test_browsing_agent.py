"""Tests for the main browsing agent helper functions and error handling."""

from __future__ import annotations

from typing import Any, cast

import pytest

from forge.agenthub.browsing_agent import browsing_agent_ultimate as module
from forge.agenthub.browsing_agent.browsing_agent_ultimate import (
    UltimateBrowsingAgent as BrowsingAgent,
    BrowsingResponseParser,
    get_error_prefix,
    get_prompt,
    get_system_message,
)
from forge.controller.state.state import State
from forge.core.config.agent_config import AgentConfig
from forge.events.action import Action, BrowseInteractiveAction, MessageAction
from forge.events.event import EventSource
from forge.events.observation import BrowserOutputObservation, Observation
from forge.llm.llm_registry import LLMRegistry


class DummyLLM:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def completion(self, messages, stop):
        self.calls.append((messages, stop))
        # Minimal response understood by the default parser
        return {"choices": [{"message": {"content": '```click("12")```'}}]}


class DummyLLMRegistry:
    def __init__(self) -> None:
        self.llm = DummyLLM()

    def get_llm_from_agent_config(self, service_id, config):  # noqa: D401 - signature matches Agent expectations
        return self.llm

    def get_llm(self, service_id, config=None):
        return self.llm


def make_agent() -> BrowsingAgent:
    registry = DummyLLMRegistry()
    agent = BrowsingAgent(
        config=AgentConfig(), llm_registry=cast(LLMRegistry, registry)
    )
    agent_any = cast(Any, agent)
    agent_any.error_accumulator = 0
    # Provide a minimal response parser stub to avoid hitting heavy logic
    agent_any.response_parser = BrowsingResponseParser()
    return agent


def _set_error_accumulator(agent: BrowsingAgent, value: int) -> None:
    cast(Any, agent).error_accumulator = value


def test_get_error_prefix_formats_message() -> None:
    result = get_error_prefix('click("12")')
    assert 'click("12")' in result
    assert result.startswith("IMPORTANT! Last action is incorrect")


def test_get_system_message_includes_goal_and_actions() -> None:
    system = get_system_message("Find docs", "Allowed: click")
    assert "Find docs" in system
    assert "Allowed: click" in system


def test_get_prompt_respects_concise_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(module, "USE_CONCISE_ANSWER", True)
    prompt = get_prompt("ERR", "https://example.com", "AXTREE", 'click("1")')
    assert "Current Page URL" in prompt
    assert module.CONCISE_INSTRUCTION.strip() in prompt

    monkeypatch.setattr(module, "USE_CONCISE_ANSWER", False)
    prompt = get_prompt("ERR", "https://example.com", "AXTREE", 'click("1")')
    assert module.CONCISE_INSTRUCTION.strip() not in prompt


def test_extract_context_from_state_identifies_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "EVAL_MODE", False)
    agent = make_agent()
    browse_action = BrowseInteractiveAction(browser_actions='click("1")')
    user_message = MessageAction("Agent says hi")
    user_message._source = EventSource.AGENT
    observation = BrowserOutputObservation(
        url="https://example.com",
        trigger_by_action='click("1")',
        content="page",
    )

    state = State(
        history=[browse_action, user_message, observation],
        inputs={"task": "default task"},
    )
    context = agent._extract_context_from_state(state)

    assert context["prev_actions"] == ['click("1")']
    assert context["last_action"] is browse_action
    assert context["agent_message"] is user_message
    assert context["last_obs"] is observation


def test_should_return_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = make_agent()
    browse_action = BrowseInteractiveAction(
        browser_actions="noop()", browsergym_send_msg_to_user="Hello user"
    )
    context = {
        "agent_message": MessageAction("hi"),
        "last_action": browse_action,
        "last_obs": BrowserOutputObservation(
            url="https://example.com",
            trigger_by_action="noop()",
            content="noop",
            error=True,
        ),
    }
    context["agent_message"]._source = EventSource.AGENT

    assert agent._should_return_agent_message(context) is True
    should_return_user_message = agent._should_return_user_message(context)
    assert bool(should_return_user_message) is True
    assert browse_action.browsergym_send_msg_to_user == "Hello user"
    assert agent._should_handle_browser_error(context) is True


def test_handle_browser_error_updates_context(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = make_agent()
    monkeypatch.setattr(
        module, "flatten_axtree_to_str", lambda *args, **kwargs: "AXTREE"
    )
    context = {
        "last_obs": BrowserOutputObservation(
            url="https://example.com",
            trigger_by_action="noop()",
            content="content",
            error=True,
            last_browser_action="noop()",
        ),
    }

    result = cast(Action | None, agent._handle_browser_error(context))
    assert result is None  # Continue processing
    assert cast(Any, agent).error_accumulator == 1
    error_prefix = cast(str, context["error_prefix"])
    assert error_prefix.startswith("IMPORTANT! Last action is incorrect")
    assert context["cur_url"] == "https://example.com"
    assert context["cur_axtree_txt"] == "AXTREE"


def test_handle_browser_error_returns_message_after_threshold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = make_agent()
    _set_error_accumulator(agent, 5)
    context = {
        "last_obs": BrowserOutputObservation(
            url="https://example.com",
            trigger_by_action="noop()",
            content="content",
            error=True,
            last_browser_action="noop()",
        ),
    }

    action = cast(MessageAction, agent._handle_browser_error(context))
    assert isinstance(action, MessageAction)
    assert "Too many errors" in action.content


def test_handle_browser_error_returns_message_on_flatten_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = make_agent()

    def boom(*args: object, **kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "flatten_axtree_to_str", boom)
    context = {
        "last_obs": BrowserOutputObservation(
            url="https://example.com",
            trigger_by_action="noop()",
            content="content",
            error=True,
            last_browser_action="noop()",
        ),
    }

    action = cast(MessageAction, agent._handle_browser_error(context))
    assert isinstance(action, MessageAction)
    assert "Error encountered when browsing" in action.content
