"""Additional tests for forge.controller.internal_task_tracker."""

from __future__ import annotations

from forge.controller.internal_task_tracker import InternalTaskTracker


def test_internal_task_tracker_basic_flow():
    """Adding, starting, and completing tasks should update progress."""

    tracker = InternalTaskTracker()
    task_id = tracker.add_task("Implement feature")
    subtask_id = tracker.add_task("Write tests", parent_id=task_id)

    tracker.start_task(task_id)
    tracker.complete_task(task_id)

    progress = tracker.get_progress()
    assert progress["total"] == 2
    assert progress["completed"] == 1
    assert progress["in_progress"] == 0
    assert progress["pending"] == 1
    assert progress["current"] == "Write tests"


def test_internal_task_tracker_decompose_and_reset():
    """Task decomposition and reset should update internal state accordingly."""

    tracker = InternalTaskTracker()
    subtasks = tracker.decompose_task("Complex task")
    assert len(subtasks) == 1

    tracker.log_progress()  # Ensure no exceptions
    tracker.reset()
    assert tracker.get_progress() == {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "current": None,
    }

