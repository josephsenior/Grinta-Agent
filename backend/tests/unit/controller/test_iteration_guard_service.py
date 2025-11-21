from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.iteration_guard_service import IterationGuardService
from forge.core.schemas import AgentState


def make_controller():
    iteration_flag = types.SimpleNamespace(current_value=0, max_value=5)
    state = types.SimpleNamespace(
        iteration_flag=iteration_flag,
        agent_state=AgentState.RUNNING,
    )
    controller = types.SimpleNamespace(
        state=state,
        state_tracker=MagicMock(),
        event_stream=MagicMock(),
        _step=AsyncMock(),
        _handle_finish_action=AsyncMock(),
    )
    controller.state_tracker.run_control_flags = MagicMock()
    controller.state_tracker.get_metrics_snapshot = lambda: {}
    return controller


@pytest.mark.asyncio
async def test_run_control_flags_executes_tracker():
    controller = make_controller()
    context = ControllerContext(controller)
    service = IterationGuardService(context)

    await service.run_control_flags()

    controller.state_tracker.run_control_flags.assert_called_once()


@pytest.mark.asyncio
async def test_run_control_flags_triggers_graceful_shutdown(monkeypatch):
    controller = make_controller()
    controller.state_tracker.run_control_flags.side_effect = RuntimeError(
        "max iteration limit"
    )
    context = ControllerContext(controller)
    service = IterationGuardService(context)

    called: dict[str, str] = {}

    def fake_schedule(self, reason: str) -> None:
        called["reason"] = reason

    monkeypatch.setattr(
        IterationGuardService, "_schedule_graceful_shutdown", fake_schedule
    )
    monkeypatch.setenv("FORGE_GRACEFUL_SHUTDOWN", "true")

    with pytest.raises(RuntimeError):
        await service.run_control_flags()

    assert called["reason"] == "max iteration limit"


@pytest.mark.asyncio
async def test_force_partial_completion_invokes_finish_action():
    controller = make_controller()
    context = ControllerContext(controller)
    service = IterationGuardService(context)

    await service._force_partial_completion("Max iterations reached")

    controller._handle_finish_action.assert_awaited()

