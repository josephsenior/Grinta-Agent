"""Unit tests for browsing agent utility helpers."""

from __future__ import annotations

import json

import pytest

from forge.agenthub.browsing_agent import utils


@pytest.fixture
def sample_html() -> str:
    return """
    <html>
        <head>
            <title>Example Page</title>
        </head>
        <body>
            <h1>Heading</h1>
            <p>First paragraph.</p>
            <div>
                <p>Second paragraph.</p>
            </div>
        </body>
    </html>
    """


def test_page_parser_extracts_title_and_text(sample_html: str) -> None:
    parser = utils.PageParser(sample_html)

    assert parser.extract_title() == "Example Page"
    text = parser.extract_text()
    # Ensure newline separation keeps logical ordering
    assert "Heading" in text
    assert "First paragraph." in text
    assert "Second paragraph." in text


def test_page_parser_handles_missing_title() -> None:
    parser = utils.PageParser("<html><body>No title here.</body></html>")

    assert parser.extract_title() == ""
    assert parser.extract_text() == "No title here."
    assert parser.to_dict() == {"title": "", "content": "No title here."}


def test_prompt_builder_concatenates_fragments() -> None:
    builder = utils.PromptBuilder()
    builder.add_fragment(utils.BrowsingPromptFragment(name="intro", content="Hello"))
    builder.add_fragment(utils.BrowsingPromptFragment(name="details", content="World"))

    prompt = builder.build()
    assert prompt == "Hello\n\nWorld"


def test_parse_error_response_round_trip() -> None:
    payload = {"message": "Bad Request", "reason": "Malformed JSON"}
    encoded = json.dumps(payload)

    error = utils.parse_error_response(encoded)
    assert isinstance(error, utils.ErrorResponse)
    assert error.message == "Bad Request"
    assert error.reason == "Malformed JSON"
