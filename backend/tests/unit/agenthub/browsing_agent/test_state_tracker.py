"""Tests for BrowsingStateTracker session management utilities."""

from __future__ import annotations

import re
from time import sleep

import pytest

from forge.agenthub.browsing_agent.state_tracker import BrowsingStateTracker


@pytest.fixture
def tracker() -> BrowsingStateTracker:
    return BrowsingStateTracker(session_id="session-123", goal="Find documentation")


def test_visit_page_tracks_navigation_history(tracker: BrowsingStateTracker) -> None:
    tracker.visit_page("https://example.com", title="Example")
    assert tracker.session.current_url == "https://example.com"
    assert tracker.session.navigation_path == ["https://example.com"]
    assert tracker.current_page and tracker.current_page.title == "Example"

    tracker.visit_page("https://example.com/docs")
    # previous page moved to visited_pages
    assert len(tracker.session.visited_pages) == 1
    assert tracker.session.visited_pages[0].url == "https://example.com"
    assert tracker.session.navigation_path == [
        "https://example.com",
        "https://example.com/docs",
    ]


def test_track_interaction_and_form_data(tracker: BrowsingStateTracker) -> None:
    tracker.visit_page("https://example.com/form")

    tracker.track_interaction("submit-button", action_type="click")
    tracker.track_form_data("email", "user@example.com")

    assert tracker.current_page
    assert tracker.current_page.elements_interacted == ["click:submit-button"]
    assert tracker.current_page.form_data == {"email": "user@example.com"}
    # Session level memory should also include last form value
    assert tracker.get_last_form_data() == {"email": "user@example.com"}

    # Returned dict is a copy
    form_snapshot = tracker.get_last_form_data()
    form_snapshot["email"] = "modified"
    assert tracker.session.form_fields_filled["email"] == "user@example.com"


def test_track_error_marks_current_page(tracker: BrowsingStateTracker) -> None:
    tracker.visit_page("https://example.com")
    tracker.track_error("Timeout while loading resource")

    assert tracker.session.errors_encountered == ["Timeout while loading resource"]
    assert tracker.current_page is not None and tracker.current_page.success is False


def test_navigation_history_helpers(tracker: BrowsingStateTracker) -> None:
    tracker.visit_page("https://example.com")
    tracker.visit_page("https://example.com/docs")
    tracker.visit_page("https://example.com/docs/tutorial")

    assert tracker.was_visited("https://example.com")
    assert tracker.get_visited_count("https://example.com") == 1
    assert tracker.can_go_back() is True
    assert tracker.get_previous_url() == "https://example.com/docs"


def test_get_context_summary_includes_key_sections(
    tracker: BrowsingStateTracker,
) -> None:
    tracker.visit_page("https://example.com")
    tracker.track_form_data("query", "python testing best practices")
    tracker.track_error("404 Not Found")

    summary = tracker.get_context_summary()
    assert "## Browsing Context" in summary
    assert "Goal: Find documentation" in summary
    assert "Pages visited: 0" in summary  # only current page, none archived yet
    assert "- query: python testing best practices" in summary
    assert re.search(r"## Recent Errors: 1", summary)


def test_get_stats_reports_session_metrics(tracker: BrowsingStateTracker) -> None:
    tracker.visit_page("https://example.com")
    tracker.track_form_data("q", "pytest fixtures")
    tracker.track_error("network unstable")
    sleep(0.01)  # ensure non-zero duration

    stats = tracker.get_stats()
    assert stats["pages_visited"] == 0  # only current page, not archived
    assert stats["unique_urls"] == 1
    assert stats["forms_filled"] == 1
    assert stats["errors"] == 1
    assert stats["duration_seconds"] >= 0.0
