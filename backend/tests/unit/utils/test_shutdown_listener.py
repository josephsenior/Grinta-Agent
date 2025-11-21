import signal
from dataclasses import dataclass, field
from signal import Signals
from typing import Callable
from unittest.mock import MagicMock, patch
from uuid import UUID
import pytest
from forge.utils import shutdown_listener
from forge.utils.shutdown_listener import (
    add_shutdown_listener,
    async_sleep_if_should_continue,
    remove_shutdown_listener,
    should_continue,
    sleep_if_should_continue,
)


@pytest.fixture(autouse=True)
def cleanup_listeners():
    shutdown_listener._shutdown_listeners.clear()
    shutdown_listener._should_exit = False


@dataclass
class MockSignal:
    handlers: dict[Signals, Callable] = field(default_factory=dict)

    def signal(self, signalnum: Signals, handler: Callable):
        result = self.handlers.get(signalnum)
        self.handlers[signalnum] = handler
        return result

    def trigger(self, signalnum: Signals):
        if handler := self.handlers.get(signalnum):
            handler(signalnum.value, None)


def test_add_shutdown_listener():
    mock_callable = MagicMock()
    listener_id = add_shutdown_listener(mock_callable)
    assert isinstance(listener_id, UUID)
    assert listener_id in shutdown_listener._shutdown_listeners
    assert shutdown_listener._shutdown_listeners[listener_id] == mock_callable


def test_remove_shutdown_listener():
    mock_callable = MagicMock()
    listener_id = add_shutdown_listener(mock_callable)
    assert remove_shutdown_listener(listener_id) is True
    assert listener_id not in shutdown_listener._shutdown_listeners
    assert remove_shutdown_listener(listener_id) is False


def test_signal_handler_calls_listeners():
    mock_signal = MockSignal()
    with patch("forge.utils.shutdown_listener.signal", mock_signal):
        mock_callable1 = MagicMock()
        mock_callable2 = MagicMock()
        add_shutdown_listener(mock_callable1)
        add_shutdown_listener(mock_callable2)
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        mock_callable1.assert_called_once()
        mock_callable2.assert_called_once()
        assert should_continue() is False


def test_listeners_called_only_once():
    mock_signal = MockSignal()
    with patch("forge.utils.shutdown_listener.signal", mock_signal):
        mock_callable = MagicMock()
        add_shutdown_listener(mock_callable)
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        assert mock_callable.call_count == 1


def test_remove_listener_during_shutdown():
    mock_signal = MockSignal()
    with patch("forge.utils.shutdown_listener.signal", mock_signal):
        mock_callable1 = MagicMock()
        mock_callable2 = MagicMock()
        listener1_id = add_shutdown_listener(mock_callable1)

        def remove_other_listener():
            remove_shutdown_listener(listener1_id)
            mock_callable2()

        add_shutdown_listener(remove_other_listener)
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        assert mock_callable1.call_count == 1
        assert mock_callable2.call_count == 1


def test_signal_handler_logs_exception(monkeypatch):
    mock_signal = MockSignal()
    logger = MagicMock()
    with patch("forge.utils.shutdown_listener.signal", mock_signal):
        monkeypatch.setattr(shutdown_listener, "logger", logger)
        add_shutdown_listener(MagicMock(side_effect=RuntimeError("boom")))
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        logger.exception.assert_called_once()


def test_register_signal_handlers_non_main_thread(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr(shutdown_listener, "logger", logger)
    monkeypatch.setattr(shutdown_listener, "_should_exit", None)
    monkeypatch.setattr(shutdown_listener.threading, "current_thread", lambda: object())
    monkeypatch.setattr(shutdown_listener.threading, "main_thread", lambda: object())
    monkeypatch.setattr(shutdown_listener, "_register_signal_handler", MagicMock())
    shutdown_listener._register_signal_handlers()
    shutdown_listener._register_signal_handler.assert_not_called()
    logger.debug.assert_any_call("_register_signal_handlers")
    logger.debug.assert_any_call("_register_signal_handlers:not_main_thread")


def test_register_signal_handlers_main_thread(monkeypatch):
    monkeypatch.setattr(shutdown_listener, "_should_exit", None)
    monkeypatch.setattr(shutdown_listener.threading, "current_thread", lambda: "main")
    monkeypatch.setattr(shutdown_listener.threading, "main_thread", lambda: "main")
    mock_register = MagicMock()
    monkeypatch.setattr(shutdown_listener, "_register_signal_handler", mock_register)
    monkeypatch.setattr(shutdown_listener, "HANDLED_SIGNALS", [signal.SIGTERM])
    shutdown_listener._register_signal_handlers()
    mock_register.assert_called_once_with(signal.SIGTERM)


def test_sleep_if_should_continue_long(monkeypatch):
    times = iter([0, 0.5, 1.1])
    monkeypatch.setattr(shutdown_listener.time, "time", lambda: next(times))
    monkeypatch.setattr(shutdown_listener.time, "sleep", lambda _: None)
    outcomes = iter([True, False])
    monkeypatch.setattr(shutdown_listener, "should_continue", lambda: next(outcomes))
    sleep_if_should_continue(2)


@pytest.mark.asyncio
async def test_async_sleep_if_should_continue_long(monkeypatch):
    times = iter([0, 0.5, 1.1])
    monkeypatch.setattr(shutdown_listener.time, "time", lambda: next(times))

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(shutdown_listener.asyncio, "sleep", fake_sleep)
    outcomes = iter([True, False])
    monkeypatch.setattr(shutdown_listener, "should_continue", lambda: next(outcomes))
    await async_sleep_if_should_continue(2)


def test_sleep_if_should_continue_short(monkeypatch):
    slept = []
    monkeypatch.setattr(
        shutdown_listener.time, "sleep", lambda value: slept.append(value)
    )
    sleep_if_should_continue(0.5)
    assert slept == [0.5]


@pytest.mark.asyncio
async def test_async_sleep_if_should_continue_short(monkeypatch):
    calls = []

    async def fake_sleep(value):
        calls.append(value)

    monkeypatch.setattr(shutdown_listener.asyncio, "sleep", fake_sleep)
    await async_sleep_if_should_continue(0.5)
    assert calls == [0.5]


def test_should_exit_and_continue(monkeypatch):
    monkeypatch.setattr(shutdown_listener, "_register_signal_handlers", lambda: None)
    monkeypatch.setattr(shutdown_listener, "_should_exit", True)
    assert shutdown_listener.should_exit() is True
    monkeypatch.setattr(shutdown_listener, "_should_exit", False)
    assert shutdown_listener.should_continue() is True


def test_register_signal_handler_invokes_original(monkeypatch):
    mock_signal = MockSignal()
    original_called = []

    def original(sig, frame):
        original_called.append((sig, frame))

    mock_signal.handlers[signal.SIGTERM] = original
    with patch("forge.utils.shutdown_listener.signal", mock_signal):
        monkeypatch.setattr(shutdown_listener, "should_continue", lambda: True)
        shutdown_listener._should_exit = False
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        assert original_called
        assert shutdown_listener._should_exit is True
