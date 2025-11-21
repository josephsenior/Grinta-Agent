from __future__ import annotations

import types
from unittest.mock import MagicMock

from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.pending_action_service import PendingActionService
from forge.events.action import MessageAction


def make_controller():
    controller = types.SimpleNamespace(
        log=MagicMock(),
        event_stream=MagicMock(),
    )
    return controller


def test_pending_action_set_and_clear(monkeypatch):
    controller = make_controller()
    context = ControllerContext(controller)
    service = PendingActionService(context, timeout=1000)
    action = MessageAction(content="hi")

    service.set(action)
    assert service.get() is action

    service.set(None)
    assert service.get() is None


def test_pending_action_timeout(monkeypatch):
    controller = make_controller()
    context = ControllerContext(controller)
    service = PendingActionService(context, timeout=1)
    action = MessageAction(content="hi")

    times = [0, 2]

    def fake_time():
        return times.pop(0)

    monkeypatch.setattr("time.time", fake_time)

    service.set(action)
    assert service.get() is None
    controller.event_stream.add_event.assert_called_once()

