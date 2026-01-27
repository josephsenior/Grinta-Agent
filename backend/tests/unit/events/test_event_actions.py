import pytest

from forge.core.schemas import ActionType
from forge.events.action.action import ActionConfirmationStatus, ActionSecurityRisk
from forge.events.action.agent import (
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
from forge.events.action.commands import CmdRunAction
from forge.events.action.empty import NullAction
from forge.events.action.files import FileEditAction, FileReadAction, FileWriteAction
from forge.events.action.mcp import MCPAction
from forge.events.action.message import (
    MessageAction,
    StreamingChunkAction,
    SystemMessageAction,
)
from forge.events.event import EventSource, FileEditSource, FileReadSource, RecallType


def test_basic_agent_actions_generate_expected_messages_and_strings():
    state_action = ChangeAgentStateAction(agent_state="review")
    assert state_action.message == "Agent state changed to review"

    finish_action = AgentFinishAction(thought="We are done")
    assert finish_action.message == "We are done"
    fallback_finish = AgentFinishAction()
    assert fallback_finish.message.startswith("All done")

    think_action = AgentThinkAction(thought="Need more context")
    assert think_action.message == "I am thinking...: Need more context"

    reject_action = AgentRejectAction(outputs={"reason": "Insufficient data"})
    assert "Insufficient data" in reject_action.message

    recall_action = RecallAction(
        recall_type=RecallType.KNOWLEDGE, query="How to tests" * 5
    )
    assert "Retrieving content" in recall_action.message
    assert "RecallAction" in str(recall_action)


def test_condensation_action_validations_and_forgotten_ids():
    summary_action = CondensationAction(
        forgotten_event_ids=[1, 2, 3],
        summary="Summarized events",
        summary_offset=5,
    )
    assert summary_action.forgotten == [1, 2, 3]
    assert summary_action.message == "Summary: Summarized events"

    range_action = CondensationAction(
        forgotten_events_start_id=3, forgotten_events_end_id=5
    )
    assert range_action.forgotten == [3, 4, 5]
    assert "Condenser is dropping" in range_action.message

    with pytest.raises(ValueError):
        CondensationAction(
            forgotten_event_ids=[1],
            forgotten_events_start_id=2,
            forgotten_events_end_id=3,
        )

    with pytest.raises(ValueError):
        CondensationAction(forgotten_event_ids=[1], summary="missing offset")


def test_condensation_request_message_and_task_tracking_counts():
    request_action = CondensationRequestAction()
    assert (
        request_action.message
        == "Requesting a condensation of the conversation history."
    )

    empty_tracking = TaskTrackingAction(task_list=[])
    assert empty_tracking.message == "Clearing the task list."

    single_tracking = TaskTrackingAction(task_list=[{"title": "todo"}])
    assert single_tracking.message == "Managing 1 task item."

    multi_tracking = TaskTrackingAction(
        task_list=[{"title": "todo"}, {"title": "done"}]
    )
    assert multi_tracking.message == "Managing 2 task items."


def test_browse_actions_include_context_in_message_and_string():
    browse_url = BrowseURLAction(url="https://example.com", thought="Check docs")
    assert browse_url.message.endswith("https://example.com")
    assert "BrowseURLAction" in str(browse_url)

    browse_interactive = BrowseInteractiveAction(
        browser_actions="click('#submit')", thought="Submit form"
    )
    assert "browser" in browse_interactive.message
    string_repr = str(browse_interactive)
    assert "BROWSER_ACTIONS" in string_repr
    assert "Submit form" in string_repr


def test_command_actions_format_messages_and_strings():
    cmd_action = CmdRunAction(command="ls", thought="List files", blocking=True)
    cmd_action._source = EventSource.AGENT
    cmd_action.set_hard_timeout(10, blocking=True)
    assert cmd_action.message == "Running command: ls"
    assert "CmdRunAction" in str(cmd_action)
    assert cmd_action.timeout == 10


def test_null_file_actions_and_messages():
    null_action = NullAction()
    assert null_action.message == "No action"
    assert null_action.action == ActionType.NULL

    read_action = FileReadAction(path="file.txt")
    assert read_action.message == "Reading file: file.txt"
    assert read_action.impl_source is FileReadSource.DEFAULT

    write_action = FileWriteAction(path="file.txt", content="data", thought="save")
    assert write_action.message == "Writing file: file.txt"
    assert "**FileWriteAction**" in repr(write_action)


def test_file_edit_action_repr_switches_on_impl_source():
    llm_edit = FileEditAction(
        path="main.py",
        content="print('hello')",
        impl_source=FileEditSource.LLM_BASED_EDIT,
        thought="Add greeting",
    )
    llm_repr = repr(llm_edit)
    assert "Range: [L" in llm_repr
    assert "Content:" in llm_repr

    aci_edit = FileEditAction(
        path="main.py",
        command="str_replace",
        old_str="foo",
        new_str="bar",
        impl_source=FileEditSource.FILE_EDITOR,
    )
    aci_repr = repr(aci_edit)
    assert "Old String" in aci_repr
    assert "New String" in aci_repr


def test_file_edit_action_repr_covers_all_command_variants():
    create_repr = repr(
        FileEditAction(
            path="created.py",
            command="create",
            file_text="print('new')",
            impl_source=FileEditSource.FILE_EDITOR,
        )
    )
    assert "Created File with Text" in create_repr

    insert_repr = repr(
        FileEditAction(
            path="insert.py",
            command="insert",
            new_str="line",
            insert_line=3,
            impl_source=FileEditSource.FILE_EDITOR,
        )
    )
    assert "Insert Line" in insert_repr

    undo_repr = repr(
        FileEditAction(
            path="undo.py",
            command="undo_edit",
            impl_source=FileEditSource.FILE_EDITOR,
        )
    )
    assert "Undo Edit" in undo_repr


def test_mcp_action_formatting():
    action = MCPAction(name="tool-name", arguments={"input": 1}, thought="Need tool")
    assert "MCP server" in action.message
    string_repr = str(action)
    assert "NAME: tool-name" in string_repr
    assert "ARGUMENTS: {'input': 1}" in string_repr


def test_message_actions_support_attachments_and_wait_flag():
    action = MessageAction(
        content="Hello world", image_urls=["img"], file_urls=["file"]
    )
    action._source = EventSource.USER
    assert action.message == "Hello world"
    action.images_urls = ["new.png"]
    assert action.image_urls == ["new.png"]
    output = str(action)
    assert "IMAGE_URL: new.png" in output
    assert "FILE_URL: file" in output

    system = SystemMessageAction(
        content="System prompt", tools=["tool-a"], agent_class="Builder"
    )
    system._source = EventSource.ENVIRONMENT
    assert system.message == "System prompt"
    assert "SystemMessageAction" in str(system)


def test_streaming_chunk_action_str_contains_state():
    chunk = StreamingChunkAction(chunk="hi", accumulated="hi", is_final=False)
    assert "STREAMING" in str(chunk)
    final_chunk = StreamingChunkAction(accumulated="done", is_final=True)
    assert "FINAL" in str(final_chunk)


def test_security_risk_enum_and_confirmation_status_are_ints():
    assert isinstance(ActionSecurityRisk.HIGH.value, int)
    assert ActionConfirmationStatus.REJECTED.value == "rejected"
