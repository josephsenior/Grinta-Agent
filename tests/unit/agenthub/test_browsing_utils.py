"""Unit tests for browsing agent utility helpers."""

from __future__ import annotations

import json

import pytest

from forge.agenthub.browsing_agent import utils as browsing_utils
from forge.agenthub.browsing_agent import browsing_agent


def test_get_error_prefix_formats_message() -> None:
    message = browsing_agent.get_error_prefix("click('1')")
    assert "incorrect" in message
    assert "click('1')" in message


@pytest.mark.parametrize(
    ("goal", "action_space"),
    [
        ("Find the product price", "click, type"),
        ("Navigate to login", "nav-only"),
    ],
)
def test_get_system_message_includes_goal_and_actions(goal: str, action_space: str) -> None:
    system_message = browsing_agent.get_system_message(goal, action_space)
    assert goal in system_message
    assert action_space in system_message
    assert system_message.startswith("# Instructions")


def test_get_prompt_adds_concise_instruction(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(browsing_agent, "USE_CONCISE_ANSWER", True, raising=False)
    prompt = browsing_agent.get_prompt("error", "http://example.com", "tree", "prev")
    assert "error" in prompt
    assert "http://example.com" in prompt
    assert "tree" in prompt
    assert "prev" in prompt
    assert "chain of thought of a valid action when providing a concise answer" in prompt


def test_page_parser_extracts_title_and_text() -> None:
    html = "<html><head><title>Sample</title></head><body><p>Hello</p><p>World</p></body></html>"
    parser = browsing_utils.PageParser(html)

    assert parser.extract_title() == "Sample"
    text_content = parser.extract_text()
    assert "Hello" in text_content
    assert "World" in text_content
    assert parser.to_dict() == {"title": "Sample", "content": text_content}


def test_prompt_builder_builds_from_fragments() -> None:
    fragment = browsing_utils.BrowsingPromptFragment(name="intro", content="Hello")
    builder = browsing_utils.PromptBuilder()
    builder.add_fragment(fragment)
    builder.add_fragment(
        browsing_utils.BrowsingPromptFragment(name="body", content="World", metadata={"kind": "body"})
    )

    assert builder.build() == "Hello\n\nWorld"


def test_parse_error_response_returns_dataclass() -> None:
    data = {"message": "Invalid action", "reason": "Missing bid"}
    error = browsing_utils.parse_error_response(json.dumps(data))

    assert error.message == "Invalid action"
    assert error.reason == "Missing bid"

