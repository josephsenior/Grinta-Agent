from unittest.mock import MagicMock
from forge.events.action import Action, ChangeAgentStateAction, CmdRunAction, MessageAction, NullAction
from forge.events.event import Event, EventSource
from forge.events.event_filter import EventFilter
from forge.events.observation import AgentStateChangedObservation, CmdOutputObservation, NullObservation
from forge.events.stream import EventStream
from forge.server.routes.manage_conversations import _get_contextual_events


def _prepare_event_kwargs(spec: dict) -> dict:
    """Prepare keyword arguments for event creation."""
    kwargs = _extract_base_kwargs(spec)
    event_type = spec["type"]

    # Apply type-specific defaults
    _apply_action_defaults(kwargs, spec, event_type)
    _apply_observation_defaults(kwargs, spec, event_type)

    return kwargs


def _extract_base_kwargs(spec: dict) -> dict:
    """Extract base keyword arguments from spec."""
    excluded_keys = ["type", "id", "source", "hidden", "cause"]
    return {k: v for k, v in spec.items() if k not in excluded_keys}


def _apply_action_defaults(kwargs: dict, spec: dict, event_type):
    """Apply defaults for action events."""
    if event_type == MessageAction:
        _apply_message_action_defaults(kwargs, spec)
    elif event_type == CmdRunAction:
        _apply_cmd_run_action_defaults(kwargs, spec)
    elif event_type == ChangeAgentStateAction:
        _apply_change_agent_state_defaults(kwargs, spec)
    elif event_type == NullAction:
        _apply_null_action_defaults(kwargs, spec)


def _apply_observation_defaults(kwargs: dict, spec: dict, event_type):
    """Apply defaults for observation events."""
    if event_type == CmdOutputObservation:
        _apply_cmd_output_observation_defaults(kwargs, spec)
    elif event_type == NullObservation:
        _apply_null_observation_defaults(kwargs, spec)
    elif event_type == AgentStateChangedObservation:
        _apply_agent_state_changed_defaults(kwargs, spec)


def _apply_message_action_defaults(kwargs: dict, spec: dict):
    """Apply defaults for MessageAction."""
    if "content" not in kwargs:
        kwargs["content"] = f"default_content_for_{spec['id']}"


def _apply_cmd_run_action_defaults(kwargs: dict, spec: dict):
    """Apply defaults for CmdRunAction."""
    if "command" not in kwargs:
        kwargs["command"] = f"default_command_for_{spec['id']}"


def _apply_cmd_output_observation_defaults(kwargs: dict, spec: dict):
    """Apply defaults for CmdOutputObservation."""
    if "content" not in kwargs:
        kwargs["content"] = f"default_obs_content_for_{spec['id']}"
    if "command_id" not in kwargs:
        kwargs["command_id"] = spec.get("cause", spec["id"] - 1 if spec["id"] > 0 else 0)
    if "command" not in kwargs:
        kwargs["command"] = f"default_cmd_for_obs_{spec['id']}"


def _apply_null_action_defaults(kwargs: dict, spec: dict):
    """Apply defaults for NullAction."""
    assert "content" not in kwargs


def _apply_null_observation_defaults(kwargs: dict, spec: dict):
    """Apply defaults for NullObservation."""
    kwargs["content"] = ""


def _apply_change_agent_state_defaults(kwargs: dict, spec: dict):
    """Apply defaults for ChangeAgentStateAction."""
    if "agent_state" not in kwargs:
        kwargs["agent_state"] = "running"
    if "thought" not in kwargs:
        kwargs["thought"] = ""


def _apply_agent_state_changed_defaults(kwargs: dict, spec: dict):
    """Apply defaults for AgentStateChangedObservation."""
    if "agent_state" not in kwargs:
        kwargs["agent_state"] = "running"


def _set_event_metadata(event: Event, spec: dict) -> None:
    """Set event metadata from spec."""
    event._id = spec["id"]
    default_source = EventSource.AGENT if issubclass(spec["type"], Action) else EventSource.USER
    event._source = spec.get("source", default_source)
    event._hidden = spec.get("hidden", False)
    if "cause" in spec:
        event._cause = spec["cause"]


def create_test_events(event_specs: list[dict]) -> list[Event]:
    """Create test events from specifications."""
    events = []
    for spec in event_specs:
        # Prepare event arguments
        kwargs = _prepare_event_kwargs(spec)

        # Create event
        event = spec["type"](**kwargs)

        # Set metadata
        _set_event_metadata(event, spec)

        events.append(event)
    return events


def test_get_contextual_events_basic_retrieval():
    """Tests basic retrieval of events, ensuring correct count, order, and string formatting.

    All events in this test are of types that are NOT filtered out by default.

    """
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 5
    context_size = 4
    all_event_specs = [
        {"id": 1, "type": MessageAction, "content": "message_1"},
        {"id": 2, "type": CmdRunAction, "command": "command_2"},
        {"id": 3, "type": CmdOutputObservation, "content": "observation_3", "command_id": 2, "command": "command_2"},
        {"id": 4, "type": MessageAction, "content": "message_4"},
        {"id": 5, "type": CmdRunAction, "command": "command_5_target"},
        {
            "id": 6,
            "type": CmdOutputObservation,
            "content": "observation_6",
            "command_id": 5,
            "command": "command_5_target",
        },
        {"id": 7, "type": MessageAction, "content": "message_7"},
        {"id": 8, "type": CmdRunAction, "command": "command_8"},
        {"id": 9, "type": CmdOutputObservation, "content": "observation_9", "command_id": 8, "command": "command_8"},
        {"id": 10, "type": MessageAction, "content": "message_10"},
        {"id": 11, "type": CmdRunAction, "command": "command_11"},
    ]
    all_events_objects = create_test_events(all_event_specs)
    events_by_id = {e.id: e for e in all_events_objects}
    events_to_return_before = [events_by_id[5], events_by_id[4], events_by_id[3], events_by_id[2]]
    events_to_return_after = [events_by_id[6], events_by_id[7], events_by_id[8], events_by_id[9], events_by_id[10]]
    mock_event_stream.search_events.side_effect = [events_to_return_before, events_to_return_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_final_event_objects = [
        events_by_id[2],
        events_by_id[3],
        events_by_id[4],
        events_by_id[5],
        events_by_id[6],
        events_by_id[7],
        events_by_id[8],
        events_by_id[9],
        events_by_id[10],
    ]
    expected_output_str = "\n".join((str(e) for e in expected_final_event_objects))
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    args_before, kwargs_before = calls[0]
    assert kwargs_before["start_id"] == target_event_id
    assert isinstance(kwargs_before["filter"], EventFilter)
    assert kwargs_before["reverse"] is True
    assert kwargs_before["limit"] == context_size
    args_after, kwargs_after = calls[1]
    assert kwargs_after["start_id"] == target_event_id + 1
    assert isinstance(kwargs_after["filter"], EventFilter)
    assert "reverse" not in kwargs_after or kwargs_after["reverse"] is False
    assert kwargs_after["limit"] == context_size + 1


def test_get_contextual_events_filtering():
    """Tests that specified event types and hidden events are filtered out."""
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 3
    all_event_specs = [
        {"id": 0, "type": NullAction},
        {"id": 1, "type": MessageAction, "content": "message_1_VISIBLE"},
        {"id": 2, "type": ChangeAgentStateAction, "agent_state": "thinking", "thought": "abc_FILTERED"},
        {"id": 3, "type": CmdRunAction, "command": "command_3_TARGET_VISIBLE"},
        {"id": 4, "type": CmdOutputObservation, "content": "obs_4_HIDDEN_FILTERED", "command_id": 3, "hidden": True},
        {"id": 5, "type": AgentStateChangedObservation, "agent_state": "running", "content": "state_change_5_FILTERED"},
        {"id": 6, "type": MessageAction, "content": "message_6_VISIBLE"},
        {"id": 7, "type": NullObservation, "content": "null_obs_7_FILTERED"},
        {"id": 8, "type": CmdRunAction, "command": "command_8_VISIBLE"},
        {"id": 9, "type": MessageAction, "content": "message_9_VISIBLE"},
        {"id": 10, "type": MessageAction, "content": "message_10_EXTRA"},
    ]
    all_events_objects = create_test_events(all_event_specs)
    events_by_id = {e.id: e for e in all_events_objects}
    [events_by_id[3], events_by_id[1]]
    simulated_search_before = [events_by_id[3], events_by_id[1]]
    simulated_search_after = [events_by_id[6], events_by_id[8], events_by_id[9]]
    mock_event_stream.search_events.side_effect = [simulated_search_before, simulated_search_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_final_event_objects = [events_by_id[1], events_by_id[3], events_by_id[6], events_by_id[8], events_by_id[9]]
    expected_output_str = "\n".join((str(e) for e in expected_final_event_objects))
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    expected_filtered_types = (NullAction, NullObservation, ChangeAgentStateAction, AgentStateChangedObservation)
    filter_before = calls[0][1]["filter"]
    assert isinstance(filter_before, EventFilter)
    assert filter_before.exclude_hidden is True
    assert set(filter_before.exclude_types) == set(expected_filtered_types)
    filter_after = calls[1][1]["filter"]
    assert isinstance(filter_after, EventFilter)
    assert filter_after.exclude_hidden is True
    assert set(filter_after.exclude_types) == set(expected_filtered_types)


def test_get_contextual_events_target_at_beginning():
    """Tests behavior when the target event_id is at the beginning of the stream,.

    resulting in fewer than context_size events before it.

    """
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 1
    context_size = 4
    all_event_specs = [
        {"id": 0, "type": MessageAction, "content": "message_0_first"},
        {"id": 1, "type": CmdRunAction, "command": "command_1_TARGET"},
        {"id": 2, "type": CmdOutputObservation, "content": "obs_2", "command_id": 1},
        {"id": 3, "type": MessageAction, "content": "message_3"},
        {"id": 4, "type": CmdRunAction, "command": "command_4"},
        {"id": 5, "type": CmdOutputObservation, "content": "obs_5", "command_id": 4},
        {"id": 6, "type": MessageAction, "content": "message_6"},
    ]
    all_events_objects = create_test_events(all_event_specs)
    events_by_id = {e.id: e for e in all_events_objects}
    simulated_search_before = [events_by_id[1], events_by_id[0]]
    simulated_search_after = [events_by_id[2], events_by_id[3], events_by_id[4], events_by_id[5], events_by_id[6]]
    mock_event_stream.search_events.side_effect = [simulated_search_before, simulated_search_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_final_event_objects = [
        events_by_id[0],
        events_by_id[1],
        events_by_id[2],
        events_by_id[3],
        events_by_id[4],
        events_by_id[5],
        events_by_id[6],
    ]
    expected_output_str = "\n".join((str(e) for e in expected_final_event_objects))
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    kwargs_before = calls[0][1]
    assert kwargs_before["start_id"] == target_event_id
    assert kwargs_before["limit"] == context_size
    kwargs_after = calls[1][1]
    assert kwargs_after["start_id"] == target_event_id + 1
    assert kwargs_after["limit"] == context_size + 1


def test_get_contextual_events_target_at_end():
    """Tests behavior when the target event_id is at the end of the stream,.

    resulting in fewer than context_size + 1 events after it.

    """
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 5
    context_size = 4
    all_event_specs = [
        {"id": 0, "type": MessageAction, "content": "message_0"},
        {"id": 1, "type": CmdRunAction, "command": "command_1"},
        {"id": 2, "type": CmdOutputObservation, "content": "obs_2", "command_id": 1},
        {"id": 3, "type": MessageAction, "content": "message_3"},
        {"id": 4, "type": CmdRunAction, "command": "command_4"},
        {"id": 5, "type": CmdOutputObservation, "content": "obs_5_TARGET", "command_id": 4},
        {"id": 6, "type": MessageAction, "content": "message_6_last"},
    ]
    all_events_objects = create_test_events(all_event_specs)
    events_by_id = {e.id: e for e in all_events_objects}
    simulated_search_before = [events_by_id[5], events_by_id[4], events_by_id[3], events_by_id[2]]
    simulated_search_after = [events_by_id[6]]
    mock_event_stream.search_events.side_effect = [simulated_search_before, simulated_search_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_final_event_objects = [events_by_id[2], events_by_id[3], events_by_id[4], events_by_id[5], events_by_id[6]]
    expected_output_str = "\n".join((str(e) for e in expected_final_event_objects))
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    kwargs_before = calls[0][1]
    assert kwargs_before["start_id"] == target_event_id
    assert kwargs_before["limit"] == context_size
    kwargs_after = calls[1][1]
    assert kwargs_after["start_id"] == target_event_id + 1
    assert kwargs_after["limit"] == context_size + 1


def test_get_contextual_events_empty_search_results():
    """Tests behavior when search_events returns empty lists for before and after."""
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 10
    context_size = 4
    simulated_search_before = []
    simulated_search_after = []
    mock_event_stream.search_events.side_effect = [simulated_search_before, simulated_search_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_output_str = ""
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    kwargs_before = calls[0][1]
    assert kwargs_before["start_id"] == target_event_id
    assert kwargs_before["limit"] == context_size
    kwargs_after = calls[1][1]
    assert kwargs_after["start_id"] == target_event_id + 1
    assert kwargs_after["limit"] == context_size + 1


def test_get_contextual_events_all_events_filtered():
    """Tests behavior when all events in the context window are of types.

    that should be filtered out.

    """
    mock_event_stream = MagicMock(spec=EventStream)
    target_event_id = 2
    simulated_search_before = []
    simulated_search_after = []
    mock_event_stream.search_events.side_effect = [simulated_search_before, simulated_search_after]
    result_str = _get_contextual_events(mock_event_stream, target_event_id)
    expected_output_str = ""
    assert result_str == expected_output_str
    calls = mock_event_stream.search_events.call_args_list
    assert len(calls) == 2
    filter_used = calls[0][1]["filter"]
    expected_filtered_types = (NullAction, NullObservation, ChangeAgentStateAction, AgentStateChangedObservation)
    assert isinstance(filter_used, EventFilter)
    assert filter_used.exclude_hidden is True
    assert set(filter_used.exclude_types) == set(expected_filtered_types)
