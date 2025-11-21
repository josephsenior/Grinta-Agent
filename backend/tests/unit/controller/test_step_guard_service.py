from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.step_guard_service import StepGuardService
from forge.core.schemas import AgentState


def make_controller():
    controller = types.SimpleNamespace(
        event_stream=MagicMock(),
        set_agent_state_to=AsyncMock(),
        _react_to_exception=AsyncMock(),
        circuit_breaker_service=None,
        stuck_service=MagicMock(is_stuck=lambda: False),
    )
    return controller


@pytest.mark.asyncio
async def test_step_guard_handles_circuit_breaker():
    controller = make_controller()
    controller.circuit_breaker_service = types.SimpleNamespace(
        check=lambda: types.SimpleNamespace(
            tripped=True, reason="boom", action="stop", recommendation="rest"
        )
    )
    context = ControllerContext(controller)
    guard = StepGuardService(context)

    allowed = await guard.ensure_can_step()

    assert allowed is False
    controller.event_stream.add_event.assert_called_once()
    controller.set_agent_state_to.assert_awaited_with(AgentState.STOPPED)


@pytest.mark.asyncio
async def test_step_guard_handles_stuck_detection():
    controller = make_controller()
    controller.circuit_breaker_service = MagicMock()
    controller.circuit_breaker_service.check.return_value = None
    controller.stuck_service.is_stuck = lambda: True
    context = ControllerContext(controller)
    guard = StepGuardService(context)

    allowed = await guard.ensure_can_step()

    assert allowed is False
    controller.circuit_breaker_service.record_stuck_detection.assert_called_once()
    controller._react_to_exception.assert_awaited()


@pytest.mark.asyncio
async def test_step_guard_allows_normal_step():
    controller = make_controller()
    context = ControllerContext(controller)
    guard = StepGuardService(context)

    allowed = await guard.ensure_can_step()

    assert allowed is True


