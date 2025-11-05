from openhands.events.action.agent import CondensationAction, CondensationRequestAction
from openhands.events.action.message import MessageAction
from openhands.events.event import Event
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.memory.view import View


def test_view_preserves_uncondensed_lists() -> None:
    """Tests that the view preserves event lists that don't contain condensation actions."""
    events: list[Event] = [MessageAction(content=f"Event {i}") for i in range(5)]
    set_ids(events)
    view = View.from_events(events)
    assert len(view) == 5
    assert view.events == events


def test_view_forgets_events() -> None:
    """Tests that views drop forgotten events and the condensation actions."""
    events: list[Event] = [
        *[MessageAction(content=f"Event {i}") for i in range(5)],
        CondensationAction(forgotten_event_ids=[0, 1, 2, 3, 4]),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.events == []


def test_view_keeps_non_forgotten_events() -> None:
    """Tests that views keep non-forgotten events."""
    for forgotten_event_id in range(5):
        events: list[Event] = [
            *[MessageAction(content=f"Event {i}") for i in range(5)],
            CondensationAction(forgotten_event_ids=[forgotten_event_id]),
        ]
        set_ids(events)
        view = View.from_events(events)
        assert view.events == events[:forgotten_event_id] + events[forgotten_event_id + 1: 5]


def test_view_inserts_summary() -> None:
    """Tests that views insert a summary observation at the specified offset."""
    for offset in range(5):
        events: list[Event] = [
            *[MessageAction(content=f"Event {i}") for i in range(5)],
            CondensationAction(forgotten_event_ids=[], summary="My Summary", summary_offset=offset),
        ]
        set_ids(events)
        view = View.from_events(events)
        assert len(view) == 6
        for index, event in enumerate(view):
            print(index, event.content)
            if index == offset:
                assert isinstance(event, AgentCondensationObservation)
                assert event.content == "My Summary"
            elif index < offset:
                assert isinstance(event, MessageAction)
                assert event.content == f"Event {index}"
            else:
                assert isinstance(event, MessageAction)
                assert event.content == f"Event {index - 1}"


def test_no_condensation_action_in_view() -> None:
    """Ensure that CondensationAction events are never present in the resulting view."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        MessageAction(content="Event 1"),
        CondensationAction(forgotten_event_ids=[0]),
        MessageAction(content="Event 2"),
        MessageAction(content="Event 3"),
    ]
    set_ids(events)
    view = View.from_events(events)
    for event in view:
        assert not isinstance(event, CondensationAction)
    assert len(view) == 3


def test_unhandled_condensation_request_with_no_condensation() -> None:
    """Test that unhandled_condensation_request is True when there's a CondensationRequestAction but no CondensationAction."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        MessageAction(content="Event 1"),
        CondensationRequestAction(),
        MessageAction(content="Event 2"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is True
    assert len(view) == 3
    for event in view:
        assert not isinstance(event, CondensationRequestAction)


def test_handled_condensation_request_with_condensation_action() -> None:
    """Test that unhandled_condensation_request is False when CondensationAction comes after CondensationRequestAction."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        MessageAction(content="Event 1"),
        CondensationRequestAction(),
        MessageAction(content="Event 2"),
        CondensationAction(forgotten_event_ids=[0, 1]),
        MessageAction(content="Event 3"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is False
    assert len(view) == 2
    for event in view:
        assert not isinstance(event, CondensationRequestAction)
        assert not isinstance(event, CondensationAction)


def test_multiple_condensation_requests_pattern() -> None:
    """Test the pattern with multiple condensation requests and actions."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        CondensationRequestAction(),
        MessageAction(content="Event 1"),
        CondensationAction(forgotten_event_ids=[0]),
        MessageAction(content="Event 2"),
        CondensationRequestAction(),
        MessageAction(content="Event 3"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is True
    assert len(view) == 3
    for event in view:
        assert not isinstance(event, CondensationRequestAction)
        assert not isinstance(event, CondensationAction)


def test_condensation_action_before_request() -> None:
    """Test that CondensationAction before CondensationRequestAction doesn't affect the unhandled status."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        CondensationAction(forgotten_event_ids=[]),
        MessageAction(content="Event 1"),
        CondensationRequestAction(),
        MessageAction(content="Event 2"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is True
    assert len(view) == 3
    for event in view:
        assert not isinstance(event, CondensationRequestAction)
        assert not isinstance(event, CondensationAction)


def test_no_condensation_events() -> None:
    """Test that unhandled_condensation_request is False when there are no condensation events."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        MessageAction(content="Event 1"),
        MessageAction(content="Event 2"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is False
    assert len(view) == 3
    assert view.events == events


def test_only_condensation_action() -> None:
    """Test behavior when there's only a CondensationAction (no request)."""
    events: list[Event] = [
        MessageAction(content="Event 0"),
        MessageAction(content="Event 1"),
        CondensationAction(forgotten_event_ids=[0]),
        MessageAction(content="Event 2"),
    ]
    set_ids(events)
    view = View.from_events(events)
    assert view.unhandled_condensation_request is False
    assert len(view) == 2
    for event in view:
        assert not isinstance(event, CondensationAction)


def test_condensation_request_always_removed_from_view() -> None:
    """Test that CondensationRequestAction is always removed from the view regardless of unhandled status."""
    events_unhandled: list[Event] = [
        MessageAction(content="Event 0"),
        CondensationRequestAction(),
        MessageAction(content="Event 1"),
    ]
    set_ids(events_unhandled)
    view_unhandled = View.from_events(events_unhandled)
    assert view_unhandled.unhandled_condensation_request is True
    assert len(view_unhandled) == 2
    for event in view_unhandled:
        assert not isinstance(event, CondensationRequestAction)
    events_handled: list[Event] = [
        MessageAction(content="Event 0"),
        CondensationRequestAction(),
        MessageAction(content="Event 1"),
        CondensationAction(forgotten_event_ids=[]),
        MessageAction(content="Event 2"),
    ]
    set_ids(events_handled)
    view_handled = View.from_events(events_handled)
    assert view_handled.unhandled_condensation_request is False
    assert len(view_handled) == 3
    for event in view_handled:
        assert not isinstance(event, CondensationRequestAction)
        assert not isinstance(event, CondensationAction)


def set_ids(events: list[Event]) -> None:
    """Set the IDs of the events in the list to their index."""
    for i, e in enumerate(events):
        e._id = i
