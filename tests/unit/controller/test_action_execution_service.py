from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.controller.services.action_execution_service import ActionExecutionService
from forge.controller.services.controller_context import ControllerContext
from forge.events.action import MessageAction
from forge.core.schemas import AgentState


def make_controller():
    controller = types.SimpleNamespace()
    controller.state = types.SimpleNamespace()
    controller.agent = types.SimpleNamespace(config=types.SimpleNamespace(enable_history_truncation=True))
    controller.event_stream = MagicMock()
    controller.tool_pipeline = None
    controller.iteration_service = MagicMock()
    controller.iteration_service.apply_dynamic_iterations = AsyncMock()
    controller.telemetry_service = MagicMock()
    controller.action_service = MagicMock()
    controller.action_service.run = AsyncMock()
    controller._register_action_context = MagicMock()
    controller.confirmation_service = MagicMock()
    return controller


@pytest.mark.asyncio
async def test_get_next_action_handles_llm_errors():
    controller = make_controller()
    controller.confirmation_service.get_next_action.side_effect = Exception("boom")
    context = ControllerContext(controller)
    service = ActionExecutionService(context)

    with pytest.raises(Exception):
        await service.get_next_action()


@pytest.mark.asyncio
async def test_execute_action_runs_pipeline():
    controller = make_controller()
    pipeline = MagicMock()
    pipeline.run_plan = AsyncMock()
    ctx = types.SimpleNamespace(blocked=False)
    pipeline.create_context = MagicMock(return_value=ctx)
    controller.tool_pipeline = pipeline
    action = MessageAction(content="hi")
    action.runnable = True
    context = ControllerContext(controller)
    service = ActionExecutionService(context)

    await service.execute_action(action)

    pipeline.create_context.assert_called_once()
    controller.action_service.run.assert_awaited()

