from __future__ import annotations

import types
from unittest.mock import MagicMock

from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.step_prerequisite_service import StepPrerequisiteService
from forge.core.schemas import AgentState


def make_controller():
    state = types.SimpleNamespace(agent_state=AgentState.RUNNING)
    controller = types.SimpleNamespace(
        state=state,
        log=MagicMock(),
        get_agent_state=lambda: controller.state.agent_state,  # type: ignore[name-defined]
    )
    return controller


def test_prerequisite_blocks_non_running_state():
    controller = make_controller()
    controller.state.agent_state = AgentState.PAUSED
    context = ControllerContext(controller)
    service = StepPrerequisiteService(context)

    assert service.can_step() is False
    controller.log.assert_called_once()


def test_prerequisite_blocks_pending_action():
    controller = make_controller()
    context = ControllerContext(controller)
    context.set_pending_action(types.SimpleNamespace(id="123"))
    service = StepPrerequisiteService(context)

    assert service.can_step() is False
    assert controller.log.call_count == 1


def test_prerequisite_allows_ready_state():
    controller = make_controller()
    context = ControllerContext(controller)
    service = StepPrerequisiteService(context)

    assert service.can_step() is True
    controller.log.assert_not_called()

