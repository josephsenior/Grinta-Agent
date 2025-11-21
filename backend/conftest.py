# mypy: ignore-errors

import sys
import os
import site
import importlib


def _sanitize_sys_path():
    repo_root = os.path.abspath(os.path.dirname(__file__))
    sys.path[:] = _filtered_sys_path(repo_root)
    _insert_site_packages()
    _prioritize_repo_root(repo_root)
    _preload_pydantic_root_model()
    _prefer_installed_mcp()


def _filtered_sys_path(repo_root: str) -> list[str]:
    tests_root = os.path.normcase(os.path.join(repo_root, "tests"))
    filtered: list[str] = []
    for path in sys.path:
        if not path:
            filtered.append(path)
            continue
        normalized = os.path.normcase(os.path.abspath(path))
        if _should_skip_test_path(normalized, tests_root):
            continue
        filtered.append(path)
    return filtered


def _should_skip_test_path(path: str, tests_root: str) -> bool:
    if not path.startswith(tests_root):
        return False
    return os.path.isdir(os.path.join(path, "mcp"))


def _insert_site_packages() -> None:
    for directory in reversed(_site_package_dirs()):
        if directory and directory not in sys.path:
            sys.path.insert(0, directory)


def _site_package_dirs() -> list[str]:
    dirs: list[str] = []
    try:
        dirs.extend(site.getsitepackages())
    except Exception:
        pass
    try:
        user_dir = site.getusersitepackages()
        if user_dir:
            dirs.append(user_dir)
    except Exception:
        pass
    return dirs


def _prioritize_repo_root(repo_root: str) -> None:
    if repo_root in sys.path:
        sys.path.remove(repo_root)
    sys.path.insert(0, repo_root)


def _preload_pydantic_root_model() -> None:
    try:
        import pydantic.root_model  # type: ignore  # noqa: F401
    except Exception:
        pass


def _prefer_installed_mcp() -> None:
    try:
        real_mcp = importlib.import_module("mcp")
    except ModuleNotFoundError:
        return
    _restrict_mcp_path(real_mcp)
    sys.modules["mcp"] = real_mcp


def _restrict_mcp_path(module: object) -> None:
    if not hasattr(module, "__path__"):
        return
    paths = [p for p in module.__path__ if "site-packages" in p]  # type: ignore[attr-defined]
    if paths:
        module.__path__ = paths  # type: ignore[attr-defined]


_sanitize_sys_path()
try:
    # Diagnostic: dump sanitized sys.path for pytest collection debugging.
    with open(os.path.join(os.path.dirname(__file__), "tmp_sys_path_after_sanitize.txt"), "w", encoding="utf-8") as f:
        for p in sys.path:
            f.write(p + "\n")
except Exception:
    pass
try:
    # Diagnostic: dump currently loaded `forge` modules (if any) to help
    # diagnose import shadowing during pytest collection.
    with open(os.path.join(os.path.dirname(__file__), "tmp_forge_sysmodules_initial.txt"), "w", encoding="utf-8") as f:
        for k in sorted(sys.modules.keys()):
            if k.startswith("forge"):
                mod = sys.modules.get(k)
                f.write(f"{k}: {getattr(mod, '__file__', None)}\n")
except Exception:
    pass

"""Early Docker SDK shim for collection safety.

This provides a robust stub when `docker` is missing or lacks expected
attributes (e.g., `docker.models`, `docker.errors`). The goal is to avoid
import-time AttributeErrors during test collection on hosts without Docker
installed. Actual runtime tests are skipped later when Docker isn't available.
"""
try:
    import types as _types
    import importlib as _importlib

    def _ensure_docker_shim():
        try:
            _docker_mod = _importlib.import_module("docker")  # type: ignore
        except Exception:
            _docker_mod = None

        # Build a stub module if missing or incomplete
        if _docker_mod is None or not hasattr(_docker_mod, "models") or not hasattr(_docker_mod, "errors"):
            docker = _types.ModuleType("docker")

            # errors submodule with common exceptions used in code/tests
            errors = _types.ModuleType("docker.errors")
            class DockerException(Exception):
                pass
            class APIError(DockerException):
                pass
            class NotFound(DockerException):
                pass
            class ImageNotFound(NotFound):
                pass
            errors.DockerException = DockerException
            errors.APIError = APIError
            errors.NotFound = NotFound
            errors.ImageNotFound = ImageNotFound

            # models submodule with containers and images
            models = _types.ModuleType("docker.models")
            containers_mod = _types.ModuleType("docker.models.containers")
            images_mod = _types.ModuleType("docker.models.images")

            class Container:
                def logs(self, *args, **kwargs):
                    return iter(())
            containers_mod.Container = Container

            class Image:
                pass
            images_mod.Image = Image

            # minimal client returned by from_env
            class _ContainersClient:
                def list(self, *args, **kwargs):
                    return []
                def get(self, *args, **kwargs):
                    raise NotFound("container not found")

            class _ImagesClient:
                def get(self, *args, **kwargs):
                    raise ImageNotFound("image not found")

            class _DockerClient:
                def __init__(self):
                    self.containers = _ContainersClient()
                    self.images = _ImagesClient()
                def close(self):
                    return None

            def from_env(*args, **kwargs):
                # Return a minimal client; tests often monkeypatch this anyway
                return _DockerClient()

            # Wire up the module tree
            docker.errors = errors
            docker.models = models
            models.containers = containers_mod
            models.images = images_mod
            docker.from_env = from_env

            # Register in sys.modules for both package and submodules
            sys.modules.setdefault("docker", docker)
            sys.modules.setdefault("docker.errors", errors)
            sys.modules.setdefault("docker.models", models)
            sys.modules.setdefault("docker.models.containers", containers_mod)
            sys.modules.setdefault("docker.models.images", images_mod)
            return

        # If a real docker module exists but lacks some attributes, patch them in
        if not hasattr(_docker_mod, "errors"):
            errors = _types.ModuleType("docker.errors")
            class DockerException(Exception):
                pass
            class APIError(DockerException):
                pass
            class NotFound(DockerException):
                pass
            class ImageNotFound(NotFound):
                pass
            errors.DockerException = DockerException
            errors.APIError = APIError
            errors.NotFound = NotFound
            errors.ImageNotFound = ImageNotFound
            setattr(_docker_mod, "errors", errors)
            sys.modules.setdefault("docker.errors", errors)

        if not hasattr(_docker_mod, "models"):
            models = _types.ModuleType("docker.models")
            setattr(_docker_mod, "models", models)
            sys.modules.setdefault("docker.models", models)

        # Ensure nested models submodules exist
        models_mod = getattr(_docker_mod, "models")
        if not hasattr(models_mod, "containers"):
            containers_mod = _types.ModuleType("docker.models.containers")
            class Container:
                def logs(self, *args, **kwargs):
                    return iter(())
            containers_mod.Container = Container
            setattr(models_mod, "containers", containers_mod)
            sys.modules.setdefault("docker.models.containers", containers_mod)
        if not hasattr(models_mod, "images"):
            images_mod = _types.ModuleType("docker.models.images")
            class Image:
                pass
            images_mod.Image = Image
            setattr(models_mod, "images", images_mod)
            sys.modules.setdefault("docker.models.images", images_mod)

        if not hasattr(_docker_mod, "from_env"):
            class _DockerClient:
                def __init__(self):
                    self.containers = _types.SimpleNamespace(list=lambda *a, **k: [], get=lambda *a, **k: (_ for _ in ()).throw(getattr(_docker_mod.errors, "NotFound")("container not found")))
                    self.images = _types.SimpleNamespace(get=lambda *a, **k: (_ for _ in ()).throw(getattr(_docker_mod.errors, "ImageNotFound")("image not found")))
                def close(self):
                    return None
            setattr(_docker_mod, "from_env", lambda *a, **k: _DockerClient())

    _ensure_docker_shim()
except Exception:
    pass

# Provide minimal LiteLLM type shims early in import lifecycle.
# Some environments/litellm versions may not export these names.
try:
    import litellm as _litellm_mod  # type: ignore

    if not hasattr(_litellm_mod, "ChatCompletionToolParamFunctionChunk"):
        class _ChatCompletionToolParamFunctionChunk(dict):
            def __init__(self, name: str, description: str | None = None, parameters: dict | None = None, strict: bool | None = None, **kwargs):
                data = {"name": name}
                if description is not None:
                    data["description"] = description
                if parameters is not None:
                    data["parameters"] = parameters
                if strict is not None:
                    data["strict"] = strict
                data.update(kwargs)
                super().__init__(data)
            def __getattr__(self, key):
                return self[key]
            def __setattr__(self, key, value):
                self[key] = value

        setattr(_litellm_mod, "ChatCompletionToolParamFunctionChunk", _ChatCompletionToolParamFunctionChunk)

    if not hasattr(_litellm_mod, "ChatCompletionToolParam"):
        class _ChatCompletionToolParam(dict):
            def __init__(self, function=None, type: str | None = None, **kwargs):
                data = {"type": type, "function": function}
                data.update(kwargs)
                super().__init__(data)
            def __getattr__(self, key):
                return self[key]
            def __setattr__(self, key, value):
                self[key] = value

        setattr(_litellm_mod, "ChatCompletionToolParam", _ChatCompletionToolParam)

    if not hasattr(_litellm_mod, "ModelInfo"):
        class _ModelInfo(dict):
            pass
        setattr(_litellm_mod, "ModelInfo", _ModelInfo)

    if not hasattr(_litellm_mod, "PromptTokensDetails"):
        class _PromptTokensDetails:
            def __init__(self, cached_tokens: int | None = None, **kwargs):
                self.cached_tokens = cached_tokens
        setattr(_litellm_mod, "PromptTokensDetails", _PromptTokensDetails)
except Exception:
    # If litellm truly isn't importable, tests that need it will skip or stub.
    pass

# Note: A more complete Docker shim is already established above; remove older minimal shim.
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

        res = subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return res.returncode == 0
    except Exception:
        return False


def pytest_configure(config):
    markers = ["docker", "windows", "optional", "heavy", "integration", "benchmark"]
    for m in markers:
        config.addinivalue_line("markers", f"{m}: mark test as {m}")


def _clear_forge_modules() -> None:
    """Aggressively clear any cached 'forge' modules before collecting a test.

    Some tests in this repository manipulate sys.modules at import time to stub
    out submodules (e.g., forge.events.observation). To prevent cross-module
    contamination during collection, clear any previously imported forge modules
    so each test module starts from a clean import state.
    """
    # Avoid clearing modules that register global side effects (e.g., Prometheus metrics)
    # which cannot be re-registered safely across repeated imports during collection.
    EXCLUDE_PREFIXES = (
        "forge.services.event_service",
    )
    try:
        for name in list(sys.modules.keys()):
            if name == "forge" or name.startswith("forge."):
                if any(name == p or name.startswith(p + ".") for p in EXCLUDE_PREFIXES):
                    continue
                sys.modules.pop(name, None)
    except Exception:
        pass


def pytest_collectstart(collector):
    # Called before starting collection of a node (including test modules).
    # Reset forge imports to avoid sys.modules pollution from previously imported tests.
    _clear_forge_modules()


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
    _apply_path_markers(items)
    context = _CollectionContext(
        docker_available=_docker_available(),
        is_windows=sys.platform.startswith("win"),
        run_tty_tests=os.environ.get("FORGE_RUN_TTY_TESTS", "0") == "1",
    )
    _apply_skip_markers(items, context)


def _apply_path_markers(items):
    for item in items:
        parts = {part.lower() for part in pathlib.Path(item.fspath).parts}
        _add_markers_to_item(item, parts)


class _CollectionContext:
    def __init__(self, docker_available: bool, is_windows: bool, run_tty_tests: bool):
        self.docker_available = docker_available
        self.is_windows = is_windows
        self.run_tty_tests = run_tty_tests


def _apply_skip_markers(items, context: "_CollectionContext") -> None:
    for item in items:
        for reason in _skip_reasons(item, context):
            item.add_marker(pytest.mark.skip(reason=reason))


def _skip_reasons(item, context: "_CollectionContext") -> Iterator[str]:
    if "docker" in item.keywords and not context.docker_available:
        yield "docker not available"
    if "windows" in item.keywords and not context.is_windows:
        yield "windows-specific test (not running on non-windows host)"
    if "tty" in item.keywords and not context.run_tty_tests:
        yield "tty tests disabled; set FORGE_RUN_TTY_TESTS=1 to enable"
    if not context.docker_available and _is_runtime_test(item):
        yield "runtime tests skipped: docker not available"


def _is_runtime_test(item) -> bool:
    return "runtime" in pathlib.Path(item.fspath).parts


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

        monkeypatch.setattr(
            "prompt_toolkit.output.win32.Win32Output", _DummyWin32Output, raising=False
        )
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
    monkeypatcher.setattr(
        forge_llm_module, "litellm_completion", _completion_stub, raising=False
    )
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
