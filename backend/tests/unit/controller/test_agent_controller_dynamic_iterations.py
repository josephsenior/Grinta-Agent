from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from forge.controller.agent_controller import AgentController
from forge.controller.tool_pipeline import ToolInvocationContext

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.state.state import State
    from forge.events.action import Action


def _make_controller(
    min_iterations: int = 20,
    multiplier: float = 50.0,
    enable_dynamic: bool = True,
) -> AgentController:
    controller = AgentController.__new__(AgentController)
    controller.state = cast(
        "State",
        SimpleNamespace(iteration_flag=SimpleNamespace(max_value=100)),
    )
    controller.agent = cast(
        "Agent",
        SimpleNamespace(
            config=SimpleNamespace(
                enable_dynamic_iterations=enable_dynamic,
                min_iterations=min_iterations,
            ),
            task_complexity_analyzer=SimpleNamespace(
                estimate_iterations=lambda complexity, _state: int(
                    min_iterations + complexity * multiplier
                ),
            ),
        ),
    )
    return controller


def _make_context(controller: AgentController, complexity: float) -> ToolInvocationContext:
    action = cast("Action", SimpleNamespace(runnable=True))
    state = cast("State", SimpleNamespace())
    ctx = ToolInvocationContext(controller=controller, action=action, state=state)
    ctx.metadata["task_complexity"] = complexity
    return ctx


@pytest.mark.asyncio
async def test_dynamic_iterations_increase_for_complex_tasks():
    controller = _make_controller()
    ctx = _make_context(controller, complexity=6.0)

    await controller._apply_dynamic_iterations(ctx)

    assert controller.state.iteration_flag.max_value == 20 + int(6.0 * 50.0)


@pytest.mark.asyncio
async def test_dynamic_iterations_decrease_for_simple_tasks():
    controller = _make_controller()
    controller.state.iteration_flag.max_value = 500
    ctx = _make_context(controller, complexity=2.0)

    await controller._apply_dynamic_iterations(ctx)

    expected = max(
        controller.agent.config.min_iterations,
        int(controller.agent.config.min_iterations + 2.0 * 50.0),
    )
    assert controller.state.iteration_flag.max_value == expected

