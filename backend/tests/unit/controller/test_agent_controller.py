import asyncio
import copy
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from pydantic import SecretStr
from forge.llm.exceptions import (
    BadRequestError,
    ContentPolicyViolationError,
    ContextWindowExceededError,
)
from forge.controller.agent import Agent
from forge.controller.agent_controller import AgentController
from forge.controller.state.control_flags import BudgetControlFlag
from forge.controller.state.state import State
from forge.core.config import ForgeConfig
from forge.core.config.agent_config import AgentConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.main import run_controller
from forge.core.schemas import AgentState
from forge.events import Event, EventSource, EventStream, EventStreamSubscriber
from forge.events.action import ChangeAgentStateAction, CmdRunAction, MessageAction
from forge.events.action.agent import CondensationAction, RecallAction
from forge.events.action.message import SystemMessageAction
from forge.events.event import RecallType
from forge.events.observation import AgentStateChangedObservation, ErrorObservation
from forge.events.observation.agent import RecallObservation
from forge.events.observation.empty import NullObservation
from forge.events.serialization import event_to_dict
from forge.llm import LLM
from forge.llm.llm_registry import LLMRegistry, RegistryEvent
from forge.llm.metrics import Metrics, TokenUsage
from forge.memory.condenser.condenser import Condensation
from forge.memory.condenser.impl.conversation_window_condenser import (
    ConversationWindowCondenser,
)
from forge.memory.memory import Memory
from forge.memory.view import View
from forge.runtime.base import Runtime
from forge.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)
from forge.runtime.runtime_status import RuntimeStatus
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.memory import InMemoryFileStore


@pytest.fixture
def temp_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("test_event_stream"))


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_agent_with_stats():
    """Create a mock agent with properly connected LLM registry and conversation stats."""
    import uuid

    config = ForgeConfig()
    llm_registry = LLMRegistry(config=config)
    file_store = InMemoryFileStore({})
    conversation_id = f"test-conversation-{uuid.uuid4()}"
    conversation_stats = ConversationStats(
        file_store=file_store, conversation_id=conversation_id, user_id="test-user"
    )
    llm_registry.subscribe(conversation_stats.register_llm)
    agent = MagicMock(spec=Agent)
    agent_config = MagicMock(spec=AgentConfig)
    llm_config = LLMConfig(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )
    agent_config.disabled_microagents = []
    agent_config.enable_mcp = True
    llm_registry.service_to_llm.clear()
    mock_llm = llm_registry.get_llm("agent_llm", llm_config)
    agent.llm = mock_llm
    agent.name = "test-agent"
    agent.sandbox_plugins = []
    agent.config = agent_config
    agent.prompt_manager = MagicMock()
    system_message = SystemMessageAction(
        content="Test system message", tools=["test_tool"]
    )
    system_message._source = EventSource.AGENT
    system_message._id = -1
    agent.get_system_message.return_value = system_message
    return (agent, conversation_stats, llm_registry)


@pytest.fixture
def mock_event_stream():
    mock = MagicMock(
        spec=EventStream,
        event_stream=EventStream(sid="test", file_store=InMemoryFileStore({})),
    )
    mock.get_latest_event_id.return_value = 0
    return mock


@pytest.fixture
def test_event_stream():
    return EventStream(sid="test", file_store=InMemoryFileStore({}))


@pytest.fixture
def mock_runtime() -> Runtime:
    from forge.runtime.impl.action_execution.action_execution_client import (
        ActionExecutionClient,
    )

    runtime = MagicMock(spec=ActionExecutionClient, event_stream=test_event_stream)
    return runtime


@pytest.fixture
def mock_memory() -> Memory:
    memory = MagicMock(spec=Memory, event_stream=test_event_stream)
    memory.get_microagent_mcp_tools.return_value = []
    return memory


@pytest.fixture
def mock_status_callback():
    return AsyncMock()


async def send_event_to_controller(controller, event):
    await controller._on_event(event)
    await asyncio.sleep(0.1)
    controller._pending_action = None


@pytest.mark.asyncio
async def test_set_agent_state(mock_agent_with_stats, mock_event_stream):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    await controller.set_agent_state_to(AgentState.RUNNING)
    assert controller.get_agent_state() == AgentState.RUNNING
    await controller.set_agent_state_to(AgentState.PAUSED)
    assert controller.get_agent_state() == AgentState.PAUSED
    await controller.close()


@pytest.mark.asyncio
async def test_on_event_message_action(mock_agent_with_stats, mock_event_stream):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    controller.state.agent_state = AgentState.RUNNING
    message_action = MessageAction(content="Test message")
    await send_event_to_controller(controller, message_action)
    assert controller.get_agent_state() == AgentState.RUNNING
    await controller.close()


@pytest.mark.asyncio
async def test_on_event_change_agent_state_action(
    mock_agent_with_stats, mock_event_stream
):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    controller.state.agent_state = AgentState.RUNNING
    change_state_action = ChangeAgentStateAction(agent_state=AgentState.PAUSED)
    await send_event_to_controller(controller, change_state_action)
    assert controller.get_agent_state() == AgentState.PAUSED
    await controller.close()


@pytest.mark.asyncio
async def test_react_to_exception(
    mock_agent_with_stats, mock_event_stream, mock_status_callback
):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        status_callback=mock_status_callback,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    error_message = "Test error"
    await controller._react_to_exception(RuntimeError(error_message))
    controller.status_callback.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_react_to_content_policy_violation(
    mock_agent_with_stats, mock_event_stream, mock_status_callback
):
    """Test that the controller properly handles content policy violations from the LLM."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        status_callback=mock_status_callback,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    controller.state.agent_state = AgentState.RUNNING
    error = ContentPolicyViolationError(
        message="Output blocked by content filtering policy",
        model="gpt-4",
        llm_provider="openai",
    )
    await controller._react_to_exception(error)
    mock_status_callback.assert_called_once_with(
        "error",
        RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION,
        RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION.value,
    )
    assert (
        controller.state.last_error
        == RuntimeStatus.ERROR_LLM_CONTENT_POLICY_VIOLATION.value
    )
    assert controller.state.agent_state == AgentState.ERROR
    await controller.close()


@pytest.mark.asyncio
async def test_run_controller_with_fatal_error(
    test_event_stream, mock_memory, mock_agent_with_stats
):
    config = ForgeConfig()
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats

    def agent_step_fn(state):
        print(f"agent_step_fn received state: {state}")
        return CmdRunAction(command="ls")

    mock_agent.step = agent_step_fn
    runtime = MagicMock(spec=ActionExecutionClient)

    def on_event(event: Event):
        if isinstance(event, CmdRunAction):
            error_obs = ErrorObservation("You messed around with Jim")
            error_obs._cause = event.id
            test_event_stream.add_event(error_obs, EventSource.USER)

    test_event_stream.subscribe(EventStreamSubscriber.RUNTIME, on_event, str(uuid4()))
    runtime.event_stream = test_event_stream
    runtime.config = copy.deepcopy(config)

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            test_event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4())
    )
    with patch("forge.core.main.create_agent", return_value=mock_agent):
        state = await run_controller(
            config=config,
            initial_user_action=MessageAction(content="Test message"),
            runtime=runtime,
            sid="test",
            fake_user_response_fn=lambda _: "repeat",
            memory=mock_memory,
        )
    print(f"state: {state}")
    events = list(test_event_stream.get_events())
    print(f"event_stream: {events}")
    error_observations = test_event_stream.get_matching_events(
        reverse=True, limit=1, event_types=AgentStateChangedObservation
    )
    assert len(error_observations) == 1
    error_observation = error_observations[0]
    assert state.iteration_flag.current_value == 3
    assert state.agent_state == AgentState.ERROR
    assert state.last_error == "AgentStuckInLoopError: Agent got stuck in a loop"
    assert (
        error_observation.reason == "AgentStuckInLoopError: Agent got stuck in a loop"
    )
    assert len(events) == 12


@pytest.mark.asyncio
async def test_run_controller_stop_with_stuck(
    test_event_stream, mock_memory, mock_agent_with_stats
):
    """Test controller stops when agent gets stuck in a loop."""
    # Setup test configuration
    config = ForgeConfig()
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats

    # Configure mock agent and runtime
    runtime = _setup_mock_runtime(test_event_stream, config)
    _configure_mock_agent(mock_agent)

    # Setup event handlers
    _setup_runtime_event_handler(test_event_stream)
    _setup_memory_event_handler(test_event_stream)

    # Run controller and verify results
    with patch("forge.core.main.create_agent", return_value=mock_agent):
        state = await run_controller(
            config=config,
            initial_user_action=MessageAction(content="Test message"),
            runtime=runtime,
            sid="test",
            fake_user_response_fn=lambda _: "repeat",
            memory=mock_memory,
        )

    # Verify controller state and events
    _verify_controller_state(state)
    _verify_events_structure(test_event_stream, state)


def _setup_mock_runtime(test_event_stream, config):
    """Setup mock runtime for testing."""
    runtime = MagicMock(spec=ActionExecutionClient)
    runtime.event_stream = test_event_stream
    runtime.config = copy.deepcopy(config)
    return runtime


def _configure_mock_agent(mock_agent):
    """Configure mock agent for testing."""

    def agent_step_fn(state):
        print(f"agent_step_fn received state: {state}")
        return CmdRunAction(command="ls")

    mock_agent.step = agent_step_fn


def _setup_runtime_event_handler(test_event_stream):
    """Setup runtime event handler to simulate errors."""

    def on_event(event: Event):
        if isinstance(event, CmdRunAction):
            non_fatal_error_obs = ErrorObservation(
                "Non fatal error here to trigger loop"
            )
            non_fatal_error_obs._cause = event.id
            test_event_stream.add_event(non_fatal_error_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(EventStreamSubscriber.RUNTIME, on_event, str(uuid4()))


def _setup_memory_event_handler(test_event_stream):
    """Setup memory event handler to simulate microagent responses."""

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            test_event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4())
    )


def _verify_controller_state(state):
    """Verify the controller state after execution."""
    assert state.iteration_flag.current_value in {3, 4}
    assert state.agent_state == AgentState.ERROR
    assert state.last_error == "AgentStuckInLoopError: Agent got stuck in a loop"


def _verify_events_structure(test_event_stream, state):
    """Verify the structure of events generated during execution."""
    events = list(test_event_stream.get_events())
    print(f"state: {state}")
    for i, event in enumerate(events):
        print(f"event {i}: {event_to_dict(event)}")

    # Verify total event count
    assert len(events) == 12

    # Verify action-observation pairs
    _verify_action_observation_pairs(events)

    # Verify final event
    _verify_final_event(events)


def _verify_action_observation_pairs(events):
    """Verify that each action has a corresponding error observation."""
    actions = [e for e in events if isinstance(e, CmdRunAction)]
    assert actions

    pairs = []
    for action in actions:
        matched = _find_matching_error_observation(action, events)
        assert matched is not None, (
            f"No ErrorObservation found for action id={action.id}"
        )
        pairs.append((action, matched))

    # Verify each pair
    for action, observation in pairs:
        _verify_action_observation_pair(action, observation)


def _find_matching_error_observation(action, events):
    """Find the error observation that matches the given action."""
    return next(
        (
            ev
            for ev in events
            if isinstance(ev, ErrorObservation)
            and getattr(ev, "_cause", None) == action.id
        ),
        None,
    )


def _verify_action_observation_pair(action, observation):
    """Verify a single action-observation pair."""
    action_dict = event_to_dict(action)
    observation_dict = event_to_dict(observation)

    assert (
        action_dict.get("action") == "run"
        and action_dict.get("args", {}).get("command") == "ls"
    )
    assert (
        observation_dict.get("observation") == "error"
        and observation_dict.get("content") == "Non fatal error here to trigger loop"
    )


def _verify_final_event(events):
    """Verify the final event in the sequence."""
    last_event = event_to_dict(events[-1])
    assert last_event["extras"]["agent_state"] == "error"
    assert last_event["observation"] == "agent_state_changed"


@pytest.mark.asyncio
async def test_max_iterations_extension(mock_agent_with_stats, mock_event_stream):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=False,
    )
    controller.state.agent_state = AgentState.RUNNING
    controller.state.iteration_flag.current_value = 10
    await controller._step()
    assert controller.state.agent_state == AgentState.ERROR
    message_action = MessageAction(content="Test message")
    message_action._source = EventSource.USER
    await send_event_to_controller(controller, message_action)
    assert controller.state.iteration_flag.max_value == 20
    assert controller.state.agent_state == AgentState.RUNNING
    await controller.close()
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    controller.state.agent_state = AgentState.RUNNING
    controller.state.iteration_flag.current_value = 10
    message_action = MessageAction(content="Test message")
    message_action._source = EventSource.USER
    await send_event_to_controller(controller, message_action)
    assert controller.state.iteration_flag.max_value == 10
    await controller._step()
    assert controller.state.agent_state == AgentState.ERROR
    await controller.close()


@pytest.mark.asyncio
async def test_step_max_budget(mock_agent_with_stats, mock_event_stream):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    metrics = Metrics()
    metrics.accumulated_cost = 10.1
    budget_flag = BudgetControlFlag(
        limit_increase_amount=10, current_value=10.1, max_value=10
    )
    mock_agent.llm.metrics.accumulated_cost = metrics.accumulated_cost
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        budget_per_task_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=False,
        initial_state=State(budget_flag=budget_flag, metrics=metrics),
    )
    controller.state.agent_state = AgentState.RUNNING
    await controller._step()
    assert controller.state.agent_state == AgentState.ERROR
    await controller.close()


@pytest.mark.asyncio
async def test_step_max_budget_headless(mock_agent_with_stats, mock_event_stream):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    metrics = Metrics()
    metrics.accumulated_cost = 10.1
    budget_flag = BudgetControlFlag(
        limit_increase_amount=10, current_value=10.1, max_value=10
    )
    mock_agent.llm.metrics.accumulated_cost = metrics.accumulated_cost
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        budget_per_task_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
        initial_state=State(budget_flag=budget_flag, metrics=metrics),
    )
    controller.state.agent_state = AgentState.RUNNING
    await controller._step()
    assert controller.state.agent_state == AgentState.ERROR
    await controller.close()


@pytest.mark.asyncio
async def test_budget_reset_on_continue(mock_agent_with_stats, mock_event_stream):
    """Test that when a user continues after hitting the budget limit:.

    1. Error is thrown when budget cap is exceeded
    2. LLM budget does not reset when user continues
    3. Budget is extended by adding the initial budget cap to the current accumulated cost.

    """
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    metrics = Metrics()
    metrics.accumulated_cost = 6.0
    initial_budget = 5.0
    initial_state = State(
        metrics=metrics,
        budget_flag=BudgetControlFlag(
            limit_increase_amount=initial_budget,
            current_value=6.0,
            max_value=initial_budget,
        ),
    )
    mock_agent.llm.metrics.accumulated_cost = metrics.accumulated_cost
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        budget_per_task_delta=initial_budget,
        sid="test",
        confirmation_mode=False,
        headless_mode=False,
        initial_state=initial_state,
    )
    controller.state.agent_state = AgentState.RUNNING
    assert controller.state.budget_flag.current_value == 6.0
    assert controller.agent.llm.metrics.accumulated_cost == 6.0
    await controller._step()
    assert controller.state.agent_state == AgentState.ERROR
    assert "budget" in controller.state.last_error.lower()
    await controller.set_agent_state_to(AgentState.RUNNING)
    message_action = MessageAction(content="Please continue")
    message_action._source = EventSource.USER
    await controller._on_event(message_action)
    assert controller.state.budget_flag.max_value == 11.0
    assert controller.agent.llm.metrics.accumulated_cost == 6.0
    assert controller.state.metrics.accumulated_cost == 6.0
    await controller.close()


@pytest.mark.asyncio
async def test_reset_with_pending_action_no_observation(
    mock_agent_with_stats, mock_event_stream
):
    """Test reset() when there's a pending action with tool call metadata but no observation."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    mock_event_stream.add_event.assert_called_once()
    mock_event_stream.add_event.reset_mock()
    pending_action = CmdRunAction(command="test")
    pending_action.tool_call_metadata = {
        "function": "test_function",
        "args": {"arg1": "value1"},
    }
    controller._pending_action = pending_action
    controller._reset()
    mock_event_stream.add_event.assert_called_once()
    args, kwargs = mock_event_stream.add_event.call_args
    error_obs, source = args
    assert isinstance(error_obs, ErrorObservation)
    assert (
        error_obs.content
        == "The action has not been executed due to a runtime error. The runtime system may have crashed and restarted due to resource constraints. Any previously established system state, dependencies, or environment variables may have been lost."
    )
    assert error_obs.tool_call_metadata == pending_action.tool_call_metadata
    assert error_obs._cause == pending_action.id
    assert source == EventSource.AGENT
    assert controller._pending_action is None
    mock_agent.reset.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_reset_with_pending_action_stopped_state(
    mock_agent_with_stats, mock_event_stream
):
    """Test reset() when there's a pending action and agent state is STOPPED."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    mock_event_stream.add_event.assert_called_once()
    mock_event_stream.add_event.reset_mock()
    pending_action = CmdRunAction(command="test")
    pending_action.tool_call_metadata = {
        "function": "test_function",
        "args": {"arg1": "value1"},
    }
    controller._pending_action = pending_action
    controller.state.agent_state = AgentState.STOPPED
    controller._reset()
    mock_event_stream.add_event.assert_called_once()
    args, kwargs = mock_event_stream.add_event.call_args
    error_obs, source = args
    assert isinstance(error_obs, ErrorObservation)
    assert error_obs.content == "Stop button pressed. The action has not been executed."
    assert error_obs.tool_call_metadata == pending_action.tool_call_metadata
    assert error_obs._cause == pending_action.id
    assert source == EventSource.AGENT
    assert controller._pending_action is None
    mock_agent.reset.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_reset_with_pending_action_existing_observation(
    mock_agent_with_stats, mock_event_stream
):
    """Test reset() when there's a pending action with tool call metadata and an existing observation."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    mock_event_stream.add_event.assert_called_once()
    mock_event_stream.add_event.reset_mock()
    pending_action = CmdRunAction(command="test")
    pending_action.tool_call_metadata = {
        "function": "test_function",
        "args": {"arg1": "value1"},
    }
    controller._pending_action = pending_action
    existing_obs = ErrorObservation(content="Previous error")
    existing_obs.tool_call_metadata = pending_action.tool_call_metadata
    controller.state.history.append(existing_obs)
    controller._reset()
    mock_event_stream.add_event.assert_not_called()
    assert controller._pending_action is None
    mock_agent.reset.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_reset_without_pending_action(mock_agent_with_stats, mock_event_stream):
    """Test reset() when there's no pending action."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    mock_event_stream.add_event.reset_mock()
    controller._reset()
    mock_event_stream.add_event.assert_not_called()
    assert controller._pending_action is None
    mock_agent.reset.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_reset_with_pending_action_no_metadata(
    mock_agent_with_stats, mock_event_stream, monkeypatch
):
    """Test reset() when there's a pending action without tool call metadata."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    mock_event_stream.add_event.reset_mock()
    pending_action = CmdRunAction(command="test")
    original_hasattr = hasattr

    def mock_hasattr(obj, name):
        if obj == pending_action and name == "tool_call_metadata":
            return False
        return original_hasattr(obj, name)

    monkeypatch.setattr("builtins.hasattr", mock_hasattr)
    controller._pending_action = pending_action
    controller._reset()
    mock_event_stream.add_event.assert_not_called()
    assert controller._pending_action is None
    mock_agent.reset.assert_called_once()
    await controller.close()


@pytest.mark.asyncio
async def test_run_controller_max_iterations_has_metrics(
    test_event_stream, mock_memory, mock_agent_with_stats
):
    config = ForgeConfig(max_iterations=3)
    event_stream = test_event_stream
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    step_count = 0

    def agent_step_fn(state):
        print(f"agent_step_fn received state: {state}")
        mock_agent.llm.metrics.add_cost(10.0)
        print(
            f"mock_agent.llm.metrics.accumulated_cost: {mock_agent.llm.metrics.accumulated_cost}"
        )
        nonlocal step_count
        step_count += 1
        return CmdRunAction(command=f"ls {step_count}")

    mock_agent.step = agent_step_fn
    runtime = MagicMock(spec=ActionExecutionClient)

    def on_event(event: Event):
        if isinstance(event, CmdRunAction):
            non_fatal_error_obs = ErrorObservation(
                f"Non fatal error. event id: {str(event.id)}"
            )
            non_fatal_error_obs._cause = event.id
            event_stream.add_event(non_fatal_error_obs, EventSource.ENVIRONMENT)

    event_stream.subscribe(EventStreamSubscriber.RUNTIME, on_event, str(uuid4()))
    runtime.event_stream = event_stream
    runtime.config = copy.deepcopy(config)

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    event_stream.subscribe(EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4()))
    with patch("forge.core.main.create_agent", return_value=mock_agent):
        state = await run_controller(
            config=config,
            initial_user_action=MessageAction(content="Test message"),
            runtime=runtime,
            sid="test",
            fake_user_response_fn=lambda _: "repeat",
            memory=mock_memory,
        )
    state.metrics = mock_agent.llm.metrics
    assert state.iteration_flag.current_value == 3
    assert state.agent_state == AgentState.ERROR
    assert (
        state.last_error
        == "RuntimeError: Agent reached maximum iteration. Current iteration: 3, max iteration: 3"
    )
    error_observations = test_event_stream.get_matching_events(
        reverse=True, limit=1, event_types=AgentStateChangedObservation
    )
    assert len(error_observations) == 1
    error_observation = error_observations[0]
    assert (
        error_observation.reason
        == "RuntimeError: Agent reached maximum iteration. Current iteration: 3, max iteration: 3"
    )
    assert state.metrics.accumulated_cost == 10.0 * 3, (
        f"Expected accumulated cost to be 30.0, but got {state.metrics.accumulated_cost}"
    )


@pytest.mark.asyncio
async def test_notify_on_llm_retry(
    mock_agent_with_stats, mock_event_stream, mock_status_callback
):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        status_callback=mock_status_callback,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )

    def notify_on_llm_retry(attempt, max_attempts):
        controller.status_callback("info", RuntimeStatus.LLM_RETRY, ANY)

    controller.agent.llm.retry_listener = notify_on_llm_retry
    controller.agent.llm.retry_listener(1, 2)
    controller.status_callback.assert_called_once_with(
        "info", RuntimeStatus.LLM_RETRY, ANY
    )
    await controller.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "context_window_error",
    [
        ContextWindowExceededError(
            message="prompt is too long: 233885 tokens > 200000 maximum",
            model="",
            llm_provider="",
        ),
        BadRequestError(
            message='ContextWindowExceededError: Maximum context length exceeded.',
            model="openrouter/qwen/qwen3-30b-a3b",
            llm_provider="openrouter",
        ),
    ],
)
async def test_context_window_exceeded_error_handling(
    context_window_error,
    mock_agent_with_stats,
    mock_runtime,
    test_event_stream,
    mock_memory,
):
    """Test that context window exceeded errors are handled correctly by the controller, providing a smaller view but keeping the history intact."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    max_iterations = 5
    error_after = 2

    # Setup test state and agent
    step_state = _create_test_step_state(error_after, context_window_error)
    mock_agent.step = step_state.step
    mock_agent.config = AgentConfig()

    # Setup event handling and configuration
    _setup_event_memory_handler(test_event_stream)
    config = _setup_test_config(max_iterations, mock_runtime, test_event_stream)

    # Run the controller
    final_state = await _run_controller_test(
        config, mock_agent, mock_runtime, mock_memory
    )

    # Verify test results
    _verify_context_window_error_handling(step_state, final_state, max_iterations)


def _create_test_step_state(error_after: int, context_window_error):
    """Create test step state for context window error testing."""

    class StepState:
        def __init__(self):
            self.has_errored = False
            self.index = 0
            self.views = []
            self.condenser = ConversationWindowCondenser()

        def step(self, state: State):
            match self.condenser.condense(state.view):
                case View() as view:
                    self.views.append(view)
                case Condensation(action=action):
                    return action

            if self.index < error_after or self.has_errored:
                self.index += 1
                return MessageAction(content=f"Test message {self.index}")

            ContextWindowExceededError(
                message="prompt is too long: 233885 tokens > 200000 maximum",
                model="",
                llm_provider="",
            )
            self.has_errored = True
            raise context_window_error

    return StepState()


def _setup_event_memory_handler(test_event_stream):
    """Setup event memory handler for testing."""

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            test_event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4())
    )


def _setup_test_config(max_iterations: int, mock_runtime, test_event_stream):
    """Setup test configuration."""
    config = ForgeConfig(max_iterations=max_iterations)
    mock_runtime.event_stream = test_event_stream
    mock_runtime.config = copy.deepcopy(config)
    return config


async def _run_controller_test(config, mock_agent, mock_runtime, mock_memory):
    """Run the controller test."""
    with patch("forge.core.main.create_agent", return_value=mock_agent):
        return await asyncio.wait_for(
            run_controller(
                config=config,
                initial_user_action=MessageAction(content="INITIAL"),
                runtime=mock_runtime,
                sid="test",
                fake_user_response_fn=lambda _: "repeat",
                memory=mock_memory,
            ),
            timeout=10,
        )


def _verify_context_window_error_handling(step_state, final_state, max_iterations: int):
    """Verify context window error handling results."""
    # Basic assertions
    assert step_state.has_errored
    assert len(step_state.views) == max_iterations - 1

    # Wait for condensation action
    condensation_action = _wait_for_condensation_action(final_state.history)
    assert condensation_action is not None, (
        "CondensationAction was not emitted into history."
    )

    # Debug output
    _print_debug_info(final_state.history, condensation_action)

    # Verify view condensation
    _verify_view_condensation(final_state, condensation_action)

    # Verify event counts
    _verify_event_counts(final_state.history, max_iterations)

    # Verify final state
    _verify_final_state(final_state, step_state)


def _wait_for_condensation_action(history):
    """Wait for condensation action to appear in history."""
    import time

    def _get_condensation_action(events):
        for e in reversed(events):
            if isinstance(e, CondensationAction):
                return e
        return None

    deadline = time.time() + 2.0
    condensation_action = None
    while time.time() < deadline and condensation_action is None:
        condensation_action = _get_condensation_action(history)
        if condensation_action is None:
            time.sleep(0.05)

    return condensation_action


def _print_debug_info(history, condensation_action):
    """Print debug information for test analysis."""
    print("step_state.views: ", getattr(condensation_action, "views", []))
    print("\n--- DEBUG: final_state.history events (id:type:repr) ---")
    for ev in history:
        try:
            ev_id = ev.id
        except Exception:
            ev_id = getattr(ev, "_id", None)
        print(f"id={ev_id} type={type(ev).__name__} repr={ev}")

    print("--- DEBUG: condensation_action details ---")
    print(
        f"condensation_action id={condensation_action.id} forgotten={
            condensation_action.forgotten
        } range=({condensation_action.forgotten_events_start_id},{
            condensation_action.forgotten_events_end_id
        }) summary={condensation_action.summary} summary_offset={
            condensation_action.summary_offset
        }"
    )


def _verify_view_condensation(final_state, condensation_action):
    """Verify that view condensation worked correctly."""
    events = list(final_state.history)
    cond_idx = next((i for i, e in enumerate(events) if e is condensation_action))
    before_events = events[:cond_idx]
    before_view = View.from_events(before_events)
    after_view = View.from_events(events)

    assert len(after_view) <= len(before_view) + 2, (
        f"Expected condensation to not dramatically increase view size: before={len(before_view)}, after={len(after_view)}"
    )


def _verify_event_counts(history, max_iterations: int):
    """Verify expected event counts in history."""
    assert (
        len([event for event in history if isinstance(event, MessageAction)])
        == max_iterations - 1
    )
    assert (
        len(
            [
                event
                for event in history
                if isinstance(event, MessageAction)
                and event.source == EventSource.AGENT
            ]
        )
        == max_iterations - 2
    )
    assert len([event for event in history if isinstance(event, RecallAction)]) == 1
    assert (
        len([event for event in history if isinstance(event, RecallObservation)]) == 1
    )
    assert (
        len([event for event in history if isinstance(event, CondensationAction)]) == 1
    )
    assert len(history) == max_iterations + 4


def _verify_final_state(final_state, step_state):
    """Verify final state properties."""
    assert len(final_state.view) <= len(step_state.views[-1]) + 1, (
        f"Expected final view to be <= last observed view + 1: last={len(step_state.views[-1])}, final={len(final_state.view)}"
    )
    assert len(final_state.history) != len(final_state.view)


@pytest.mark.asyncio
async def test_run_controller_with_context_window_exceeded_with_truncation(
    mock_agent_with_stats, mock_runtime, mock_memory, test_event_stream
):
    """Tests that the controller can make progress after handling context window exceeded errors, as long as enable_history_truncation is ON."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats

    class StepState:
        def __init__(self):
            self.has_errored = False
            self.condenser = ConversationWindowCondenser()

        def step(self, state: State):
            match self.condenser.condense(state.view):
                case Condensation(action=action):
                    return action
                case _:
                    pass
            if len(state.history) > 5 and (not self.has_errored):
                error = ContextWindowExceededError(
                    message="prompt is too long: 233885 tokens > 200000 maximum",
                    model="",
                    llm_provider="",
                )
                self.has_errored = True
                raise error
            return MessageAction(content=f"STEP {len(state.history)}")

    step_state = StepState()
    mock_agent.step = step_state.step
    mock_agent.config = AgentConfig()

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            test_event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4())
    )
    mock_runtime.event_stream = test_event_stream
    config = ForgeConfig(max_iterations=5)
    mock_runtime.config = copy.deepcopy(config)
    try:
        with patch("forge.core.main.create_agent", return_value=mock_agent):
            state = await asyncio.wait_for(
                run_controller(
                    config=config,
                    initial_user_action=MessageAction(content="INITIAL"),
                    runtime=mock_runtime,
                    sid="test",
                    fake_user_response_fn=lambda _: "repeat",
                    memory=mock_memory,
                ),
                timeout=10,
            )
    except asyncio.TimeoutError as e:
        raise AssertionError(
            "The run_controller function did not complete in time."
        ) from e
    assert state.iteration_flag.current_value == 5
    assert state.agent_state == AgentState.ERROR
    assert (
        state.last_error
        == "RuntimeError: Agent reached maximum iteration. Current iteration: 5, max iteration: 5"
    )
    assert step_state.has_errored


@pytest.mark.asyncio
async def test_run_controller_with_context_window_exceeded_without_truncation(
    mock_agent_with_stats, mock_runtime, mock_memory, test_event_stream
):
    """Tests that the controller would quit upon context window exceeded errors without enable_history_truncation ON."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats

    class StepState:
        def __init__(self):
            self.has_errored = False

        def step(self, state: State):
            if len(state.history) > 3 and (not self.has_errored):
                error = ContextWindowExceededError(
                    message="prompt is too long: 233885 tokens > 200000 maximum",
                    model="",
                    llm_provider="",
                )
                self.has_errored = True
                raise error
            return MessageAction(content=f"STEP {len(state.history)}")

    step_state = StepState()
    mock_agent.step = step_state.step
    mock_agent.config = AgentConfig()
    mock_agent.config.enable_history_truncation = False

    def on_event_memory(event: Event):
        if isinstance(event, RecallAction):
            microagent_obs = RecallObservation(
                content="Test microagent content", recall_type=RecallType.KNOWLEDGE
            )
            microagent_obs._cause = event.id
            test_event_stream.add_event(microagent_obs, EventSource.ENVIRONMENT)

    test_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, on_event_memory, str(uuid4())
    )
    mock_runtime.event_stream = test_event_stream
    config = ForgeConfig(max_iterations=3)
    mock_runtime.config = copy.deepcopy(config)
    try:
        with patch("forge.core.main.create_agent", return_value=mock_agent):
            state = await asyncio.wait_for(
                run_controller(
                    config=config,
                    initial_user_action=MessageAction(content="INITIAL"),
                    runtime=mock_runtime,
                    sid="test",
                    fake_user_response_fn=lambda _: "repeat",
                    memory=mock_memory,
                ),
                timeout=10,
            )
    except asyncio.TimeoutError as e:
        raise AssertionError(
            "The run_controller function did not complete in time."
        ) from e
    assert state.iteration_flag.current_value in (1, 2)
    assert state.agent_state == AgentState.ERROR
    assert (
        state.last_error
        == "LLMContextWindowExceedError: Conversation history longer than LLM context window limit. Consider turning on enable_history_truncation config to avoid this error"
    )
    error_observations = test_event_stream.get_matching_events(
        reverse=True, limit=1, event_types=AgentStateChangedObservation
    )
    assert len(error_observations) == 1
    error_observation = error_observations[0]
    assert (
        error_observation.reason
        == "LLMContextWindowExceedError: Conversation history longer than LLM context window limit. Consider turning on enable_history_truncation config to avoid this error"
    )
    assert step_state.has_errored


@pytest.mark.asyncio
async def test_run_controller_with_memory_error(
    test_event_stream, mock_agent_with_stats
):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    config = ForgeConfig()
    event_stream = test_event_stream
    mock_agent.llm = MagicMock(spec=LLM)
    mock_agent.llm.metrics = Metrics()
    mock_agent.llm.config = config.get_llm_config()

    def agent_step_fn(state):
        return MessageAction(content="Agent returned a message")

    mock_agent.step = agent_step_fn
    runtime = MagicMock(spec=ActionExecutionClient)
    runtime.event_stream = event_stream
    runtime.config = copy.deepcopy(config)
    memory = Memory(event_stream=event_stream, sid="test-memory")

    def mock_find_microagent_knowledge(*args, **kwargs):
        raise RuntimeError("Test memory error")

    with patch.object(
        memory, "_find_microagent_knowledge", side_effect=mock_find_microagent_knowledge
    ):
        with patch("forge.core.main.create_agent", return_value=mock_agent):
            state = await run_controller(
                config=config,
                initial_user_action=MessageAction(content="Test message"),
                runtime=runtime,
                sid="test",
                fake_user_response_fn=lambda _: "repeat",
                memory=memory,
            )
    assert state.iteration_flag.current_value >= 1
    assert state.agent_state == AgentState.ERROR
    assert any(s in state.last_error for s in ["Recall error", "RuntimeError", "AgentStuckInLoopError"])


@pytest.mark.asyncio
async def test_action_metrics_copy(mock_agent_with_stats):
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    file_store = InMemoryFileStore({})
    event_stream = EventStream(sid="test", file_store=file_store)
    metrics = Metrics(model_name="test-model")
    metrics.accumulated_cost = 0.05
    initial_state = State(metrics=metrics, budget_flag=None)
    usage1 = TokenUsage(
        model="test-model",
        prompt_tokens=5,
        completion_tokens=10,
        cache_read_tokens=2,
        cache_write_tokens=2,
        response_id="test-id-1",
    )
    usage2 = TokenUsage(
        model="test-model",
        prompt_tokens=10,
        completion_tokens=20,
        cache_read_tokens=5,
        cache_write_tokens=5,
        response_id="test-id-2",
    )
    metrics.token_usages = [usage1, usage2]
    metrics._accumulated_token_usage = TokenUsage(
        model="test-model",
        prompt_tokens=15,
        completion_tokens=30,
        cache_read_tokens=7,
        cache_write_tokens=7,
        response_id="accumulated",
    )
    metrics.add_cost(0.02)
    metrics.add_response_latency(0.5, "test-id-2")
    mock_agent.llm.metrics = metrics
    llm_registry.service_to_llm["agent"] = mock_agent.llm
    llm_registry.notify(RegistryEvent(llm=mock_agent.llm, service_id="agent"))
    action = MessageAction(content="Test message")

    def agent_step_fn(state):
        return action

    mock_agent.step = agent_step_fn
    controller = AgentController(
        agent=mock_agent,
        event_stream=event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
        initial_state=initial_state,
    )
    controller.state.agent_state = AgentState.RUNNING
    await controller._step()
    events = list(event_stream.get_events())
    assert events
    last_action = events[-1]
    assert last_action.llm_metrics is not None
    assert last_action.llm_metrics.accumulated_cost == 0.07
    assert len(last_action.llm_metrics.token_usages) == 0
    assert last_action.llm_metrics.accumulated_token_usage.prompt_tokens == 15
    assert last_action.llm_metrics.accumulated_token_usage.completion_tokens == 30
    assert last_action.llm_metrics.accumulated_token_usage.cache_read_tokens == 7
    assert last_action.llm_metrics.accumulated_token_usage.cache_write_tokens == 7
    assert len(last_action.llm_metrics.costs) == 0
    assert len(last_action.llm_metrics.response_latencies) == 0
    assert not hasattr(last_action.llm_metrics, "latency")
    assert not hasattr(last_action.llm_metrics, "total_latency")
    assert not hasattr(last_action.llm_metrics, "average_latency")
    mock_agent.llm.metrics.accumulated_cost = 0.1
    assert last_action.llm_metrics.accumulated_cost == 0.07
    await controller.close()


@pytest.mark.asyncio
async def test_condenser_metrics_included(mock_agent_with_stats, test_event_stream):
    """Test that metrics from the condenser's LLM are included in the action metrics."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    mock_agent.llm.metrics.accumulated_cost = 0.05
    mock_agent.llm.metrics._accumulated_token_usage = TokenUsage(
        model="agent-model",
        prompt_tokens=100,
        completion_tokens=50,
        cache_read_tokens=10,
        cache_write_tokens=10,
        response_id="agent-accumulated",
    )
    mock_agent.name = "TestAgent"
    condenser = MagicMock()
    condenser.llm = MagicMock(spec=LLM)
    condenser_metrics = Metrics(model_name="condenser-model")
    condenser_metrics.accumulated_cost = 0.03
    condenser_metrics._accumulated_token_usage = TokenUsage(
        model="condenser-model",
        prompt_tokens=200,
        completion_tokens=100,
        cache_read_tokens=20,
        cache_write_tokens=5000,
        response_id="condenser-accumulated",
    )
    condenser.llm.metrics = condenser_metrics
    llm_registry.service_to_llm["condenser"] = condenser.llm
    llm_registry.notify(RegistryEvent(llm=condenser.llm, service_id="condenser"))
    mock_agent.condenser = condenser
    action = CondensationAction(
        forgotten_events_start_id=1,
        forgotten_events_end_id=5,
        summary="Test summary",
        summary_offset=1,
    )
    action._source = EventSource.AGENT

    def agent_step_fn(state):
        return action

    mock_agent.step = agent_step_fn
    controller = AgentController(
        agent=mock_agent,
        event_stream=test_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
        initial_state=State(metrics=mock_agent.llm.metrics, budget_flag=None),
    )
    controller.state.agent_state = AgentState.RUNNING
    await controller._step()
    events = list(test_event_stream.get_events())
    assert events
    last_action = events[-1]
    assert last_action.llm_metrics is not None
    assert last_action.llm_metrics.accumulated_cost == 0.08
    assert last_action.llm_metrics.accumulated_token_usage.prompt_tokens == 300
    assert last_action.llm_metrics.accumulated_token_usage.completion_tokens == 150
    assert last_action.llm_metrics.accumulated_token_usage.cache_read_tokens == 30
    assert last_action.llm_metrics.accumulated_token_usage.cache_write_tokens == 5010
    await controller.close()


@pytest.mark.asyncio
async def test_first_user_message_with_identical_content(
    test_event_stream, mock_agent_with_stats
):
    """Test that _first_user_message correctly identifies the first user message.

    This test verifies that messages with identical content but different IDs are properly
    distinguished, and that the result is correctly cached.

    The issue we're checking is that the comparison (action == self._first_user_message())
    should correctly differentiate between messages with the same content but different IDs.
    """
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    controller = AgentController(
        agent=mock_agent,
        event_stream=test_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
    )
    first_message = MessageAction(content="Hello, this is a test message")
    first_message._source = EventSource.USER
    test_event_stream.add_event(first_message, EventSource.USER)
    second_message = MessageAction(content="Hello, this is a test message")
    second_message._source = EventSource.USER
    test_event_stream.add_event(second_message, EventSource.USER)
    first_user_message = controller._first_user_message()
    assert first_user_message is not None
    assert first_user_message.id == first_message.id
    assert first_user_message.id != second_message.id
    assert first_user_message == first_message == second_message
    assert first_message == first_user_message
    assert second_message.id != first_user_message.id
    assert controller._cached_first_user_message is not None
    assert controller._cached_first_user_message is first_user_message
    with patch.object(test_event_stream, "get_events") as mock_get_events:
        cached_message = controller._first_user_message()
        assert cached_message is first_user_message
        mock_get_events.assert_not_called()
    await controller.close()


@pytest.mark.asyncio
async def test_agent_controller_processes_null_observation_with_cause(
    mock_agent_with_stats,
):
    """Test that AgentController processes NullObservation events with a cause value.

    And that the agent's step method is called as a result.
    """
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    file_store = InMemoryFileStore()
    event_stream = EventStream(sid="test-session", file_store=file_store)
    Memory(event_stream=event_stream, sid="test-session")
    controller = AgentController(
        agent=mock_agent,
        event_stream=event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test-session",
    )
    with patch.object(controller, "_step") as mock_step:
        user_message = MessageAction(content="First user message")
        user_message._source = EventSource.USER
        event_stream.add_event(user_message, EventSource.USER)
        await asyncio.sleep(1)
        events = list(event_stream.get_events())
        recall_actions = [event for event in events if isinstance(event, RecallAction)]
        assert recall_actions, "No RecallAction was created"
        recall_action = recall_actions[0]
        null_obs_events = [
            event for event in events if isinstance(event, NullObservation)
        ]
        assert null_obs_events, "No NullObservation was created"
        null_observation = null_obs_events[0]
        assert null_observation.cause is not None, "NullObservation cause is None"
        assert null_observation.cause == recall_action.id, f"Expected cause={
            recall_action.id
        }, got cause={null_observation.cause}"
        assert controller.should_step(null_observation), (
            "should_step should return True for this NullObservation"
        )
        assert mock_step.called, "Controller's step method was not called"
        null_observation_zero = NullObservation(content="Test observation with cause=0")
        null_observation_zero._cause = 0
        assert not controller.should_step(null_observation_zero), (
            "should_step should return False for NullObservation with cause=0"
        )


def test_agent_controller_should_step_with_null_observation_cause_zero(
    mock_agent_with_stats,
):
    """Test that AgentController's should_step method returns False for NullObservation with cause = 0."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    file_store = InMemoryFileStore()
    event_stream = EventStream(sid="test-session", file_store=file_store)
    controller = AgentController(
        agent=mock_agent,
        event_stream=event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
        sid="test-session",
    )
    null_observation = NullObservation(content="Test observation")
    null_observation._cause = 0
    result = controller.should_step(null_observation)
    assert result is False, (
        "should_step should return False for NullObservation with cause = 0"
    )


def test_system_message_in_event_stream(mock_agent_with_stats, test_event_stream):
    """Test that SystemMessageAction is added to event stream in AgentController."""
    mock_agent, conversation_stats, llm_registry = mock_agent_with_stats
    _ = AgentController(
        agent=mock_agent,
        event_stream=test_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=10,
    )
    events = list(test_event_stream.get_events())
    assert len(events) == 1
    assert isinstance(events[0], SystemMessageAction)
    assert events[0].content == "Test system message"
    assert events[0].tools == ["test_tool"]
