from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.agenthub.codeact_agent.task_complexity import TaskComplexityAnalyzer


def make_config(**overrides):
    defaults = dict(
        planning_complexity_threshold=3,
        enable_auto_planning=True,
        enable_dynamic_iterations=True,
        min_iterations=20,
        max_iterations_override=200,
        complexity_iteration_multiplier=10.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_state(actions=None):
    history = actions or []
    return SimpleNamespace(history=history)


def test_analyze_complexity_simple_task():
    analyzer = TaskComplexityAnalyzer(make_config())
    score = analyzer.analyze_complexity("Add a comment to the file", make_state())
    assert score == pytest.approx(1.5)


def test_analyze_complexity_complex_patterns():
    analyzer = TaskComplexityAnalyzer(make_config())
    message = "Create and configure the service, then test integration end-to-end"
    score = analyzer.analyze_complexity(message, make_state())
    assert score > 4


def test_history_complexity_score_counts_events():
    analyzer = TaskComplexityAnalyzer(make_config())
    history = [SimpleNamespace(action="edit"), SimpleNamespace(action="write")]
    score = analyzer.analyze_complexity("Update docs", make_state(history))
    assert score > 1.0


def test_should_plan_respects_config():
    analyzer = TaskComplexityAnalyzer(make_config(enable_auto_planning=False))
    assert analyzer.should_plan("Create files", make_state()) is False

    analyzer = TaskComplexityAnalyzer(make_config(planning_complexity_threshold=1))
    assert analyzer.should_plan("Create files", make_state()) is True


def test_estimate_iterations_dynamic_and_static():
    analyzer = TaskComplexityAnalyzer(make_config(max_iterations_override=100))
    iterations = analyzer.estimate_iterations(complexity=5.0, state=make_state())
    assert 20 <= iterations <= 100

    analyzer = TaskComplexityAnalyzer(make_config(enable_dynamic_iterations=False))
    iterations = analyzer.estimate_iterations(5.0, make_state())
    assert iterations == analyzer._config.max_iterations_override
from types import SimpleNamespace

import pytest

from forge.agenthub.codeact_agent.task_complexity import TaskComplexityAnalyzer


def _make_config(**overrides):
    defaults = dict(
        planning_complexity_threshold=3,
        enable_auto_planning=True,
        enable_dynamic_iterations=True,
        min_iterations=20,
        max_iterations_override=None,
        complexity_iteration_multiplier=50.0,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_state(message: str | None):
    if message is None:
        return SimpleNamespace(history=[])

    from forge.events.event import EventSource

    user_event = SimpleNamespace(source=EventSource.USER, content=message)
    return SimpleNamespace(history=[user_event])


def test_simple_task_has_low_complexity_and_does_not_plan():
    config = _make_config()
    analyzer = TaskComplexityAnalyzer(config)
    message = "Add a docstring to the process_payment function."

    complexity = analyzer.analyze_complexity(message, _make_state(message))
    should_plan = analyzer.should_plan(message, _make_state(message))

    assert complexity < config.planning_complexity_threshold
    assert should_plan is False


def test_complex_task_triggers_planning():
    config = _make_config()
    analyzer = TaskComplexityAnalyzer(config)
    message = (
        "Build authentication, update the dashboard UI, and add integration tests."
    )

    complexity = analyzer.analyze_complexity(message, _make_state(message))
    should_plan = analyzer.should_plan(message, _make_state(message))

    assert complexity >= config.planning_complexity_threshold
    assert should_plan is True


@pytest.mark.parametrize(
    "complexity,expected",
    [
        (2.0, 20 + int(2.0 * 50.0)),  # simple task
        (6.0, 20 + int(6.0 * 50.0)),  # moderate task
        (10.0, 400),  # capped by max_iterations_override
    ],
)
def test_estimate_iterations_respects_bounds(complexity, expected):
    config = _make_config(max_iterations_override=400)
    analyzer = TaskComplexityAnalyzer(config)

    iterations = analyzer.estimate_iterations(complexity, state=None)

    assert iterations == expected

