from __future__ import annotations

from types import SimpleNamespace

import pytest

import forge.agenthub.dummy_agent.agent as dummy
from forge.core.config import AgentConfig
from forge.events.action import AgentFinishAction, CmdRunAction
from forge.events.observation import FileWriteObservation


class StubLLMRegistry:
    def __init__(self):
        self.llm = SimpleNamespace()

    def get_llm_from_agent_config(self, *_):
        return self.llm


@pytest.fixture
def agent():
    config = AgentConfig(name="DummyAgent")
    return dummy.DummyAgent(config, StubLLMRegistry())


def test_remove_variable_fields(agent):
    obs = {"id": "1", "timestamp": "now", "cause": {}, "source": "agent", "keep": 1}
    agent._remove_variable_fields(obs)
    assert obs == {"keep": 1}


def test_normalize_metadata(agent):
    obs = {
        "extras": {
            "metadata": {
                "pid": 1,
                "username": "user",
                "hostname": "host",
                "working_dir": "/tmp",
                "py_interpreter_path": "/bin/python",
                "suffix": ".txt",
                "other": "keep",
            }
        }
    }
    agent._normalize_metadata(obs)
    assert obs["extras"]["metadata"] == {"other": "keep"}


def test_normalize_metadata_non_dict(agent):
    obs = {"extras": {"metadata": "not dict"}}
    agent._normalize_metadata(obs)
    assert obs["extras"]["metadata"] == "not dict"


def test_normalize_path(agent):
    obs = {"extras": {"path": "/tmp/some/file.txt"}}
    agent._normalize_path(obs)
    assert obs["extras"]["path"] == "file.txt"


def test_normalize_path_missing(agent):
    obs = {"extras": {}}
    agent._normalize_path(obs)
    assert obs["extras"] == {}


def test_normalize_path_non_string(agent):
    obs = {"extras": {"path": 123}}
    agent._normalize_path(obs)
    assert obs["extras"]["path"] == 123


@pytest.mark.parametrize(
    ("message", "action", "expected"),
    [
        ("I wrote to the file /tmp/hello.sh.", "wrote to", "I wrote to the file hello.sh."),
        ("I read the file /var/data/log.txt.", "read", "I read the file log.txt."),
        ("No match here", "wrote to", "No match here"),
    ],
)
def test_normalize_file_message(agent, message, action, expected):
    assert agent._normalize_file_message(message, action) == expected


def test_normalize_message(agent):
    obs = {"message": "I wrote to the file /tmp/foo.txt."}
    agent._normalize_message(obs)
    assert obs["message"] == "I wrote to the file foo.txt."


def test_normalize_message_skips_non_string(agent):
    obs = {}
    agent._normalize_message(obs)
    obs = {"message": 123}
    agent._normalize_message(obs)
    assert obs["message"] == 123


def test_normalize_observation_combines_all(agent):
    obs = {
        "id": "123",
        "timestamp": "now",
        "cause": {},
        "source": "agent",
        "extras": {
            "path": "/tmp/foo.txt",
            "metadata": {"pid": 1, "other": "keep"},
        },
        "message": "I read the file /tmp/foo.txt.",
    }
    agent._normalize_observation(obs)
    assert obs == {
        "extras": {"path": "foo.txt", "metadata": {"other": "keep"}},
        "message": "I read the file foo.txt.",
    }


def test_validate_observations_normalizes_expected(agent):
    obs = FileWriteObservation(content="hello", path="/tmp/hello.txt")
    state = SimpleNamespace(view=[obs])
    prev_step = {"observations": [FileWriteObservation(content="hello", path="hello.txt")]}
    agent._validate_observations(state, prev_step)
    # No exceptions indicate normalization and comparison succeeded


def test_step_returns_finish_when_exhausted(agent):
    state = SimpleNamespace(
        iteration_flag=SimpleNamespace(current_value=len(agent.steps)),
        view=[],
    )
    action = agent.step(state)
    assert isinstance(action, AgentFinishAction)


def test_step_returns_current_action_and_validates(agent, monkeypatch):
    called = {}

    def fake_validate(state, prev):
        called["state"] = state
        called["prev"] = prev

    monkeypatch.setattr(agent, "_validate_observations", fake_validate)
    state = SimpleNamespace(
        iteration_flag=SimpleNamespace(current_value=1),
        view=[FileWriteObservation(content="", path="hello.sh")],
    )
    action = agent.step(state)
    assert action is agent.steps[1]["action"]
    assert isinstance(action, CmdRunAction)
    assert called["prev"] == agent.steps[0]


def test_validate_observations_handles_missing_history(agent):
    state = SimpleNamespace(view=[])
    prev_step = {"observations": [FileWriteObservation(content="", path="hello.txt")]}
    agent._validate_observations(state, prev_step)


def test_validate_observations_handles_mismatched_obs(agent):
    hist = FileWriteObservation(content="a", path="hello.txt")
    expected = FileWriteObservation(content="b", path="hello.txt")
    state = SimpleNamespace(view=[hist])
    prev_step = {"observations": [expected]}
    agent._validate_observations(state, prev_step)


