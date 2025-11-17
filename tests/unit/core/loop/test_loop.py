import asyncio
from types import SimpleNamespace
from typing import Any, Callable, cast

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
        self.status_callback: Callable[..., None] | None = None
        self._force_iteration_reset = False
        self.set_calls: list[AgentState] = []

    async def set_agent_state_to(self, new_state: AgentState) -> None:
        self.set_calls.append(new_state)
        self.state.agent_state = new_state


class DummyRuntime:
    def __init__(self) -> None:
        self.status_callback: Callable[..., None] | None = None


class DummyMemory:
    def __init__(self) -> None:
        self.status_callback: Callable[..., None] | None = None


def test_handle_error_status_resets_iteration_flag(monkeypatch):
    controller = DummyController()
    tasks = []

    def fake_create_task(coro):
        tasks.append(coro)
        return coro

    monkeypatch.setattr(loop_module.asyncio, "create_task", fake_create_task)

    loop_module._handle_error_status(
        cast(Any, controller),
        RuntimeStatus.ERROR_MEMORY,
        "Bad things happened",
    )

    assert controller.state.last_error == "Bad things happened"
    # Iteration is no longer reset; boundary is recorded instead
    assert controller.state.iteration_flag.current_value == 5
    assert getattr(controller.state, "_memory_error_boundary") == 5
    assert len(tasks) == 1

    asyncio.run(tasks[0])
    assert controller.state.agent_state == AgentState.ERROR
    assert controller.set_calls[-1] == AgentState.ERROR


def test_handle_error_status_non_memory_preserves_iteration(monkeypatch):
    controller = DummyController()
    monkeypatch.setattr(loop_module.asyncio, "create_task", lambda coro: coro)

    loop_module._handle_error_status(
        cast(Any, controller),
        RuntimeStatus.ERROR,
        "Another error",
    )

    assert controller.state.last_error == "Another error"
    assert controller.state.iteration_flag.current_value == 5


def test_handle_error_status_handles_iteration_failure(monkeypatch):
    controller = DummyController()

    class FailingFlag:
        def __init__(self) -> None:
            self._value = 5

        @property
        def current_value(self):
            raise RuntimeError("cannot read flag")

        @current_value.setter
        def current_value(self, value):
            raise RuntimeError("cannot write flag")

    controller.state.iteration_flag = FailingFlag()
    monkeypatch.setattr(loop_module.asyncio, "create_task", lambda coro: coro)

    loop_module._handle_error_status(
        cast(Any, controller),
        RuntimeStatus.ERROR_MEMORY,
        "flag failure",
    )

    assert controller.state.last_error == "flag failure"


def test_status_callback_uses_logging(monkeypatch):
    controller = DummyController()
    captured = {"error": None, "info": None}

    def fake_error(msg):
        captured["error"] = msg

    def fake_info(msg):
        captured["info"] = msg

    calls = []

    def fake_handle(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(loop_module.logger, "error", fake_error)
    monkeypatch.setattr(loop_module.logger, "info", fake_info)
    monkeypatch.setattr(loop_module, "_handle_error_status", fake_handle)

    callback = loop_module._create_status_callback(cast(Any, controller))

    callback("error", RuntimeStatus.ERROR, "problem")
    assert captured["error"] == "problem"
    assert calls and calls[0][0][2] == "problem"

    callback("info", RuntimeStatus.READY, "fine")
    assert captured["info"] == "fine"


def test_validate_status_callbacks_detects_preexisting_callbacks():
    runtime = DummyRuntime()
    controller = DummyController()

    runtime.status_callback = lambda *_args: None
    with pytest.raises(ValueError):
        loop_module._validate_status_callbacks(cast(Any, runtime), cast(Any, controller))

    runtime.status_callback = None
    controller.status_callback = lambda *_args: None
    with pytest.raises(ValueError):
        loop_module._validate_status_callbacks(cast(Any, runtime), cast(Any, controller))


def test_set_status_callbacks_assigns_all():
    runtime = DummyRuntime()
    controller = DummyController()
    memory = DummyMemory()

    callback = lambda *_args: None
    loop_module._set_status_callbacks(
        cast(Any, runtime), cast(Any, controller), cast(Any, memory), callback
    )

    assert runtime.status_callback is callback
    assert controller.status_callback is callback
    assert memory.status_callback is callback


@pytest.mark.asyncio
async def test_run_agent_until_done_sets_callbacks_and_waits(monkeypatch):
    runtime = DummyRuntime()
    memory = DummyMemory()
    controller = DummyController()

    async def fake_sleep(_seconds: float) -> None:
        controller.state.agent_state = AgentState.FINISHED

    monkeypatch.setattr(loop_module.asyncio, "sleep", fake_sleep)

    await loop_module.run_agent_until_done(
        cast(Any, controller),
        cast(Any, runtime),
        cast(Any, memory),
        end_states=[AgentState.FINISHED],
    )

    assert controller.state.agent_state == AgentState.FINISHED
    assert (
        runtime.status_callback is controller.status_callback is memory.status_callback
    )
    assert callable(runtime.status_callback)
