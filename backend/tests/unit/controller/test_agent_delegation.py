import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4
import pytest
from forge.controller.agent import Agent
from forge.controller.agent_controller import AgentController
from forge.controller.state.control_flags import BudgetControlFlag, IterationControlFlag
from forge.controller.state.state import State
from forge.core.config import ForgeConfig
from forge.core.config.agent_config import AgentConfig
from forge.core.config.llm_config import LLMConfig
from forge.core.schemas import AgentState
from forge.events import EventSource, EventStream
from forge.events.action import AgentDelegateAction, AgentFinishAction, MessageAction
from forge.events.action.agent import RecallAction
from forge.events.action.commands import CmdRunAction
from forge.events.action.message import SystemMessageAction
from forge.events.event import Event, RecallType
from forge.events.observation.agent import RecallObservation
from forge.events.stream import EventStreamSubscriber
from forge.llm.llm import LLM
from forge.llm.llm_registry import LLMRegistry
from forge.llm.metrics import Metrics
from forge.memory.memory import Memory
from forge.server.services.conversation_stats import ConversationStats
from forge.storage.memory import InMemoryFileStore


@pytest.fixture
def llm_registry():
    config = ForgeConfig()
    return LLMRegistry(config=config)


@pytest.fixture
def conversation_stats():
    import uuid

    file_store = InMemoryFileStore({})
    conversation_id = f"test-conversation-{uuid.uuid4()}"
    return ConversationStats(
        file_store=file_store, conversation_id=conversation_id, user_id="test-user"
    )


@pytest.fixture
def connected_registry_and_stats(llm_registry, conversation_stats):
    """Connect the LLMRegistry and ConversationStats properly."""
    llm_registry.subscribe(conversation_stats.register_llm)
    return (llm_registry, conversation_stats)


@pytest.fixture
def mock_event_stream():
    """Creates an event stream in memory."""
    sid = f"test-{uuid4()}"
    file_store = InMemoryFileStore({})
    return EventStream(sid=sid, file_store=file_store)


@pytest.fixture
def mock_parent_agent(llm_registry):
    """Creates a mock parent agent for testing delegation."""
    agent = MagicMock(spec=Agent)
    agent.name = "ParentAgent"
    agent.llm = MagicMock(spec=LLM)
    agent.llm.service_id = "main_agent"
    agent.llm.metrics = Metrics()
    agent.llm.config = LLMConfig()
    agent.llm.retry_listener = None
    agent.config = AgentConfig()
    agent.llm_registry = llm_registry
    system_message = SystemMessageAction(content="Test system message")
    system_message._source = EventSource.AGENT
    system_message._id = -1
    agent.get_system_message.return_value = system_message
    return agent


@pytest.fixture
def mock_child_agent(llm_registry):
    """Creates a mock child agent for testing delegation."""
    agent = MagicMock(spec=Agent)
    agent.name = "ChildAgent"
    agent.llm = MagicMock(spec=LLM)
    agent.llm.service_id = "main_agent"
    agent.llm.metrics = Metrics()
    agent.llm.config = LLMConfig()
    agent.llm.retry_listener = None
    agent.config = AgentConfig()
    agent.llm_registry = llm_registry
    system_message = SystemMessageAction(content="Test system message")
    system_message._source = EventSource.AGENT
    system_message._id = -1
    agent.get_system_message.return_value = system_message
    return agent


def create_mock_agent_factory(mock_child_agent, llm_registry):
    """Helper function to create a mock agent factory with proper LLM registration."""

    def create_mock_agent(config, llm_registry=None):
        if llm_registry:
            mock_child_agent.llm = llm_registry.get_llm("agent_llm", LLMConfig())
            mock_child_agent.llm_registry = llm_registry
        return mock_child_agent

    return create_mock_agent


@pytest.mark.asyncio
async def test_delegation_flow(
    mock_parent_agent, mock_child_agent, mock_event_stream, connected_registry_and_stats
):
    """Test parent delegation flow and metrics accumulation."""
    llm_registry, conversation_stats = connected_registry_and_stats
    Agent.get_cls = Mock(
        return_value=create_mock_agent_factory(mock_child_agent, llm_registry)
    )
    step_count = 0

    def agent_step_fn(state):
        nonlocal step_count
        step_count += 1
        return CmdRunAction(command=f"ls {step_count}")

    mock_child_agent.step = agent_step_fn
    parent_llm = llm_registry.service_to_llm["agent"]
    parent_llm.metrics.accumulated_cost = 2
    mock_parent_agent.llm = parent_llm
    parent_metrics = Metrics()
    parent_metrics.accumulated_cost = 2
    parent_state = State(
        inputs={},
        metrics=parent_metrics,
        budget_flag=BudgetControlFlag(
            current_value=2, limit_increase_amount=10, max_value=10
        ),
        iteration_flag=IterationControlFlag(
            current_value=1, limit_increase_amount=10, max_value=10
        ),
    )
    parent_controller = AgentController(
        agent=mock_parent_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=1,
        sid="parent",
        confirmation_mode=False,
        headless_mode=True,
        initial_state=parent_state,
    )
    mock_memory = MagicMock(spec=Memory)
    mock_memory.event_stream = mock_event_stream

    def on_event(event: Event):
        if isinstance(event, RecallAction):
            microagent_observation = RecallObservation(
                recall_type=RecallType.KNOWLEDGE, content="Found info"
            )
            microagent_observation._cause = event.id
            mock_event_stream.add_event(microagent_observation, EventSource.ENVIRONMENT)

    mock_memory.on_event = on_event
    mock_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, mock_memory.on_event, mock_memory
    )

    def child_step_factory(state):
        act = CmdRunAction(command="echo")
        act._tool_call_metadata = None
        return act

    mock_child_agent.step.side_effect = child_step_factory

    def child_step_factory(state):
        act = CmdRunAction(command="echo")
        act._tool_call_metadata = None
        return act

    mock_child_agent.step.side_effect = child_step_factory

    def parent_step_factory(*args, **kwargs):
        return AgentDelegateAction(agent="ChildAgent", inputs={"test": True})

    mock_parent_agent.step.side_effect = parent_step_factory
    message_action = MessageAction(content="please delegate now")
    message_action._source = EventSource.USER
    await parent_controller._on_event(message_action)
    await asyncio.sleep(1)
    events = list(mock_event_stream.get_events())
    assert mock_event_stream.get_latest_event_id() >= 3
    assert any((isinstance(event, RecallObservation) for event in events))
    assert any((isinstance(event, AgentDelegateAction) for event in events))
    assert parent_controller.delegate is not None, (
        "Parent's delegate controller was not set."
    )
    assert parent_controller.state.iteration_flag.current_value == 2, (
        "Parent iteration should be incremented after step."
    )
    delegate_controller = parent_controller.delegate
    for i in range(4):
        delegate_controller.state.iteration_flag.step()
        delegate_controller.agent.step(delegate_controller.state)
        delegate_controller.agent.llm.metrics.add_cost(1.0)
    assert delegate_controller.state.get_local_step() == 4
    combined_metrics = (
        delegate_controller.state.conversation_stats.get_combined_metrics()
    )
    assert combined_metrics.accumulated_cost == 6
    delegate_controller.state.outputs = {"delegate_result": "done"}
    child_finish_action = AgentFinishAction()
    await delegate_controller._on_event(child_finish_action)
    await asyncio.sleep(0.5)
    assert parent_controller.delegate is None, (
        "Parent delegate should be None after child finishes."
    )
    assert parent_controller.state.iteration_flag.current_value == 7, (
        "Parent iteration should be the child's iteration + 1 after child is done."
    )
    await parent_controller.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "delegate_state",
    [AgentState.RUNNING, AgentState.FINISHED, AgentState.ERROR, AgentState.REJECTED],
)
async def test_delegate_step_different_states(
    mock_parent_agent, mock_event_stream, delegate_state, connected_registry_and_stats
):
    """Ensure delegate handling based on delegate state."""
    llm_registry, conversation_stats = connected_registry_and_stats
    state = State(inputs={})
    state.iteration_flag.max_value = 10
    controller = AgentController(
        agent=mock_parent_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=1,
        sid="test",
        confirmation_mode=False,
        headless_mode=True,
        initial_state=state,
    )
    mock_delegate = AsyncMock()
    controller.delegate = mock_delegate
    mock_delegate.state.iteration_flag = MagicMock()
    mock_delegate.state.iteration_flag.current_value = 5
    mock_delegate.state.outputs = {"result": "test"}
    mock_delegate.agent.name = "TestDelegate"
    mock_delegate.get_agent_state = Mock(return_value=delegate_state)
    mock_delegate._step = AsyncMock()
    mock_delegate.close = AsyncMock()

    def call_on_event_with_new_loop():
        """Create a fresh loop in another thread and deliver an event."""
        loop_in_thread = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop_in_thread)
            msg_action = MessageAction(content="Test message")
            msg_action._source = EventSource.USER
            controller.on_event(msg_action)
        finally:
            loop_in_thread.close()

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        future = loop.run_in_executor(executor, call_on_event_with_new_loop)
        await future
    await asyncio.sleep(0.5)
    if delegate_state == AgentState.RUNNING:
        assert controller.delegate is not None
        assert controller.state.iteration_flag.current_value == 0
        mock_delegate.close.assert_not_called()
    else:
        assert controller.delegate is None
        assert controller.state.iteration_flag.current_value == 5
        assert mock_delegate.close.call_count == 1
    await controller.close()


@pytest.mark.asyncio
async def test_delegate_hits_global_limits(
    mock_child_agent, mock_event_stream, mock_parent_agent, connected_registry_and_stats
):
    """Global limits from control flags should apply to delegates."""
    llm_registry, conversation_stats = connected_registry_and_stats
    Agent.get_cls = Mock(
        return_value=create_mock_agent_factory(mock_child_agent, llm_registry)
    )
    mock_parent_agent.llm.metrics.accumulated_cost = 2
    mock_parent_agent.llm.service_id = "main_agent"
    llm_registry.service_to_llm["main_agent"] = mock_parent_agent.llm
    parent_metrics = Metrics()
    parent_metrics.accumulated_cost = 2
    parent_state = State(
        inputs={},
        metrics=parent_metrics,
        budget_flag=BudgetControlFlag(
            current_value=2, limit_increase_amount=10, max_value=10
        ),
        iteration_flag=IterationControlFlag(
            current_value=2, limit_increase_amount=3, max_value=3
        ),
    )
    parent_controller = AgentController(
        agent=mock_parent_agent,
        event_stream=mock_event_stream,
        conversation_stats=conversation_stats,
        iteration_delta=1,
        sid="parent",
        confirmation_mode=False,
        headless_mode=False,
        initial_state=parent_state,
    )
    mock_memory = MagicMock(spec=Memory)
    mock_memory.event_stream = mock_event_stream

    def on_event(event: Event):
        if isinstance(event, RecallAction):
            microagent_observation = RecallObservation(
                recall_type=RecallType.KNOWLEDGE, content="Found info"
            )
            microagent_observation._cause = event.id
            mock_event_stream.add_event(microagent_observation, EventSource.ENVIRONMENT)

    mock_memory.on_event = on_event
    mock_event_stream.subscribe(
        EventStreamSubscriber.MEMORY, mock_memory.on_event, mock_memory
    )

    def parent_step_factory(*args, **kwargs):
        action = AgentDelegateAction(agent="ChildAgent", inputs={"test": True})
        action._tool_call_metadata = None
        return action

    mock_parent_agent.step.side_effect = parent_step_factory
    message_action = MessageAction(content="please delegate now")
    message_action._source = EventSource.USER
    await parent_controller._on_event(message_action)
    await asyncio.sleep(1)
    events = list(mock_event_stream.get_events())
    assert mock_event_stream.get_latest_event_id() >= 3
    assert any((isinstance(event, RecallObservation) for event in events))
    assert any((isinstance(event, AgentDelegateAction) for event in events))
    assert parent_controller.delegate is not None, (
        "Parent's delegate controller was not set."
    )
    delegate_controller = parent_controller.delegate
    # Ensure the child agent produces a valid action when allowed to step again
    def child_step_factory(state):
        act = CmdRunAction(command="echo")
        act._tool_call_metadata = None
        return act

    mock_child_agent.step.side_effect = child_step_factory

    await delegate_controller.set_agent_state_to(AgentState.RUNNING)
    message_action = MessageAction(content="Test message")
    message_action._source = EventSource.USER
    await delegate_controller._on_event(message_action)
    await asyncio.sleep(0.1)
    assert delegate_controller.state.agent_state == AgentState.ERROR
    assert (
        delegate_controller.state.last_error
        == "RuntimeError: Agent reached maximum iteration. Current iteration: 3, max iteration: 3"
    )
    await delegate_controller.set_agent_state_to(AgentState.RUNNING)
    await asyncio.sleep(0.1)
    assert delegate_controller.state.iteration_flag.max_value == 6
    assert (
        delegate_controller.state.iteration_flag.max_value
        == parent_controller.state.iteration_flag.max_value
    )
    message_action = MessageAction(content="Test message 2")
    message_action._source = EventSource.USER
    await delegate_controller._on_event(message_action)
    await asyncio.sleep(0.1)
    assert delegate_controller.state.iteration_flag.current_value == 4
    assert (
        delegate_controller.state.iteration_flag.current_value
        == parent_controller.state.iteration_flag.current_value
    )
