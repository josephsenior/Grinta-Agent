"""Additional tests for forge.controller.progress_tracker."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.controller.progress_tracker import ProgressMetrics, ProgressTracker
from forge.events.action import CmdRunAction, FileEditAction
from forge.events.observation import CmdOutputObservation


def build_state(iteration: int, history: list) -> SimpleNamespace:
    """Create a lightweight state object for tracker tests."""
    return SimpleNamespace(
        iteration_flag=SimpleNamespace(current_value=iteration),
        history=history,
    )


def test_progress_tracker_tracks_metrics():
    """ProgressTracker.update should compute metrics and record milestones."""
    tracker = ProgressTracker(max_iterations=10)

    history = [
        FileEditAction(path="main.py"),
        CmdRunAction(command="pytest -q"),
        CmdOutputObservation(
            content="ok", command="pytest -q", metadata={"exit_code": 0}
        ),
    ]
    state = build_state(iteration=3, history=history)

    metrics = tracker.update(state)
    assert isinstance(metrics, ProgressMetrics)
    assert metrics.iterations_completed == 3
    assert tracker.files_modified == {"main.py"}
    assert tracker.tests_run == 1
    assert tracker.tests_passed == 1
    assert metrics.is_making_progress is True
    assert metrics.milestones_reached


def test_progress_tracker_detects_stagnation():
    """If no new milestones are reached, stagnation iterations should grow."""
    tracker = ProgressTracker(max_iterations=5)

    # First update establishes progress
    state_progress = build_state(
        iteration=1,
        history=[
            CmdRunAction(command="pytest"),
            CmdOutputObservation(
                content="ok", command="pytest", metadata={"exit_code": 0}
            ),
        ],
    )
    tracker.update(state_progress)

    # Subsequent update without progress increases stagnation counter
    state_no_progress = build_state(iteration=2, history=state_progress.history)
    metrics = tracker.update(state_no_progress)
    assert metrics.stagnation_iterations >= 1


def test_progress_tracker_estimate_completion_when_velocity_positive():
    """Estimated completion time should be populated when velocity is non-zero."""
    tracker = ProgressTracker(max_iterations=100)
    history = [
        CmdRunAction(command="echo hi"),
        CmdOutputObservation(
            content="done", command="echo hi", metadata={"exit_code": 0}
        ),
    ]
    state = build_state(iteration=20, history=history)
    metrics = tracker.update(state)

    # Velocity should be positive after at least one update
    assert metrics.velocity >= 0
    if metrics.velocity > 0:
        assert metrics.estimated_completion_time is not None


def test_progress_tracker_handles_no_actions():
    """Tracker should handle empty history without crashing."""
    tracker = ProgressTracker(max_iterations=5)
    state = build_state(iteration=0, history=[])
    metrics = tracker.update(state)
    assert metrics.completion_percentage >= 0
    assert metrics.milestones_reached == []
