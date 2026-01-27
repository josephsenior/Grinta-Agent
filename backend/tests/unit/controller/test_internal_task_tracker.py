from __future__ import annotations

import logging

import pytest

from forge.controller.internal_task_tracker import InternalTaskTracker


def test_internal_task_tracker_add_start_complete(caplog):
    caplog.set_level(logging.DEBUG)
    tracker = InternalTaskTracker()
    task_id = tracker.add_task("do something")
    tracker.start_task(task_id)
    tracker.complete_task(task_id)
    progress = tracker.get_progress()
    assert progress["total"] == 1
    assert progress["completed"] == 1
    tracker.log_progress()


def test_internal_task_tracker_progress_empty():
    tracker = InternalTaskTracker()
    assert tracker.get_progress() == {
        "total": 0,
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "current": None,
    }


def test_internal_task_tracker_decompose_and_reset():
    tracker = InternalTaskTracker()
    ids = tracker.decompose_task("complex work")
    assert ids and ids[0].startswith("task_")
    tracker.reset()
    assert tracker.get_progress()["total"] == 0


def test_start_task_nonexistent():
    """Test start_task with non-existent task_id (branch 72->71)."""
    tracker = InternalTaskTracker()
    # Add a task first so the loop actually runs
    tracker.add_task("real task")
    # Try to start a non-existent task - loop will exit without finding it
    tracker.start_task("nonexistent_task")
    # Should not raise, just silently fail
    assert tracker.get_progress()["in_progress"] == 0


def test_complete_task_nonexistent():
    """Test complete_task with non-existent task_id."""
    tracker = InternalTaskTracker()
    tracker.complete_task("nonexistent_task")
    # Should not raise, just silently fail
    assert tracker.get_progress()["completed"] == 0


def test_get_current_task_empty():
    """Test get_current_task when tasks list is empty (line 98)."""
    tracker = InternalTaskTracker()
    # No tasks added, should return None immediately
    assert tracker.get_current_task() is None


def test_get_current_task_all_completed():
    """Test get_current_task when all tasks are completed (line 103)."""
    tracker = InternalTaskTracker()
    task_id1 = tracker.add_task("task 1")
    task_id2 = tracker.add_task("task 2")
    tracker.complete_task(task_id1)
    tracker.complete_task(task_id2)
    # All tasks are done, should return None after loop
    assert tracker.get_current_task() is None


def test_get_progress_all_completed():
    """Test get_progress when all tasks are completed."""
    tracker = InternalTaskTracker()
    task_id1 = tracker.add_task("task 1")
    task_id2 = tracker.add_task("task 2")
    tracker.complete_task(task_id1)
    tracker.complete_task(task_id2)
    progress = tracker.get_progress()
    assert progress["total"] == 2
    assert progress["completed"] == 2
    assert progress["current"] is None
    assert progress["completion_percentage"] == 100


def test_calculate_completion_percentage_empty():
    """Test _calculate_completion_percentage when tasks list is empty."""
    tracker = InternalTaskTracker()
    # Directly test the method when tasks is empty
    # This tests line 170: return 0 when not self.tasks
    tracker.tasks = []  # Manually set to empty
    percentage = tracker._calculate_completion_percentage(0)
    assert percentage == 0