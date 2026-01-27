import pytest
from dataclasses import dataclass
from types import SimpleNamespace

from forge.controller.action_parser import (
    ActionParseError,
    ActionParser,
    ResponseParser,
)
from forge.controller.agent import Agent
from forge.controller.autonomy import AutonomyController, AutonomyLevel
from forge.events.action import Action, CmdRunAction, FileEditAction, FileWriteAction


@pytest.fixture(autouse=True)
def _clear_agent_registry():
    original = Agent._registry.copy()
    Agent._registry.clear()
    try:
        yield
    finally:
        Agent._registry = original


@dataclass
class _DummyAction(Action):
    content: str = "dummy"
    thought: str = ""


class _ConcreteParser(ResponseParser):
    def parse(self, response):
        text = self.parse_response(response)
        return self.parse_action(text)

    def parse_response(self, response):
        if "action" not in response:
            raise ActionParseError("missing action")
        return response["action"]

    def parse_action(self, action_str):
        if action_str == "dummy":
            return _DummyAction()
        raise ActionParseError("bad action")


class _ConcreteActionParser(ActionParser):
    def check_condition(self, action_str: str) -> bool:
        return action_str == "dummy"

    def parse(self, action_str: str) -> Action:
        return _DummyAction()


class _FakePromptManager:
    def __init__(self, message: str) -> None:
        self._message = message

    def get_system_message(self, cli_mode: bool, config):
        return self._message


class _TestAgent(Agent):
    def __init__(self):
        llm_registry = SimpleNamespace(
            get_llm_from_agent_config=lambda *_: SimpleNamespace(
                config=SimpleNamespace()
            )
        )
        config = SimpleNamespace(cli_mode=False)
        super().__init__(config=config, llm_registry=llm_registry)
        self._prompt_manager = _FakePromptManager("system-message")
        self._step_called = False

    def step(self, state):
        self._step_called = True
        return _DummyAction()


def test_action_parse_error_str():
    err = ActionParseError("boom")
    assert str(err) == "boom"


def test_response_parser_success():
    parser = _ConcreteParser()
    parser.action_parsers.append(_ConcreteActionParser())
    action = parser.parse({"action": "dummy"})
    assert isinstance(action, _DummyAction)


def test_response_parser_missing_action():
    parser = _ConcreteParser()
    with pytest.raises(ActionParseError) as exc:
        parser.parse({})
    assert "missing action" in str(exc.value)


def test_agent_get_system_message_and_registry():
    agent = _TestAgent()
    message_action = agent.get_system_message()
    assert message_action.content == "system-message"
    assert message_action.agent_class == agent.name


def test_agent_register_and_list():
    Agent.register("dummy", _TestAgent)
    assert "dummy" in Agent.list_agents()
    cls = Agent.get_cls("dummy")
    assert cls is _TestAgent


def test_agent_set_mcp_tools_adds_unique_tools(caplog):
    caplog.set_level("INFO")
    agent = _TestAgent()
    tool = {
        "type": "function",
        "function": {
            "name": "tool_one",
            "description": "",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    agent.set_mcp_tools([tool, tool])
    assert agent.tools[0]["function"]["name"] == "tool_one"
    # duplicate tool should be ignored, so list length stays 1
    assert len(agent.tools) == 1


class _AutonomyConfig(SimpleNamespace):
    autonomy_level: str = AutonomyLevel.BALANCED.value
    auto_retry_on_error: bool = True
    max_autonomous_iterations: int = 1
    stuck_detection_enabled: bool = True
    stuck_threshold_iterations: int = 5


class _StubAction(CmdRunAction):
    def __init__(self, command: str):
        super().__init__(command=command, thought="")


@pytest.mark.parametrize(
    "level,action,expected",
    [
        (AutonomyLevel.FULL.value, _StubAction("rm -rf /"), False),
        (AutonomyLevel.SUPERVISED.value, _StubAction("echo hi"), True),
        (
            AutonomyLevel.BALANCED.value,
            _StubAction("rm -rf important"),
            True,
        ),
    ],
)
def test_autonomy_request_confirmation(level, action, expected):
    config = _AutonomyConfig(autonomy_level=level)
    controller = AutonomyController(config)
    assert controller.should_request_confirmation(action) is expected


def test_autonomy_retry_only_for_import_errors(monkeypatch):
    config = _AutonomyConfig(auto_retry_on_error=True)
    controller = AutonomyController(config)
    assert controller.should_retry_on_error(ModuleNotFoundError("foo"), 0)
    assert not controller.should_retry_on_error(ModuleNotFoundError("foo"), 1)
    assert not controller.should_retry_on_error(ValueError("no retry"), 0)


def test_autonomy_retry_disabled():
    config = _AutonomyConfig(auto_retry_on_error=False)
    controller = AutonomyController(config)
    assert not controller.should_retry_on_error(ImportError("foo"), 0)


@pytest.mark.parametrize(
    "command",
    [
        "reboot",
        "sudo reboot",
        "shutdown -h now",
        "init 0",
        "systemctl stop service",
    ],
)
def test_autonomy_system_modification_commands(command):
    config = _AutonomyConfig(autonomy_level=AutonomyLevel.BALANCED.value)
    controller = AutonomyController(config)
    action = _StubAction(command)
    assert controller.should_request_confirmation(action) is True


def test_autonomy_file_write_action():
    config = _AutonomyConfig(autonomy_level=AutonomyLevel.BALANCED.value)
    controller = AutonomyController(config)
    action = FileWriteAction(path="test.txt", content="test")
    # File operations are not high-risk, so should not require confirmation in balanced mode
    assert controller.should_request_confirmation(action) is False


def test_autonomy_file_edit_action():
    config = _AutonomyConfig(autonomy_level=AutonomyLevel.BALANCED.value)
    controller = AutonomyController(config)
    action = FileEditAction(path="test.txt")
    # File operations are not high-risk, so should not require confirmation in balanced mode
    assert controller.should_request_confirmation(action) is False
