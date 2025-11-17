from __future__ import annotations

from types import SimpleNamespace

import pytest

import forge.agenthub.visualbrowsing_agent.visualbrowsing_agent as vba


class DummyAction:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class DummyBrowseInteractiveAction(DummyAction):
    def __init__(
        self,
        browser_actions: str = "",
        return_axtree: bool = False,
        thought: str = "",
        browsergym_send_msg_to_user: str | None = None,
    ):
        super().__init__(
            browser_actions=browser_actions,
            return_axtree=return_axtree,
            thought=thought,
            browsergym_send_msg_to_user=browsergym_send_msg_to_user,
        )


class DummyMessageAction(DummyAction):
    def __init__(self, content):
        super().__init__(content=content, source=None)


class DummyAgentFinishAction(DummyAction):
    pass


class DummyObservation:
    pass


class DummyBrowserOutputObservation(DummyObservation):
    def __init__(
        self,
        error: bool = False,
        last_browser_action_error: str = "",
        focused_element_bid: str | None = None,
        open_pages_urls=None,
        active_page_index: int = 0,
        axtree_object=None,
        extra_element_properties=None,
        set_of_marks: str | None = None,
    ):
        if open_pages_urls is None:
            open_pages_urls = []
        super().__init__()
        self.error = error
        self.last_browser_action_error = last_browser_action_error
        self.focused_element_bid = focused_element_bid
        self.open_pages_urls = open_pages_urls
        self.active_page_index = active_page_index
        self.axtree_object = axtree_object
        self.extra_element_properties = extra_element_properties
        self.set_of_marks = set_of_marks


class DummyTextContent:
    def __init__(self, type: str = "text", text: str = ""):
        self.type = type
        self.text = text


class DummyImageContent:
    def __init__(self, image_urls):
        self.image_urls = image_urls


class DummyMessage:
    def __init__(self, role: str, content):
        self.role = role
        self.content = content


class DummyActionSet:
    def __init__(self, subsets, strict, multiaction):
        self.subsets = subsets
        self.strict = strict
        self.multiaction = multiaction

    def describe(self, with_long_description=False, with_examples=False):
        return "ACTION DESC"

    def example_action(self, abstract=False):
        return "click('123')"


class DummyResponseParser:
    def __init__(self):
        self.last = None

    def parse(self, response):
        self.last = response
        return "parsed-action"


class DummyLLM:
    def __init__(self):
        self.calls = []

    def completion(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "ok"}


class DummyLLMRegistry:
    def __init__(self):
        self.llm = DummyLLM()

    def get_llm_from_agent_config(self, *_):
        return self.llm


class DummyState:
    def __init__(self, view, goal=("Goal", ["img://goal"]), task="Task"):
        self.view = view
        self._goal = goal
        self.inputs = {"task": task}

    def get_current_user_intent(self):
        return self._goal


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(vba, "HighLevelActionSet", DummyActionSet)
    monkeypatch.setattr(vba, "BrowseInteractiveAction", DummyBrowseInteractiveAction)
    monkeypatch.setattr(vba, "MessageAction", DummyMessageAction)
    monkeypatch.setattr(vba, "AgentFinishAction", DummyAgentFinishAction)
    monkeypatch.setattr(vba, "Observation", DummyObservation)
    monkeypatch.setattr(vba, "BrowserOutputObservation", DummyBrowserOutputObservation)
    monkeypatch.setattr(vba, "TextContent", DummyTextContent)
    monkeypatch.setattr(vba, "ImageContent", DummyImageContent)
    monkeypatch.setattr(vba, "Message", DummyMessage)
    monkeypatch.setattr(vba, "EventSource", SimpleNamespace(AGENT="agent"))
    monkeypatch.setattr(vba, "flatten_axtree_to_str", lambda *args, **kwargs: "AX")


@pytest.fixture
def agent(monkeypatch):
    parser = DummyResponseParser()
    vba.VisualBrowsingAgent.response_parser = parser
    config = SimpleNamespace(cli_mode=False)
    llm_registry = DummyLLMRegistry()
    agent = vba.VisualBrowsingAgent(config, llm_registry)
    agent.response_parser = parser
    return agent, parser, llm_registry.llm


def test_get_error_prefix_handles_timeout():
    obs = SimpleNamespace(last_browser_action_error="timeout after click")
    assert vba.get_error_prefix(obs) == ""


def test_get_error_prefix_includes_error_text():
    obs = SimpleNamespace(last_browser_action_error="boom")
    assert "boom" in vba.get_error_prefix(obs)


def test_create_goal_prompt_with_images():
    txt, images = vba.create_goal_prompt("Do a thing", ["img://1", "img://2"])
    assert "Goal" in txt and len(images) == 2


def test_create_observation_prompt_with_screenshot(caplog):
    text, screenshot = vba.create_observation_prompt("AX", "tabs", "focus", "", "img")
    assert "Image:" in text and screenshot == "img"


def test_get_tabs_marks_active_tab():
    obs = SimpleNamespace(open_pages_urls=["a", "b"], active_page_index=1)
    prompt = vba.get_tabs(obs)
    assert "active tab" in prompt


def test_get_axtree_includes_notes():
    out = vba.get_axtree("data")
    assert "bid" in out and "visible" in out


def test_get_action_prompt_includes_description():
    action_set = DummyActionSet(["chat"], False, False)
    prompt = vba.get_action_prompt(action_set)
    assert "ACTION DESC" in prompt


def test_get_history_prompt_formats_steps():
    actions = [
        DummyBrowseInteractiveAction(thought="t1", browser_actions="[]"),
        DummyBrowseInteractiveAction(thought="t2", browser_actions="[]"),
    ]
    prompt = vba.get_history_prompt(actions)
    assert "step 1" in prompt and "step 2" in prompt


def test_handle_initial_state_returns_noop(agent):
    agent_instance, _, _ = agent
    state = DummyState(view=[object()])
    action = agent_instance._handle_initial_state(state)
    assert isinstance(action, DummyBrowseInteractiveAction)
    assert action.browser_actions == "noop(1000)"


def test_process_events_trims_first_action(agent):
    agent_instance, _, _ = agent
    history = [
        DummyBrowseInteractiveAction(),
        DummyBrowseInteractiveAction(thought="keep"),
        DummyBrowserOutputObservation(),
    ]
    state = DummyState(view=history)
    prev_actions, last_action, last_obs = agent_instance._process_events(state)
    assert len(prev_actions) == 1
    assert last_action is history[1]
    assert isinstance(last_obs, DummyBrowserOutputObservation)


def test_handle_user_message_action_returns_message(agent):
    agent_instance, _, _ = agent
    action = DummyBrowseInteractiveAction(
        browsergym_send_msg_to_user="hello there", thought="",
    )
    result = agent_instance._handle_user_message_action(action)
    assert isinstance(result, DummyMessageAction)
    assert result.content == "hello there"


def test_process_browser_observation_increments_error(agent):
    agent_instance, _, _ = agent
    obs = DummyBrowserOutputObservation(
        error=True,
        last_browser_action_error="boom",
        focused_element_bid="42",
        open_pages_urls=["https://example.com"],
        set_of_marks="img://current",
    )
    result = agent_instance._process_browser_observation(obs)
    assert agent_instance.error_accumulator == 1
    error_prefix, focused_element, tabs, ax, screenshot = result
    assert "boom" in error_prefix
    assert "bid='42'" in focused_element
    assert "https://example.com" in tabs
    assert "AX" in ax
    assert screenshot == "img://current"


def test_process_browser_observation_raises_after_many_errors(agent):
    agent_instance, _, _ = agent
    agent_instance.error_accumulator = 5
    obs = DummyBrowserOutputObservation(
        error=True, last_browser_action_error="boom", set_of_marks=None
    )
    with pytest.raises(RuntimeError):
        agent_instance._process_browser_observation(obs)


def test_process_browser_observation_handles_flatten_errors(agent, monkeypatch):
    agent_instance, _, _ = agent
    obs = DummyBrowserOutputObservation(
        error=False, last_browser_action_error="", set_of_marks=None
    )
    def raise_flatten(*_, **__):
        raise ValueError("bad tree")

    monkeypatch.setattr(vba, "flatten_axtree_to_str", raise_flatten)
    with pytest.raises(RuntimeError):
        agent_instance._process_browser_observation(obs)


def test_build_human_prompt_includes_images(agent):
    agent_instance, _, _ = agent
    state = DummyState(view=[object()])
    prompt = agent_instance._build_human_prompt(
        state,
        cur_axtree_txt="AX",
        tabs="tabs",
        focused_element="focus",
        error_prefix="",
        set_of_marks="img://obs",
        history_prompt="history",
    )
    image_entries = [item for item in prompt if isinstance(item, DummyImageContent)]
    assert len(image_entries) == 2  # goal image + observation screenshot


def test_step_returns_initial_action(agent):
    agent_instance, _, _ = agent
    state = DummyState(view=[object()])
    action = agent_instance.step(state)
    assert isinstance(action, DummyBrowseInteractiveAction)


def test_step_handles_user_message_action(agent):
    agent_instance, _, _ = agent
    message_action = DummyBrowseInteractiveAction(
        browsergym_send_msg_to_user="done", thought="",
    )
    message_action.source = "agent"
    obs = DummyBrowserOutputObservation()
    state = DummyState(view=[object(), message_action, obs])
    action = agent_instance.step(state)
    assert isinstance(action, DummyMessageAction)
    assert action.content == "done"


def test_step_runs_llm_and_parser(agent):
    agent_instance, parser, llm = agent
    browse_actions = [
        DummyBrowseInteractiveAction(thought="t1", browser_actions="[]"),
        DummyBrowseInteractiveAction(thought="t2", browser_actions="[]"),
    ]
    obs = DummyBrowserOutputObservation(
        error=False,
        last_browser_action_error="",
        focused_element_bid=None,
        open_pages_urls=["https://example.com"],
        active_page_index=0,
        set_of_marks="img://som",
    )
    state = DummyState(view=[object(), *browse_actions, obs])
    result = agent_instance.step(state)
    assert result == "parsed-action"
    assert llm.calls, "LLM should be invoked"
    assert parser.last is not None

