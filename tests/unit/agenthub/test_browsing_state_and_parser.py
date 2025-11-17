"""Tests covering browsing state tracking and response parser behaviour."""

from __future__ import annotations

import ast

import pytest

from typing import cast

from forge.agenthub.browsing_agent import response_parser
from forge.agenthub.browsing_agent.state_tracker import BrowsingStateTracker
from forge.events.action import BrowseInteractiveAction


def test_state_tracker_records_visits_and_interactions() -> None:
    tracker = BrowsingStateTracker(session_id="sess-1", goal="Collect info")
    tracker.visit_page("https://example.com", title="Example")
    tracker.track_interaction("btn-login", "click")
    tracker.track_form_data("email", "user@example.com")
    tracker.track_error("Timeout")

    assert tracker.session.current_url == "https://example.com"
    assert tracker.was_visited("https://example.com")
    assert tracker.get_visited_count("https://example.com") == 1
    assert tracker.get_last_form_data() == {"email": "user@example.com"}
    assert tracker.can_go_back() is False

    tracker.visit_page("https://example.com/dashboard")
    assert tracker.can_go_back() is True
    assert tracker.get_previous_url() == "https://example.com"

    context_summary = tracker.get_context_summary()
    assert "Goal: Collect info" in context_summary
    assert "Recent Errors" in context_summary

    stats = tracker.get_stats()
    assert stats["pages_visited"] == 1
    assert stats["unique_urls"] == 2
    assert stats["forms_filled"] == 1
    assert stats["errors"] == 1


@pytest.mark.parametrize(
    "action_text, expected_message",
    [
        ('Taking a look```click("11")```', ""),
        ("Message only with no code", "Message only with no code"),
    ],
)
def test_response_parser_generates_actions(
    action_text: str, expected_message: str
) -> None:
    parser = response_parser.BrowsingResponseParser()
    action = parser.parse(action_text)

    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions
    if expected_message:
        assert expected_message in action.browsergym_send_msg_to_user


def test_response_parser_handles_structured_response() -> None:
    parser = response_parser.BrowsingResponseParser()
    structured = cast(
        dict[str, list[dict[str, dict[str, str | None]]]],
        {
            "choices": [
                {
                    "message": {
                        "content": "Thinking```noop()```",
                    }
                }
            ]
        },
    )
    action = parser.parse(structured)
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions == "noop()"


def test_browsing_action_parser_handles_send_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = response_parser.BrowsingActionParserBrowseInteractive()
    action_str = 'Thought```send_msg_to_user("hello")```'

    action = parser.parse(action_str)
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browser_actions == 'send_msg_to_user("hello")'
    assert action.browsergym_send_msg_to_user == "hello"

    # trigger fallback regex path
    bad_action = '```send_msg_to_user("invalid"'

    def _raise_syntax_error(*args, **kwargs):
        raise SyntaxError("bad")

    monkeypatch.setattr(ast, "parse", _raise_syntax_error)
    action = parser.parse(f"Thought{bad_action}")
    assert isinstance(action, BrowseInteractiveAction)
    assert action.browsergym_send_msg_to_user == ""
