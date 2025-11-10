"""Unit tests for `forge.agenthub.browsing_agent.browsing_agent`."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import forge.agenthub.browsing_agent.browsing_agent as browsing
from forge.agenthub.browsing_agent.browsing_agent import BrowsingAgent
from forge.core.config import AgentConfig
from forge.controller.state.state import State
from forge.events.action import AgentFinishAction, BrowseInteractiveAction, MessageAction
from forge.events.event import EventSource
from forge.events.observation.browse import BrowserOutputObservation


class DummyLLM:
    """Minimal LLM stub capturing completion calls."""

    def __init__(self, response: object | None = None) -> None:
        self.response = response or "dummy-response"
        self.calls: list[dict[str, object]] = []

    def completion(self, messages, stop=None):  # pragma: no cover - exercised in tests
        """Return preset response and store call metadata."""
        self.calls.append({"messages": messages, "stop": stop})
        return self.response


class DummyLLMRegistry:
    """Minimal registry stub returning a provided LLM."""

    def __init__(self, llm: DummyLLM) -> None:
        self.llm = llm
        self.requests: list[tuple[str, AgentConfig]] = []

    def get_llm_from_agent_config(self, service_id: str, config: AgentConfig) -> DummyLLM:
        self.requests.append((service_id, config))
        return self.llm


@pytest.fixture(autouse=True)
def restore_env_flags():
    """Ensure global flags modified during tests are restored afterwards."""
    original_use_nav = browsing.USE_NAV
    original_use_concise = browsing.USE_CONCISE_ANSWER
    original_eval_mode = browsing.EVAL_MODE
    yield
    browsing.USE_NAV = original_use_nav
    browsing.USE_CONCISE_ANSWER = original_use_concise
    browsing.EVAL_MODE = original_eval_mode


@pytest.fixture
def dummy_llm() -> DummyLLM:
    """Provide a reusable dummy LLM instance."""
    return DummyLLM()


@pytest.fixture
def agent(dummy_llm: DummyLLM) -> BrowsingAgent:
    """Instantiate a browsing agent wired to stub registries and parsers."""
    registry = DummyLLMRegistry(dummy_llm)
    agent = BrowsingAgent(config=AgentConfig(), llm_registry=registry)
    agent.action_space = SimpleNamespace(describe=lambda **_: "Allowed actions")
    agent.response_parser = SimpleNamespace(parse=lambda response: "parsed-action")
    agent.error_accumulator = 0
    return agent


def _make_message(content: str, source: EventSource | None = None) -> MessageAction:
    message = MessageAction(content)
    if source is not None:
        message._source = source
    return message


def _make_browse_action(
    actions: str,
    *,
    send_msg: str = "",
) -> BrowseInteractiveAction:
    action = BrowseInteractiveAction(browser_actions=actions, browsergym_send_msg_to_user=send_msg)
    action._source = EventSource.AGENT
    return action


def _make_browser_obs(
    *,
    error: bool,
    last_action: str,
    url: str = "http://example.com",
) -> BrowserOutputObservation:
    obs = BrowserOutputObservation(
        content="browser output",
        url=url,
        trigger_by_action="action",
        error=error,
        last_browser_action=last_action,
    )
    obs._source = EventSource.ENVIRONMENT
    return obs


def test_get_error_prefix_includes_last_action():
    prefix = browsing.get_error_prefix("click('submit')")
    assert "click('submit')" in prefix


def test_get_system_message_includes_goal_and_action_space():
    goal = "Find the product price"
    action_space = "Click, type, or send_msg_to_user"
    msg = browsing.get_system_message(goal, action_space)
    assert goal in msg
    assert action_space in msg


def test_get_prompt_appends_concise_instruction_when_enabled(monkeypatch):
    monkeypatch.setattr(browsing, "USE_CONCISE_ANSWER", True)
    monkeypatch.setattr(browsing, "CONCISE_INSTRUCTION", "\nextra instructions\n")

    prompt = browsing.get_prompt("prefix", "http://example.com", "tree", "action history")
    assert "extra instructions" in prompt


def test_extract_context_collects_actions_messages_and_observations(agent: BrowsingAgent):
    browse_action = _make_browse_action("click('1')")
    message = _make_message("Agent reply", EventSource.AGENT)
    observation = _make_browser_obs(error=False, last_action="noop()")

    state = State(history=[browse_action, message, observation])

    context = agent._extract_context_from_state(state)
    assert context["prev_actions"] == ["click('1')"]
    assert context["last_action"] is browse_action
    assert context["agent_message"] is message
    assert context["last_obs"] is observation


def test_extract_context_drops_initial_action_in_eval_mode(agent: BrowsingAgent):
    browsing.EVAL_MODE = True
    first_action = _make_browse_action("call('first')")
    second_action = _make_browse_action("call('second')")
    state = State(history=[first_action, second_action])

    context = agent._extract_context_from_state(state)
    assert context["prev_actions"] == ["call('second')"]
    assert context["last_action"] is second_action


def test_step_returns_finish_action_when_agent_message_present(agent: BrowsingAgent):
    browsing.EVAL_MODE = False
    agent_message = _make_message("Send this to user", EventSource.AGENT)
    state = State(history=[agent_message])

    result = agent.step(state, _make_browser_obs(error=False, last_action="noop()"))
    assert isinstance(result, AgentFinishAction)
    assert result.outputs["content"] == "Send this to user"


def test_step_returns_user_message_when_last_action_requests_message(agent: BrowsingAgent):
    browsing.EVAL_MODE = False
    action = _make_browse_action("noop()", send_msg="Hello User")
    state = State(history=[action])

    result = agent.step(state, _make_browser_obs(error=False, last_action="noop()"))
    assert isinstance(result, MessageAction)
    assert result.content == "Hello User"


def test_step_returns_noop_action_in_eval_mode(agent: BrowsingAgent):
    browsing.EVAL_MODE = True
    state = State(history=[_make_browse_action("noop()")])

    result = agent.step(state, _make_browser_obs(error=False, last_action="noop()"))
    assert isinstance(result, BrowseInteractiveAction)
    assert result.browser_actions == "noop()"


def test_handle_browser_error_returns_failure_after_too_many_errors(agent: BrowsingAgent):
    agent.error_accumulator = 5
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": _make_browser_obs(error=True, last_action="click('a')"),
    }

    action = agent._handle_browser_error(context)
    assert isinstance(action, MessageAction)
    assert "Too many errors" in action.content


def test_handle_browser_error_returns_message_when_flatten_fails(agent: BrowsingAgent, monkeypatch):
    agent.error_accumulator = 0
    monkeypatch.setattr(browsing, "flatten_axtree_to_str", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")))
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": _make_browser_obs(error=True, last_action="click('b')"),
    }

    action = agent._handle_browser_error(context)
    assert isinstance(action, MessageAction)
    assert "Error encountered" in action.content


def test_handle_browser_error_updates_context_and_returns_none(agent: BrowsingAgent, monkeypatch):
    agent.error_accumulator = 0
    monkeypatch.setattr(browsing, "flatten_axtree_to_str", lambda *args, **kwargs: "AX TREE")
    observation = _make_browser_obs(error=True, last_action="click('c')", url="http://foo")
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": observation,
    }

    result = agent._handle_browser_error(context)
    assert result is None
    assert context["cur_url"] == "http://foo"
    assert context["cur_axtree_txt"] == "AX TREE"
    assert context["error_prefix"].startswith("IMPORTANT! Last action is incorrect")


def test_generate_browsing_action_uses_fallback_task_and_parser(agent: BrowsingAgent, dummy_llm: DummyLLM):
    dummy_response = object()
    dummy_llm.response = dummy_response
    expected_action = "expected-action"
    agent.response_parser = SimpleNamespace(parse=lambda response: expected_action)

    state = State(history=[], inputs={"task": "Fallback task"})
    state.get_current_user_intent = lambda: (None, None)  # type: ignore[assignment]
    context = {
        "prev_actions": ["click('1')"],
        "error_prefix": "",
        "cur_url": "http://example.com",
        "cur_axtree_txt": "AX tree",
    }

    result = agent._generate_browsing_action(state, context)
    assert result == expected_action
    assert dummy_llm.calls, "LLM completion should have been invoked"
    recorded_call = dummy_llm.calls[0]
    assert recorded_call["stop"] == [")```", ")\n```"]
    system_message = recorded_call["messages"][0]
    assert "Fallback task" in system_message.content[0].text
    user_message = recorded_call["messages"][1]
    assert "click('1')" in user_message.content[0].text

