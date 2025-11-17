from __future__ import annotations

from typing import TYPE_CHECKING, Type

from forge.core.logger import forge_logger as logger
from forge.events import EventSource
from forge.events.action import AgentDelegateAction, MessageAction
from forge.events.observation import AgentDelegateObservation
from forge.controller.agent import Agent
from forge.controller.state.state import State
from forge.core.schemas import AgentState
from forge.controller.services.delegate_context import DelegateRunContext

if TYPE_CHECKING:
    from forge.controller.services.controller_context import ControllerContext


class DelegateService:
    """Manages delegate agent lifecycle and completion reporting."""

    def __init__(self, context: "ControllerContext") -> None:
        self._context = context

    async def handle_delegate_action(self, action: AgentDelegateAction) -> None:
        await self._start_delegate(action)
        controller = self._context.get_controller()
        if "task" in action.inputs:
            controller.event_stream.add_event(
                MessageAction(content="TASK: " + action.inputs["task"]),
                EventSource.USER,
            )
            if controller.delegate:
                await controller.delegate.set_agent_state_to(AgentState.RUNNING)

    async def _start_delegate(self, action: AgentDelegateAction) -> None:
        controller = self._context.get_controller()
        run_context = DelegateRunContext.capture(controller)
        agent_cls: Type[Agent] = self._resolve_agent_class(action.agent)
        agent_config = controller.agent_configs.get(action.agent, controller.agent.config)
        delegate_agent = agent_cls(
            config=agent_config, llm_registry=controller.agent.llm_registry
        )
        runtime_handle = self._acquire_delegate_runtime(delegate_agent)
        event_stream = (
            runtime_handle.event_stream if runtime_handle else controller.event_stream
        )
        state = State(
            session_id=controller.id.removesuffix("-delegate"),
            user_id=controller.user_id,
            inputs=action.inputs or {},
            iteration_flag=controller.state.iteration_flag,
            budget_flag=controller.state.budget_flag,
            delegate_level=controller.state.delegate_level + 1,
            metrics=controller.state.metrics,
            start_id=controller.event_stream.get_latest_event_id() + 1,
            parent_metrics_snapshot=controller.state_tracker.get_metrics_snapshot(),
            parent_iteration=controller.state.iteration_flag.current_value,
        )
        controller.log("debug", f"start delegate, creating agent {delegate_agent.name}")
        from forge.controller.agent_controller import AgentController  # delayed import to avoid cycle

        controller.delegate = AgentController(
            sid=f"{controller.id}-delegate",
            file_store=controller.file_store,
            user_id=controller.user_id,
            agent=delegate_agent,
            event_stream=event_stream,
            conversation_stats=controller.conversation_stats,
            iteration_delta=controller._initial_max_iterations,
            budget_per_task_delta=controller._initial_max_budget_per_task,
            agent_to_llm_config=controller.agent_to_llm_config,
            agent_configs=controller.agent_configs,
            initial_state=state,
            is_delegate=True,
            headless_mode=controller.headless_mode,
            security_analyzer=controller.security_analyzer,
        )
        run_context.inherits_runtime = runtime_handle is None
        run_context.attach(controller, controller.delegate)
        if controller.delegate is not None:
            setattr(controller.delegate, "runtime_handle", runtime_handle)

    def end_delegate(self) -> None:
        controller = self._context.get_controller()
        if controller.delegate is None:
            return
        delegate = controller.delegate
        controller.delegate = None
        delegate_state = delegate.get_agent_state()
        controller.state.iteration_flag.current_value = (
            delegate.state.iteration_flag.current_value
        )
        logger.info("Local metrics for delegate: %s", controller.state.get_local_metrics())
        runtime_handle = getattr(delegate, "runtime_handle", None)
        controller._run_or_schedule(self._shutdown_delegate(delegate, runtime_handle))
        delegate_outputs = delegate.state.outputs if delegate.state else {}
        content = self._get_delegate_completion_message(
            delegate_state, delegate_outputs, delegate.agent.name
        )
        obs = AgentDelegateObservation(outputs=delegate_outputs, content=content)
        self._attach_tool_call_metadata_to_observation(obs)
        try:
            controller.event_stream.add_event(obs, EventSource.AGENT)
        except Exception as emit_exc:
            logger.error(
                "Failed to emit delegate completion observation: %s",
                emit_exc,
            )

    def _acquire_delegate_runtime(self, delegate_agent: Agent):
        controller = self._context.get_controller()
        provider = getattr(controller, "delegate_runtime_provider", None)
        if provider is None:
            return None
        try:
            return provider.acquire(delegate_agent)
        except Exception as exc:
            logger.warning("Failed to acquire delegate runtime: %s", exc)
            return None

    async def _shutdown_delegate(self, delegate, runtime_handle) -> None:
        await delegate.close(set_stop_state=False)
        if runtime_handle:
            runtime_handle.release()

    def _resolve_agent_class(self, agent_name: str) -> Type[Agent]:
        return Agent.get_cls(agent_name)

    def _get_delegate_completion_message(
        self,
        delegate_state: AgentState,
        delegate_outputs: dict,
        agent_name: str,
    ) -> str:
        if delegate_state in (AgentState.FINISHED, AgentState.REJECTED):
            display_outputs = {
                k: v for k, v in delegate_outputs.items() if k != "metrics"
            }
            formatted_output = ", ".join(
                (f"{key}: {value}" for key, value in display_outputs.items())
            )
            content = f"{agent_name} finishes task with {formatted_output}"
        else:
            content = f"{agent_name} encountered an error during execution."
        return f"Delegated agent finished with result:\n\n{content}"

    def _attach_tool_call_metadata_to_observation(
        self, obs: AgentDelegateObservation
    ) -> None:
        controller = self._context.get_controller()
        for event in reversed(controller.state.history):
            if isinstance(event, AgentDelegateAction):
                metadata = event.tool_call_metadata
                if metadata is not None:
                    obs.tool_call_metadata = metadata
                break


