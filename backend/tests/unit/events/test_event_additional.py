"""Additional coverage for event helpers and action utilities."""

from __future__ import annotations

import asyncio
import pytest

from datetime import datetime, timezone

from forge.events.action.agent import (
    AgentDelegateAction,
    AgentFinishAction,
    AgentRejectAction,
    AgentThinkAction,
    ChangeAgentStateAction,
    CondensationAction,
    CondensationRequestAction,
    RecallAction,
    TaskTrackingAction,
)
from forge.events.action.browse import BrowseInteractiveAction, BrowseURLAction
from forge.events.action.empty import NullAction
from forge.events.action.files import (
    FileEditAction,
    FileEditSource,
    FileReadAction,
    FileWriteAction,
)
from forge.events.action.message import (
    MessageAction,
    StreamingChunkAction,
    SystemMessageAction,
)
from forge.events.async_event_store_wrapper import AsyncEventStoreWrapper
from forge.events.event import Event, EventSource, RecallType
from forge.events.observation.agent import (
    AgentCondensationObservation,
    AgentStateChangedObservation,
    AgentThinkObservation,
    MicroagentKnowledge,
    RecallObservation,
)
from forge.events.observation.commands import CmdOutputObservation
from forge.events.observation.empty import NullObservation
from forge.events.observation.server import ServerReadyObservation
from forge.events.utils import get_pairs_from_events
from forge.llm.metrics import Metrics
from forge.events.tool import ToolCallMetadata


class _DummyEventStore:
    """Simple event store that returns a predefined list."""

    def __init__(self, events: list[Event]) -> None:
        self._events = events
        self.search_calls: list[tuple[tuple, dict]] = []

    def search_events(self, *args, **kwargs):
        self.search_calls.append((args, kwargs))
        yield from self._events


def _set_ids(
    event: Event,
    *,
    event_id: int,
    cause: int | None = None,
    source: EventSource | None = None,
) -> Event:
    """Helper to set private metadata for tests."""
    event._id = event_id
    if cause is not None:
        event._cause = cause
    if source is not None:
        event._source = source
    return event


def test_async_event_store_wrapper_iterates_in_order() -> None:
    """Async wrapper should yield the same sequence as the underlying store."""
    events = [
        _set_ids(AgentThinkAction(thought="considering"), event_id=0),
        _set_ids(AgentFinishAction(final_thought="done"), event_id=1),
    ]
    store = _DummyEventStore(events)
    wrapper = AsyncEventStoreWrapper(store)

    async def _collect() -> list[Event]:
        collected: list[Event] = []
        async for evt in wrapper:
            collected.append(evt)
        return collected

    collected = asyncio.run(_collect())

    assert collected == events
    assert store.search_calls == [((), {})]


def test_get_pairs_from_events_matches_actions_and_observations() -> None:
    """Pairs should align actions with observations and fill in gaps."""
    action_with_result = _set_ids(
        AgentFinishAction(final_thought="complete"), event_id=1
    )
    observation_for_action = _set_ids(
        CmdOutputObservation(content="ok", command="ls", hidden=True),
        event_id=2,
        cause=1,
    )

    action_without_observation = _set_ids(
        AgentThinkAction(thought="still working"), event_id=3
    )
    orphaned_observation = _set_ids(
        CmdOutputObservation(content="warning", command="cat", hidden=True),
        event_id=4,
        cause=99,
    )

    pairs = get_pairs_from_events(
        [
            action_with_result,
            observation_for_action,
            action_without_observation,
            orphaned_observation,
        ],
    )

    assert (action_with_result, observation_for_action) in pairs
    assert any(
        pair[0] is action_without_observation and isinstance(pair[1], NullObservation)
        for pair in pairs
    )
    assert any(
        isinstance(pair[0], NullAction) and pair[1] is orphaned_observation
        for pair in pairs
    )


def test_get_pairs_logs_missing_identifiers(caplog: pytest.LogCaptureFixture) -> None:
    """Ensure helper handles events lacking IDs or causes."""
    action_no_id = AgentThinkAction(thought="no id")
    observation_no_cause = CmdOutputObservation(content="result", command="ls")

    with caplog.at_level("DEBUG"):
        pairs = get_pairs_from_events([action_no_id, observation_no_cause])

    assert len(pairs) == 1
    action, observation = pairs[0]
    assert isinstance(action, AgentThinkAction)
    assert isinstance(observation, NullObservation)


def test_server_ready_observation_message_reflects_health() -> None:
    """Message should include status emoji depending on health."""
    healthy = ServerReadyObservation(
        content="ready", port=8080, url="http://localhost:8080", health_status="healthy"
    )
    degraded = ServerReadyObservation(
        content="pending",
        port=8080,
        url="http://localhost:8080",
        health_status="probing",
    )

    assert "✅" in healthy.message
    assert "🔄" in degraded.message


def test_condensation_action_validations_and_output() -> None:
    """Condensation actions should validate and present state correctly."""
    with pytest.raises(ValueError):
        CondensationAction(
            forgotten_event_ids=[1, 2],
            forgotten_events_start_id=1,
            forgotten_events_end_id=2,
        )

    summary_action = CondensationAction(
        forgotten_event_ids=[7, 9], summary="summarised", summary_offset=5
    )
    range_action = CondensationAction(
        forgotten_events_start_id=1, forgotten_events_end_id=3
    )

    assert summary_action.message == "Summary: summarised"
    assert range_action.forgotten == [1, 2, 3]
    assert "Condenser is dropping the events" in range_action.message


def test_agent_action_messages_cover_variants() -> None:
    """Exercise message helpers across the agent action classes."""
    assert (
        AgentFinishAction(final_thought="done", thought="Explained.").message
        == "Explained."
    )
    assert AgentRejectAction(outputs={"reason": "Not feasible"}).message.endswith(
        "Reason: Not feasible"
    )
    assert (
        ChangeAgentStateAction(agent_state="running").message
        == "Agent state changed to running"
    )
    assert (
        AgentDelegateAction(agent="helper", inputs={}).message
        == "I'm asking helper for help with this task."
    )
    assert RecallAction(
        recall_type=RecallType.WORKSPACE_CONTEXT, query="documentation"
    ).message.startswith("Retrieving content")
    assert "RecallAction" in str(
        RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT, query="docs")
    )
    assert (
        CondensationRequestAction().message
        == "Requesting a condensation of the conversation history."
    )


def test_task_tracking_action_messages_scale_with_tasks() -> None:
    """Task tracking message should reflect number of tasks."""
    assert TaskTrackingAction(task_list=[]).message == "Clearing the task list."
    assert (
        TaskTrackingAction(task_list=[{"title": "one"}]).message
        == "Managing 1 task item."
    )
    assert (
        TaskTrackingAction(task_list=[{"title": "one"}, {"title": "two"}]).message
        == "Managing 2 task items."
    )


def test_message_action_str_and_images_alias() -> None:
    """Legacy images_urls alias should synchronize with image_urls."""
    action = MessageAction(content="hi", image_urls=["img1"], file_urls=["file1"])
    action.images_urls = ["img2"]

    assert action.image_urls == ["img2"]
    rendered = str(action)
    assert "IMAGE_URL: img2" in rendered
    assert "FILE_URL: file1" in rendered
    assert action.message == "hi"


def test_system_and_streaming_message_actions_repr() -> None:
    """Ensure system and streaming actions provide informative strings."""
    system = SystemMessageAction(
        content="sys prompt", tools=[{"name": "tool"}], agent_class="AgentX"
    )
    system._source = EventSource.AGENT
    rendered = str(system)
    assert "TOOLS: 1 tools available" in rendered
    assert "AGENT_CLASS: AgentX" in rendered
    assert system.message == "sys prompt"

    chunk = StreamingChunkAction(
        chunk="hello", accumulated="hello world", is_final=True
    )
    output = str(chunk)
    assert "FINAL" in output
    assert "11 chars" in output


def test_browse_actions_render_context() -> None:
    """Check browse action helpers for message and string output."""
    browse_url = BrowseURLAction(
        url="https://example.com", thought="check docs", return_axtree=True
    )
    browse_interactive = BrowseInteractiveAction(
        browser_actions='click("submit")',
        thought="submit form",
        browsergym_send_msg_to_user="Submitting",
        return_axtree=True,
    )

    assert browse_url.message == "I am browsing the URL: https://example.com"
    assert "THOUGHT: check docs" in str(browse_url)
    assert "return_axtree" not in str(browse_url)

    assert 'click("submit")' in browse_interactive.message
    assert 'BROWSER_ACTIONS: click("submit")' in str(browse_interactive)


def test_agent_observations_messages_and_repr() -> None:
    """Cover message helpers for agent-related observations."""
    state_obs = AgentStateChangedObservation(content="", agent_state="paused")
    assert state_obs.message == ""

    think_obs = AgentThinkObservation(content="Considering options")
    assert think_obs.message == "Considering options"

    condensation_obs = AgentCondensationObservation(content="Summary")
    assert condensation_obs.message == "Summary"


def test_recall_observation_formats_workspace_details() -> None:
    knowledge = [
        MicroagentKnowledge(
            name="python_best_practices", trigger="python", content="Always lint."
        ),
        MicroagentKnowledge(name="git", trigger="git", content="Use branches."),
    ]
    recall = RecallObservation(
        content="knowledge",
        recall_type=RecallType.WORKSPACE_CONTEXT,
        repo_name="forge",
        repo_instructions="Keep tests green",
        runtime_hosts={"local": 1},
        additional_agent_instructions="Stay safe",
        date="2025-11-08",
        custom_secrets_descriptions={"API_KEY": "Used for requests"},
        conversation_instructions="Start from README",
        microagent_knowledge=knowledge,
    )

    assert recall.message == "Added workspace context"
    description = str(recall)
    assert "recall_type=RecallType.WORKSPACE_CONTEXT" in description
    assert "microagent_knowledge=python_best_practices, git" in description

    recall_microagent = RecallObservation(
        content="info",
        recall_type=RecallType.KNOWLEDGE,
        microagent_knowledge=knowledge[:1],
    )
    assert recall_microagent.message == "Added microagent knowledge"
    assert "RecallObservation" in str(recall_microagent)


def test_file_action_helpers_render_readable_output() -> None:
    """Exercise message/repr helpers on file actions."""
    read_action = FileReadAction(path="README.md")
    write_action = FileWriteAction(path="output.txt", content="hello world")
    edit_action_llm = FileEditAction(
        path="main.py",
        content="print('hi')",
        impl_source=FileEditSource.LLM_BASED_EDIT,
        thought="update print",
    )
    edit_action_aci = FileEditAction(
        path="main.py",
        command="insert",
        new_str="print('hi')",
        insert_line=10,
        impl_source=FileEditSource.OH_ACI,
    )

    assert "Reading file: README.md" == read_action.message
    assert "Writing file: output.txt" == write_action.message
    assert "L1:L-1" in repr(edit_action_llm)
    assert "Insert Line" in repr(edit_action_aci)
    assert "```\nhello world\n```" in repr(write_action)


def test_event_base_properties_cover_accessors() -> None:
    """Directly manipulate event core attributes to cover accessors."""

    class SimpleEvent(Event):
        def __init__(self) -> None:
            self.blocking = True

    event = SimpleEvent()
    event._message = None
    assert event.message is None
    del event._message
    assert event.message == ""

    event._id = 10
    event._sequence = 11
    event._source = EventSource.AGENT
    event._cause = 9

    assert event.id == 10
    assert event.sequence == 11
    assert event.source == EventSource.AGENT
    assert event.cause == 9

    assert event.timeout is None
    event.set_hard_timeout(5.5, blocking=False)
    assert pytest.approx(event.timeout or 0.0, rel=0, abs=1e-9) == 5.5
    assert event.blocking is False

    now = datetime.now(timezone.utc)
    event.timestamp = now
    assert event.timestamp == now.isoformat()

    metrics = Metrics()
    event.llm_metrics = metrics
    assert event.llm_metrics is metrics

    metadata = ToolCallMetadata(
        function_name="fn",
        tool_call_id="call-1",
        model_response={
            "id": "1",
            "choices": [],
            "created": 0,
            "model": "gpt-4",
            "object": "chat.completion",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        },
        total_calls_in_response=1,
    )
    event.tool_call_metadata = metadata
    assert event.tool_call_metadata == metadata

    event.response_id = "resp-123"
    assert event.response_id == "resp-123"
