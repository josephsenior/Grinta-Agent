"""Unit tests for `forge.agenthub.browsing_agent.browsing_agent_ultimate`."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

import pytest
from browsergym.core.action.highlevel import HighLevelActionSet

import forge.agenthub.browsing_agent.browsing_agent_ultimate as browsing
from forge.agenthub.browsing_agent.browsing_agent_ultimate import (
    UltimateBrowsingAgent as BrowsingAgent,
)
from forge.agenthub.browsing_agent.response_parser import BrowsingResponseParser
from forge.core.config import AgentConfig
from forge.core.message import ImageContent, Message, TextContent
from forge.controller.state.state import State
from forge.events.action import (
    Action,
    AgentFinishAction,
    BrowseInteractiveAction,
    MessageAction,
)
from forge.events.event import EventSource
from forge.events.observation.browse import BrowserOutputObservation
from forge.llm.llm_registry import LLMRegistry
from forge.agenthub.browsing_agent.state_tracker import BrowsingStateTracker, PageVisit


class DummyLLM:
    """Minimal LLM stub capturing completion calls."""

    def __init__(self, response: object | None = None) -> None:
        self.response = response or "dummy-response"
        self.calls: list[dict[str, object]] = []

    def completion(self, messages, stop=None, **kwargs):  # pragma: no cover - exercised in tests
        """Return preset response and store call metadata."""
        payload = {"messages": messages, "stop": stop}
        if kwargs:
            payload.update(kwargs)
        self.calls.append(payload)
        return self.response


class DummyLLMRegistry:
    """Minimal registry stub returning a provided LLM."""

    def __init__(self, llm: DummyLLM) -> None:
        self.llm = llm
        self.requests: list[tuple[str, AgentConfig]] = []

    def get_llm_from_agent_config(
        self, service_id: str, config: AgentConfig
    ) -> DummyLLM:
        self.requests.append((service_id, config))
        return self.llm


class DummyResponseParser(BrowsingResponseParser):
    """Response parser stub returning a predetermined action."""

    def __init__(self, action: Action) -> None:
        super().__init__()
        self._action = action

    def parse(
        self, response: str | dict[str, list[dict[str, dict[str, str | None]]]]
    ) -> Action:
        return self._action


def _set_error_accumulator(agent: BrowsingAgent, value: int) -> None:
    cast(Any, agent).error_accumulator = value


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
    agent = BrowsingAgent(
        config=AgentConfig(), llm_registry=cast(LLMRegistry, registry)
    )
    agent_any = cast(Any, agent)
    agent_any.action_space = HighLevelActionSet()
    agent_any.response_parser = BrowsingResponseParser()
    agent_any.error_accumulator = 0
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
    action = BrowseInteractiveAction(
        browser_actions=actions, browsergym_send_msg_to_user=send_msg
    )
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


def _attach_tracker(agent: BrowsingAgent) -> BrowsingStateTracker:
    tracker = BrowsingStateTracker(session_id="session", goal="Find info")
    tracker.visit_page("http://first")
    tracker.visit_page("http://second")
    cast(Any, agent).state_tracker = tracker
    return tracker


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

    prompt = browsing.get_prompt(
        "prefix", "http://example.com", "tree", "action history"
    )
    assert "extra instructions" in prompt


def test_extract_context_collects_actions_messages_and_observations(
    agent: BrowsingAgent,
):
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

    result = agent.step(state)
    assert isinstance(result, AgentFinishAction)
    assert result.outputs["content"] == "Send this to user"


def test_step_returns_user_message_when_last_action_requests_message(
    agent: BrowsingAgent,
):
    browsing.EVAL_MODE = False
    action = _make_browse_action("noop()", send_msg="Hello User")
    state = State(history=[action])

    result = agent.step(state)
    assert isinstance(result, MessageAction)
    assert result.content == "Hello User"


def test_step_returns_noop_action_in_eval_mode(agent: BrowsingAgent):
    browsing.EVAL_MODE = True
    state = State(history=[_make_browse_action("noop()")])

    result = agent.step(state)
    assert isinstance(result, BrowseInteractiveAction)
    assert result.browser_actions == "noop()"


def test_handle_browser_error_returns_failure_after_too_many_errors(
    agent: BrowsingAgent,
):
    _set_error_accumulator(agent, 5)
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": _make_browser_obs(error=True, last_action="click('a')"),
    }

    action = agent._handle_browser_error(context)
    assert isinstance(action, MessageAction)
    assert "Too many errors" in action.content


def test_handle_browser_error_returns_message_when_flatten_fails(
    agent: BrowsingAgent, monkeypatch
):
    _set_error_accumulator(agent, 0)
    monkeypatch.setattr(
        browsing,
        "flatten_axtree_to_str",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")),
    )
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": _make_browser_obs(error=True, last_action="click('b')"),
    }

    action = agent._handle_browser_error(context)
    assert isinstance(action, MessageAction)
    assert "Error encountered" in action.content


def test_handle_browser_error_updates_context_and_returns_none(
    agent: BrowsingAgent, monkeypatch
):
    _set_error_accumulator(agent, 0)
    monkeypatch.setattr(
        browsing, "flatten_axtree_to_str", lambda *args, **kwargs: "AX TREE"
    )
    observation = _make_browser_obs(
        error=True, last_action="click('c')", url="http://foo"
    )
    context = {
        "cur_axtree_txt": "",
        "cur_url": "",
        "error_prefix": "",
        "last_obs": observation,
    }

    result = cast(Action | None, agent._handle_browser_error(context))
    assert result is None
    assert context["cur_url"] == "http://foo"
    assert context["cur_axtree_txt"] == "AX TREE"
    error_prefix = cast(str, context["error_prefix"])
    assert error_prefix.startswith("IMPORTANT! Last action is incorrect")


def test_generate_browsing_action_uses_fallback_task_and_parser(
    agent: BrowsingAgent, dummy_llm: DummyLLM
):
    dummy_response = object()
    dummy_llm.response = dummy_response
    expected_action = BrowseInteractiveAction(browser_actions="expected-action")
    cast(Any, agent).response_parser = DummyResponseParser(expected_action)

    state = State(history=[], inputs={"task": "Fallback task"})
    state.get_current_user_intent = lambda: (None, None)  # type: ignore[assignment]
    context = {
        "prev_actions": ["click('1')"],
        "error_prefix": "",
        "cur_url": "http://example.com",
        "cur_axtree_txt": "AX tree",
    }

    result = agent._generate_browsing_action(state, context)
    assert result is expected_action
    assert dummy_llm.calls, "LLM completion should have been invoked"
    recorded_call = dummy_llm.calls[0]
    assert cast(list[str], recorded_call["stop"]) == [")```", ")\n```"]
    messages = cast(list[Message], recorded_call["messages"])
    system_message = messages[0]
    assert system_message.content
    assert isinstance(system_message.content[0], TextContent)
    assert "Fallback task" in system_message.content[0].text
    user_message = messages[1]
    assert user_message.content
    assert isinstance(user_message.content[0], TextContent)
    assert "click('1')" in user_message.content[0].text


def test_track_action_records_click_and_type(agent: BrowsingAgent) -> None:
    tracker = _attach_tracker(agent)
    agent._track_action('click("cta")')
    agent._track_action('type("username", "alice")')

    assert tracker.current_page is not None
    assert tracker.current_page.elements_interacted[-1].startswith("type:")
    assert tracker.session.form_fields_filled["username"] == "alice"


def test_build_observation_content_includes_error_state_and_screenshot(
    agent: BrowsingAgent,
) -> None:
    tracker = _attach_tracker(agent)
    tracker.current_page.elements_interacted.append("click:header")
    tracker.track_form_data("email", "user@example.com")
    tracker.session.visited_pages.append(tracker.current_page)

    context = {
        "error_prefix": "Something went wrong",
        "cur_url": "http://example.com",
        "cur_axtree_txt": "AX TREE",
        "prev_actions": ["click('1')", "type('q', 'term')"],
        "screenshot_url": "http://img",
    }

    cast(Any, agent).state_tracker = tracker

    content = agent._build_observation_content(context)
    assert isinstance(content[0], TextContent)
    assert "Error from Previous Action" in content[0].text
    assert "Session Stats" in content[0].text
    assert isinstance(content[1], ImageContent)
    assert content[1].image_urls == ["http://img"]


def test_build_react_messages_fallback_when_template_missing(
    agent: BrowsingAgent,
) -> None:
    tracker = _attach_tracker(agent)

    class StubPromptManager:
        def get_system_message(self, goal: str) -> str:
            return ""

    cast(Any, agent)._prompt_manager = StubPromptManager()
    context = {
        "error_prefix": "",
        "cur_url": "http://example.com",
        "cur_axtree_txt": "tree",
        "prev_actions": [],
        "screenshot_url": None,
    }

    cast(Any, agent).state_tracker = tracker
    messages = agent._build_react_messages("Browse docs", context)
    assert len(messages) == 3
    assert "You are a web browsing agent" in messages[0].content[0].text
    assert "Browsing Context" in messages[1].content[0].text
    assert isinstance(messages[2].content[0], TextContent)


def test_generate_browsing_action_react_enforces_tool_choice(
    agent: BrowsingAgent, dummy_llm: DummyLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    tracker = _attach_tracker(agent)
    context = agent._base_context()
    context["cur_url"] = "http://example.com"
    context["cur_axtree_txt"] = "tree"

    expected_action = _make_browse_action("click('submit')")
    cast(Any, agent).response_parser = DummyResponseParser(expected_action)
    cast(Any, agent).state_tracker = tracker
    cast(Any, agent)._prompt_manager = type(
        "StubPM", (), {"get_system_message": lambda self, goal: "system"}
    )()

    monkeypatch.setattr(
        browsing.UltimateBrowsingAgent,
        "_supports_tool_choice",
        lambda self: True,
    )

    state = State(history=[])
    state.get_current_user_intent = lambda: ("Goal", None)  # type: ignore[assignment]

    result = agent._generate_browsing_action_react(state, context)
    assert result is expected_action
    assert dummy_llm.calls, "LLM should be invoked"
    assert dummy_llm.calls[0]["tool_choice"] == "auto"


def test_handle_browser_error_smart_handles_retries_and_backtracking(
    agent: BrowsingAgent,
) -> None:
    tracker = _attach_tracker(agent)
    observation = _make_browser_obs(error=True, last_action="click('1')")
    observation.last_browser_action_error = "Network fail"
    last_action = _make_browse_action("click('1')")
    context = {
        "last_obs": observation,
        "last_action": last_action,
    }
    cast(Any, agent).state_tracker = tracker
    cast(Any, agent).retry_count = agent.max_retries - 1
    cast(Any, agent).last_failed_action = str(last_action)

    state = State(history=[])
    result = agent._handle_browser_error_smart(context, state)
    assert isinstance(result, BrowseInteractiveAction)
    assert result.browser_actions == "go_back()"
    assert tracker.session.errors_encountered[-1] == "Network fail"


def test_handle_browser_error_smart_limits_total_errors(agent: BrowsingAgent) -> None:
    tracker = _attach_tracker(agent)
    observation = _make_browser_obs(error=True, last_action="noop()")
    observation.last_browser_action_error = "fatal"
    context = {"last_obs": observation, "last_action": None}
    cast(Any, agent).state_tracker = tracker
    cast(Any, agent).error_accumulator = 8

    result = agent._handle_browser_error_smart(context, State(history=[]))
    assert isinstance(result, MessageAction)
    assert "Too many errors" in result.content


def test_track_action_performance_and_report(agent: BrowsingAgent) -> None:
    agent.track_action_performance("click", 100, True)
    agent.track_action_performance("type", 200, False)
    report = agent.get_performance_report()

    assert report["total_actions"] == 2
    assert report["successful_actions"] == 1
    assert report["failed_actions"] == 1
    assert report["success_rate"] == 50.0
    assert report["avg_action_time_ms"] == 150.0


def test_export_session_includes_session_data(agent: BrowsingAgent) -> None:
    tracker = _attach_tracker(agent)
    tracker.track_interaction("cta", "click")
    tracker.track_form_data("query", "value")
    tracker.track_error("Timeout")
    cast(Any, agent).state_tracker = tracker
    agent.track_action_performance("click", 120, True)

    data = agent.export_session()
    assert data["goal"] == "Find info"
    assert data["visited_pages"]
    assert data["interactions"]
    assert data["form_data"]["query"] == "value"
    assert data["performance"]["total_actions"] == 1


def test_collect_session_interactions_serializes_entries(agent: BrowsingAgent) -> None:
    visits = []
    for idx in range(2):
        visit = PageVisit(
            url=f"http://page{idx}",
            timestamp=datetime(2024, 1, 1, 12, 0, idx),
            title=f"Page {idx}",
        )
        visit.elements_interacted.append(f"click:btn-{idx}")
        visits.append(visit)

    entries = agent._collect_session_interactions(visits)
    assert len(entries) == 2
    assert entries[0]["action_type"] == "click"
    assert entries[0]["url"] == "http://page0"


def test_action_space_respects_nav_flag(dummy_llm: DummyLLM, monkeypatch) -> None:
    browsing.USE_NAV = False
    registry = DummyLLMRegistry(dummy_llm)
    agent = BrowsingAgent(
        config=AgentConfig(), llm_registry=cast(LLMRegistry, registry)
    )
    description = agent.action_space.describe()
    assert "nav" not in description


def test_prompt_manager_property_caches_instance(
    agent: BrowsingAgent, monkeypatch
) -> None:
    instances: list[object] = []

    class StubPromptManager:
        def __init__(self, *_, **__):
            instances.append(self)

    monkeypatch.setattr(browsing, "PromptManager", StubPromptManager)
    cast(Any, agent)._prompt_manager = None
    pm1 = agent.prompt_manager
    pm2 = agent.prompt_manager
    assert pm1 is pm2
    assert len(instances) == 1


def test_reset_logs_when_metrics_populated(agent: BrowsingAgent) -> None:
    agent.track_action_performance("click", 100, True)
    agent.reset()
    assert cast(Any, agent).error_accumulator == 0


def test_step_invokes_smart_error_recovery(agent: BrowsingAgent, monkeypatch) -> None:
    observation = _make_browser_obs(error=True, last_action="noop()")
    observation.last_browser_action_error = "boom"
    state = State(history=[observation])
    state.get_current_user_intent = lambda: ("goal", None)  # type: ignore[assignment]
    recovered_action = MessageAction("Recovered")

    called = {}

    def fake_handle(self, context, state_arg):
        called["context"] = context
        return recovered_action

    monkeypatch.setattr(
        browsing.UltimateBrowsingAgent, "_handle_browser_error_smart", fake_handle
    )

    result = agent.step(state)
    assert result is recovered_action
    assert "last_obs" in called["context"]


def test_extract_context_with_browser_observation_tracks_visit(
    agent: BrowsingAgent, monkeypatch
) -> None:
    tracker = _attach_tracker(agent)
    monkeypatch.setattr(browsing, "flatten_axtree_to_str", lambda *args, **kwargs: "AX")
    observation = BrowserOutputObservation(
        content="obs",
        url="http://new",
        trigger_by_action="action",
        axtree_object={"role": "root"},
        screenshot="shot",
    )
    state = State(history=[observation])
    context = agent._extract_context_from_state(state)
    assert context["cur_axtree_txt"] == "AX"
    assert context["screenshot_url"] == "shot"
    assert tracker.session.navigation_path[-1] == "http://new"


def test_safe_flatten_axtree_handles_missing_tree(agent: BrowsingAgent) -> None:
    observation = BrowserOutputObservation(
        content="obs", url="http://example", trigger_by_action="noop()"
    )
    observation.axtree_object = None
    assert agent._safe_flatten_axtree(observation) == ""


def test_track_action_returns_early_when_no_tracker(agent: BrowsingAgent) -> None:
    cast(Any, agent).state_tracker = None
    agent._track_action('click("noop")')


def test_should_return_agent_message_and_handle_error_flags(agent: BrowsingAgent) -> None:
    context = agent._base_context()
    context["agent_message"] = _make_message("hi", EventSource.AGENT)
    assert agent._should_return_agent_message(context) is True
    context["last_obs"] = _make_browser_obs(error=True, last_action="noop()")
    assert agent._should_handle_browser_error(context) is True


def test_handle_browser_error_smart_returns_message_when_cannot_go_back(
    agent: BrowsingAgent,
) -> None:
    observation = _make_browser_obs(error=True, last_action="noop()")
    observation.last_browser_action_error = "fail"
    action = _make_browse_action("noop()")
    context = {"last_obs": observation, "last_action": action}
    cast(Any, agent).state_tracker = None
    cast(Any, agent).retry_count = agent.max_retries - 1
    cast(Any, agent).last_failed_action = str(action)
    result = agent._handle_browser_error_smart(context, State(history=[]))
    assert isinstance(result, MessageAction)
    assert "Cannot proceed" in result.content


def test_handle_browser_error_smart_allows_retry_logging(agent: BrowsingAgent) -> None:
    observation = _make_browser_obs(error=True, last_action="noop()")
    observation.last_browser_action_error = "transient"
    context = {"last_obs": observation, "last_action": _make_browse_action("retry()")}
    cast(Any, agent).state_tracker = None
    cast(Any, agent).retry_count = 0
    cast(Any, agent).last_failed_action = "different"
    result = agent._handle_browser_error_smart(context, State(history=[]))
    assert result is None


def test_handle_browser_error_returns_none_without_observation(
    agent: BrowsingAgent,
) -> None:
    context = agent._base_context()
    assert agent._handle_browser_error(context) is None


def test_generate_browsing_action_react_uses_task_fallback(
    agent: BrowsingAgent, dummy_llm: DummyLLM
) -> None:
    context = agent._base_context()
    state = State(history=[], inputs={"task": "Task goal"})
    state.get_current_user_intent = lambda: (None, None)  # type: ignore[assignment]
    expected_action = _make_browse_action("click('1')")
    cast(Any, agent).response_parser = DummyResponseParser(expected_action)
    cast(Any, agent)._prompt_manager = type(
        "StubPM", (), {"get_system_message": lambda self, goal: "system"}
    )()
    cast(Any, agent).llm.config = type("Cfg", (), {"model": "local"})()
    result = agent._generate_browsing_action_react(state, context)
    assert result is expected_action


def test_generate_browsing_action_legacy_default_goal(
    agent: BrowsingAgent, dummy_llm: DummyLLM
) -> None:
    expected_action = _make_browse_action("noop()")
    cast(Any, agent).response_parser = DummyResponseParser(expected_action)
    state = State(history=[])
    state.inputs = []  # type: ignore[assignment]
    state.get_current_user_intent = lambda: (None, None)  # type: ignore[assignment]
    result = agent._generate_browsing_action(state, agent._base_context())
    assert result is expected_action
    recorded_messages = dummy_llm.calls[0]["messages"]
    assert any(
        "Browse the web" in content.text
        for msg in recorded_messages
        for content in msg.content
        if isinstance(content, TextContent)
    )


def test_supports_tool_choice_checks_model_name(agent: BrowsingAgent) -> None:
    cast(Any, agent).llm.config = type("Cfg", (), {"model": "gpt-4"})()
    assert agent._supports_tool_choice() is True
    cast(Any, agent).llm.config.model = "local-only"
    assert agent._supports_tool_choice() is False


def test_response_to_actions_parses_response(agent: BrowsingAgent) -> None:
    expected_action = _make_browse_action("noop()")
    cast(Any, agent).response_parser = DummyResponseParser(expected_action)
    result = agent.response_to_actions("raw")
    assert result == [expected_action]


def test_track_action_performance_warns_on_slow_action(agent: BrowsingAgent) -> None:
    agent.track_action_performance("click", 6000, True)


def test_get_performance_report_handles_zero_actions(agent: BrowsingAgent) -> None:
    report = agent.get_performance_report()
    assert report["success_rate"] == 0.0


def test_export_session_returns_error_when_tracker_missing(
    agent: BrowsingAgent,
) -> None:
    cast(Any, agent).state_tracker = None
    assert agent.export_session() == {"error": "No active session"}


def test_step_falls_back_to_react_generation(
    agent: BrowsingAgent, monkeypatch: pytest.MonkeyPatch
) -> None:
    produced = MessageAction("react")

    def fake_generate(self, state_arg, context):
        return produced

    monkeypatch.setattr(
        browsing.UltimateBrowsingAgent,
        "_generate_browsing_action_react",
        fake_generate,
    )
    state = State(history=[])
    state.get_current_user_intent = lambda: ("goal", None)  # type: ignore[assignment]

    result = agent.step(state)
    assert result is produced
