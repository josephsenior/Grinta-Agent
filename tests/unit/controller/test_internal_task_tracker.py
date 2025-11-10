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

