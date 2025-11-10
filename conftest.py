import asyncio
import inspect
import pathlib
import importlib
import os
import shutil
import sys
import time
from collections.abc import Iterator

import pytest


@pytest.fixture
def event_loop():
    """Provide a fresh event loop for async tests without requiring pytest-asyncio."""

    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        if not loop.is_closed():
            loop.close()


def pytest_pyfunc_call(pyfuncitem):
    """Execute coroutine tests by driving them with an event loop."""

    if inspect.iscoroutinefunction(pyfuncitem.obj):
        loop = pyfuncitem.funcargs.get("event_loop")  # type: ignore[attr-defined]
        owns_loop = False
        if loop is None:
            loop = asyncio.new_event_loop()
            owns_loop = True

        try:
            asyncio.set_event_loop(loop)
            fixture_names = getattr(pyfuncitem, "_fixtureinfo").argnames
            test_kwargs = {name: pyfuncitem.funcargs[name] for name in fixture_names}
            loop.run_until_complete(pyfuncitem.obj(**test_kwargs))
        finally:
            asyncio.set_event_loop(None)
            if owns_loop and not loop.is_closed():
                loop.close()
        return True
    return None


def _has_pkg(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:
        return False


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        import subprocess

        res = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def pytest_configure(config):
    markers = ["docker", "windows", "optional", "heavy", "integration", "benchmark"]
    for m in markers:
        config.addinivalue_line("markers", f"{m}: mark test as {m}")


@pytest.fixture
def require_pkg(request):
    """Fixture to skip a test if a package is missing.

    Usage: def test_foo(require_pkg): require_pkg('reportlab')
    """

    def _require(name: str):
        if not _has_pkg(name):
            pytest.skip(f"skipping test, missing required package: {name}")

    return _require


def _is_benchmark_test(parts):
    """Check if test is a benchmark test based on path parts."""
    return "evaluation" in parts or "benchmarks" in parts or "benchmark" in parts


def _is_heavy_test(parts):
    """Check if test is a heavy test based on path parts."""
    return "third_party" in parts or "external" in parts


def _is_integration_test(parts):
    """Check if test is an integration test based on path parts."""
    return "tests" in parts and ("e2e" in parts or "integration" in parts)


def _add_markers_to_item(item, parts):
    """Add appropriate markers to test item based on path parts."""
    if _is_benchmark_test(parts):
        item.add_marker(pytest.mark.benchmark)
        item.add_marker(pytest.mark.heavy)

    if _is_heavy_test(parts):
        item.add_marker(pytest.mark.heavy)

    if _is_integration_test(parts):
        item.add_marker(pytest.mark.integration)


def pytest_collection_modifyitems(config, items):
    """Modify test items by adding markers and applying skips."""
    # Add markers based on file paths
    for item in items:
        path = pathlib.Path(item.fspath)
        parts = {p.lower() for p in path.parts}
        _add_markers_to_item(item, parts)

    # Apply conditional skips
    docker_ok = _docker_available()
    is_windows = sys.platform.startswith("win")
    run_tty_tests = os.environ.get("FORGE_RUN_TTY_TESTS", "0") == "1"
    for item in items:
        if "docker" in item.keywords and (not docker_ok):
            item.add_marker(pytest.mark.skip(reason="docker not available"))
        if "windows" in item.keywords and (not is_windows):
            item.add_marker(pytest.mark.skip(reason="windows-specific test (not running on non-windows host)"))
        if "tty" in item.keywords and (not run_tty_tests):
            item.add_marker(pytest.mark.skip(reason="tty tests disabled; set FORGE_RUN_TTY_TESTS=1 to enable"))


@pytest.fixture(autouse=True)
def use_repo_root_cwd(tmp_path, monkeypatch):
    """Autouse fixture that sets CWD to repository root for the test run.

    It uses the location of this conftest.py as a hint: repo root is the parent
    directory of the `Forge` package directory. This is intentionally
    conservative and only changes cwd for the duration of each test.
    """
    repo_root = pathlib.Path(__file__).resolve().parent
    try:
        assert repo_root.exists()
        monkeypatch.chdir(str(repo_root))
        yield
    finally:
        pass


@pytest.fixture(autouse=True)
def stub_win32_output_on_windows(monkeypatch):
    """On Windows CI or non-console test environments, prompt_toolkit's.

    Win32 output classes try to access the real console and raise
    NoConsoleScreenBufferError. Provide a minimal stub to avoid requiring a
    real console during unit tests.

    This fixture is conservative: it only patches the specific Win32 class if
    prompt_toolkit is importable and the Win32 output class exists.
    """
    try:
        import sys

        if not sys.platform.startswith("win"):
            yield
            return
        try:
            from prompt_toolkit.output.base import Output
        except Exception:
            yield
            return

        class _DummyWin32Output(Output):
            """A minimal Win32Output-like stub. Tests only need a few methods.

            such as get_size(), write(), flush, and basic cursor/screen
            manipulation. All methods are no-ops for tests.
            """

            def __init__(self, *args, **kwargs):
                self._size = (80, 24)

            def get_size(self):
                return self._size

            def write(self, data):
                return None

            def flush(self):
                return None

            def restore(self):
                return None

            def erase_screen(self):
                return None

            def clear(self):
                return None

            def hide_cursor(self):
                return None

            def show_cursor(self):
                return None

            def enable_mouse_support(self):
                return None

            def disable_mouse_support(self):
                return None

            def set_title(self, title: str):
                return None

            def cursor_goto(self, x: int, y: int):
                return None

            def enable_alternate_screen_buffer(self):
                return None

            def disable_alternate_screen_buffer(self):
                return None

            def write_raw(self, data: bytes):
                return None

        monkeypatch.setattr("prompt_toolkit.output.win32.Win32Output", _DummyWin32Output, raising=False)
        try:
            from prompt_toolkit.output.defaults import DummyOutput

            monkeypatch.setattr(
                "prompt_toolkit.output.defaults.create_output",
                lambda stdout=None, always_prefer_tty=False: DummyOutput(),
                raising=False,
            )
        except Exception:
            pass
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True, scope="session")
def mock_litellm() -> Iterator[None]:
    """Provide deterministic LiteLLM completions during tests to avoid real API calls."""

    try:
        import litellm
        from litellm.types.utils import ModelResponse
        from forge.llm import llm as forge_llm_module
    except Exception:
        # If LiteLLM or the Forge LLM module is unavailable, skip mocking.
        yield
        return

    def _extract_messages(args, kwargs):
        messages = kwargs.get("messages")
        if messages is None and args:
            messages = args[0]
        return messages

    def _build_response(messages=None, model=None):
        content = "Mock response"
        if isinstance(messages, list):
            for message in reversed(messages):
                if isinstance(message, dict):
                    payload = message.get("content")
                    if isinstance(payload, str) and payload.strip():
                        content = f"Mock response: {payload.strip()}"
                        break
        data = {
            "id": "mock-response-id",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model or "mock-model",
            "system_fingerprint": "mock-fingerprint",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        return ModelResponse.model_validate(data)

    def _stream_generator(messages, model):
        response = _build_response(messages=messages, model=model)
        content = response.choices[0]["message"]["content"]
        yield {
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": None,
                }
            ],
            "model": response.model,
        }
        yield {
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
            "model": response.model,
        }

    def _completion_stub(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        model = kwargs.get("model")
        if kwargs.get("stream"):
            return _stream_generator(messages, model)
        return _build_response(messages=messages, model=model)

    async def _acompletion_stub(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        model = kwargs.get("model")
        if kwargs.get("stream"):
            async def _async_gen():
                for chunk in _stream_generator(messages, model):
                    yield chunk

            return _async_gen()
        return _build_response(messages=messages, model=model)

    def _streaming_stub(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        model = kwargs.get("model")
        return _stream_generator(messages, model)

    monkeypatcher = pytest.MonkeyPatch()
    monkeypatcher.setattr(litellm, "completion", _completion_stub)
    monkeypatcher.setattr(litellm, "acompletion", _acompletion_stub)
    monkeypatcher.setattr(litellm, "stream", _streaming_stub, raising=False)
    monkeypatcher.setattr(litellm, "streaming", _streaming_stub, raising=False)
    monkeypatcher.setattr(forge_llm_module, "litellm_completion", _completion_stub, raising=False)
    try:
        yield
    finally:
        monkeypatcher.undo()


@pytest.fixture(autouse=True, scope="session")
def set_dummy_llm_env() -> Iterator[None]:
    """Ensure LLM-related environment variables exist so config validation passes."""

    env_defaults = {
        "LLM_API_KEY": "test_key",
        "OPENAI_API_KEY": "test_key",
        "LITELLM_API_KEY": "test_key",
        "ANTHROPIC_API_KEY": "test_key",
    }
    monkeypatcher = pytest.MonkeyPatch()
    for key, value in env_defaults.items():
        if not os.environ.get(key):
            monkeypatcher.setenv(key, value)
    try:
        yield
    finally:
        monkeypatcher.undo()


# ---------------------------------------------------------------------------
# Runtime test helpers
# ---------------------------------------------------------------------------
try:
    from tests.runtime.conftest import _close_test_runtime as _runtime_close  # type: ignore
    from tests.runtime.conftest import _load_runtime as _runtime_load  # type: ignore
except Exception:  # pragma: no cover - optional dependency for runtime tests
    def _load_runtime(*args, **kwargs):  # type: ignore[override]
        pytest.skip("runtime test helpers are unavailable in this environment")

    def _close_test_runtime(*args, **kwargs):  # type: ignore[override]
        return None
else:
    globals().setdefault("_load_runtime", _runtime_load)
    globals().setdefault("_close_test_runtime", _runtime_close)

__all__ = [
    "event_loop",
    "pytest_pyfunc_call",
    "require_pkg",
    "use_repo_root_cwd",
    "stub_win32_output_on_windows",
    "mock_litellm",
    "set_dummy_llm_env",
]

if "_load_runtime" in globals():
    __all__.extend(["_load_runtime", "_close_test_runtime"])
