"""Agent control loop helpers for running runtimes and handling status callbacks."""

import asyncio

from forge.controller import AgentController
from forge.core.logger import forge_logger as logger
from forge.core.schema import AgentState
from forge.memory.memory import Memory
from forge.runtime.base import Runtime
from forge.runtime.runtime_status import RuntimeStatus


def _handle_error_status(controller: AgentController, runtime_status: RuntimeStatus, msg: str) -> None:
    """Handle error status in the status callback."""
    if controller:
        controller.state.last_error = msg
        try:
            if runtime_status == RuntimeStatus.ERROR_MEMORY:
                logger.info(
                    "LOOP.status_callback: resetting iteration_flag from %s to 0",
                    controller.state.iteration_flag.current_value,
                )
                controller.state.iteration_flag.current_value = 0
                setattr(controller.state, "_force_iteration_reset", True)
                setattr(controller, "_force_iteration_reset", True)
                logger.info(
                    "LOOP.status_callback: iteration_flag now %s",
                    controller.state.iteration_flag.current_value,
                )
        except Exception:
            pass
        asyncio.create_task(controller.set_agent_state_to(AgentState.ERROR))


def _create_status_callback(controller: AgentController) -> callable:
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
    if hasattr(runtime, "status_callback") and runtime.status_callback:
        msg = "Runtime status_callback was set, but run_agent_until_done will override it"
        raise ValueError(msg)
    if hasattr(controller, "status_callback") and controller.status_callback:
        msg = "Controller status_callback was set, but run_agent_until_done will override it"
        raise ValueError(msg)


def _set_status_callbacks(
    runtime: Runtime,
    controller: AgentController,
    memory: Memory,
    status_callback: callable,
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

    while controller.state.agent_state not in end_states:
        await asyncio.sleep(1)
