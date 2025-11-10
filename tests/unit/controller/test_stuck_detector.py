from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.controller.stuck import StuckDetector
from forge.controller.state.state import State
from forge.events.action import MessageAction
from forge.events.action.commands import CmdRunAction, IPythonRunCellAction
from forge.events.action.empty import NullAction
from forge.events.event import EventSource
from forge.events.observation import CmdOutputObservation, IPythonRunCellObservation
from forge.events.observation.agent import AgentCondensationObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.empty import NullObservation


def _assign(event, event_id: int, source: EventSource):
    event._id = event_id  # type: ignore[attr-defined]
    event._source = source  # type: ignore[attr-defined]


def _cmd_action(command: str, event_id: int) -> CmdRunAction:
    action = CmdRunAction(command=command, thought="")
    _assign(action, event_id, EventSource.AGENT)
    return action


def _cmd_observation(content: str, command: str, exit_code: int, event_id: int) -> CmdOutputObservation:
    obs = CmdOutputObservation(content=content, command=command, exit_code=exit_code)
    _assign(obs, event_id, EventSource.ENVIRONMENT)
    return obs


def _ipython_observation(error_line: str, event_id: int) -> IPythonRunCellObservation:
    content = "\n".join(
        [
            "Cell In[1], line 1",
            "print('hello')",
            "Traceback (most recent call last):",
            error_line,
            "[Jupyter current working directory: /workspace]",
            "[Jupyter Python interpreter: python]",
        ],
    )
    obs = IPythonRunCellObservation(content=content, code="code")
    _assign(obs, event_id, EventSource.ENVIRONMENT)
    return obs


def test_is_stuck_false_for_short_history():
    detector = StuckDetector(State(history=[]))
    assert not detector.is_stuck()


def test_detects_repeating_action_observation_loop():
    history = []
    for i in range(4):
        history.append(_cmd_action("ls", i * 2 + 1))
        history.append(_cmd_observation("listing", "ls", 0, i * 2 + 2))
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_repeating_action_error_loop():
    history = []
    for i in range(3):
        history.append(_cmd_action("ls", i * 2 + 1))
        obs = ErrorObservation(content="boom", error_id="E")
        _assign(obs, i * 2 + 2, EventSource.ENVIRONMENT)
        history.append(obs)
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_ipython_syntax_error_loop():
    history = []
    for i in range(3):
        history.append(IPythonRunCellAction(code="print('test')"))
        history.append(
            _ipython_observation(
                "SyntaxError: invalid syntax. Perhaps you forgot a comma?",
                i * 2 + 2,
            ),
        )
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_monologue_without_observations():
    history = []
    for i in range(3):
        msg = MessageAction(content="thinking")
        _assign(msg, i + 1, EventSource.AGENT)
        history.append(msg)
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_action_observation_pattern():
    history = []
    for i in range(6):
        history.append(_cmd_action(f"ls {i%2}", i * 2 + 1))
        history.append(_cmd_observation("out", "ls", 0, i * 2 + 2))
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_context_window_error_loop():
    history = []
    for i in range(12):
        obs = AgentCondensationObservation(content=f"summary {i}")
        _assign(obs, i + 1, EventSource.ENVIRONMENT)
        history.append(obs)
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_detects_semantic_loop():
    history = []
    for i in range(6):
        history.append(_cmd_action("pytest tests", i * 2 + 1))
        history.append(_cmd_observation("failure", "pytest tests", 1, i * 2 + 2))
    detector = StuckDetector(SimpleNamespace(history=history))
    assert detector.is_stuck()


def test_cmd_action_and_python_action_categorization():
    detector = StuckDetector(SimpleNamespace(history=[]))
    assert detector._categorize_cmd_action("pytest my_tests") == "run_test"
    assert detector._categorize_cmd_action("pip install foo") == "install_dependency"
    assert detector._categorize_cmd_action("unknown command") == "other_command"
    assert detector._categorize_python_action("edit_file('a')") == "edit_file"
    assert detector._categorize_python_action("import os") == "import_module"
    assert detector._categorize_python_action("print('hi')") == "execute_python"


def test_cmd_output_categorization():
    detector = StuckDetector(SimpleNamespace(history=[]))
    error_obs = _cmd_observation("boom", "cmd", 1, 1)
    assert detector._categorize_cmd_output(error_obs) == "error"
    not_found = _cmd_observation("file not found", "cmd", 0, 2)
    assert detector._categorize_cmd_output(not_found) == "not_found"
    perm = _cmd_observation("permission denied", "cmd", 0, 3)
    assert detector._categorize_cmd_output(perm) == "permission_error"
    no_output = _cmd_observation("", "cmd", 0, 4)
    assert detector._categorize_cmd_output(no_output) == "no_output"
    success = _cmd_observation("ok", "cmd", 0, 5)
    assert detector._categorize_cmd_output(success) == "success"


def test_python_output_categorization():
    detector = StuckDetector(SimpleNamespace(history=[]))
    error = IPythonRunCellObservation(content="Exception occurred", code="")
    no_change = IPythonRunCellObservation(content="None", code="")
    success = IPythonRunCellObservation(content="Successful output", code="")
    assert detector._categorize_python_output(error) == "error"
    assert detector._categorize_python_output(no_change) == "no_change"
    assert detector._categorize_python_output(success) == "success"


def test_get_history_to_check_interactive_mode():
    state = State()
    user_msg = MessageAction(content="hello")
    _assign(user_msg, 1, EventSource.USER)
    agent_msg = MessageAction(content="reply")
    _assign(agent_msg, 2, EventSource.AGENT)
    state.history.extend([user_msg, agent_msg])

    detector = StuckDetector(state)
    assert detector._get_history_to_check(headless_mode=False) == [agent_msg]
    assert detector._get_history_to_check(headless_mode=True) == state.history


def test_filter_relevant_history():
    state = State()
    user_msg = MessageAction(content="task")
    _assign(user_msg, 1, EventSource.USER)
    agent_msg = MessageAction(content="response")
    _assign(agent_msg, 2, EventSource.AGENT)
    null_obs = AgentCondensationObservation(content="summary")
    _assign(null_obs, 3, EventSource.ENVIRONMENT)
    state.history.extend([user_msg, agent_msg, NullObservation("")])
    detector = StuckDetector(state)
    filtered = detector._filter_relevant_history(state.history + [null_obs])
    assert agent_msg in filtered
    assert user_msg not in filtered
    assert all(not isinstance(event, NullObservation) for event in filtered)


def test_is_stuck_semantic_loop_thresholds():
    history = []
    for i in range(5):
        history.append(_cmd_action(f"pytest test_{i}", i * 2 + 1))
        history.append(_cmd_observation("ok", "pytest", 0, i * 2 + 2))
    # Add extra non-repeating actions to exceed len>=10 without triggering earlier patterns
    for i in range(5):
        history.append(IPythonRunCellAction(code=f"print({i})"))
        obs = IPythonRunCellObservation(content="Successful output", code="")
        _assign(obs, 100 + i, EventSource.ENVIRONMENT)
        history.append(obs)
    detector = StuckDetector(SimpleNamespace(history=history))
    assert not detector.is_stuck()


def test_ipython_error_observations_return_false_when_not_matching():
    history = [
        _cmd_action("ls", 1),
        _cmd_observation("ok", "ls", 0, 2),
        _cmd_action("ls", 3),
        _cmd_observation("ok", "ls", 0, 4),
    ]
    detector = StuckDetector(SimpleNamespace(history=history))
    last_actions, last_obs = detector._collect_recent_events(history)
    assert not detector._check_ipython_error_observations(last_obs)


def test_check_specific_error_pattern_other_message():
    detector = StuckDetector(SimpleNamespace(history=[]))
    obs = _ipython_observation("Some other error", 1)
    assert not detector._check_specific_error_pattern([obs], "Different error")


def test_check_for_consistent_invalid_syntax_formatting():
    detector = StuckDetector(SimpleNamespace(history=[]))
    obs = IPythonRunCellObservation(content="short", code="")
    assert not detector._check_for_consistent_invalid_syntax([obs], "SyntaxError")

    bad_header = "\n".join(
        [
            "Line 1",
            "Traceback",
            "SyntaxError: invalid syntax. Perhaps you forgot a comma?",
            "[Jupyter current working directory: /]",
            "[Jupyter Python interpreter: python]",
        ],
    )
    obs2 = IPythonRunCellObservation(content=bad_header, code="")
    assert not detector._check_for_consistent_invalid_syntax(
        [obs2, obs2, obs2],
        "SyntaxError: invalid syntax. Perhaps you forgot a comma?",
    )


def test_extract_error_line_from_observation_conditions():
    detector = StuckDetector(SimpleNamespace(history=[]))
    obs = IPythonRunCellObservation(content="a\nb", code="")
    assert detector._extract_error_line_from_observation(obs, "error") is None

    content = "\n".join(
        [
            "Cell In[1], line 1",
            "Traceback",
            "SyntaxError: invalid syntax. Perhaps you forgot a comma?",
            "missing metadata",
        ],
    )
    obs2 = IPythonRunCellObservation(content=content, code="")
    assert detector._extract_error_line_from_observation(
        obs2,
        "SyntaxError: invalid syntax. Perhaps you forgot a comma?",
    ) is None


def test_check_for_consistent_line_error_requires_all_matches():
    detector = StuckDetector(SimpleNamespace(history=[]))
    obs1 = _ipython_observation("SyntaxError: unterminated string literal (detected at line 1)", 1)
    obs2 = IPythonRunCellObservation(content="short", code="")
    assert not detector._check_for_consistent_line_error([obs1, obs2], "SyntaxError: unterminated string literal (detected at line")


def test_is_stuck_action_observation_pattern_requires_enough_events():
    detector = StuckDetector(SimpleNamespace(history=[]))
    history = [_cmd_action("ls", 1), _cmd_observation("ok", "ls", 0, 2)]
    assert not detector._is_stuck_action_observation_pattern(history)


def test_check_consecutive_condensation_events_false():
    detector = StuckDetector(SimpleNamespace(history=[]))
    history = []
    for i in range(5):
        obs = AgentCondensationObservation(content=f"summary {i}")
        _assign(obs, i * 2 + 1, EventSource.ENVIRONMENT)
        history.append(obs)
        if i < 4:
            spacer = _cmd_observation("ok", "cmd", 0, i * 2 + 2)
            history.append(spacer)
    events = detector._get_condensation_events(history)
    assert not detector._check_consecutive_condensation_events(events, history)


def test_context_window_error_requires_minimum_events():
    detector = StuckDetector(SimpleNamespace(history=[AgentCondensationObservation(content="s")]))
    assert not detector._is_stuck_context_window_error(detector.state.history)  # type: ignore[attr-defined]


def test_extract_intents_and_outcomes_filters_events():
    detector = StuckDetector(SimpleNamespace(history=[]))
    events = [
        NullAction(),
        MessageAction(content="msg"),
        NullObservation(""),
        _cmd_action("ls", 1),
        _cmd_observation("ok", "ls", 0, 2),
    ]
    intents, outcomes = detector._extract_intents_and_outcomes(events)
    assert intents == ["inspect_filesystem"]
    assert outcomes == ["success"]


def test_calculate_intent_diversity_and_failure_rate():
    detector = StuckDetector(SimpleNamespace(history=[]))
    assert detector._calculate_intent_diversity([]) == 1.0
    assert detector._calculate_failure_rate([]) == 0.0
    intents = ["a", "a", "b", "a"]
    assert detector._calculate_intent_diversity(intents) == 0.5
    outcomes = ["error", "success", "no_change", "permission_error"]
    assert detector._calculate_failure_rate(outcomes) == pytest.approx(0.5)


def test_extract_action_intent_variants():
    detector = StuckDetector(SimpleNamespace(history=[]))
    assert detector._extract_action_intent(IPythonRunCellAction(code="edit_file_by_replace('a')")) == "edit_file"
    assert detector._extract_action_intent(IPythonRunCellAction(code="print('x')")) == "execute_python"
    assert detector._extract_action_intent(_cmd_action("python script.py", 1)) == "execute_code"
    assert detector._extract_action_intent(MessageAction(content="hi")) == "other_action"


def test_extract_observation_outcome_unknown():
    detector = StuckDetector(SimpleNamespace(history=[]))
    assert detector._extract_observation_outcome(MessageAction(content="hi")) == "unknown"


def test_eq_no_pid_ipython_special_case():
    detector = StuckDetector(SimpleNamespace(history=[]))
    code = "edit_file_by_replace(\nline1\nline2\n)"
    action1 = IPythonRunCellAction(code=code)
    action2 = IPythonRunCellAction(code=code.replace("line2", "line2"))
    assert detector._eq_no_pid(action1, action2)

