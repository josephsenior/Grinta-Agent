from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from types import SimpleNamespace

from forge.controller.progress_tracker import ProgressMetrics, ProgressTracker
from forge.controller.state.control_flags import IterationControlFlag
from forge.events.action import CmdRunAction, FileEditAction
from forge.events.observation import CmdOutputObservation


@dataclass
class _DummyState:
    iteration_flag: IterationControlFlag
    history: list


def _build_state(iteration: int) -> _DummyState:
    flag = IterationControlFlag(limit_increase_amount=10, current_value=iteration, max_value=100)
    history = [
        FileEditAction(path="src/app.py"),
        CmdRunAction(command="pytest tests/unit", thought="run tests"),
        CmdOutputObservation(content="tests passed", command="pytest", exit_code=0),
    ]
    return _DummyState(iteration_flag=flag, history=history)


def test_progress_tracker_update_metrics(monkeypatch):
    tracker = ProgressTracker(max_iterations=100)

    # freeze time to have stable velocity
    fake_now = datetime.now()
    monkeypatch.setattr("forge.controller.progress_tracker.datetime", SimpleNamespace(now=lambda: fake_now))

    state = _build_state(5)
    metrics = tracker.update(state)
    assert isinstance(metrics, ProgressMetrics)
    assert metrics.completion_percentage > 0
    assert metrics.iterations_completed == 5
    assert metrics.is_making_progress
    assert tracker.files_modified == {"src/app.py"}


def test_progress_tracker_estimate_completion(monkeypatch):
    tracker = ProgressTracker(max_iterations=50)
    start_time = datetime.now() - timedelta(minutes=10)

    monkeypatch.setattr(tracker, "start_time", start_time)

    state = _build_state(20)
    metrics = tracker.update(state)
    assert metrics.velocity > 0
    if metrics.completion_percentage < 1:
        assert metrics.estimated_completion_time is None or metrics.estimated_completion_time >= datetime.now()


