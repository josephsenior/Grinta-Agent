from __future__ import annotations

import asyncio
import signal
import time
from types import SimpleNamespace

import pytest

from forge.utils import shutdown_listener
from forge.utils import tenacity_stop
from forge.utils import term_color


def _reset_shutdown_listener() -> None:
    shutdown_listener._should_exit = None
    shutdown_listener._shutdown_listeners.clear()


def test_shutdown_listener_handles_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_shutdown_listener()
    captured = {}

    def fake_signal(sig, handler):
        captured["handler"] = handler
        return lambda *_: None

    monkeypatch.setattr(shutdown_listener, "HANDLED_SIGNALS", [signal.SIGINT])
    monkeypatch.setattr(shutdown_listener.signal, "signal", fake_signal)
    assert shutdown_listener.should_exit() is False

    called = False

    def listener():
        nonlocal called
        called = True

    listener_id = shutdown_listener.add_shutdown_listener(listener)
    captured["handler"](signal.SIGINT, None)
    assert shutdown_listener.should_exit() is True
    assert called is True
    assert shutdown_listener.should_continue() is False
    assert shutdown_listener.remove_shutdown_listener(listener_id) is True


def test_sleep_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_shutdown_listener()
    monkeypatch.setattr(shutdown_listener, "should_continue", lambda: False)
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    shutdown_listener.sleep_if_should_continue(0.5)

    # Exercise looped branch
    timings = [0.0, 0.5, 1.0, 1.5]
    monkeypatch.setattr(time, "time", lambda: timings.pop(0) if timings else 2.0)

    state = {"calls": 0}

    def should_continue_loop():
        state["calls"] += 1
        return state["calls"] < 2

    monkeypatch.setattr(shutdown_listener, "should_continue", should_continue_loop)
    shutdown_listener.sleep_if_should_continue(2)

    calls = []

    async def fake_sleep(duration):
        calls.append(duration)

    monkeypatch.setattr(shutdown_listener.asyncio, "sleep", fake_sleep)
    asyncio.run(shutdown_listener.async_sleep_if_should_continue(0.25))
    assert calls == [0.25]


def test_stop_if_should_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tenacity_stop, "should_exit", lambda: True)
    stopper = tenacity_stop.stop_if_should_exit()
    assert stopper(SimpleNamespace()) is True

    monkeypatch.setattr(tenacity_stop, "should_exit", lambda: False)
    assert stopper(SimpleNamespace()) is False


def test_term_color_colorize(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_colored(text, color):
        captured["text"] = text
        captured["color"] = color
        return f"<{color}>{text}"

    monkeypatch.setattr(term_color, "colored", fake_colored)
    result = term_color.colorize("hi", term_color.TermColor.INFO)
    assert result == "<blue>hi"
    assert captured == {"text": "hi", "color": "blue"}
