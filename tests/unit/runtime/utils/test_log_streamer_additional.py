from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

# Stub docker module to avoid heavy dependency/import errors
docker_mod = sys.modules.setdefault("docker", types.ModuleType("docker"))
if not hasattr(docker_mod, "models"):
    setattr(
        docker_mod,
        "models",
        types.SimpleNamespace(
            containers=types.SimpleNamespace(Container=object),
        ),
    )

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.log_streamer",
    ROOT / "forge" / "runtime" / "utils" / "log_streamer.py",
)
assert spec and spec.loader
log_streamer_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.log_streamer"] = log_streamer_mod
spec.loader.exec_module(log_streamer_mod)

LogStreamer = log_streamer_mod.LogStreamer


class DummyThread:
    def __init__(self, target=None, args=(), kwargs=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.started = False
        self.join_called = False
        self.join_timeout = None
        self.daemon = False
        self._alive = False
        self._ran = False

    def start(self):
        self.started = True
        self._alive = True

    def run(self):
        if not self._ran and self.target:
            self._ran = True
            self.target(*self.args, **self.kwargs)

    def join(self, timeout=None):
        self.join_called = True
        self.join_timeout = timeout
        self._alive = False

    def is_alive(self):
        return self._alive


class DummyGenerator:
    def __init__(self, lines, error: Exception | None = None):
        self._lines = list(lines)
        self._error = error
        self._raised = False
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._lines:
            return self._lines.pop(0)
        if self._error and not self._raised:
            self._raised = True
            raise self._error
        raise StopIteration

    def close(self):
        self.closed = True


class DummyContainer:
    def __init__(self, return_value):
        self.return_value = return_value
        self.call_kwargs = None
        self.logs_called = False

    def logs(self, **kwargs):
        self.logs_called = True
        self.call_kwargs = kwargs
        if isinstance(self.return_value, Exception):
            raise self.return_value
        return self.return_value


class Recorder:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []
        self.streamer = None

    def __call__(self, level: str, message: str):
        self.messages.append((level, message))


class StopRecorder(Recorder):
    def __call__(self, level: str, message: str):
        super().__call__(level, message)
        if "[inside container] first" in message and self.streamer is not None:
            self.streamer._stop_event.set()


@pytest.fixture
def patch_thread(monkeypatch):
    monkeypatch.setattr(
        log_streamer_mod,
        "threading",
        types.SimpleNamespace(
            Thread=DummyThread, Event=log_streamer_mod.threading.Event
        ),
    )
    yield


@pytest.mark.asyncio
async def test_log_streamer_streams_logs(monkeypatch, patch_thread):
    generator = DummyGenerator([b"first line\n", b"second line"])
    container = DummyContainer(generator)
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]

    assert container.logs_called
    assert ("debug", "[inside container] first line") in recorder.messages
    assert ("debug", "[inside container] second line") in recorder.messages
    streamer.close()
    assert generator.closed


@pytest.mark.asyncio
async def test_log_streamer_handles_initialization_failure(monkeypatch, patch_thread):
    container = DummyContainer(RuntimeError("boom"))
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)

    assert ("error", "Failed to initialize log streaming: boom") in recorder.messages
    assert streamer.stdout_thread is None


@pytest.mark.asyncio
async def test_log_streamer_handles_stream_error(monkeypatch, patch_thread):
    error = RuntimeError("stream failure")
    generator = DummyGenerator([b"line\n"], error=error)
    container = DummyContainer(generator)
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]

    assert any(
        "stream failure" in message
        for level, message in recorder.messages
        if level == "error"
    )


@pytest.mark.asyncio
async def test_log_streamer_close_joins_thread_and_closes_generator(patch_thread):
    generator = DummyGenerator([b"only line\n"])
    container = DummyContainer(generator)
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]
    thread = streamer.stdout_thread
    assert isinstance(thread, DummyThread)
    assert thread.started

    streamer.close(timeout=2.5)
    assert thread.join_called
    assert thread.join_timeout == 2.5
    assert generator.closed


@pytest.mark.asyncio
async def test_log_streamer_log_generator_missing(patch_thread):
    container = DummyContainer(None)
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]

    assert ("error", "Log generator not initialized") in recorder.messages


def test_log_streamer_destructor_calls_close(monkeypatch, patch_thread):
    generator = DummyGenerator([])
    container = DummyContainer(generator)
    recorder = Recorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]
    invoked = []

    def fake_close(self, timeout=5):
        invoked.append(timeout)

    monkeypatch.setattr(LogStreamer, "close", fake_close)
    # Ensure thread appears alive so __del__ invokes close
    streamer.stdout_thread._alive = True  # type: ignore[attr-defined]
    streamer.__del__()
    assert invoked == [5]


def test_log_streamer_respects_stop_event(patch_thread):
    generator = DummyGenerator([b"first\n", b"second\n"])
    container = DummyContainer(generator)
    recorder = StopRecorder()

    streamer = LogStreamer(container, recorder)
    recorder.streamer = streamer
    streamer.stdout_thread.run()  # type: ignore[attr-defined]

    assert any(
        "first" in message for level, message in recorder.messages if level == "debug"
    )
    assert not any(
        "second" in message for level, message in recorder.messages if level == "debug"
    )
