from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from forge.controller.tool_pipeline import (
    PlanningMiddleware,
    ReflectionMiddleware,
    ToolInvocationContext,
)
from forge.agenthub.codeact_agent.task_complexity import TaskComplexityAnalyzer

if TYPE_CHECKING:
    from forge.controller.agent import Agent
    from forge.controller.agent_controller import AgentController
    from forge.controller.state.state import State
    from forge.events.action import Action


def _make_controller_with_analyzer(threshold: int = 3) -> AgentController:
    config = SimpleNamespace(
        planning_complexity_threshold=threshold,
        enable_auto_planning=True,
        enable_dynamic_iterations=True,
        min_iterations=20,
        max_iterations_override=None,
        complexity_iteration_multiplier=50.0,
        enable_reflection=True,
    )
    analyzer = TaskComplexityAnalyzer(config)
    agent = cast(Agent, SimpleNamespace(config=config, task_complexity_analyzer=analyzer))
    controller = cast(
        AgentController,
        SimpleNamespace(agent=agent),
    )
    return controller


def _make_state_with_message(message: str) -> State:
    from forge.events.event import EventSource

    event = SimpleNamespace(source=EventSource.USER, content=message)
    return cast(State, SimpleNamespace(history=[event]))


@pytest.mark.asyncio
async def test_planning_middleware_tags_complex_tasks():
    controller = _make_controller_with_analyzer()
    middleware = PlanningMiddleware(controller)
    action = cast(Action, SimpleNamespace(runnable=True))
    message = "Implement feature A and refactor module B, then add integration tests."
    state = _make_state_with_message(message)
    ctx = ToolInvocationContext(controller=controller, action=action, state=state)

    await middleware.plan(ctx)

    assert ctx.metadata.get("should_plan") is True
    assert ctx.metadata.get("task_complexity", 0) >= controller.agent.config.planning_complexity_threshold


@pytest.mark.asyncio
async def test_planning_middleware_skips_simple_tasks():
    controller = _make_controller_with_analyzer()
    middleware = PlanningMiddleware(controller)
    action = cast(Action, SimpleNamespace(runnable=True))
    message = "Add a docstring to the helper function."
    state = _make_state_with_message(message)
    ctx = ToolInvocationContext(controller=controller, action=action, state=state)

    await middleware.plan(ctx)

    assert "should_plan" not in ctx.metadata
    assert "task_complexity" not in ctx.metadata


@pytest.mark.asyncio
async def test_reflection_middleware_warns_on_invalid_json(monkeypatch):
    controller = _make_controller_with_analyzer()
    middleware = ReflectionMiddleware(controller)
    action = cast(
        Action,
        SimpleNamespace(
            runnable=True,
            action="edit",
            path="config.json",
            content="{invalid",
        ),
    )
    state = cast(State, SimpleNamespace())
    ctx = ToolInvocationContext(controller=controller, action=action, state=state)

    warnings = []
    monkeypatch.setattr(
        "forge.controller.tool_pipeline.logger.warning",
        lambda message, *args, **kwargs: warnings.append(str(message)),
    )

    await middleware.verify(ctx)

    assert any("JSON syntax error" in message for message in warnings)


@pytest.mark.asyncio
async def test_reflection_middleware_flags_destructive_command(monkeypatch):
    controller = _make_controller_with_analyzer()
    middleware = ReflectionMiddleware(controller)
    action = cast(
        Action,
        SimpleNamespace(
            runnable=True,
            action="run",
            command="rm -rf /",
        ),
    )
    state = cast(State, SimpleNamespace())
    ctx = ToolInvocationContext(controller=controller, action=action, state=state)

    warnings = []
    monkeypatch.setattr(
        "forge.controller.tool_pipeline.logger.warning",
        lambda message, *args, **kwargs: warnings.append(str(message)),
    )

    await middleware.verify(ctx)

    assert any("Potentially destructive command" in message for message in warnings)

