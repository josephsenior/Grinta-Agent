"""Tests for `forge.llm.debug_mixin.DebugMixin`."""

from __future__ import annotations

from logging import DEBUG, Logger
from types import SimpleNamespace

import pytest

from forge.llm.debug_mixin import DebugMixin, MESSAGE_SEPARATOR


class DummyLogger:
    def __init__(self) -> None:
        self.enabled = True
        self.messages: list[str] = []

    def isEnabledFor(self, level):  # noqa: N802 - match logging API
        return self.enabled and level == DEBUG

    def debug(self, message, *args, **kwargs):  # noqa: D401 - logging signature
        if args or kwargs:
            message = message % args if args else message.format(**kwargs)
        self.messages.append(message)


class DummyMixin(DebugMixin):
    def __init__(self, prompt_logger, response_logger, debug=False):
        super().__init__(debug=debug)
        self._prompt_logger = prompt_logger
        self._response_logger = response_logger

    def vision_is_active(self) -> bool:
        return False


def test_log_prompt_emits_joined_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_logger = DummyLogger()
    response_logger = DummyLogger()
    main_logger = DummyLogger()
    monkeypatch.setattr("forge.llm.debug_mixin.llm_prompt_logger", prompt_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.llm_response_logger", response_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.logger", main_logger)

    mixin = DummyMixin(prompt_logger, response_logger)
    messages = [{"content": "one"}, {"content": "two"}]
    mixin.log_prompt(messages)

    assert prompt_logger.messages[0] == MESSAGE_SEPARATOR.join(["one", "two"])


def test_log_response_handles_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_logger = DummyLogger()
    response_logger = DummyLogger()
    main_logger = DummyLogger()
    monkeypatch.setattr("forge.llm.debug_mixin.llm_prompt_logger", prompt_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.llm_response_logger", response_logger)
    monkeypatch.setattr("forge.llm.debug_mixin.logger", main_logger)

    mixin = DummyMixin(prompt_logger, response_logger)
    response = {
        "choices": [
            {
                "message": {
                    "content": "message",
                    "tool_calls": [
                        SimpleNamespace(function=SimpleNamespace(name="fn", arguments="{}")),
                    ],
                }
            }
        ]
    }
    mixin.log_response(response)
    assert "Function call: fn({})" in response_logger.messages[0]

