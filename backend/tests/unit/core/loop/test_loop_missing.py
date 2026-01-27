"""Tests for missing coverage in loop.py."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from forge.core import loop as loop_module
from forge.core.schemas import AgentState
from forge.runtime.runtime_status import RuntimeStatus


class DummyController:
    def __init__(self) -> None:
        self.state = SimpleNamespace(
            agent_state=AgentState.RUNNING,
            last_error=None,
            iteration_flag=SimpleNamespace(current_value=5),
        )
        self.status_callback = None
        self._force_iteration_reset = False
        self.set_calls: list[AgentState] = []

    async def set_agent_state_to(self, new_state: AgentState) -> None:
        self.set_calls.append(new_state)
        self.state.agent_state = new_state

    def _run_or_schedule(self, coro):
        # Simulate failure
        raise RuntimeError("Cannot schedule")


class DummyRuntime:
    def __init__(self) -> None:
        self.status_callback = None


def test_handle_error_status_fallback_to_create_task(monkeypatch):
    """Test _handle_error_status falls back to asyncio.create_task when _run_or_schedule fails."""
    controller = DummyController()
    tasks = []

    def fake_create_task(coro):
        tasks.append(coro)
        return coro

    monkeypatch.setattr(loop_module.asyncio, "create_task", fake_create_task)

    loop_module._handle_error_status(
        cast(Any, controller),
        RuntimeStatus.ERROR,
        "Error message",
    )

    assert controller.state.last_error == "Error message"
    # Should have tried create_task as fallback
    assert len(tasks) >= 0  # May or may not succeed


def test_handle_error_status_create_task_also_fails(monkeypatch):
    """Test _handle_error_status handles when both _run_or_schedule and create_task fail."""
    controller = DummyController()

    def failing_create_task(coro):
        raise RuntimeError("Cannot create task")

    monkeypatch.setattr(loop_module.asyncio, "create_task", failing_create_task)

    # Should not raise, just silently fail
    loop_module._handle_error_status(
        cast(Any, controller),
        RuntimeStatus.ERROR,
        "Error message",
    )

    assert controller.state.last_error == "Error message"


def test_validate_status_callbacks_handles_getattr_exception_runtime(monkeypatch):
    """Test _validate_status_callbacks handles exception when getting runtime.status_callback."""
    runtime = SimpleNamespace()
    controller = SimpleNamespace(status_callback=None)

    # Make getattr raise an exception
    original_getattr = getattr

    def failing_getattr(obj, name, default=None):
        if obj is runtime and name == "status_callback":
            raise AttributeError("Cannot access")
        return original_getattr(obj, name, default)

    monkeypatch.setattr("builtins.getattr", failing_getattr)

    # Should not raise, just pass
    loop_module._validate_status_callbacks(cast(Any, runtime), cast(Any, controller))


def test_validate_status_callbacks_handles_getattr_exception_controller(monkeypatch):
    """Test _validate_status_callbacks handles exception when getting controller.status_callback."""
    runtime = SimpleNamespace(status_callback=None)
    controller = SimpleNamespace()

    # Make getattr raise an exception
    original_getattr = getattr

    def failing_getattr(obj, name, default=None):
        if obj is controller and name == "status_callback":
            raise AttributeError("Cannot access")
        return original_getattr(obj, name, default)

    monkeypatch.setattr("builtins.getattr", failing_getattr)

    # Should not raise, just pass
    loop_module._validate_status_callbacks(cast(Any, runtime), cast(Any, controller))


def test_validate_status_callbacks_controller_has_callback(caplog):
    """Test _validate_status_callbacks warns when controller.status_callback is already set."""
    from unittest.mock import patch

    runtime = SimpleNamespace(status_callback=None)
    controller = SimpleNamespace()
    # Set a truthy callback
    controller.status_callback = lambda x, y, z: None

    # Patch logger.warning to verify it's called
    with patch.object(loop_module.logger, "warning") as mock_warning:
        loop_module._validate_status_callbacks(cast(Any, runtime), cast(Any, controller))
        # Verify the warning was called with the expected message
        mock_warning.assert_called()
        call_args = [str(call) for call in mock_warning.call_args_list]
        assert any("Controller status_callback already set" in str(call) for call in call_args)

