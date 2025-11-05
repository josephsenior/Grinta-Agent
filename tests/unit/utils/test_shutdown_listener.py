import signal
from dataclasses import dataclass, field
from signal import Signals
from typing import Callable
from unittest.mock import MagicMock, patch
from uuid import UUID
import pytest
from openhands.utils import shutdown_listener
from openhands.utils.shutdown_listener import add_shutdown_listener, remove_shutdown_listener, should_continue


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
    with patch("openhands.utils.shutdown_listener.signal", mock_signal):
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
    with patch("openhands.utils.shutdown_listener.signal", mock_signal):
        mock_callable = MagicMock()
        add_shutdown_listener(mock_callable)
        shutdown_listener._register_signal_handler(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        mock_signal.trigger(signal.SIGTERM)
        assert mock_callable.call_count == 1


def test_remove_listener_during_shutdown():
    mock_signal = MockSignal()
    with patch("openhands.utils.shutdown_listener.signal", mock_signal):
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
