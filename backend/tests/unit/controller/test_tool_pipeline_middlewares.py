from __future__ import annotations

from types import SimpleNamespace
from typing import Any, TYPE_CHECKING, cast

import pytest

from forge.controller.services.telemetry_service import TelemetryService
from forge.controller.tool_pipeline import (
    CircuitBreakerMiddleware,
    CostQuotaMiddleware,
    LoggingMiddleware,
    PlanningMiddleware,
    ReflectionMiddleware,
    SafetyValidatorMiddleware,
    TelemetryMiddleware,
)
from forge.core.config.agent_config import AgentConfig

if TYPE_CHECKING:
    from forge.controller.agent_controller import AgentController


@pytest.fixture
def capture_pipeline(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Capture middlewares passed to ToolInvocationPipeline."""

    captured: dict[str, Any] = {}

    class DummyPipeline:
        def __init__(self, controller, middlewares) -> None:
            self.middlewares = list(middlewares)
            captured["middlewares"] = self.middlewares
            controller.tool_pipeline = self

    monkeypatch.setattr(
        "forge.controller.tool_pipeline.ToolInvocationPipeline", DummyPipeline
    )
    return captured


def _build_controller(config: AgentConfig) -> "AgentController":
    agent = SimpleNamespace(config=config)
    controller = SimpleNamespace(
        agent=agent,
        tool_pipeline=None,
        _action_contexts_by_object={},
        _action_contexts_by_event_id={},
    )
    return cast("AgentController", controller)


def _middleware_types(captured: dict[str, Any]) -> list[type]:
    return [type(m) for m in captured["middlewares"]]


def test_tool_pipeline_default_middlewares(capture_pipeline):
    controller = _build_controller(AgentConfig())
    service = TelemetryService(controller)
    service.initialize_tool_pipeline()
    types = _middleware_types(capture_pipeline)
    assert types == [
        SafetyValidatorMiddleware,
        CircuitBreakerMiddleware,
        CostQuotaMiddleware,
        LoggingMiddleware,
        TelemetryMiddleware,
    ]


def test_tool_pipeline_with_planning_middleware(capture_pipeline):
    config = AgentConfig(enable_planning_middleware=True)
    controller = _build_controller(config)
    service = TelemetryService(controller)
    service.initialize_tool_pipeline()
    types = _middleware_types(capture_pipeline)
    assert types == [
        SafetyValidatorMiddleware,
        CircuitBreakerMiddleware,
        CostQuotaMiddleware,
        PlanningMiddleware,
        LoggingMiddleware,
        TelemetryMiddleware,
    ]


def test_tool_pipeline_with_reflection_middleware(capture_pipeline):
    config = AgentConfig(enable_reflection_middleware=True)
    controller = _build_controller(config)
    service = TelemetryService(controller)
    service.initialize_tool_pipeline()
    types = _middleware_types(capture_pipeline)
    assert types == [
        SafetyValidatorMiddleware,
        CircuitBreakerMiddleware,
        CostQuotaMiddleware,
        ReflectionMiddleware,
        LoggingMiddleware,
        TelemetryMiddleware,
    ]


def test_tool_pipeline_with_both_optional_middlewares(capture_pipeline):
    config = AgentConfig(
        enable_planning_middleware=True, enable_reflection_middleware=True
    )
    controller = _build_controller(config)
    service = TelemetryService(controller)
    service.initialize_tool_pipeline()
    types = _middleware_types(capture_pipeline)
    assert types == [
        SafetyValidatorMiddleware,
        CircuitBreakerMiddleware,
        CostQuotaMiddleware,
        PlanningMiddleware,
        ReflectionMiddleware,
        LoggingMiddleware,
        TelemetryMiddleware,
    ]

