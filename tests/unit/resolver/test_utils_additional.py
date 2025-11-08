"""Additional unit tests for forge.resolver.utils."""

from __future__ import annotations

import builtins
import io
import logging
from types import SimpleNamespace
from unittest import mock

import pytest

from forge.events.action import MessageAction
from forge.events.event import EventSource
from forge.integrations.service_types import ProviderType
from forge.resolver import utils


@pytest.mark.asyncio
async def test_identify_token_success(monkeypatch):
    async def fake_validate(secret, base_domain):
        assert secret.get_secret_value() == "token-value"
        assert base_domain == "custom.example.com"
        return ProviderType.GITHUB

    monkeypatch.setattr(utils, "validate_provider_token", fake_validate)
    provider = await utils.identify_token("token-value", "custom.example.com")
    assert provider is ProviderType.GITHUB


@pytest.mark.asyncio
async def test_identify_token_invalid(monkeypatch):
    async def fake_validate(secret, base_domain):
        return None

    monkeypatch.setattr(utils, "validate_provider_token", fake_validate)
    with pytest.raises(ValueError, match="Token is invalid."):
        await utils.identify_token("invalid", None)


def test_codeact_user_response_base_message():
    state = SimpleNamespace(history=[])
    msg = utils.codeact_user_response(state, encapsulate_solution=True)
    assert "<solution>" in msg
    assert "IMPORTANT" in msg


def test_codeact_user_response_exit(monkeypatch):
    message = MessageAction(content="hello")
    message._source = EventSource.AGENT
    state = SimpleNamespace(history=[message])

    def fake_try_parse(action):
        return "done"

    result = utils.codeact_user_response(state, encapsulate_solution=False, try_parse=fake_try_parse)
    assert result == "/exit"


def test_codeact_user_response_giveup_option():
    user_msg1 = MessageAction(content="Hi")
    user_msg1._source = EventSource.USER
    user_msg2 = MessageAction(content="Need help")
    user_msg2._source = EventSource.USER
    state = SimpleNamespace(history=[user_msg1, user_msg2])

    response = utils.codeact_user_response(state)
    assert "<execute_bash> exit </execute_bash>" in response


def test_cleanup_terminates_children(monkeypatch):
    process = mock.Mock()
    monkeypatch.setattr(utils.mp, "active_children", lambda: [process])

    with mock.patch.object(utils.logger, "info") as info_mock:
        utils.cleanup()
        process.terminate.assert_called_once()
        process.join.assert_called_once()
        assert any("Cleaning up child processes" in str(call.args[0]) for call in info_mock.call_args_list)


def test_reset_logger_for_multiprocessing(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    fake_console_handler = logging.NullHandler()
    logger_obj = logging.getLogger("resolver-test-logger")
    logger_obj.handlers = [logging.StreamHandler()]

    monkeypatch.setattr(utils, "get_console_handler", lambda: fake_console_handler)

    created_files = {}

    class DummyFileHandler(logging.Handler):
        def __init__(self, filename):
            super().__init__()
            created_files["path"] = filename

    monkeypatch.setattr(logging, "FileHandler", DummyFileHandler)

    utils.reset_logger_for_multiprocessing(logger_obj, "42", str(log_dir))

    # Console handler added then removed, only file handler should remain
    assert len(logger_obj.handlers) == 1
    assert isinstance(logger_obj.handlers[0], DummyFileHandler)

    expected_path = log_dir / "instance_42.log"
    assert created_files["path"] == str(expected_path)

    logger_obj.handlers = []


def test_extract_image_urls():
    text = "![alt](https://example.com/image.png) and ![b](http://foo/bar.jpg)"
    urls = utils.extract_image_urls(text)
    assert urls == ["https://example.com/image.png", "http://foo/bar.jpg"]


def test_get_unique_uid(monkeypatch):
    passwd_content = io.StringIO("root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000::/home/user:/bin/sh\n")

    def fake_open(path, mode="r", encoding=None):
        assert path == "/etc/passwd"
        return passwd_content

    monkeypatch.setattr(builtins, "open", fake_open)
    uid = utils.get_unique_uid(start_uid=1000)
    assert uid == 1001

