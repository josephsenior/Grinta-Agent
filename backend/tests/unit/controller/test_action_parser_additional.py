"""Tests for forge.controller.action_parser abstraction utilities."""

from __future__ import annotations

from forge.controller.action_parser import (
    ActionParseError,
    ActionParser,
    ResponseParser,
)
from forge.events.action import Action


class DummyAction(Action):
    """Minimal Action subclass for testing."""

    runnable = False


class ConcreteParser(ResponseParser):
    """Concrete implementation for testing abstract base class behavior."""

    def parse(self, response):
        return self.parse_action(self.parse_response(response))

    def parse_response(self, response):
        return str(response)

    def parse_action(self, action_str):
        parser = next(
            (p for p in self.action_parsers if p.check_condition(action_str)),
            None,
        )
        if not parser:
            raise ActionParseError("no parser")
        return parser.parse(action_str)


class ConcreteActionParser(ActionParser):
    """Concrete ActionParser for tests."""

    def check_condition(self, action_str: str) -> bool:
        return action_str == "ok"

    def parse(self, action_str: str) -> Action:
        return DummyAction()


def test_action_parse_error_str():
    """ActionParseError should expose its message via __str__."""
    err = ActionParseError("failure")
    assert str(err) == "failure"


def test_response_parser_dispatches_to_action_parser():
    """Concrete ResponseParser should iterate through registered ActionParsers."""
    parser = ConcreteParser()
    parser.action_parsers.append(ConcreteActionParser())
    action = parser.parse("ok")
    assert isinstance(action, DummyAction)


def test_response_parser_raises_when_no_parser_matched():
    """An ActionParseError should be raised when no parser matches the response."""
    parser = ConcreteParser()
    try:
        parser.parse("not-ok")
    except ActionParseError as exc:
        assert "no parser" in str(exc)
    else:
        raise AssertionError("Expected ActionParseError")
