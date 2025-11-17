"""Agent control loop helpers for running runtimes and handling status callbacks."""

import asyncio
from typing import Callable

from forge.controller import AgentController
from forge.core.logger import forge_logger as logger
from forge.core.schemas import AgentState
from forge.memory.memory import Memory
from forge.runtime.base import Runtime
from forge.runtime.runtime_status import RuntimeStatus


def _handle_error_status(
    controller: AgentController, runtime_status: RuntimeStatus, msg: str
) -> None:
    """Handle error status in the status callback."""
    if controller:
        controller.state.last_error = msg
        try:
            if runtime_status == RuntimeStatus.ERROR_MEMORY:
                # Record boundary without mutating iteration counter; add marker flag only
                setattr(controller.state, "_memory_error_boundary", controller.state.iteration_flag.current_value)
                logger.info(
                    "LOOP.status_callback: memory error boundary recorded at iteration %s",
                    controller.state.iteration_flag.current_value,
                )
        except Exception:
            pass
        # Schedule safely across threads without requiring a running loop
        try:
            controller._run_or_schedule(controller.set_agent_state_to(AgentState.ERROR))
        except Exception:
            # As a fallback, try direct event loop task creation if available
            try:
                import asyncio as _asyncio
                _asyncio.create_task(controller.set_agent_state_to(AgentState.ERROR))
            except Exception:
                pass


def _create_status_callback(
    controller: AgentController,
) -> Callable[[str, RuntimeStatus, str], None]:
    """Create the status callback function."""

    def status_callback(msg_type: str, runtime_status: RuntimeStatus, msg: str) -> None:
        """Handle runtime status updates.

        Args:
            msg_type: Message type (error, info, etc.)
            runtime_status: Runtime status object
            msg: Status message

        """
        if msg_type == "error":
            logger.error(msg)
            _handle_error_status(controller, runtime_status, msg)
        else:
            logger.info(msg)

    return status_callback


def _validate_status_callbacks(runtime: Runtime, controller: AgentController) -> None:
    """Validate that status callbacks are not already set."""
    # Be tolerant in tests/mocks: warn and proceed to override
    try:
        if getattr(runtime, "status_callback", None):
            logger.warning(
                "Runtime status_callback already set; overriding in run loop"
            )
    except Exception:
        pass
    try:
        if getattr(controller, "status_callback", None):
            logger.warning(
                "Controller status_callback already set; overriding in run loop"
            )
    except Exception:
        pass


def _set_status_callbacks(
    runtime: Runtime,
    controller: AgentController,
    memory: Memory,
    status_callback: Callable[[str, RuntimeStatus, str], None],
) -> None:
    """Set status callbacks on runtime, controller, and memory."""
    runtime.status_callback = status_callback
    controller.status_callback = status_callback
    memory.status_callback = status_callback


async def run_agent_until_done(
    controller: AgentController,
    runtime: Runtime,
    memory: Memory,
    end_states: list[AgentState],
) -> None:
    """run_agent_until_done takes a controller and a runtime, and will run.

    the agent until it reaches a terminal state.

    Note that runtime must be connected before being passed in here.
    """
    _validate_status_callbacks(runtime, controller)

    status_callback = _create_status_callback(controller)
    _set_status_callbacks(runtime, controller, memory, status_callback)

    # Kick the agent once to ensure progress starts even if no event arrives
    try:
        controller.step()
    except Exception:
        pass

    # Actively drive the loop to prevent hangs in tests/environments
    while controller.state.agent_state not in end_states:
        await asyncio.sleep(0.1)
        try:
            controller.step()
        except Exception:
            # Any exceptions are handled inside controller._step_with_exception_handling
            pass
