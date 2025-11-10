"""Agent controller orchestration, logging, and execution helpers."""

from __future__ import annotations

import asyncio
import copy
import os
import time
import traceback
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from forge.core.config import AgentConfig, LLMConfig
    from forge.events.event import Event
    from forge.security.analyzer import SecurityAnalyzer
    from forge.server.services.conversation_stats import ConversationStats
    from forge.storage.files import FileStore
from litellm.exceptions import (
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
from forge.controller.replay import ReplayManager
from forge.controller.state.state import State
from forge.controller.state.state_tracker import StateTracker
from forge.controller.stuck import StuckDetector
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
from forge.core.schema import AgentState
from forge.events import EventSource, EventStream, EventStreamSubscriber, RecallType
from forge.events.action import (
    Action,
    ActionConfirmationStatus,
    ActionSecurityRisk,
    AgentDelegateAction,
    AgentFinishAction,
    AgentRejectAction,
    BrowseInteractiveAction,
    ChangeAgentStateAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    IPythonRunCellAction,
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
    AgentDelegateObservation,
    AgentStateChangedObservation,
    ErrorObservation,
    NullObservation,
    Observation,
)
from forge.events.observation.agent import RecallObservation
from forge.events.serialization.event import truncate_content
from forge.llm.metrics import Metrics
from forge.runtime.runtime_status import RuntimeStatus

TRAFFIC_CONTROL_REMINDER = "Please click on resume button if you'd like to continue, or start a new task."
ERROR_ACTION_NOT_EXECUTED_STOPPED_ID = "AGENT_ERROR$ERROR_ACTION_NOT_EXECUTED_STOPPED"
ERROR_ACTION_NOT_EXECUTED_ERROR_ID = "AGENT_ERROR$ERROR_ACTION_NOT_EXECUTED_ERROR"
ERROR_ACTION_NOT_EXECUTED_STOPPED = "Stop button pressed. The action has not been executed."
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
    parent: AgentController | None = None
    delegate: AgentController | None = None
    _pending_action_info: tuple[Action, float] | None = None
    _closed: bool = False
    _cached_first_user_message: MessageAction | None = None

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
        is_delegate: bool = False,
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
            is_delegate: Whether this controller is a delegate
            headless_mode: Whether the agent is run in headless mode
            status_callback: Optional callback function to handle status updates
            replay_events: A list of logs to replay
            security_analyzer: Optional security analyzer for the agent

        """
        self._initialize_core_attributes(
            sid,
            event_stream,
            agent,
            user_id,
            file_store,
            headless_mode,
            is_delegate,
            conversation_stats,
            status_callback,
            security_analyzer,
        )

        self._initialize_state_and_tracking(
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

        self._initialize_agent_configs(agent_to_llm_config, agent_configs, iteration_delta, budget_per_task_delta)
        self._initialize_autonomy_and_validators(agent)

    def _initialize_core_attributes(
        self,
        sid,
        event_stream,
        agent,
        user_id,
        file_store,
        headless_mode,
        is_delegate,
        conversation_stats,
        status_callback,
        security_analyzer,
    ) -> None:
        """Initialize core controller attributes.

        Args:
            sid: Session ID
            event_stream: Event stream
            agent: Agent instance
            user_id: User ID
            file_store: File storage
            headless_mode: Headless mode flag
            is_delegate: Delegate flag
            conversation_stats: Conversation statistics
            status_callback: Status callback
            security_analyzer: Security analyzer

        """
        self.id = sid or event_stream.sid
        self.user_id = user_id
        self.file_store = file_store
        self.agent = agent
        self.headless_mode = headless_mode
        self.is_delegate = is_delegate
        self.conversation_stats = conversation_stats
        self.event_stream = event_stream
        self.status_callback = status_callback
        self.security_analyzer = security_analyzer

        if not self.is_delegate:
            self.event_stream.subscribe(EventStreamSubscriber.AGENT_CONTROLLER, self.on_event, self.id)

    def _initialize_state_and_tracking(
        self,
        sid,
        file_store,
        user_id,
        initial_state,
        conversation_stats,
        iteration_delta,
        budget_per_task_delta,
        confirmation_mode,
        replay_events,
    ) -> None:
        """Initialize state tracking components.

        Args:
            sid: Session ID
            file_store: File storage
            user_id: User ID
            initial_state: Initial state
            conversation_stats: Conversation statistics
            iteration_delta: Max iterations
            budget_per_task_delta: Max budget
            confirmation_mode: Confirmation mode flag
            replay_events: Replay events list

        """
        self.state_tracker = StateTracker(sid, file_store, user_id)
        self.set_initial_state(
            state=initial_state,
            conversation_stats=conversation_stats,
            max_iterations=iteration_delta,
            max_budget_per_task=budget_per_task_delta,
            confirmation_mode=confirmation_mode,
        )
        self.state = self.state_tracker.state
        self.confirmation_mode = confirmation_mode
        self._stuck_detector = StuckDetector(self.state)
        self._replay_manager = ReplayManager(replay_events)

    def _initialize_agent_configs(
        self, agent_to_llm_config, agent_configs, iteration_delta, budget_per_task_delta,
    ) -> None:
        """Initialize agent configuration attributes.

        Args:
            agent_to_llm_config: Agent to LLM config mapping
            agent_configs: Agent configs mapping
            iteration_delta: Max iterations
            budget_per_task_delta: Max budget

        """
        self.agent_to_llm_config = agent_to_llm_config or {}
        self.agent_configs = agent_configs or {}
        self._initial_max_iterations = iteration_delta
        self._initial_max_budget_per_task = budget_per_task_delta

    def _initialize_autonomy_and_validators(self, agent: Agent) -> None:
        """Initialize autonomy controller and validators.

        Args:
            agent: Agent instance

        """
        from forge.controller.autonomy import AutonomyController

        from forge.core.config.agent_config import AgentConfig as _AgentConfig

        agent_config = getattr(agent, "config", None)
        if agent_config is None or not isinstance(agent_config, _AgentConfig):
            self.autonomy_controller = None
            self.safety_validator = None
            self.task_validator = None
            self.circuit_breaker = None
            self._retry_count = 0
            self.PENDING_ACTION_TIMEOUT = 120.0
            return

        self.autonomy_controller = AutonomyController(agent_config)
        self._retry_count = 0

        self._initialize_safety_validator(agent)
        self._initialize_task_validator(agent)

    def _initialize_safety_validator(self, agent: Agent) -> None:
        """Initialize safety validator if enabled.

        Args:
            agent: Agent instance

        """
        self.safety_validator = None
        if hasattr(agent.config, "safety") and agent.config.safety.enable_mandatory_validation:
            from forge.controller.safety_validator import SafetyValidator

            self.safety_validator = SafetyValidator(agent.config.safety)
            logger.info("SafetyValidator enabled for production safety")

    def _initialize_task_validator(self, agent: Agent) -> None:
        """Initialize task validator if enabled.

        Args:
            agent: Agent instance

        """
        self.task_validator = None
        if hasattr(agent.config, "enable_completion_validation") and agent.config.enable_completion_validation:
            from forge.validation.task_validator import (
                CompositeValidator,
                GitDiffValidator,
                TestPassingValidator,
            )

            validators = [TestPassingValidator(), GitDiffValidator()]
            self.task_validator = CompositeValidator(
                validators=validators,
                min_confidence=0.7,
                require_all_pass=False,  # Majority vote
            )
            logger.info("TaskValidator enabled for completion checking")

        # Initialize circuit breaker for anomaly detection
        self.circuit_breaker = None
        if hasattr(agent.config, "enable_circuit_breaker") and agent.config.enable_circuit_breaker:
            from forge.controller.circuit_breaker import (
                CircuitBreaker,
                CircuitBreakerConfig,
            )

            cb_config = CircuitBreakerConfig(
                enabled=True,
                max_consecutive_errors=getattr(agent.config, "max_consecutive_errors", 5),
                max_high_risk_actions=getattr(agent.config, "max_high_risk_actions", 10),
                max_stuck_detections=getattr(agent.config, "max_stuck_detections", 3),
            )

            self.circuit_breaker = CircuitBreaker(cb_config)
            logger.info("CircuitBreaker enabled for anomaly detection")

        # Pending action timeout (120 seconds)
        self.PENDING_ACTION_TIMEOUT = 120.0

        self._add_system_message()

    async def _handle_security_analyzer(self, action: Action) -> None:
        """Handle security risk analysis for an action.

        If a security analyzer is configured, use it to analyze the action.
        If no security analyzer is configured, set the risk to HIGH (fail-safe approach).

        Args:
            action: The action to analyze for security risks.

        """
        if self.security_analyzer:
            try:
                if hasattr(action, "security_risk") and action.security_risk is not None:
                    logger.debug("Original security risk for %s: %s)", action, action.security_risk)
                if hasattr(action, "security_risk"):
                    action.security_risk = await self.security_analyzer.security_risk(action)
                    logger.debug(
                        "[Security Analyzer: %s] Override security risk for action %s: %s",
                        self.security_analyzer.__class__,
                        action,
                        action.security_risk,
                    )
            except Exception as e:
                logger.warning("Failed to analyze security risk for action %s: %s", action, e)
                if hasattr(action, "security_risk"):
                    action.security_risk = ActionSecurityRisk.UNKNOWN
        else:
            logger.debug("No security analyzer configured, setting UNKNOWN risk for action: %s", action)
            if hasattr(action, "security_risk"):
                action.security_risk = ActionSecurityRisk.UNKNOWN

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
                f"{system_message.content[:50]}..." if len(system_message.content) > 50 else system_message.content
            )
            logger.debug("System message: %s", preview)
            self.event_stream.add_event(system_message, EventSource.AGENT)

    async def close(self, set_stop_state: bool = True) -> None:
        """Closes the agent controller, canceling any ongoing tasks and unsubscribing from the event stream.

        Note that it's fairly important that this closes properly, otherwise the state is incomplete.
        """
        if set_stop_state:
            await self.set_agent_state_to(AgentState.STOPPED)
        self.state_tracker.close(self.event_stream)
        if not self.is_delegate:
            self.event_stream.unsubscribe(EventStreamSubscriber.AGENT_CONTROLLER, self.id)
        self._closed = True

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
        """React to an exception with enhanced recovery strategies.

        Note: LLM errors are already retried 6x with exponential backoff by RetryMixin.
        This method handles other recoverable errors with targeted recovery actions.

        Args:
            e: Exception to handle

        """
        # CRITICAL DEBUG: Log what exception we received
        self.log("error", f"_react_to_exception called with: {type(e).__name__}: {e}")
        self.log("error", f"Is APIConnectionError: {isinstance(e, APIConnectionError)}")
        
        # Set user-friendly error messages for LLM connection issues
        if isinstance(e, APIConnectionError):
            self.state.last_error = f"API Connection Error: Unable to connect to the AI service. {e}"
            self.log("info", f"Set APIConnectionError message: {self.state.last_error}")
        elif isinstance(e, AuthenticationError):
            self.state.last_error = f"Authentication Error: There's an issue with your API key configuration. {e}"
            self.log("info", f"Set AuthenticationError message: {self.state.last_error}")
        elif isinstance(e, RateLimitError):
            self.state.last_error = f"Rate Limit Error: You've exceeded the API rate limit. {e}"
            self.log("info", f"Set RateLimitError message: {self.state.last_error}")
        else:
            self.state.last_error = f"{type(e).__name__}: {e!s}"
            self.log("info", f"Set generic error message: {self.state.last_error}")

        from forge.controller.error_recovery import ErrorRecoveryStrategy

        error_type = ErrorRecoveryStrategy.classify_error(e)

        # Try recovery if applicable
        if await self._try_error_recovery(e, error_type):
            return

        # Handle non-recoverable error
        await self._handle_non_recoverable_error(e)

    async def _try_error_recovery(self, e: Exception, error_type) -> bool:
        """Attempt error recovery with retry logic.

        Args:
            e: Exception to recover from
            error_type: Classified error type

        Returns:
            True if recovery was attempted, False otherwise

        """
        from forge.controller.error_recovery import ErrorRecoveryStrategy

        # DO NOT attempt error recovery for authentication errors - they require user intervention
        if isinstance(e, AuthenticationError):
            self.log("info", "Skipping error recovery for AuthenticationError - requires user intervention")
            return False

        # Maximum retry limit to prevent infinite loops
        MAX_RETRIES = 3
        if self._retry_count >= MAX_RETRIES:
            self.log("warning", f"Maximum retry limit ({MAX_RETRIES}) reached for error: {type(e).__name__}")
            return False

        # For tool call errors, skip recovery to prevent infinite loops
        if error_type == ErrorRecoveryStrategy.ErrorType.TOOL_CALL_ERROR:
            logger.info("Skipping recovery for tool call error to prevent infinite loop")
            return False

        # Check autonomy-based retry
        if self.autonomy_controller.should_retry_on_error(e, self._retry_count):
            await self._execute_recovery_actions(error_type, e)
            return True

        # Check recoverable error type
        if error_type != ErrorRecoveryStrategy.ErrorType.UNKNOWN_ERROR:
            recovery_actions = ErrorRecoveryStrategy.get_recovery_actions(error_type, e)
            if recovery_actions:
                await self._execute_recovery_actions(error_type, e)
                return True

        return False

    async def _execute_recovery_actions(self, error_type, e: Exception) -> None:
        """Execute recovery actions and schedule retry.

        Args:
            error_type: Classified error type
            e: Original exception

        """
        from forge.controller.error_recovery import ErrorRecoveryStrategy

        logger.info(f"Auto-recovery for {error_type}: attempt {self._retry_count + 1}")
        recovery_actions = ErrorRecoveryStrategy.get_recovery_actions(error_type, e)

        for recovery_action in recovery_actions:
            self.event_stream.add_event(recovery_action, EventSource.AGENT)

        self._retry_count += 1

        # If no recovery actions were available (like for tool call errors), don't retry
        # This prevents infinite loops where tool call errors cause more tool call errors
        if not recovery_actions:
            logger.info(f"No recovery actions available for {error_type}, skipping retry to prevent infinite loop")
            return

        # Only retry if we haven't exceeded the maximum retry limit
        if self.state.agent_state == AgentState.RUNNING and self._retry_count <= 3:
            await asyncio.sleep(2**self._retry_count)  # Exponential backoff
            
            # For tool call errors, be more cautious about immediate retry
            if error_type == ErrorRecoveryStrategy.ErrorType.TOOL_CALL_ERROR:
                logger.info("Tool call error recovery: allowing time for user to review and potentially fix the issue")
                # Still retry, but with a longer delay for tool call errors
                await asyncio.sleep(3)
            
            self.step()
        else:
            if self._retry_count > 3:
                logger.warning(f"Reached maximum retry limit ({self._retry_count}), stopping recovery attempt")
            else:
                logger.info("Agent not in RUNNING state, skipping retry")

    async def _handle_non_recoverable_error(self, e: Exception) -> None:
        """Handle non-recoverable error.

        Args:
            e: Exception to handle

        """
        if self.circuit_breaker:
            self.circuit_breaker.record_error(e)

        if self.status_callback is not None:
            runtime_status = self._determine_runtime_status(e)
            if runtime_status == RuntimeStatus.ERROR_LLM_OUT_OF_CREDITS:
                await self._handle_rate_limit_error(e)
                return
            
            # Use the user-friendly error message that was set in _react_to_exception
            self.log("error", f"CALLING status_callback with: runtime_status={runtime_status}, error_message='{self.state.last_error}'")
            self.status_callback("error", runtime_status, self.state.last_error)

        await self.set_agent_state_to(AgentState.ERROR)

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
            self.state.last_error = RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION.value
            return RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION
        if isinstance(e, RateLimitError):
            self.state.last_error = RuntimeStatus.LLM_RETRY.value
            return RuntimeStatus.LLM_RETRY
        return RuntimeStatus.ERROR

    async def _handle_rate_limit_error(self, e: Exception) -> None:
        """Handle rate limit error with appropriate state transition."""
        if hasattr(e, "retry_attempt") and hasattr(e, "max_retries") and (e.retry_attempt >= e.max_retries):
            self.state.last_error = RuntimeStatus.AGENT_RATE_LIMITED_STOPPED_MESSAGE.value
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
                self.log("info", f"✅ PASSING THROUGH LLM EXCEPTION: {type(e).__name__}: {e}")
            else:
                reported = RuntimeError(
                    f"There was an unexpected error while running the agent: {
                        e.__class__.__name__}. You can refresh the page or ask the agent to try again.",
                )
                self.log("warning", f"❌ WRAPPING EXCEPTION: {type(e).__name__} -> RuntimeError")
            
            # CRITICAL DEBUG: Log what we're about to pass to _react_to_exception
            self.log("error", f"ABOUT TO CALL _react_to_exception with: {type(reported).__name__}: {reported}")
            await self._react_to_exception(reported)

    def _should_step_for_action(self, event: Action) -> bool:
        """Determine if agent should step for action events."""
        if isinstance(event, MessageAction):
            return self._should_step_for_message_action(event)
        if isinstance(event, AgentDelegateAction):
            return True
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
        if self.delegate is not None:
            return False

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
        if self.delegate is not None:
            delegate_state = self.delegate.get_agent_state()
            if delegate_state not in (AgentState.FINISHED, AgentState.ERROR, AgentState.REJECTED):
                asyncio.get_event_loop().run_until_complete(self.delegate._on_event(event))
            else:
                self.end_delegate()
            return
        asyncio.get_event_loop().run_until_complete(self._on_event(event))

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
            event_id = getattr(event, 'id', 'NO_ID')
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
        if self.should_step(event):
            self.log(
                "warning",
                f"🚀 STEPPING agent after event: {type(event).__name__} (id={getattr(event, 'id', 'NO_ID')})",
                extra={"msg_type": "STEPPING_AGENT"},
            )
            await self._step_with_exception_handling()
        elif isinstance(event, MessageAction) and event.source == EventSource.USER:
            self.log(
                "warning",
                f"Not stepping agent after user message. Current state: {
                    self.get_agent_state()}",
                extra={"msg_type": "NOT_STEPPING_AFTER_USER_MESSAGE"},
            )

    async def _handle_delegate_action(self, action: AgentDelegateAction) -> None:
        """Handle agent delegation action."""
        await self.start_delegate(action)
        assert self.delegate is not None
        if "task" in action.inputs:
            self.event_stream.add_event(MessageAction(content="TASK: " + action.inputs["task"]), EventSource.USER)
            await self.delegate.set_agent_state_to(AgentState.RUNNING)

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
        return hasattr(self, "task_validator") and self.task_validator and not getattr(action, "force_finish", False)

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

        logger.info("Validating task completion before finishing...")
        validation = await self.task_validator.validate_completion(task, self.state)

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
            feedback += "\nMissing items:\n" + "\n".join(f"- {item}" for item in validation.missing_items)

        if validation.suggestions:
            feedback += "\n\nSuggestions:\n" + "\n".join(f"- {sug}" for sug in validation.suggestions)

        feedback += "\n\nPlease continue working to complete the task."
        return feedback

    async def _handle_reject_action(self, action: AgentRejectAction) -> None:
        """Handle agent reject action."""
        self.state.outputs = action.outputs
        await self.set_agent_state_to(AgentState.REJECTED)

    async def _handle_action(self, action: Action) -> None:
        """Handles an Action from the agent or delegate."""
        if isinstance(action, ChangeAgentStateAction):
            await self.set_agent_state_to(action.agent_state)
        elif isinstance(action, MessageAction):
            await self._handle_message_action(action)
        elif isinstance(action, AgentDelegateAction):
            await self._handle_delegate_action(action)
            return
        elif isinstance(action, AgentFinishAction):
            await self._handle_finish_action(action)
        elif isinstance(action, AgentRejectAction):
            await self._handle_reject_action(action)

    def _prepare_observation_for_logging(self, observation: Observation) -> Observation:
        """Prepare observation for logging with content truncation if needed."""
        observation_to_print = copy.deepcopy(observation)
        if len(observation_to_print.content) > self.agent.llm.config.max_message_chars:
            observation_to_print.content = truncate_content(
                observation_to_print.content,
                self.agent.llm.config.max_message_chars,
            )
        return observation_to_print

    def _get_log_level(self) -> str:
        """Get appropriate log level based on environment."""
        return "info" if os.getenv("LOG_ALL_EVENTS") in ("true", "1") else "debug"

    async def _handle_pending_action_observation(self, observation: Observation) -> None:
        """Handle observation related to pending action."""
        if not (self._pending_action and self._pending_action.id == observation.cause):
            return

        if self.state.agent_state == AgentState.AWAITING_USER_CONFIRMATION:
            return

        self._pending_action = None

        if self.state.agent_state == AgentState.USER_CONFIRMED:
            await self.set_agent_state_to(AgentState.RUNNING)
        elif self.state.agent_state == AgentState.USER_REJECTED:
            await self.set_agent_state_to(AgentState.AWAITING_USER_INPUT)

    async def _handle_observation(self, observation: Observation) -> None:
        """Handles observation from the event stream.

        Args:
            observation (observation): The observation to handle.

        """
        observation_to_print = self._prepare_observation_for_logging(observation)
        log_level = self._get_log_level()
        self.log(log_level, str(observation_to_print), extra={"msg_type": "OBSERVATION"})

        await self._handle_pending_action_observation(observation)

    async def _handle_message_action(self, action: MessageAction) -> None:
        """Handles message actions from the event stream.

        Args:
            action (MessageAction): The message action to handle.

        """
        if action.source == EventSource.USER:
            log_level = "info" if os.getenv("LOG_ALL_EVENTS") in ("true", "1") else "debug"
            self.log(log_level, str(action), extra={"msg_type": "ACTION", "event_source": EventSource.USER})
            first_user_message = self._first_user_message()
            is_first_user_message = action.id == first_user_message.id if first_user_message else False
            recall_type = RecallType.WORKSPACE_CONTEXT if is_first_user_message else RecallType.KNOWLEDGE
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
        if self._pending_action and hasattr(self._pending_action, "tool_call_metadata"):
            found_observation = any(
                isinstance(event, Observation) and event.tool_call_metadata == self._pending_action.tool_call_metadata
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

    def _handle_state_reset(self, new_state: AgentState) -> None:
        """Reset agent if entering stopped or error state."""
        if new_state in (AgentState.STOPPED, AgentState.ERROR):
            self._reset()

    def _handle_error_recovery(self, old_state: AgentState, new_state: AgentState) -> None:
        """Handle recovery from error state."""
        if old_state == AgentState.ERROR and new_state == AgentState.RUNNING:
            self.state_tracker.maybe_increase_control_flags_limits(self.headless_mode)

    def _handle_pending_action_confirmation(self, new_state: AgentState) -> None:
        """Handle pending action confirmation or rejection."""
        if self._pending_action is None or new_state not in (AgentState.USER_CONFIRMED, AgentState.USER_REJECTED):
            return

        if hasattr(self._pending_action, "thought"):
            self._pending_action.thought = ""

        confirmation_state = (
            ActionConfirmationStatus.CONFIRMED
            if new_state == AgentState.USER_CONFIRMED
            else ActionConfirmationStatus.REJECTED
        )
        self._pending_action.confirmation_state = confirmation_state
        self._pending_action._id = None
        self.event_stream.add_event(self._pending_action, EventSource.AGENT)

    async def set_agent_state_to(self, new_state: AgentState) -> None:
        """Updates the agent's state and handles side effects. Can emit events to the event stream.

        Args:
            new_state (AgentState): The new state to set for the agent.

        """
        self.log("info", f"Setting agent({self.agent.name}) state from {self.state.agent_state} to {new_state}")

        if new_state == self.state.agent_state:
            return

        old_state = self.state.agent_state
        self.state.agent_state = new_state

        self._handle_state_reset(new_state)
        self._handle_error_recovery(old_state, new_state)
        self._handle_pending_action_confirmation(new_state)

        reason = self.state.last_error if new_state == AgentState.ERROR else ""
        self.event_stream.add_event(
            AgentStateChangedObservation("", self.state.agent_state, reason),
            EventSource.ENVIRONMENT,
        )
        self.save_state()

    def get_agent_state(self) -> AgentState:
        """Returns the current state of the agent.

        Returns:
            AgentState: The current state of the agent.

        """
        return self.state.agent_state

    async def start_delegate(self, action: AgentDelegateAction) -> None:
        """Start a delegate agent to handle a subtask.

        Forge is a multi-agentic system. A `task` is a conversation between
        Forge (the whole system) and the user, which might involve one or more inputs
        from the user. It starts with an initial input (typically a task statement) from
        the user, and ends with either an `AgentFinishAction` initiated by the agent, a
        stop initiated by the user, or an error.

        A `subtask` is a conversation between an agent and the user, or another agent. If a `task`
        is conducted by a single agent, then it's also a `subtask`. Otherwise, a `task` consists of
        multiple `subtasks`, each executed by one agent.

        Args:
            action (AgentDelegateAction): The action containing information about the delegate agent to start.

        """
        agent_cls: type[Agent] = Agent.get_cls(action.agent)
        agent_config = self.agent_configs.get(action.agent, self.agent.config)
        delegate_agent = agent_cls(config=agent_config, llm_registry=self.agent.llm_registry)
        state = State(
            session_id=self.id.removesuffix("-delegate"),
            user_id=self.user_id,
            inputs=action.inputs or {},
            iteration_flag=self.state.iteration_flag,
            budget_flag=self.state.budget_flag,
            delegate_level=self.state.delegate_level + 1,
            metrics=self.state.metrics,
            start_id=self.event_stream.get_latest_event_id() + 1,
            parent_metrics_snapshot=self.state_tracker.get_metrics_snapshot(),
            parent_iteration=self.state.iteration_flag.current_value,
        )
        self.log("debug", f"start delegate, creating agent {delegate_agent.name}")
        self.delegate = AgentController(
            sid=f"{
                self.id}-delegate",
            file_store=self.file_store,
            user_id=self.user_id,
            agent=delegate_agent,
            event_stream=self.event_stream,
            conversation_stats=self.conversation_stats,
            iteration_delta=self._initial_max_iterations,
            budget_per_task_delta=self._initial_max_budget_per_task,
            agent_to_llm_config=self.agent_to_llm_config,
            agent_configs=self.agent_configs,
            initial_state=state,
            is_delegate=True,
            headless_mode=self.headless_mode,
            security_analyzer=self.security_analyzer,
        )

    def _get_delegate_completion_message(
        self,
        delegate_state: AgentState,
        delegate_outputs: dict,
        agent_name: str,
    ) -> str:
        """Generate completion message based on delegate state."""
        if delegate_state in (AgentState.FINISHED, AgentState.REJECTED):
            display_outputs = {k: v for k, v in delegate_outputs.items() if k != "metrics"}
            formatted_output = ", ".join((f"{key}: {value}" for key, value in display_outputs.items()))
            content = f"{agent_name} finishes task with {formatted_output}"
        else:
            content = f"{agent_name} encountered an error during execution."
        return f"Delegated agent finished with result:\n\n{content}"

    def _attach_tool_call_metadata_to_observation(self, obs: AgentDelegateObservation) -> None:
        """Attach tool call metadata from delegate action to observation."""
        for event in reversed(self.state.history):
            if isinstance(event, AgentDelegateAction):
                obs.tool_call_metadata = event.tool_call_metadata
                break

    def end_delegate(self) -> None:
        """Ends the currently active delegate (e.g., if it is finished or errored).

        so that this controller can resume normal operation.
        """
        if self.delegate is None:
            return

        delegate_state = self.delegate.get_agent_state()
        self.state.iteration_flag.current_value = self.delegate.state.iteration_flag.current_value
        delegate_metrics = self.state.get_local_metrics()
        logger.info("Local metrics for delegate: %s", delegate_metrics)
        asyncio.get_event_loop().run_until_complete(self.delegate.close(set_stop_state=False))

        delegate_outputs = self.delegate.state.outputs if self.delegate.state else {}
        content = self._get_delegate_completion_message(delegate_state, delegate_outputs, self.delegate.agent.name)

        obs = AgentDelegateObservation(outputs=delegate_outputs, content=content)
        self._attach_tool_call_metadata_to_observation(obs)
        self.event_stream.add_event(obs, EventSource.AGENT)
        self.delegate = None

    def _check_step_prerequisites(self) -> bool:
        """Check if agent can step based on state and pending actions."""
        if self.get_agent_state() != AgentState.RUNNING:
            self.log(
                "debug",
                f"Agent not stepping because state is {
                    self.get_agent_state()} (not RUNNING)",
                extra={"msg_type": "STEP_BLOCKED_STATE"},
            )
            return False
        if self._pending_action and (not isinstance(self._pending_action, RecallAction)):
            action_id = getattr(self._pending_action, "id", "unknown")
            action_type = type(self._pending_action).__name__
            self.log(
                "debug",
                f"Agent not stepping because of pending action: {action_type} (id={action_id})",
                extra={"msg_type": "STEP_BLOCKED_PENDING_ACTION"},
            )
            return False
        return True

    def _log_step_info(self) -> None:
        """Log step information for debugging."""
        self.log(
            "debug",
            f"LEVEL {
                self.state.delegate_level} LOCAL STEP {
                self.state.get_local_step()} GLOBAL STEP {
                self.state.iteration_flag.current_value}",
            extra={"msg_type": "STEP"},
        )

    def _check_stuck_condition(self) -> bool:
        """Check if agent is stuck and handle it."""
        return bool(self._is_stuck())

    def _run_control_flags(self) -> None:
        """Run control flags and handle exceptions with graceful shutdown."""
        try:
            logger.debug("AGENT_CTRL: before run_control_flags, iteration=%s", self.state.iteration_flag.current_value)
            self.state_tracker.run_control_flags()
            logger.debug("AGENT_CTRL: after run_control_flags, iteration=%s", self.state.iteration_flag.current_value)
        except Exception as e:
            # Check if this is a limit error (max iterations or budget exceeded)
            error_str = str(e).lower()
            is_limit_error = (
                "limit" in error_str or "maximum" in error_str or "budget" in error_str or "iteration" in error_str
            )

            if is_limit_error:
                logger.warning(f"Control flag limit hit: {type(e).__name__}")
                # Trigger graceful shutdown instead of immediate stop
                asyncio.create_task(self._graceful_shutdown(reason=str(e)))
            else:
                logger.warning("Control flag error (non-limit)")

            raise

    async def _graceful_shutdown(self, reason: str) -> None:
        """Give agent one final turn to save work and summarize progress.

        This is called when max_iterations or budget limits are hit, allowing
        the agent to create a final summary and save important work.

        Args:
            reason: Reason for shutdown (e.g., "Max iterations reached")

        """
        from forge.events.action import MessageAction

        logger.info(f"Initiating graceful shutdown: {reason}")

        # Set flag to indicate we're in shutdown mode
        if not hasattr(self.state, "graceful_shutdown_mode"):
            self.state.graceful_shutdown_mode = True

        # Create final summary prompt for the agent
        summary_msg = MessageAction(
            content=(
                f"SYSTEM NOTICE: {reason}\n\n"
                f"You have ONE FINAL TURN to:\n"
                f"1. Save all important work and progress\n"
                f"2. Create a summary of what you accomplished\n"
                f"3. List any remaining work or next steps\n"
                f"4. Use the finish tool with your final summary\n\n"
                f"Please be concise and focus on preserving critical information."
            ),
            source=EventSource.ENVIRONMENT,
        )

        # Add the message to event stream
        self.event_stream.add_event(summary_msg, EventSource.ENVIRONMENT)

        # Give agent ONE final step to respond
        try:
            # Temporarily allow one more iteration
            if hasattr(self.state.iteration_flag, "current_value"):
                original_max = self.state.iteration_flag.max_value
                self.state.iteration_flag.max_value = self.state.iteration_flag.current_value + 1

            await self._step()

            # Wait a moment for agent to finish
            await asyncio.sleep(2)

            # Restore original max
            if hasattr(self.state.iteration_flag, "max_value"):
                self.state.iteration_flag.max_value = original_max

        except Exception as e:
            logger.error(f"Error during graceful shutdown step: {e}")

        # If agent didn't finish on its own, force partial completion
        if self.state.agent_state not in [AgentState.FINISHED, AgentState.ERROR]:
            await self._force_partial_completion(reason)

    async def _force_partial_completion(self, reason: str) -> None:
        """Force partial completion when agent doesn't finish gracefully.

        Args:
            reason: Reason for forced completion

        """
        from forge.events.action import AgentFinishAction

        logger.info(f"Forcing partial completion: {reason}")

        # Create a partial completion finish action
        finish_action = AgentFinishAction(
            outputs={
                "status": "partial",
                "reason": reason,
                "message": (
                    f"Task partially completed. Stopped due to: {reason}\n\n"
                    f"Progress: {self.state.iteration_flag.current_value} iterations completed.\n"
                    f"Please review the conversation history for completed work."
                ),
            },
            final_thought=f"Task stopped: {reason}",
            force_finish=True,  # Bypass validation
        )

        # Set force_finish attribute to bypass task validation
        finish_action.force_finish = True

        # Handle the finish action
        await self._handle_finish_action(finish_action)

    def _get_action_from_replay_or_agent(self) -> Action:
        """Get action from replay manager or agent step."""
        if self._replay_manager.should_replay():
            return self._replay_manager.step()
        action = self.agent.step(self.state)
        if action is None:
            msg = "No action was returned"
            raise LLMNoActionError(msg)
        if not isinstance(action, Action):
            action = NullAction()
        action.source = EventSource.AGENT
        return action

    def _is_context_window_error(self, error_str: str, e: Exception) -> bool:
        """Check if the error is a context window error."""
        return (
            "contextwindowexceedederror" not in error_str
            and "prompt is too long" not in error_str
            and ("input length and `max_tokens` exceed context limit" not in error_str)
            and ("please reduce the length of either one" not in error_str)
            and ("the request exceeds the available context size" not in error_str)
            and ("context length exceeded" not in error_str)
            and ("sambanovaexception" not in error_str or "maximum context length" not in error_str)
            and (not isinstance(e, ContextWindowExceededError))
        )

    def _is_action_requiring_confirmation(self, action: Action) -> bool:
        """Check if action requires confirmation based on type."""
        return (
            type(action) is CmdRunAction
            or type(action) is IPythonRunCellAction
            or type(action) is BrowseInteractiveAction
            or (type(action) is FileEditAction)
            or (type(action) is FileReadAction)
        )

    def _determine_security_risk(self, action: Action) -> tuple[bool, bool]:
        """Determine security risk level for action."""
        security_risk = getattr(action, "security_risk", ActionSecurityRisk.UNKNOWN)
        is_high_security_risk = security_risk == ActionSecurityRisk.HIGH
        is_ask_for_every_action = security_risk == ActionSecurityRisk.UNKNOWN and (not self.security_analyzer)
        return (is_high_security_risk, is_ask_for_every_action)

    def _set_confirmation_state(
        self,
        action: Action,
        is_high_security_risk: bool,
        is_ask_for_every_action: bool,
    ) -> None:
        """Set confirmation state for action based on security risk and autonomy level."""
        # Check autonomy controller first
        if self.autonomy_controller.should_request_confirmation(action):
            # Autonomy controller says we should confirm
            if self.agent.config.cli_mode:
                action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
            elif (is_high_security_risk or is_ask_for_every_action) and self.confirmation_mode:
                logger.debug("[non-CLI mode] Detected HIGH security risk in action: %s. Ask for confirmation", action)
                action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION
        else:
            # Autonomy controller says proceed without confirmation
            logger.debug("[Autonomous mode] Executing action without confirmation: %s", type(action).__name__)

    async def _step(self) -> None:
        """Executes a single step of the parent or delegate agent. Detects stuck agents and limits on the number of iterations and the task budget."""
        if not self._check_step_prerequisites():
            return

        self._log_step_info()
        self.state_tracker.sync_budget_flag_with_metrics()

        # NEW: Check circuit breaker before proceeding
        if self.circuit_breaker:
            cb_result = self.circuit_breaker.check(self.state)
            if cb_result.tripped:
                logger.error(f"Circuit breaker tripped: {cb_result.reason}")

                from forge.events.observation import ErrorObservation

                # Send error observation with recommendation
                error_obs = ErrorObservation(
                    content=(
                        f"CIRCUIT BREAKER TRIPPED: {cb_result.reason}\n\n"
                        f"Action: {cb_result.action.upper()}\n\n"
                        f"{cb_result.recommendation}"
                    ),
                    error_id="CIRCUIT_BREAKER_TRIPPED",
                )
                self.event_stream.add_event(error_obs, EventSource.ENVIRONMENT)

                # Pause or stop based on recommendation
                if cb_result.action == "stop":
                    await self.set_agent_state_to(AgentState.STOPPED)
                else:
                    await self.set_agent_state_to(AgentState.PAUSED)

                return

        if self._check_stuck_condition():
            # Record stuck detection in circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_stuck_detection()

            await self._react_to_exception(AgentStuckInLoopError("Agent got stuck in a loop"))
            return

        if not await self._run_control_flags_safely():
            return

        action = await self._get_action_safely()
        if action is None:
            return

        # Reset retry count on successful action execution
        # This prevents getting stuck if a previous error has been resolved
        if self._retry_count > 0:
            logger.debug(f"Resetting retry count from {self._retry_count} to 0 after successful execution")
            self._retry_count = 0

        await self._process_action(action)

    async def _run_control_flags_safely(self) -> bool:
        """Run control flags with exception handling."""
        try:
            self._run_control_flags()
            return True
        except Exception as e:
            await self._react_to_exception(e)
            return False

    async def _get_action_safely(self) -> Action | None:
        """Get action with proper exception handling."""
        try:
            return self._get_action_from_replay_or_agent()
        except (
            LLMMalformedActionError,
            LLMNoActionError,
            LLMResponseError,
            FunctionCallValidationError,
            FunctionCallNotExistsError,
        ) as e:
            self.event_stream.add_event(ErrorObservation(content=str(e)), EventSource.AGENT)
            return None
        except (ContextWindowExceededError, BadRequestError, OpenAIError) as e:
            return await self._handle_context_window_error(e)
        except (
            APIConnectionError,
            AuthenticationError,
            RateLimitError,
            ServiceUnavailableError,
            APIError,
            InternalServerError,
            Timeout,
        ) as e:
            # Re-raise LLM connection errors so they can be properly handled by _step_with_exception_handling
            raise

    async def _handle_context_window_error(self, e: Exception) -> Action | None:
        """Handle context window exceeded error."""
        error_str = str(e).lower()
        if self._is_context_window_error(error_str, e):
            raise e
        if not self.agent.config.enable_history_truncation:
            raise LLMContextWindowExceedError from e
        self.event_stream.add_event(CondensationRequestAction(), EventSource.AGENT)
        return None

    async def _process_action(self, action: Action) -> None:
        """Process the action with confirmation and security checks."""
        if action.runnable:
            await self._handle_runnable_action(action)

        if not isinstance(action, NullAction):
            await self._finalize_action(action)

    async def _handle_runnable_action(self, action: Action) -> None:
        """Handle runnable action with security analysis."""
        # NEW: Mandatory safety validation (even in full autonomy)
        if self.safety_validator:
            from forge.controller.safety_validator import ExecutionContext
            from forge.events.observation import ErrorObservation

            context = ExecutionContext(
                session_id=self.id,
                iteration=self.state.iteration_flag.current_value,
                agent_state=self.state.agent_state.value,
                recent_errors=[self.state.last_error] if self.state.last_error else [],
                is_autonomous=(self.autonomy_controller.autonomy_level == "full"),
            )

            validation = await self.safety_validator.validate(action, context)

            if not validation.allowed:
                # Action blocked by safety validator
                logger.error(f"Action blocked by SafetyValidator: {validation.blocked_reason}")

                # Create error observation
                error_obs = ErrorObservation(
                    content=f"ACTION BLOCKED FOR SAFETY:\n{validation.blocked_reason}",
                    error_id="SAFETY_VALIDATOR_BLOCKED",
                )
                error_obs.cause = getattr(action, "id", None)
                self.event_stream.add_event(error_obs, EventSource.ENVIRONMENT)

                # Clear pending action and return (don't execute)
                self._pending_action = None
                return

        # Existing confirmation logic (for non-critical actions)
        if self.state.confirmation_mode and self._is_action_requiring_confirmation(action):
            await self._handle_security_analyzer(action)
            is_high_security_risk, is_ask_for_every_action = self._determine_security_risk(action)
            self._set_confirmation_state(action, is_high_security_risk, is_ask_for_every_action)
        self._pending_action = action

    async def _finalize_action(self, action: Action) -> None:
        """Finalize action processing."""
        if (
            hasattr(action, "confirmation_state")
            and action.confirmation_state == ActionConfirmationStatus.AWAITING_CONFIRMATION
        ):
            await self.set_agent_state_to(AgentState.AWAITING_USER_CONFIRMATION)

        self._prepare_metrics_for_frontend(action)
        self.event_stream.add_event(action, action.source or EventSource.AGENT)

        # Record successful action in circuit breaker
        if self.circuit_breaker:
            self.circuit_breaker.record_success()

            # Record high-risk actions
            if hasattr(action, "security_risk"):
                self.circuit_breaker.record_high_risk_action(action.security_risk)

        log_level = "info" if LOG_ALL_EVENTS else "debug"
        self.log(log_level, str(action), extra={"msg_type": "ACTION"})

    @property
    def _pending_action(self) -> Action | None:
        """Get the current pending action with time tracking and auto-clear timeout.

        Returns:
            Action | None: The current pending action, or None if there isn't one.

        """
        if self._pending_action_info is None:
            return None

        action, timestamp = self._pending_action_info
        current_time = time.time()
        elapsed_time = current_time - timestamp

        # NEW: Auto-clear after timeout
        if elapsed_time > self.PENDING_ACTION_TIMEOUT:
            from forge.events.observation import ErrorObservation

            action_id = getattr(action, "id", "unknown")
            action_type = type(action).__name__

            self.log(
                "warning",
                f"Pending action timed out after {elapsed_time:.1f}s, auto-clearing: {action_type} (id={action_id})",
                extra={"msg_type": "PENDING_ACTION_TIMEOUT_CLEARED"},
            )

            # Create timeout observation
            timeout_obs = ErrorObservation(
                content=f"Pending action timed out after {elapsed_time:.1f}s: {action_type}",
                error_id="PENDING_ACTION_TIMEOUT",
            )
            timeout_obs.cause = action_id if action_id != "unknown" else None
            self.event_stream.add_event(timeout_obs, EventSource.ENVIRONMENT)

            # Clear pending action
            self._pending_action_info = None
            return None

        # Log warnings at intervals (every 30 seconds after first minute)
        if elapsed_time > 60.0 and int(elapsed_time) % 30 == 0:
            action_id = getattr(action, "id", "unknown")
            action_type = type(action).__name__
            self.log(
                "info",
                f"Pending action active for {elapsed_time:.1f}s: {action_type} (id={action_id})",
                extra={"msg_type": "PENDING_ACTION_TIMEOUT"},
            )

        return action

    @_pending_action.setter
    def _pending_action(self, action: Action | None) -> None:
        """Set or clear the pending action with timestamp and logging.

        Args:
            action: The action to set as pending, or None to clear.

        """
        if action is None:
            if self._pending_action_info is not None:
                prev_action, timestamp = self._pending_action_info
                action_id = getattr(prev_action, "id", "unknown")
                action_type = type(prev_action).__name__
                elapsed_time = time.time() - timestamp
                self.log(
                    "debug",
                    f"Cleared pending action after {
                        elapsed_time:.2f}s: {action_type} (id={action_id})",
                    extra={"msg_type": "PENDING_ACTION_CLEARED"},
                )
            self._pending_action_info = None
        else:
            action_id = getattr(action, "id", "unknown")
            action_type = type(action).__name__
            self.log(
                "debug",
                f"Set pending action: {action_type} (id={action_id})",
                extra={"msg_type": "PENDING_ACTION_SET"},
            )
            self._pending_action_info = (action, time.time())

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
        """Checks if the agent or its delegate is stuck in a loop.

        Returns:
            bool: True if the agent is stuck, False otherwise.

        """
        if self.delegate and self.delegate._is_stuck():
            return True
        return self._stuck_detector.is_stuck(self.headless_mode)

    def _prepare_metrics_for_frontend(self, action: Action) -> None:
        """Create a minimal metrics object for frontend display and log it.

        To avoid performance issues with long conversations, we only keep:
        - accumulated_cost: The current total cost
        - accumulated_token_usage: Accumulated token statistics across all API calls
        - max_budget_per_task: The maximum budget allowed for the task

        This includes metrics from both the agent's LLM and the condenser's LLM if it exists.

        Args:
            action: The action to attach metrics to

        """
        metrics = self.conversation_stats.get_combined_metrics()
        clean_metrics = Metrics()
        clean_metrics.accumulated_cost = metrics.accumulated_cost
        clean_metrics._accumulated_token_usage = copy.deepcopy(metrics.accumulated_token_usage)
        if self.state.budget_flag:
            clean_metrics.max_budget_per_task = self.state.budget_flag.max_value
        action.llm_metrics = clean_metrics
        latest_usage = None
        if self.state.metrics.token_usages:
            latest_usage = self.state.metrics.token_usages[-1]
        accumulated_usage = self.state.metrics.accumulated_token_usage
        self.log(
            "debug", f"Action metrics - accumulated_cost: {
                metrics.accumulated_cost}, max_budget: {
                metrics.max_budget_per_task}, latest tokens (prompt/completion/cache_read/cache_write): {
                (
                    latest_usage.prompt_tokens if latest_usage else 0)}/{
                        (
                            latest_usage.completion_tokens if latest_usage else 0)}/{
                                (
                                    latest_usage.cache_read_tokens if latest_usage else 0)}/{
                                        (
                                            latest_usage.cache_write_tokens if latest_usage else 0)}, accumulated tokens (prompt/completion): {
                                                accumulated_usage.prompt_tokens}/{
                                                    accumulated_usage.completion_tokens}", extra={
                                                        "msg_type": "METRICS"}, )

    def __repr__(self) -> str:
        """Get string representation of controller with key state information.
        
        Returns:
            String representation including ID, agent state, and pending action info

        """
        pending_action_info = "<none>"
        if hasattr(self, "_pending_action_info") and self._pending_action_info is not None:
            action, timestamp = self._pending_action_info
            action_id = getattr(action, "id", "unknown")
            action_type = type(action).__name__
            elapsed_time = time.time() - timestamp
            pending_action_info = f"{action_type}(id={action_id}, elapsed={elapsed_time:.2f}s)"
        return f"AgentController(id={
            getattr(
                self,
                'id',
                '<uninitialized>')}, agent={
            getattr(
                self,
                'agent',
                '<uninitialized>')!r}, event_stream={
                    getattr(
                        self,
                        'event_stream',
                        '<uninitialized>')!r}, state={
                            getattr(
                                self,
                                'state',
                                '<uninitialized>')!r}, delegate={
                                    getattr(
                                        self,
                                        'delegate',
                                        '<uninitialized>')!r}, _pending_action={pending_action_info})"

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

    def _first_user_message(self, events: list[Event] | None = None) -> MessageAction | None:
        """Get the first user message for this agent.

        For regular agents, this is the first user message from the beginning (start_id=0).
        For delegate agents, this is the first user message after the delegate's start_id.

        Args:
            events: Optional list of events to search through. If None, uses the event stream.

        Returns:
            MessageAction | None: The first user message, or None if no user message found

        """
        if events is not None:
            return next((e for e in events if isinstance(e, MessageAction) and e.source == EventSource.USER), None)
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
