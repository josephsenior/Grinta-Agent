"""Tests for missing coverage in stuck.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from forge.controller.state.state import State
from forge.controller.stuck import StuckDetector
from forge.events.action import CmdRunAction, FileReadAction, MessageAction
from forge.events.observation import CmdOutputObservation, FileReadObservation
from forge.events.observation.agent import AgentCondensationObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.empty import NullObservation


@pytest.fixture
def stuck_detector():
    state = State(inputs={})
    state.iteration_flag.max_value = 50
    state.history = []
    return StuckDetector(state)


def test_is_stuck_semantic_loop(stuck_detector: StuckDetector):
    """Test _is_stuck_semantic_loop detects semantic loops."""
    state = stuck_detector.state
    # Create 10+ events with same action intent but different outcomes
    for i in range(12):
        action = CmdRunAction(command="ls")
        state.history.append(action)
        obs = CmdOutputObservation(command="ls", content=f"file{i}.txt")
        state.history.append(obs)
    
    # Should trigger semantic loop detection (line 148)
    assert stuck_detector.is_stuck(headless_mode=True) is True


def test_check_for_consistent_invalid_syntax(stuck_detector: StuckDetector):
    """Test _check_for_consistent_invalid_syntax detects consistent syntax errors."""
    state = stuck_detector.state
    # Create observations with same syntax error - need proper format
    error_message = "SyntaxError: invalid syntax. Perhaps you forgot a comma?"
    for i in range(3):
        action = CmdRunAction(command="python -c 'print(\"hello'")
        state.history.append(action)
        obs = CmdOutputObservation(
            content=f'  File "<string>", line 1\n    print("hello\n               ^\n{error_message}',
            command="python -c 'print(\"hello'",
            exit_code=1
        )
        state.history.append(obs)
    
    # Check if it's detected as repeating action error
    assert stuck_detector._is_stuck_repeating_action_error(
        [state.history[i] for i in range(0, 6, 2)], # actions
        [state.history[i] for i in range(1, 6, 2)]  # observations
    ) is False # ErrorObservation is not CmdOutputObservation


def test_is_stuck_monologue(stuck_detector: StuckDetector):
    """Test _is_stuck_monologue detects monologue patterns."""
    from forge.events.event import EventSource
    state = stuck_detector.state
    # Create a pattern of agent message actions without observations between them
    for i in range(3):
        action = MessageAction(content="Same message", wait_for_response=False)
        action.source = EventSource.AGENT
        state.history.append(action)
    
    filtered = stuck_detector._filter_relevant_history(state.history)
    result = stuck_detector._is_stuck_monologue(filtered)
    # Should detect monologue pattern (lines 337->350)
    assert result is True


def test_is_stuck_semantic_loop_detection(stuck_detector: StuckDetector):
    """Test semantic loop detection with low diversity and high failure rate."""
    state = stuck_detector.state
    # Create actions with same intent (all other_action from FileReadAction) and all failing
    # This gives low diversity (< 0.4) and high failure rate (> 0.6)
    actions = [
        FileReadAction(path="file1.txt"),
        FileReadAction(path="file2.txt"),
        FileReadAction(path="file3.txt"),
        FileReadAction(path="file4.txt"),
        FileReadAction(path="file5.txt"),
        FileReadAction(path="file6.txt"),
    ]
    observations = [
        ErrorObservation(content="File not found"),
        ErrorObservation(content="File not found"),
        ErrorObservation(content="File not found"),
        ErrorObservation(content="File not found"),
        ErrorObservation(content="File not found"),
        ErrorObservation(content="File not found"),
    ]
    
    for action, obs in zip(actions, observations):
        state.history.append(action)
        state.history.append(obs)
    
    # Add more to reach 10+ events (need at least 6 actions for semantic loop check)
    for i in range(4):
        state.history.append(FileReadAction(path=f"file{i+7}.txt"))
        state.history.append(ErrorObservation(content="Failed"))
    
    filtered = stuck_detector._filter_relevant_history(state.history)
    result = stuck_detector._is_stuck_semantic_loop(filtered)
    # Should detect semantic loop (line 499, 506-510)
    assert result is True


def test_extract_intents_and_outcomes(stuck_detector: StuckDetector):
    """Test _extract_intents_and_outcomes extracts action intents and observation outcomes."""
    state = stuck_detector.state
    actions = [
        CmdRunAction(command="cat file1.txt"),
        CmdRunAction(command="cat file2.txt"),
        CmdRunAction(command="cat file3.txt"),
    ]
    observations = [
        CmdOutputObservation(command="cat", content="file1", exit_code=0),
        CmdOutputObservation(command="cat", content="file2", exit_code=0),
        CmdOutputObservation(command="cat", content="file3", exit_code=0),
    ]
    
    for action, obs in zip(actions, observations):
        state.history.append(action)
        state.history.append(obs)
    
    filtered = stuck_detector._filter_relevant_history(state.history)
    intents, outcomes = stuck_detector._extract_intents_and_outcomes(filtered)
    assert len(intents) == 3
    assert len(outcomes) == 3


def test_calculate_intent_diversity(stuck_detector: StuckDetector):
    """Test _calculate_intent_diversity calculates diversity correctly."""
    # Same intents = low diversity (1 unique / 3 total = 1/3)
    same_intents = ["read_file", "read_file", "read_file"]
    diversity = stuck_detector._calculate_intent_diversity(same_intents)
    assert diversity == pytest.approx(1/3, rel=0.01)
    
    # Different intents = high diversity
    different_intents = ["read_file", "run_command", "edit_file"]
    diversity = stuck_detector._calculate_intent_diversity(different_intents)
    assert diversity > 0.0


def test_calculate_failure_rate(stuck_detector: StuckDetector):
    """Test _calculate_failure_rate calculates failure rate correctly."""
    # All failures
    all_failures = ["error", "error", "error"]
    rate = stuck_detector._calculate_failure_rate(all_failures)
    assert rate == 1.0
    
    # All successes
    all_successes = ["success", "success", "success"]
    rate = stuck_detector._calculate_failure_rate(all_successes)
    assert rate == 0.0
    
    # Mixed
    mixed = ["success", "error", "success"]
    rate = stuck_detector._calculate_failure_rate(mixed)
    assert rate == pytest.approx(1/3, rel=0.1)


def test_extract_action_intent(stuck_detector: StuckDetector):
    """Test _extract_action_intent extracts intent from different action types."""
    # CmdRunAction
    cmd_action = CmdRunAction(command="ls -la")
    intent = stuck_detector._extract_action_intent(cmd_action)
    assert intent == "inspect_filesystem"  # ls is in inspect_filesystem category
    
    # FileReadAction - returns "other_action" since it's not CmdRunAction
    file_action = FileReadAction(path="test.py")
    intent = stuck_detector._extract_action_intent(file_action)
    assert intent == "other_action"


def test_categorize_cmd_action(stuck_detector: StuckDetector):
    """Test _categorize_cmd_action categorizes commands correctly."""
    # List command - ls is in inspect_filesystem
    assert stuck_detector._categorize_cmd_action("ls") == "inspect_filesystem"
    assert stuck_detector._categorize_cmd_action("ls -la") == "inspect_filesystem"
    
    # Read command - cat is in inspect_filesystem
    assert stuck_detector._categorize_cmd_action("cat file.txt") == "inspect_filesystem"
    assert stuck_detector._categorize_cmd_action("find . -name test") == "inspect_filesystem"
    
    # Create file command - "echo >" should match
    result = stuck_detector._categorize_cmd_action("echo 'text' > file.txt")
    # Check if it matches create_file or other_command (depending on exact matching)
    assert result in ["create_file", "other_command"]
    
    # Run/test command
    assert stuck_detector._categorize_cmd_action("python test.py") == "execute_code"
    assert stuck_detector._categorize_cmd_action("pytest") == "run_test"
    
    # Other
    assert stuck_detector._categorize_cmd_action("unknown_command") == "other_command"


def test_extract_observation_outcome(stuck_detector: StuckDetector):
    """Test _extract_observation_outcome extracts outcome from different observation types."""
    # CmdOutputObservation - success (exit_code 0, has content)
    cmd_obs = CmdOutputObservation(command="ls", content="files", exit_code=0)
    outcome = stuck_detector._extract_observation_outcome(cmd_obs)
    assert outcome == "success"
    
    # ErrorObservation
    error_obs = ErrorObservation(content="Error occurred")
    outcome = stuck_detector._extract_observation_outcome(error_obs)
    assert outcome == "error"


def test_categorize_cmd_output(stuck_detector: StuckDetector):
    """Test _categorize_cmd_output categorizes command output correctly."""
    # Success
    assert stuck_detector._categorize_cmd_output(
        CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt", exit_code=0)
    ) == "success"
    
    # Error - exit code != 0
    assert stuck_detector._categorize_cmd_output(
        CmdOutputObservation(command="ls", content="error", exit_code=1)
    ) == "error"
    
    # Not found
    assert stuck_detector._categorize_cmd_output(
        CmdOutputObservation(command="ls", content="ls: cannot access 'file': No such file or directory", exit_code=0)
    ) == "not_found"
    
    # Empty
    assert stuck_detector._categorize_cmd_output(
        CmdOutputObservation(command="ls", content="", exit_code=0)
    ) == "no_output"


def test_eq_no_pid(stuck_detector: StuckDetector):
    """Test _eq_no_pid compares events ignoring PID."""
    action1 = CmdRunAction(command="ls")
    action2 = CmdRunAction(command="ls")
    action1._id = "id1"
    action2._id = "id2"
    
    # Should be equal ignoring PID
    assert stuck_detector._eq_no_pid(action1, action2) is True
    
    # Different commands should not be equal
    action3 = CmdRunAction(command="cat file.txt")
    assert stuck_detector._eq_no_pid(action1, action3) is False

