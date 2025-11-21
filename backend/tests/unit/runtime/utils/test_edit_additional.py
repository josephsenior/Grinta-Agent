from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Sequence, Type, cast

import pytest


# Stub minimal dependencies before importing module
if "forge.core.logger" not in sys.modules:
    logger_stub = types.ModuleType("forge.core.logger")

    class DummyLogger:
        def __getattr__(self, name: str) -> Callable[..., None]:
            return lambda *args, **kwargs: None

    setattr(logger_stub, "forge_logger", DummyLogger())
    sys.modules["forge.core.logger"] = logger_stub


if "forge.events.action" not in sys.modules:
    action_stub = types.ModuleType("forge.events.action")

    class FileEditAction:
        def __init__(
            self, path: str, start: int = 1, end: int = -1, content: str = ""
        ) -> None:
            self.path = path
            self.start = start
            self.end = end
            self.content = content

    class FileWriteAction(FileEditAction):
        pass

    class FileReadAction:
        def __init__(self, path: str) -> None:
            self.path = path

    class IPythonRunCellAction:
        def __init__(self, code: str) -> None:
            self.code = code

    setattr(action_stub, "FileEditAction", FileEditAction)
    setattr(action_stub, "FileWriteAction", FileWriteAction)
    setattr(action_stub, "FileReadAction", FileReadAction)
    setattr(action_stub, "IPythonRunCellAction", IPythonRunCellAction)
    sys.modules["forge.events.action"] = action_stub


if "forge.events.observation" not in sys.modules:
    observation_stub = types.ModuleType("forge.events.observation")

    class Observation:
        def __init__(self, content: str = "") -> None:
            self.content = content

    class FileEditObservation(Observation):
        def __init__(
            self,
            content: str,
            path: str,
            prev_exist: bool,
            old_content: str,
            new_content: str,
        ) -> None:
            super().__init__(content)
            self.path = path
            self.prev_exist = prev_exist
            self.old_content = old_content
            self.new_content = new_content

        def visualize_diff(self, change_applied: bool = True) -> str:
            return self.content

    class FileWriteObservation(Observation):
        pass

    class FileReadObservation(Observation):
        pass

    class ErrorObservation(Observation):
        pass

    setattr(observation_stub, "Observation", Observation)
    setattr(observation_stub, "FileEditObservation", FileEditObservation)
    setattr(observation_stub, "FileWriteObservation", FileWriteObservation)
    setattr(observation_stub, "FileReadObservation", FileReadObservation)
    setattr(observation_stub, "ErrorObservation", ErrorObservation)
    sys.modules["forge.events.observation"] = observation_stub


if "forge.linter" not in sys.modules:
    linter_stub = types.ModuleType("forge.linter")

    class DefaultLinter:
        def lint_file_diff(self, old: str, new: str) -> Sequence[Any]:
            return []

    setattr(linter_stub, "DefaultLinter", DefaultLinter)
    sys.modules["forge.linter"] = linter_stub


if "forge.utils.chunk_localizer" not in sys.modules:
    chunk_stub = types.ModuleType("forge.utils.chunk_localizer")

    class Chunk:
        def __init__(self, text: str):
            self.text = text
            self.line_range = (0, 0)
            self.normalized_lcs = 1.0

        def visualize(self) -> str:
            return self.text

    def get_top_k_chunk_matches(*args: Any, **kwargs: Any) -> list[Chunk]:
        return []

    setattr(chunk_stub, "Chunk", Chunk)
    setattr(chunk_stub, "get_top_k_chunk_matches", get_top_k_chunk_matches)
    sys.modules["forge.utils.chunk_localizer"] = chunk_stub

agenthub_pkg = sys.modules.setdefault(
    "forge.agenthub", types.ModuleType("forge.agenthub")
)
assert isinstance(agenthub_pkg, types.ModuleType)
agenthub_pkg.__path__ = []
codeact_pkg = sys.modules.setdefault(
    "forge.agenthub.codeact_agent", types.ModuleType("forge.agenthub.codeact_agent")
)
assert isinstance(codeact_pkg, types.ModuleType)
codeact_pkg.__path__ = []
setattr(agenthub_pkg, "codeact_agent", codeact_pkg)

tools_stub = sys.modules.setdefault(
    "forge.agenthub.codeact_agent.tools",
    types.ModuleType("forge.agenthub.codeact_agent.tools"),
)
assert isinstance(tools_stub, types.ModuleType)
if not hasattr(tools_stub, "LLMBasedFileEditTool"):

    class LLMBasedFileEditTool: ...

    setattr(tools_stub, "LLMBasedFileEditTool", LLMBasedFileEditTool)
setattr(codeact_pkg, "tools", tools_stub)

fc_stub = sys.modules.setdefault(
    "forge.agenthub.codeact_agent.function_calling",
    types.ModuleType("forge.agenthub.codeact_agent.function_calling"),
)
assert isinstance(fc_stub, types.ModuleType)
if not hasattr(fc_stub, "response_to_actions"):

    def response_to_actions(response):
        return []

    setattr(fc_stub, "response_to_actions", response_to_actions)
setattr(codeact_pkg, "function_calling", fc_stub)

llm_pkg = sys.modules.setdefault("forge.llm", types.ModuleType("forge.llm"))
assert isinstance(llm_pkg, types.ModuleType)
llm_pkg.__path__ = []
llm_utils_stub = sys.modules.setdefault(
    "forge.llm.llm_utils", types.ModuleType("forge.llm.llm_utils")
)
assert isinstance(llm_utils_stub, types.ModuleType)
if not hasattr(llm_utils_stub, "check_tools"):
    setattr(llm_utils_stub, "check_tools", lambda tools, config: tools)
setattr(llm_pkg, "llm_utils", llm_utils_stub)

action_mod = sys.modules["forge.events.action"]
observation_mod = sys.modules["forge.events.observation"]
linter_mod = sys.modules["forge.linter"]
chunk_mod = sys.modules["forge.utils.chunk_localizer"]

FileEditActionType = cast(type, getattr(action_mod, "FileEditAction"))
FileWriteObservationType = cast(Any, getattr(observation_mod, "FileWriteObservation"))
FileReadObservationType = cast(Any, getattr(observation_mod, "FileReadObservation"))
ErrorObservationType = cast(Any, getattr(observation_mod, "ErrorObservation"))
ObservationType = cast(Any, getattr(observation_mod, "Observation"))


MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "forge" / "runtime" / "utils" / "edit.py"
)
spec = importlib.util.spec_from_file_location("forge.runtime.utils.edit", MODULE_PATH)
assert spec and spec.loader
edit_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.edit"] = edit_mod
spec.loader.exec_module(edit_mod)
if TYPE_CHECKING:
    from forge.runtime.utils.edit import (
        FileEditRuntimeMixin as FileEditRuntimeMixinType,
    )
    from forge.llm.llm_registry import LLMRegistry
else:
    FileEditRuntimeMixinType = cast(type, getattr(edit_mod, "FileEditRuntimeMixin"))


def test_extract_code_success():
    response = "<updated_code>print('hi')</updated_code>"
    assert edit_mod._extract_code(response) == "print('hi')"


def test_extract_code_with_tag_prefix():
    response = "<updated_code>#EDIT:foo\nprint('hi')</updated_code>"
    assert edit_mod._extract_code(response) == "print('hi')"


def test_extract_code_missing():
    assert edit_mod._extract_code("no tags") is None


class DummyLLM:
    def __init__(self, responses):
        self.responses = responses

    def completion(self, messages):
        return self.responses.pop(0)


def test_get_new_file_contents_success():
    llm = DummyLLM(
        [
            {
                "choices": [
                    {"message": {"content": "<updated_code>print('ok')</updated_code>"}}
                ]
            }
        ],
    )
    result = edit_mod.get_new_file_contents(llm, "old", "draft")
    assert result == "print('ok')"


def test_get_new_file_contents_retries():
    llm = DummyLLM(
        [
            {"choices": [{"message": {"content": "no code"}}]},
            {
                "choices": [
                    {"message": {"content": "<updated_code>print('ok')</updated_code>"}}
                ]
            },
        ],
    )
    result = edit_mod.get_new_file_contents(llm, "old", "draft", num_retries=2)
    assert result == "print('ok')"


def test_get_new_file_contents_failure():
    llm = DummyLLM([{"choices": [{"message": {"content": "failure"}}]}])
    assert edit_mod.get_new_file_contents(llm, "old", "draft", num_retries=1) is None


class DummyConfig:
    def __init__(self):
        self.sandbox = types.SimpleNamespace(enable_auto_lint=False)

    def get_llm_config(self, name):
        config = types.SimpleNamespace(caching_prompt=False, correct_num=3)
        return config


class DummyLLMRegistry:
    def __init__(self, llm):
        self.llm = llm

    def get_llm(self, name, config):
        self.llm.config = config
        return self.llm


class DummyLLMInstance:
    def __init__(self):
        self.metrics = {}

    def completion(self, **kwargs):
        return {
            "choices": [{"message": {"content": "<updated_code>done</updated_code>"}}]
        }


class DummyRuntime(FileEditRuntimeMixinType):
    def __init__(self, enable_llm_editor=True, llm=None):
        self.config = DummyConfig()
        self._writes = []
        llm_registry = DummyLLMRegistry(llm or DummyLLMInstance())
        super().__init__(
            enable_llm_editor=enable_llm_editor,
            llm_registry=cast("LLMRegistry", llm_registry),
        )

    def read(self, action):
        return FileReadObservationType("line1\nline2\n")

    def write(self, action):
        self._writes.append(action)
        return FileWriteObservationType()

    def run_ipython(self, action):
        return ObservationType()


def test_validate_range_errors():
    runtime = DummyRuntime(enable_llm_editor=False)
    err = runtime._validate_range(0, 5, 10)
    assert isinstance(err, ErrorObservationType)
    err = runtime._validate_range(5, 1, 10)
    assert isinstance(err, ErrorObservationType)


def test_validate_range_success():
    runtime = DummyRuntime(enable_llm_editor=False)
    assert runtime._validate_range(1, 5, 10) is None


def test_handle_new_file_creation(monkeypatch):
    runtime = DummyRuntime()

    def fake_write(action):
        return FileWriteObservationType()

    monkeypatch.setattr(runtime, "write", fake_write)
    action = FileEditActionType(path="file.txt", content="print('x')")
    obs = runtime._handle_new_file_creation(action)
    assert isinstance(obs, getattr(observation_mod, "FileEditObservation"))
    assert obs.prev_exist is False


def test_handle_new_file_creation_error(monkeypatch):
    runtime = DummyRuntime()
    failure = ErrorObservationType("write failed")
    monkeypatch.setattr(runtime, "write", lambda action: failure, raising=False)
    action = FileEditActionType(path="file.txt", content="x")
    assert runtime._handle_new_file_creation(action) is failure


def test_handle_new_file_creation_unexpected(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(
        runtime, "write", lambda action: ObservationType("oops"), raising=False
    )
    action = FileEditActionType(path="file.txt", content="x")
    with pytest.raises(ValueError):
        runtime._handle_new_file_creation(action)


def test_handle_append_edit(monkeypatch):
    runtime = DummyRuntime()

    def fake_write(action):
        return FileWriteObservationType()

    monkeypatch.setattr(runtime, "write", fake_write)
    action = FileEditActionType(path="file.txt", start=-1, content="line3")
    obs = runtime._handle_append_edit(
        action, "line1\nline2", ["line1", "line2"], retry_num=0
    )
    assert isinstance(obs, getattr(observation_mod, "FileEditObservation"))
    assert "line3" in obs.new_content


def test_handle_append_edit_autolint(monkeypatch):
    runtime = DummyRuntime()
    runtime.config.sandbox.enable_auto_lint = True

    def fake_write(action):
        return FileWriteObservationType()

    monkeypatch.setattr(runtime, "write", fake_write)
    monkeypatch.setattr(
        runtime,
        "_get_lint_error",
        lambda *args, **kwargs: ErrorObservationType("lint"),
        raising=False,
    )
    monkeypatch.setattr(
        runtime,
        "correct_edit",
        lambda **kwargs: ObservationType("corrected"),
        raising=False,
    )
    action = FileEditActionType(path="file.txt", start=-1, content="line3")
    obs = runtime._handle_append_edit(
        action, "line1\nline2", ["line1", "line2"], retry_num=0
    )
    assert isinstance(obs, ObservationType)
    assert obs.content == "corrected"


def test_get_lint_error_returns_error(monkeypatch):
    runtime = DummyRuntime()

    class FakeLintError:
        def visualize(self):
            return "lint issue"

    class FakeLinter:
        def lint_file_diff(self, old, new):
            return [FakeLintError()]

    monkeypatch.setattr(edit_mod, "DefaultLinter", lambda: FakeLinter(), raising=False)
    result = runtime._get_lint_error(".py", "print(1)", "print(2)", "file.py", "diff")
    assert isinstance(result, ErrorObservationType)


def test_get_lint_error_no_issues(monkeypatch):
    runtime = DummyRuntime()

    class FakeLinter:
        def lint_file_diff(self, old, new):
            return []

    monkeypatch.setattr(edit_mod, "DefaultLinter", lambda: FakeLinter(), raising=False)
    assert (
        runtime._get_lint_error(".py", "print(1)", "print(2)", "file.py", "diff")
        is None
    )


def test_build_range_error_message(monkeypatch):
    runtime = DummyRuntime()

    class FakeChunk:
        def __init__(self):
            self.line_range = (1, 3)
            self.normalized_lcs = 0.9

        def visualize(self):
            return "snippet"

    monkeypatch.setattr(
        edit_mod,
        "get_top_k_chunk_matches",
        lambda *args, **kwargs: [FakeChunk()],
        raising=False,
    )
    action = FileEditActionType(path="file.txt", content="new")
    msg = runtime._build_range_error_message(
        action,
        0,
        400,
        401,
        "old content",
    )
    assert "snippet" in msg


def test_perform_llm_edit_success(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(
        edit_mod,
        "get_new_file_contents",
        lambda *args, **kwargs: "edited",
        raising=False,
    )

    def fake_write(action):
        return FileWriteObservationType()

    monkeypatch.setattr(runtime, "write", fake_write)
    obs = runtime._perform_llm_edit(
        FileEditActionType(path="file.txt", content="draft", start=1, end=1),
        "line1\nline2",
        ["line1", "line2"],
        0,
        1,
        0,
    )
    assert isinstance(obs, getattr(observation_mod, "FileEditObservation"))


def test_perform_llm_edit_failure(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(
        edit_mod, "get_new_file_contents", lambda *args, **kwargs: None, raising=False
    )
    runtime.draft_editor_llm.metrics = {"calls": 1}
    obs = runtime._perform_llm_edit(
        FileEditActionType(path="file.txt", content="draft", start=1, end=1),
        "line1\nline2",
        ["line1", "line2"],
        0,
        1,
        0,
    )
    assert isinstance(obs, ErrorObservationType)


def test_perform_llm_edit_autolint_retry(monkeypatch):
    runtime = DummyRuntime()
    runtime.config.sandbox.enable_auto_lint = True
    monkeypatch.setattr(
        edit_mod,
        "get_new_file_contents",
        lambda *args, **kwargs: "edited",
        raising=False,
    )
    monkeypatch.setattr(
        runtime,
        "_get_lint_error",
        lambda *args, **kwargs: ErrorObservationType("lint"),
        raising=False,
    )
    monkeypatch.setattr(
        runtime, "write", lambda action: FileWriteObservationType(), raising=False
    )
    monkeypatch.setattr(
        runtime,
        "correct_edit",
        lambda **kwargs: ObservationType("fixed"),
        raising=False,
    )
    obs = runtime._perform_llm_edit(
        FileEditActionType(path="file.txt", content="draft", start=1, end=1),
        "line1\nline2",
        ["line1", "line2"],
        0,
        1,
        0,
    )
    assert isinstance(obs, ObservationType)
    assert obs.content == "fixed"


def test_llm_based_edit_file_not_found(monkeypatch):
    runtime = DummyRuntime()

    def fake_read(action):
        return ErrorObservationType("File not found locally")

    monkeypatch.setattr(runtime, "read", fake_read)
    monkeypatch.setattr(
        runtime,
        "_handle_new_file_creation",
        lambda action: ObservationType("created"),
        raising=False,
    )
    result = runtime.llm_based_edit(FileEditActionType(path="file.txt", content="new"))
    assert isinstance(result, ObservationType)
    assert result.content == "created"


def test_llm_based_edit_invalid_range(monkeypatch):
    runtime = DummyRuntime()

    def fake_read(action):
        return FileReadObservationType("line1\nline2\n")

    monkeypatch.setattr(runtime, "read", fake_read)
    monkeypatch.setattr(
        runtime,
        "_validate_range",
        lambda *args, **kwargs: ErrorObservationType("bad"),
        raising=False,
    )
    result = runtime.llm_based_edit(FileEditActionType(path="file.txt", start=0, end=1))
    assert isinstance(result, ErrorObservationType)


def test_llm_based_edit_append(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(
        runtime,
        "read",
        lambda action: FileReadObservationType("line1\n"),
        raising=False,
    )
    monkeypatch.setattr(
        runtime, "_validate_range", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        runtime,
        "_handle_append_edit",
        lambda *args, **kwargs: ObservationType("appended"),
        raising=False,
    )
    action = FileEditActionType(path="file.txt", start=-1, content="line2")
    result = runtime.llm_based_edit(action)
    assert isinstance(result, ObservationType)


def test_llm_based_edit_success(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(
        runtime,
        "read",
        lambda action: FileReadObservationType("line1\nline2\n"),
        raising=False,
    )
    monkeypatch.setattr(
        runtime, "_validate_range", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        runtime,
        "_perform_llm_edit",
        lambda *args, **kwargs: ObservationType("done"),
        raising=False,
    )
    action = FileEditActionType(path="file.txt", start=1, end=1, content="new")
    result = runtime.llm_based_edit(action)
    assert isinstance(result, ObservationType)


def test_check_retry_num():
    runtime = DummyRuntime()
    runtime.draft_editor_llm.config.correct_num = 1
    assert runtime.check_retry_num(2) is True
    assert runtime.check_retry_num(1) is False


def test_correct_edit_retry_limit(monkeypatch):
    runtime = DummyRuntime()
    monkeypatch.setattr(runtime, "check_retry_num", lambda retry: True, raising=False)
    error = ErrorObservationType("lint errors")
    result = runtime.correct_edit("content", error_obs=cast(Any, error), retry_num=0)
    assert result is error


def test_correct_edit_success(monkeypatch):
    runtime = DummyRuntime()
    runtime.draft_editor_llm.completion = lambda **kwargs: {
        "choices": [{"message": {"content": "ok"}}]
    }
    runtime.draft_editor_llm.config.correct_num = 5

    fc_module = sys.modules["forge.agenthub.codeact_agent.function_calling"]
    monkeypatch.setattr(
        fc_module,
        "response_to_actions",
        lambda response: [
            FileEditActionType(path="file.txt", start=1, end=1, content="new")
        ],
        raising=False,
    )
    llm_utils_module = sys.modules["forge.llm.llm_utils"]
    monkeypatch.setattr(
        llm_utils_module, "check_tools", lambda tools, config: tools, raising=False
    )
    monkeypatch.setattr(
        runtime,
        "llm_based_edit",
        lambda action, retry_num=0: ObservationType("fixed"),
        raising=False,
    )
    error = ErrorObservationType("lint errors")
    result = runtime.correct_edit("content", error_obs=cast(Any, error), retry_num=0)
    assert isinstance(result, ObservationType)
    assert result.content == "fixed"


def test_correct_edit_multiple_actions(monkeypatch):
    runtime = DummyRuntime()
    runtime.draft_editor_llm.completion = lambda **kwargs: {
        "choices": [{"message": {"content": "ok"}}]
    }
    fc_module = sys.modules["forge.agenthub.codeact_agent.function_calling"]
    monkeypatch.setattr(
        fc_module,
        "response_to_actions",
        lambda response: [
            FileEditActionType(path="file.txt", start=1, end=1, content="new"),
            FileEditActionType(path="file2.txt", start=1, end=1, content="new"),
        ],
        raising=False,
    )
    error = ErrorObservationType("lint errors")
    assert (
        runtime.correct_edit("content", error_obs=cast(Any, error), retry_num=0)
        is error
    )


def test_correct_edit_non_file_action(monkeypatch):
    runtime = DummyRuntime()
    runtime.draft_editor_llm.completion = lambda **kwargs: {
        "choices": [{"message": {"content": "ok"}}]
    }

    class DummyAction: ...

    fc_module = sys.modules["forge.agenthub.codeact_agent.function_calling"]
    monkeypatch.setattr(
        fc_module,
        "response_to_actions",
        lambda response: [DummyAction()],
        raising=False,
    )
    error = ErrorObservationType("lint errors")
    assert (
        runtime.correct_edit("content", error_obs=cast(Any, error), retry_num=0)
        is error
    )


def test_correct_edit_exception(monkeypatch):
    runtime = DummyRuntime()

    def failing_completion(**kwargs):
        raise RuntimeError("boom")

    runtime.draft_editor_llm.completion = failing_completion
    error = ErrorObservationType("lint errors")
    assert (
        runtime.correct_edit("content", error_obs=cast(Any, error), retry_num=0)
        is error
    )
