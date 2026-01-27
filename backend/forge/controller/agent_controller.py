"""Agent controller orchestration, logging, and execution helpers."""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
import traceback
from collections.abc import Coroutine
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from forge.controller.autonomy import AutonomyController
    from forge.controller.replay import ReplayManager
    from forge.controller.state.state_tracker import StateTracker
    from forge.controller.tool_pipeline import ToolInvocationPipeline
    from forge.core.config import AgentConfig, LLMConfig
    from forge.events.event import Event
    from forge.security.analyzer import SecurityAnalyzer
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore
from forge.llm.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
    InternalServerError,
    NotFoundError,
    OpenAIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from forge.controller.agent import Agent
from forge.controller.services import (
    ActionExecutionService,
    ActionService,
    AutonomyService,
    BudgetGuardService,
    ConfirmationService,
    CircuitBreakerService,
    ControllerContext,
    IterationGuardService,
    IterationService,
    LifecycleService,
    ObservationService,
    PendingActionService,
    RecoveryService,
    RetryService,
    SafetyService,
    StateTransitionService,
    StepGuardService,
    StepPrerequisiteService,
    StuckDetectionService,
    TelemetryService,
)
from forge.controller.state.state import State
from forge.core.exceptions import (
    AgentStuckInLoopError,
    FunctionCallNotExistsError,
    FunctionCallValidationError,
    LLMContextWindowExceedError,
    LLMMalformedActionError,
    LLMNoActionError,
    LLMResponseError,
)
from forge.core.logger import LOG_ALL_EVENTS
from forge.core.logger import forge_logger as logger
from forge.core.schemas import AgentState
from forge.controller.tool_pipeline import ToolInvocationContext
from forge.controller.error_recovery import ErrorRecoveryStrategy, ErrorType
from forge.events import EventSource, EventStream, EventStreamSubscriber, RecallType
from forge.events.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
    AgentFinishAction,
    AgentRejectAction,
    BrowseInteractiveAction,
    ChangeAgentStateAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    MessageAction,
    NullAction,
    SystemMessageAction,
)
from forge.events.action.agent import (
    CondensationAction,
    CondensationRequestAction,
    RecallAction,
)
from forge.events.observation import (
    AgentStateChangedObservation,
    ErrorObservation,
    NullObservation,
    Observation,
)
from forge.events.observation.agent import AgentThinkObservation, RecallObservation
from forge.runtime.runtime_status import RuntimeStatus

TRAFFIC_CONTROL_REMINDER = (
    "Please click on resume button if you'd like to continue, or start a new task."
)
ERROR_ACTION_NOT_EXECUTED_STOPPED_ID = "AGENT_ERROR$ERROR_ACTION_NOT_EXECUTED_STOPPED"
ERROR_ACTION_NOT_EXECUTED_ERROR_ID = "AGENT_ERROR$ERROR_ACTION_NOT_EXECUTED_ERROR"
ERROR_ACTION_NOT_EXECUTED_STOPPED = (
    "Stop button pressed. The action has not been executed."
)
ERROR_ACTION_NOT_EXECUTED_ERROR = "The action has not been executed due to a runtime error. The runtime system may have crashed and restarted due to resource constraints. Any previously established system state, dependencies, or environment variables may have been lost."


class AgentController:
    """Coordinates agent loop execution, event stream handling, and runtime interactions."""

    id: str
    agent: Agent
    max_iterations: int
    event_stream: EventStream
    state: State
    confirmation_mode: bool
    agent_to_llm_config: dict[str, LLMConfig]
    agent_configs: dict[str, AgentConfig]
    _closed: bool = False
    _cached_first_user_message: MessageAction | None = None
    user_id: str | None
    file_store: "FileStore | None"
    headless_mode: bool
    security_analyzer: "SecurityAnalyzer | None"
    status_callback: Callable | None
    state_tracker: "StateTracker"
    autonomy_controller: "AutonomyController | None"
    safety_validator: Any | None
    task_validator: Any | None
    tool_pipeline: "ToolInvocationPipeline | None"
    _action_contexts_by_event_id: dict[int, ToolInvocationContext]
    _action_contexts_by_object: dict[int, ToolInvocationContext]
    _replay_manager: "ReplayManager"
    PENDING_ACTION_TIMEOUT: float = 120.0
    conversation_stats: "ConversationStats"
    _initial_max_iterations: int
    _initial_max_budget_per_task: float | None

    def __init__(
        self,
        agent: Agent,
        event_stream: EventStream,
        conversation_stats: ConversationStats,
        iteration_delta: int,
        budget_per_task_delta: float | None = None,
        agent_to_llm_config: dict[str, LLMConfig] | None = None,
        agent_configs: dict[str, AgentConfig] | None = None,
        sid: str | None = None,
        file_store: FileStore | None = None,
        user_id: str | None = None,
        confirmation_mode: bool = False,
        initial_state: State | None = None,
        headless_mode: bool = True,
        status_callback: Callable | None = None,
        replay_events: list[Event] | None = None,
        security_analyzer: SecurityAnalyzer | None = None,
    ) -> None:
        """Initializes a new instance of the AgentController class.

        Args:
            agent: The agent instance to control
            event_stream: The event stream to publish events to
            conversation_stats: Statistics for the conversation
            iteration_delta: The maximum number of iterations the agent can run
            budget_per_task_delta: The maximum budget (in USD) allowed per task
            agent_to_llm_config: Dictionary mapping agent names to LLM configurations
            agent_configs: Dictionary mapping agent names to agent configurations
            sid: The session ID of the agent
            file_store: File storage for the agent
            user_id: The user ID associated with the agent
            confirmation_mode: Whether to enable confirmation mode for agent actions
            initial_state: The initial state of the controller
            headless_mode: Whether the agent is run in headless mode
            status_callback: Optional callback function to handle status updates
            replay_events: A list of logs to replay
            security_analyzer: Optional security analyzer for the agent

        """
        self.lifecycle_service = LifecycleService(self)
        self.autonomy_service = AutonomyService(self)
        self._controller_context = ControllerContext(self)
        self.iteration_service = IterationService(self._controller_context)
        self.iteration_guard = IterationGuardService(self._controller_context)
        self.step_guard = StepGuardService(self._controller_context)
        self.step_prerequisites = StepPrerequisiteService(self._controller_context)
        self.budget_guard = BudgetGuardService(self._controller_context)
        self.safety_service = SafetyService(self._controller_context)
        self.observation_service = ObservationService(self._controller_context)
        self.pending_action_service = PendingActionService(
            self._controller_context, self.PENDING_ACTION_TIMEOUT
        )
        self.confirmation_service = ConfirmationService(
            self._controller_context, self.safety_service
        )
        self.action_service = ActionService(
            self._controller_context,
            self.observation_service,
            self.pending_action_service,
            self.confirmation_service,
        )
        self.observation_service.set_action_service(self.action_service)
        self.action_execution = ActionExecutionService(self._controller_context)
        self.state_service = StateTransitionService(self._controller_context)
        self.telemetry_service = TelemetryService(self._controller_context)
        self.retry_service = RetryService(self._controller_context)
        self.recovery_service = RecoveryService(self._controller_context, self.retry_service)
        self.circuit_breaker_service = CircuitBreakerService(self._controller_context)
        self.stuck_service = StuckDetectionService(self)

        self.lifecycle_service.initialize_core_attributes(
            sid,
            event_stream,
            agent,
            user_id,
            file_store,
            headless_mode,
            conversation_stats,
            status_callback,
            security_analyzer,
        )

        self.lifecycle_service.initialize_state_and_tracking(
            sid,
            file_store,
            user_id,
            initial_state,
            conversation_stats,
            iteration_delta,
            budget_per_task_delta,
            confirmation_mode,
            replay_events,
        )

        self.stuck_service.initialize(self.state)
        self.lifecycle_service.initialize_agent_configs(
            agent_to_llm_config,
            agent_configs,
            iteration_delta,
            budget_per_task_delta,
        )
        self.autonomy_service.initialize(agent)
        self.telemetry_service.initialize_tool_pipeline()
        self.retry_service.initialize()


    def _register_action_context(
        self, action: Action, ctx: ToolInvocationContext
    ) -> None:
        """Register an invocation context before execution."""
        if hasattr(self, "_action_contexts_by_object"):
            self._action_contexts_by_object[id(action)] = ctx

    def _bind_action_context(
        self, action: Action, ctx: ToolInvocationContext
    ) -> None:
        """Bind a context to an action's event ID after emission."""
        if not hasattr(self, "_action_contexts_by_event_id"):
            return
        ctx.action_id = action.id
        if ctx.action_id is not None:
            self._action_contexts_by_event_id[ctx.action_id] = ctx
        if hasattr(self, "_action_contexts_by_object"):
            with contextlib.suppress(KeyError):
                self._action_contexts_by_object.pop(id(action))

    def _cleanup_action_context(
        self,
        ctx: ToolInvocationContext,
        *,
        action: Action | None = None,
    ) -> None:
        """Remove context bookkeeping entries."""
        if hasattr(self, "_action_contexts_by_object"):
            if action is not None:
                with contextlib.suppress(KeyError):
                    self._action_contexts_by_object.pop(id(action))
            else:
                keys_to_remove = [
                    key
                    for key, value in self._action_contexts_by_object.items()
                    if value is ctx
                ]
                for key in keys_to_remove:
                    with contextlib.suppress(KeyError):
                        self._action_contexts_by_object.pop(key)
        if (
            hasattr(self, "_action_contexts_by_event_id")
            and ctx.action_id is not None
        ):
            with contextlib.suppress(KeyError):
                self._action_contexts_by_event_id.pop(ctx.action_id)

    def _add_system_message(self) -> None:
        """Add system message to event stream if not already present.

        Checks if a system message has already been added for this agent session.
        If not, retrieves the agent's system message and adds it to the event stream.
        """
        for event in self.event_stream.search_events(start_id=self.state.start_id):
            if isinstance(event, MessageAction) and event.source == EventSource.USER:
                return
            if isinstance(event, SystemMessageAction):
                return
        system_message = self.agent.get_system_message()
        if system_message and system_message.content:
            preview = (
                f"{system_message.content[:50]}..."
                if len(system_message.content) > 50
                else system_message.content
            )
            logger.debug("System message: %s", preview)
            self.event_stream.add_event(system_message, EventSource.AGENT)

    async def close(self, set_stop_state: bool = True) -> None:
        """Closes the agent controller, canceling any ongoing tasks and unsubscribing from the event stream.

        Note that it's fairly important that this closes properly, otherwise the state is incomplete.
        """
        self._closed = True
        if set_stop_state:
            await self.set_agent_state_to(AgentState.STOPPED)
        self.state_tracker.close(self.event_stream)
        self.event_stream.unsubscribe(
            EventStreamSubscriber.AGENT_CONTROLLER, self.id
        )
        await self.retry_service.shutdown()

    def log(self, level: str, message: str, extra: dict | None = None) -> None:
        """Logs a message to the agent controller's logger.

        Args:
            level (str): The logging level to use (e.g., 'info', 'debug', 'error').
            message (str): The message to log.
            extra (dict | None, optional): Additional fields to log. Includes session_id by default.

        """
        message = f"[Agent Controller {self.id}] {message}"
        if extra is None:
            extra = {}
        extra_merged = {"session_id": self.id, **extra}
        getattr(logger, level)(message, extra=extra_merged, stacklevel=2)

    async def _react_to_exception(self, e: Exception) -> None:
        """Delegate exception handling to the recovery service."""
        await self.recovery_service.react_to_exception(e)

    async def _try_error_recovery(self, e: Exception, error_type) -> bool:
        """Deprecated: RecoveryService handles error recovery."""
        return False

    async def _handle_non_recoverable_error(self, e: Exception) -> None:
        """Legacy wrapper retained for compatibility."""
        await self.recovery_service.react_to_exception(e)

    def _determine_runtime_status(self, e: Exception) -> RuntimeStatus:
        """Determine the appropriate runtime status based on exception type."""
        if isinstance(e, AuthenticationError):
            self.state.last_error = RuntimeStatus.ERROR_LLM_AUTHENTICATION.value
            return RuntimeStatus.ERROR_LLM_AUTHENTICATION
        if isinstance(e, (ServiceUnavailableError, APIConnectionError, APIError)):
            self.state.last_error = RuntimeStatus.ERROR_LLM_SERVICE_UNAVAILABLE.value
            return RuntimeStatus.ERROR_LLM_SERVICE_UNAVAILABLE
        if isinstance(e, InternalServerError):
            self.state.last_error = RuntimeStatus.ERROR_LLM_INTERNAL_SERVER_ERROR.value
            return RuntimeStatus.ERROR_LLM_INTERNAL_SERVER_ERROR
        if isinstance(e, BadRequestError) and "ExceededBudget" in str(e):
            self.state.last_error = RuntimeStatus.ERROR_LLM_OUT_OF_CREDITS.value
            return RuntimeStatus.ERROR_LLM_OUT_OF_CREDITS
        if isinstance(e, ContentPolicyViolationError) or (
            isinstance(e, BadRequestError) and "ContentPolicyViolationError" in str(e)
        ):
            self.state.last_error = (
                RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION.value
            )
            return RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION
        if isinstance(e, RateLimitError):
            self.state.last_error = RuntimeStatus.LLM_RETRY.value
            return RuntimeStatus.LLM_RETRY
        return RuntimeStatus.ERROR

    async def _handle_rate_limit_error(self, e: Exception) -> None:
        """Handle rate limit error with appropriate state transition."""
        if (
            hasattr(e, "retry_attempt")
            and hasattr(e, "max_retries")
            and (e.retry_attempt >= e.max_retries)
        ):
            self.state.last_error = (
                RuntimeStatus.AGENT_RATE_LIMITED_STOPPED_MESSAGE.value
            )
            await self.set_agent_state_to(AgentState.ERROR)
        else:
            await self.set_agent_state_to(AgentState.RATE_LIMITED)

    def step(self) -> None:
        """Trigger agent to take one step asynchronously.

        Creates async task for step execution with exception handling.
        """
        asyncio.create_task(self._step_with_exception_handling())

    async def _step_with_exception_handling(self) -> None:
        """Execute agent step with comprehensive exception handling.

        Catches and handles LLM errors (rate limits, API errors, context window),
        agent errors (stuck, malformed actions), and runtime errors.
        """
        try:
            await self._step()
        except Exception as e:
            # CRITICAL DEBUG: Log the exact exception type and module
            self.log(
                "error",
                f"EXCEPTION CAUGHT - Type: {type(e).__name__}, Module: {type(e).__module__}, Value: {e}",
            )
            self.log(
                "error",
                f"Exception is APIConnectionError: {isinstance(e, APIConnectionError)}",
            )
            self.log(
                "error",
                f"Exception isinstance check: APIConnectionError={isinstance(e, APIConnectionError)}, APIError={isinstance(e, APIError)}",
            )
            self.log(
                "error",
                f"Error while running the agent (session ID: {self.id}): {e}. Traceback: {traceback.format_exc()}",
            )

            # Check if this is a known LLM exception that should be passed through directly
            reported: Exception
            if isinstance(
                e,
                (
                    Timeout,
                    APIError,
                    APIConnectionError,
                    BadRequestError,
                    NotFoundError,
                    InternalServerError,
                    AuthenticationError,
                    RateLimitError,
                    ServiceUnavailableError,
                    ContentPolicyViolationError,
                    ContextWindowExceededError,
                    LLMContextWindowExceedError,
                ),
            ):
                reported = e
                self.log(
                    "info", f"✅ PASSING THROUGH LLM EXCEPTION: {type(e).__name__}: {e}"
                )
            else:
                reported = RuntimeError(
                    f"There was an unexpected error while running the agent: {
                        e.__class__.__name__
                    }. You can refresh the page or ask the agent to try again.",
                )
                self.log(
                    "warning",
                    f"❌ WRAPPING EXCEPTION: {type(e).__name__} -> RuntimeError",
                )

            # CRITICAL DEBUG: Log what we're about to pass to _react_to_exception
            self.log(
                "error",
                f"ABOUT TO CALL _react_to_exception with: {type(reported).__name__}: {reported}",
            )
            await self._react_to_exception(reported)

    def _should_step_for_action(self, event: Action) -> bool:
        """Determine if agent should step for action events."""
        if isinstance(event, MessageAction):
            return self._should_step_for_message_action(event)
        if isinstance(event, CondensationAction):
            return True
        return isinstance(event, CondensationRequestAction)

    def _should_step_for_message_action(self, event: MessageAction) -> bool:
        """Determine if agent should step for message action events."""
        if event.source == EventSource.USER:
            return True
        # Step after agent messages unless the controller is explicitly waiting on the user.
        return self.get_agent_state() != AgentState.AWAITING_USER_INPUT

    def _should_step_for_observation(self, event: Observation) -> bool:
        """Determine if agent should step for observation events."""
        if isinstance(event, NullObservation):
            # Step only when the observation references a prior event (non-zero cause).
            return bool(event.cause)
        return not isinstance(event, (AgentStateChangedObservation, RecallObservation))

    def should_step(self, event: Event) -> bool:
        """Whether the agent should take a step based on an event.

        In general, the agent should take a step if it receives a message from the user,
        or observes something in the environment (after acting).
        """
        if isinstance(event, Action):
            return self._should_step_for_action(event)
        if isinstance(event, Observation):
            return self._should_step_for_observation(event)

        return False

    def on_event(self, event: Event) -> None:
        """Callback from the event stream. Notifies the controller of incoming events.

        Args:
            event (Event): The incoming event to process.

        """
        self._run_or_schedule(self._on_event(event))

    @staticmethod
    def _run_or_schedule(coro: Coroutine[Any, Any, Any]) -> None:
        """Execute coroutine immediately, handling nested loops and thread contexts."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop:
            loop.create_task(coro)
            return

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(coro)

    def _schedule_coroutine(self, coro: Coroutine[Any, Any, Any]) -> None:
        """Schedule a coroutine using the current or new event loop."""
        self._run_or_schedule(coro)

    async def _on_event(self, event: Event) -> None:
        """Handle incoming events from the event stream.

        Processes actions and observations, updates state tracking, and
        manages agent execution flow. Filters out hidden events.

        Args:
            event: Event to process (Action or Observation)

        """
        if hasattr(event, "hidden") and event.hidden:
            return

        # DUPLICATE MESSAGE DETECTION: Log every MessageAction to detect duplicates
        if isinstance(event, MessageAction):
            event_id = getattr(event, "id", "NO_ID")
            self.log(
                "warning",
                f"🔍 PROCESSING MessageAction: id={event_id}, source={event.source}, content={event.content[:50]}...",
                extra={"msg_type": "MESSAGE_RECEIVED"},
            )

        self.state_tracker.add_history(event)
        if isinstance(event, Action):
            await self._handle_action(event)
        elif isinstance(event, Observation):
            await self._handle_observation(event)

    async def _handle_finish_action(self, action: AgentFinishAction) -> None:
        """Handle agent finish action with completion validation.

        Args:
            action: Finish action from agent

        """
        # Validate task completion if enabled
        if await self._should_validate_completion(action):
            if not await self._validate_and_handle_completion(action):
                return

        # Validation passed or not configured - allow finish
        self.state.outputs = action.outputs
        await self.set_agent_state_to(AgentState.FINISHED)

    async def _should_validate_completion(self, action: AgentFinishAction) -> bool:
        """Check if task completion should be validated.

        Args:
            action: Finish action from agent

        Returns:
            True if validation should occur

        """
        validator = getattr(self, "task_validator", None)
        return bool(validator) and not getattr(action, "force_finish", False)

    async def _validate_and_handle_completion(self, action: AgentFinishAction) -> bool:
        """Validate task completion and handle result.

        Args:
            action: Finish action from agent

        Returns:
            True if validation passed, False if failed

        """
        task = self._get_initial_task()
        if not task:
            return True

        validator = getattr(self, "task_validator", None)
        if validator is None:
            return True

        logger.info("Validating task completion before finishing...")
        validation = await validator.validate_completion(task, self.state)

        if not validation.passed:
            await self._handle_validation_failure(validation)
            return False

        logger.info(f"Task completion validation passed: {validation.reason}")
        return True

    async def _handle_validation_failure(self, validation) -> None:
        """Handle failed task completion validation.

        Args:
            validation: Validation result object

        """
        from forge.events.observation import ErrorObservation

        logger.warning(f"Task completion validation failed: {validation.reason}")
        feedback_content = self._build_validation_feedback(validation)

        error_obs = ErrorObservation(
            content=feedback_content,
            error_id="TASK_VALIDATION_FAILED",
        )
        self.event_stream.add_event(error_obs, EventSource.ENVIRONMENT)

        if self.state.agent_state != AgentState.RUNNING:
            await self.set_agent_state_to(AgentState.RUNNING)

    def _build_validation_feedback(self, validation) -> str:
        """Build feedback message for validation failure.

        Args:
            validation: Validation result object

        Returns:
            Formatted feedback string

        """
        feedback = f"TASK NOT COMPLETE: {validation.reason}\n\nConfidence: {validation.confidence:.1%}\n"

        if validation.missing_items:
            feedback += "\nMissing items:\n" + "\n".join(
                f"- {item}" for item in validation.missing_items
            )

        if validation.suggestions:
            feedback += "\n\nSuggestions:\n" + "\n".join(
                f"- {sug}" for sug in validation.suggestions
            )

        feedback += "\n\nPlease continue working to complete the task."
        return feedback

    async def _handle_reject_action(self, action: AgentRejectAction) -> None:
        """Handle agent reject action."""
        self.state.outputs = action.outputs
        await self.set_agent_state_to(AgentState.REJECTED)

    async def _handle_action(self, action: Action) -> None:
        """Handles an Action from the agent."""
        if isinstance(action, ChangeAgentStateAction):
            try:
                target_state = AgentState(action.agent_state)
            except ValueError:
                self.log(
                    "warning",
                    f"Received unknown agent state '{action.agent_state}', ignoring.",
                )
            else:
                await self.set_agent_state_to(target_state)
        elif isinstance(action, MessageAction):
            await self._handle_message_action(action)
        elif isinstance(action, AgentFinishAction):
            await self._handle_finish_action(action)
        elif isinstance(action, AgentRejectAction):
            await self._handle_reject_action(action)

    async def _handle_observation(self, observation: Observation) -> None:
        await self.observation_service.handle_observation(observation)

    async def _handle_message_action(self, action: MessageAction) -> None:
        """Handles message actions from the event stream.

        Args:
            action (MessageAction): The message action to handle.

        """
        if action.source == EventSource.USER:
            log_level = (
                "info" if os.getenv("LOG_ALL_EVENTS") in ("true", "1") else "debug"
            )
            self.log(
                log_level,
                str(action),
                extra={"msg_type": "ACTION", "event_source": EventSource.USER},
            )
            first_user_message = self._first_user_message()
            is_first_user_message = (
                action.id == first_user_message.id if first_user_message else False
            )
            recall_type = (
                RecallType.WORKSPACE_CONTEXT
                if is_first_user_message
                else RecallType.KNOWLEDGE
            )
            recall_action = RecallAction(query=action.content, recall_type=recall_type)
            self._pending_action = recall_action
            self.event_stream.add_event(recall_action, EventSource.USER)
            if self.get_agent_state() != AgentState.RUNNING:
                await self.set_agent_state_to(AgentState.RUNNING)
        elif action.source == EventSource.AGENT:
            if action.wait_for_response:
                await self.set_agent_state_to(AgentState.AWAITING_USER_INPUT)

    def _reset(self) -> None:
        """Resets the agent controller."""
        if hasattr(self, "_action_contexts_by_object"):
            self._action_contexts_by_object.clear()
        if hasattr(self, "_action_contexts_by_event_id"):
            self._action_contexts_by_event_id.clear()
        if self._pending_action and hasattr(self._pending_action, "tool_call_metadata"):
            found_observation = any(
                isinstance(event, Observation)
                and event.tool_call_metadata == self._pending_action.tool_call_metadata
                for event in self.state.history
            )
            if not found_observation:
                if self.state.agent_state == AgentState.STOPPED:
                    error_content = ERROR_ACTION_NOT_EXECUTED_STOPPED
                    error_id = ERROR_ACTION_NOT_EXECUTED_STOPPED_ID
                else:
                    error_content = ERROR_ACTION_NOT_EXECUTED_ERROR
                    error_id = ERROR_ACTION_NOT_EXECUTED_ERROR_ID
                obs = ErrorObservation(content=error_content, error_id=error_id)
                if meta := getattr(self._pending_action, "tool_call_metadata", None):
                    obs.tool_call_metadata = meta
                obs.cause = getattr(self._pending_action, "id", None)
                self.event_stream.add_event(obs, EventSource.AGENT)
        self._pending_action = None
        self.agent.reset()

    async def set_agent_state_to(self, new_state: AgentState) -> None:
        """Delegate to the state transition service for consistency."""
        await self.state_service.set_agent_state(new_state)

    def get_agent_state(self) -> AgentState:
        """Returns the current state of the agent.

        Returns:
            AgentState: The current state of the agent.

        """
        return self.state.agent_state

    def _log_step_info(self) -> None:
        """Log step information for debugging."""
        self.log(
            "debug",
            f"LOCAL STEP {
                self.state.get_local_step()
            } GLOBAL STEP {self.state.iteration_flag.current_value}",
            extra={"msg_type": "STEP"},
        )

    def _is_context_window_error(self, error_str: str, e: Exception) -> bool:
        """Check if the error is a context window error."""
        return (
            "contextwindowexceedederror" not in error_str
            and "prompt is too long" not in error_str
            and ("input length and `max_tokens` exceed context limit" not in error_str)
            and ("please reduce the length of either one" not in error_str)
            and ("the request exceeds the available context size" not in error_str)
            and ("context length exceeded" not in error_str)
            and (
                "sambanovaexception" not in error_str
                or "maximum context length" not in error_str
            )
            and (not isinstance(e, ContextWindowExceededError))
        )

    async def _step(self) -> None:
        """Executes a single step of the agent. Detects stuck agents and limits on the number of iterations and the task budget."""
        if not self.step_prerequisites.can_step():
            return

        self._log_step_info()
        self.budget_guard.sync_with_metrics()

        if not await self.step_guard.ensure_can_step():
            return

        if not await self._run_control_flags_safely():
            return

        action = await self.action_execution.get_next_action()
        if action is None:
            return

        # Reset retry count on successful action execution
        # This prevents getting stuck if a previous error has been resolved
        if self.retry_service.retry_count > 0:
            logger.debug(
                "Resetting retry count from "
                f"{self.retry_service.retry_count} to 0 after successful execution"
            )
            self.retry_service.reset_retry_metrics()

        await self.action_execution.execute_action(action)

    async def _run_control_flags_safely(self) -> bool:
        """Run control flags with exception handling."""
        try:
            await self.iteration_guard.run_control_flags()
            return True
        except Exception as e:
            await self._react_to_exception(e)
            return False

    @property
    def _pending_action(self) -> Action | None:
        pending_service = getattr(self, "pending_action_service", None)
        if pending_service:
            return pending_service.get()
        service = getattr(self, "action_service", None)
        if service:
            return service.get_pending_action()
        return None

    @_pending_action.setter
    def _pending_action(self, action: Action | None) -> None:
        pending_service = getattr(self, "pending_action_service", None)
        if pending_service:
            pending_service.set(action)
            return
        service = getattr(self, "action_service", None)
        if service:
            service.set_pending_action(action)

    def get_state(self) -> State:
        """Returns the current running state object.

        Returns:
            State: The current state object.

        """
        return self.state

    def set_initial_state(
        self,
        state: State | None,
        conversation_stats: ConversationStats,
        max_iterations: int,
        max_budget_per_task: float | None,
        confirmation_mode: bool = False,
    ) -> None:
        """Set the initial state for the agent controller.

        Args:
            state: Initial state object (None for new conversations)
            conversation_stats: Statistics tracker for the conversation
            max_iterations: Maximum number of agent iterations allowed
            max_budget_per_task: Maximum budget in USD per task
            confirmation_mode: Whether to require user confirmation for actions

        """
        self.state_tracker.set_initial_state(
            self.id,
            state,
            conversation_stats,
            max_iterations,
            max_budget_per_task,
            confirmation_mode,
        )
        self.state_tracker._init_history(self.event_stream)

    def get_trajectory(self, include_screenshots: bool = False) -> list[dict]:
        """Get the complete trajectory of agent actions and observations.

        Must be called after controller is closed.

        Args:
            include_screenshots: Whether to include screenshot data in trajectory

        Returns:
            List of trajectory events as dictionaries

        """
        assert self._closed
        return self.state_tracker.get_trajectory(include_screenshots)

    def _is_stuck(self) -> bool:
        """Checks if the agent is stuck in a loop.

        Returns:
            bool: True if the agent is stuck, False otherwise.

        """
        return self.stuck_service.is_stuck()

    def __repr__(self) -> str:
        """Get string representation of controller with key state information.

        Returns:
            String representation including ID, agent state, and pending action info

        """
        pending_action_info = "<none>"
        action_service = getattr(self, "action_service", None)
        if action_service:
            info = action_service.get_pending_action_info()
            if info is not None:
                action, timestamp = info
                action_id = getattr(action, "id", "unknown")
                action_type = type(action).__name__
                elapsed_time = time.time() - timestamp
                pending_action_info = (
                    f"{action_type}(id={action_id}, elapsed={elapsed_time:.2f}s)"
                )
        return f"AgentController(id={getattr(self, 'id', '<uninitialized>')}, agent={
            getattr(self, 'agent', '<uninitialized>')!r
        }, event_stream={getattr(self, 'event_stream', '<uninitialized>')!r}, state={
            getattr(self, 'state', '<uninitialized>')!r
        }, _pending_action={
            pending_action_info
        })"

    def _is_awaiting_observation(self) -> bool:
        """Check if agent is waiting for an observation to complete current action.

        Searches backward through event stream to find most recent agent state change.

        Returns:
            True if agent is in RUNNING state (awaiting observation)

        """
        events = self.event_stream.search_events(reverse=True)
        return next(
            (
                event.agent_state == AgentState.RUNNING
                for event in events
                if isinstance(event, AgentStateChangedObservation)
            ),
            False,
        )

    def _first_user_message(
        self, events: list[Event] | None = None
    ) -> MessageAction | None:
        """Get the first user message for this agent.

        Args:
            events: Optional list of events to search through. If None, uses the event stream.

        Returns:
            MessageAction | None: The first user message, or None if no user message found

        """
        if events is not None:
            return next(
                (
                    e
                    for e in events
                    if isinstance(e, MessageAction) and e.source == EventSource.USER
                ),
                None,
            )
        if self._cached_first_user_message is not None:
            return self._cached_first_user_message
        self._cached_first_user_message = next(
            (
                e
                for e in self.event_stream.search_events(start_id=self.state.start_id)
                if isinstance(e, MessageAction) and e.source == EventSource.USER
            ),
            None,
        )
        return self._cached_first_user_message

    def _get_initial_task(self):
        """Get the initial task from first user message.

        Returns:
            Task object or None

        """
        first_msg = self._first_user_message()
        if not first_msg:
            return None

        from forge.validation.task_validator import Task

        return Task(
            description=first_msg.content,
            requirements=[],  # Could be extracted from content
            acceptance_criteria=[],
        )

    def save_state(self) -> None:
        """Save current agent state to persistent storage."""
        self.state_tracker.save_state()
