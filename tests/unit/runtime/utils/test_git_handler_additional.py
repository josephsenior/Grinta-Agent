from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Callable, TypeAlias

import pytest

if "litellm" not in sys.modules:
    from pydantic import BaseModel

    class ModelResponse(BaseModel):
        model: str | None = None
        choices: list[Any] = []

    class ModelInfo(BaseModel):
        model_name: str | None = None

    class PromptTokensDetails(BaseModel):
        cached_tokens: int | None = None

    class ChatCompletionToolParam(BaseModel):
        name: str | None = None
        description: str | None = None
        parameters: dict[str, Any] = {}

    async def acompletion(*args, **kwargs) -> dict[str, Any]:
        return {}

    def completion(*args, **kwargs) -> dict[str, Any]:
        return {}

    class APIConnectionError(Exception):
        pass

    class ContentPolicyViolationError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class ServiceUnavailableError(Exception):
        pass

    class Timeout(Exception):
        pass

    class InternalServerError(Exception):
        pass

    class CostPerToken(BaseModel):
        input_cost_per_token: float | None = None
        output_cost_per_token: float | None = None

    class Usage(BaseModel):
        prompt_tokens: int | None = None
        completion_tokens: int | None = None
        total_tokens: int | None = None

    class _LiteLLMUtilsModule(types.ModuleType):
        create_pretrained_tokenizer: Callable[..., Any]
        get_model_info: Callable[..., Any]

    utils_module = _LiteLLMUtilsModule("litellm.utils")
    utils_module.create_pretrained_tokenizer = lambda *args, **kwargs: None
    utils_module.get_model_info = lambda *args, **kwargs: {}

    class _LiteLLMExceptionsModule(types.ModuleType):
        APIConnectionError: type[Exception]
        ContentPolicyViolationError: type[Exception]
        RateLimitError: type[Exception]
        ServiceUnavailableError: type[Exception]
        Timeout: type[Exception]
        InternalServerError: type[Exception]

    exceptions_module = _LiteLLMExceptionsModule("litellm.exceptions")
    exceptions_module.APIConnectionError = APIConnectionError
    exceptions_module.ContentPolicyViolationError = ContentPolicyViolationError
    exceptions_module.RateLimitError = RateLimitError
    exceptions_module.ServiceUnavailableError = ServiceUnavailableError
    exceptions_module.Timeout = Timeout
    exceptions_module.InternalServerError = InternalServerError

    class _LiteLLMTypesUtilsModule(types.ModuleType):
        CostPerToken: type[CostPerToken]
        ModelResponse: type[ModelResponse]
        Usage: type[Usage]

    types_utils_module = _LiteLLMTypesUtilsModule("litellm.types.utils")
    types_utils_module.CostPerToken = CostPerToken
    types_utils_module.ModelResponse = ModelResponse
    types_utils_module.Usage = Usage

    class _LiteLLMModule(types.ModuleType):
        ModelResponse: type[ModelResponse]
        ModelInfo: type[ModelInfo]
        PromptTokensDetails: type[PromptTokensDetails]
        ChatCompletionToolParam: type[ChatCompletionToolParam]
        acompletion: Callable[..., Any]
        completion: Callable[..., Any]
        completion_cost: Callable[..., Any]
        APIConnectionError: type[Exception]
        ContentPolicyViolationError: type[Exception]
        RateLimitError: type[Exception]
        ServiceUnavailableError: type[Exception]
        Timeout: type[Exception]
        InternalServerError: type[Exception]
        CostPerToken: type[CostPerToken]
        Usage: type[Usage]
        suppress_debug_info: bool
        set_verbose: bool
        utils: _LiteLLMUtilsModule
        exceptions: _LiteLLMExceptionsModule
        create_pretrained_tokenizer: Callable[..., Any]
        get_model_info: Callable[..., Any]

    litellm_stub = _LiteLLMModule("litellm")
    litellm_stub.ModelResponse = ModelResponse
    litellm_stub.ModelInfo = ModelInfo
    litellm_stub.PromptTokensDetails = PromptTokensDetails
    litellm_stub.ChatCompletionToolParam = ChatCompletionToolParam
    litellm_stub.acompletion = acompletion
    litellm_stub.completion = completion
    litellm_stub.completion_cost = lambda *args, **kwargs: 0
    litellm_stub.APIConnectionError = APIConnectionError
    litellm_stub.ContentPolicyViolationError = ContentPolicyViolationError
    litellm_stub.RateLimitError = RateLimitError
    litellm_stub.ServiceUnavailableError = ServiceUnavailableError
    litellm_stub.Timeout = Timeout
    litellm_stub.InternalServerError = InternalServerError
    litellm_stub.CostPerToken = CostPerToken
    litellm_stub.Usage = Usage
    litellm_stub.suppress_debug_info = True
    litellm_stub.set_verbose = False
    litellm_stub.utils = utils_module
    litellm_stub.exceptions = exceptions_module
    litellm_stub.create_pretrained_tokenizer = utils_module.create_pretrained_tokenizer
    litellm_stub.get_model_info = utils_module.get_model_info
    sys.modules["litellm"] = litellm_stub
    sys.modules["litellm.utils"] = utils_module
    sys.modules["litellm.exceptions"] = exceptions_module
    sys.modules["litellm.types.utils"] = types_utils_module

if "tokenizers" not in sys.modules:
    tokenizers_stub = types.ModuleType("tokenizers")
    sys.modules["tokenizers"] = tokenizers_stub

from forge.runtime.utils import git_changes
from forge.runtime.utils.git_handler import (
    CommandResult,
    GIT_CHANGES_CMD,
    GIT_DIFF_CMD,
    GIT_BRANCH_CMD,
    GitHandler,
)

ResponseMap: TypeAlias = dict[tuple[str, str | None], CommandResult]


def make_handler(
    responses: ResponseMap,
    create_file_ret: int = 0,
) -> tuple[GitHandler, list[tuple[str, str | None]], list[tuple[str, str]]]:
    """Create a GitHandler with injectable command responses for testing."""
    calls: list[tuple[str, str | None]] = []
    created: list[tuple[str, str]] = []

    def execute(cmd: str, cwd: str | None) -> CommandResult:
        calls.append((cmd, cwd))
        result = responses.get((cmd, cwd))
        if result is None:
            return CommandResult("", 1)
        return result

    def create_file(path: str, content: str) -> int:
        created.append((path, content))
        return create_file_ret

    handler = GitHandler(execute_shell_fn=execute, create_file_fn=create_file)
    return handler, calls, created


def test_get_current_branch_success():
    responses: ResponseMap = {(GIT_BRANCH_CMD, "/repo"): CommandResult("feature\n", 0)}
    handler, calls, _ = make_handler(responses)
    handler.set_cwd("/repo")
    assert handler.get_current_branch() == "feature"
    assert calls == [(GIT_BRANCH_CMD, "/repo")]


def test_get_current_branch_blank_output():
    responses: ResponseMap = {(GIT_BRANCH_CMD, "/repo"): CommandResult("\n", 0)}
    handler, _, _ = make_handler(responses)
    handler.set_cwd("/repo")
    assert handler.get_current_branch() is None


def test_get_current_branch_error_without_cwd():
    responses: ResponseMap = {}
    handler, _, _ = make_handler(responses)
    assert handler.get_current_branch() is None


def test_get_current_branch_nonzero_exit():
    responses: ResponseMap = {(GIT_BRANCH_CMD, "/repo"): CommandResult("error", 1)}
    handler, _, _ = make_handler(responses)
    handler.set_cwd("/repo")
    assert handler.get_current_branch() is None


def test_get_git_changes_success():
    payload = json.dumps([{"status": "M", "path": "file.txt"}])
    responses: ResponseMap = {("git-changes", "/repo"): CommandResult(payload, 0)}
    handler, calls, _ = make_handler(responses)
    handler.set_cwd("/repo")
    handler.git_changes_cmd = "git-changes"
    assert handler.get_git_changes() == [{"status": "M", "path": "file.txt"}]
    assert calls == [("git-changes", "/repo")]


def test_get_git_changes_without_cwd():
    payload = json.dumps([{"status": "M", "path": "file.txt"}])
    responses: ResponseMap = {("git-changes", "/repo"): CommandResult(payload, 0)}
    handler, _, _ = make_handler(responses)
    handler.git_changes_cmd = "git-changes"
    assert handler.get_git_changes() is None


def test_get_git_changes_custom_cmd_failure():
    responses: ResponseMap = {("custom", "/repo"): CommandResult("fail", 1)}
    handler, calls, _ = make_handler(responses)
    handler.set_cwd("/repo")
    handler.git_changes_cmd = "custom"
    assert handler.get_git_changes() is None
    assert calls == [("custom", "/repo")]


def test_get_git_changes_invalid_json(monkeypatch):
    responses: ResponseMap = {("git-changes", "/repo"): CommandResult("not-json", 0)}
    handler, _, _ = make_handler(responses)
    handler.set_cwd("/repo")
    handler.git_changes_cmd = "git-changes"
    # Avoid logger noise in test output
    monkeypatch.setattr(
        "forge.runtime.utils.git_handler.logger.exception", lambda *args, **kwargs: None
    )
    assert handler.get_git_changes() is None


def test_get_git_changes_fallback(monkeypatch):
    payload = json.dumps([{"status": "A", "path": "file.txt"}])
    script_path = Path("/tmp/git_changes.py")
    responses: ResponseMap = {
        (GIT_CHANGES_CMD, "/repo"): CommandResult("failure", 1),
        (f"python3 {script_path}", "/repo"): CommandResult(payload, 0),
        ("mktemp -d", "/repo"): CommandResult("/tmp", 0),
        (f'chmod +x "{script_path}"', "/repo"): CommandResult("", 0),
    }
    handler, calls, created = make_handler(responses)
    handler.set_cwd("/repo")
    # Allow _create_python_script_file to run but ensure it returns predictable path
    assert handler.get_git_changes() == [{"status": "A", "path": "file.txt"}]
    assert calls.count((GIT_CHANGES_CMD, "/repo")) == 1
    assert (f"python3 {script_path}", "/repo") in calls
    # confirm script file creation occurred
    assert any(path.endswith("git_changes.py") for path, _ in created)


def test_get_git_diff_requires_cwd():
    responses: ResponseMap = {}
    handler, _, _ = make_handler(responses)
    with pytest.raises(ValueError, match="no_dir_in_git_diff"):
        handler.get_git_diff("file.txt")


def test_get_git_diff_success():
    payload = json.dumps({"original": "old", "modified": "new"})
    command = 'python3 script "{file_path}"'
    responses: ResponseMap = {
        (command.format(file_path="file.txt"), "/repo"): CommandResult(payload, 0)
    }
    handler, calls, _ = make_handler(responses)
    handler.set_cwd("/repo")
    handler.git_diff_cmd = command
    assert handler.get_git_diff("file.txt") == {"original": "old", "modified": "new"}
    assert calls == [(command.format(file_path="file.txt"), "/repo")]


def test_get_git_diff_fallback(monkeypatch):
    payload = json.dumps({"original": "", "modified": ""})
    script_path = Path("/tmp/git_diff.py")
    original_cmd = GIT_DIFF_CMD
    fallback_cmd = f'python3 {script_path} "{{file_path}}"'
    responses: ResponseMap = {
        (original_cmd.format(file_path="file.txt"), "/repo"): CommandResult(
            "failure", 1
        ),
        (fallback_cmd.format(file_path="file.txt"), "/repo"): CommandResult(payload, 0),
        ("mktemp -d", "/repo"): CommandResult("/tmp", 0),
        (f'chmod +x "{script_path}"', "/repo"): CommandResult("", 0),
    }
    handler, calls, created = make_handler(responses)
    handler.set_cwd("/repo")
    assert handler.get_git_diff("file.txt") == {"original": "", "modified": ""}
    assert (original_cmd.format(file_path="file.txt"), "/repo") in calls
    assert (fallback_cmd.format(file_path="file.txt"), "/repo") in calls
    assert any(path.endswith("git_diff.py") for path, _ in created)


def test_get_git_diff_failure_custom_cmd():
    command = 'python3 script "{file_path}"'
    responses: ResponseMap = {
        (command.format(file_path="file.txt"), "/repo"): CommandResult("fail", 1)
    }
    handler, calls, _ = make_handler(responses)
    handler.set_cwd("/repo")
    handler.git_diff_cmd = command
    with pytest.raises(ValueError, match="error_in_git_diff"):
        handler.get_git_diff("file.txt")
    assert calls == [(command.format(file_path="file.txt"), "/repo")]


def test_create_python_script_file_reads_source(tmp_path):
    commands = [
        ("mktemp -d", "/repo"),
    ]
    responses: ResponseMap = {
        ("mktemp -d", "/repo"): CommandResult(str(tmp_path), 0),
        (
            f'chmod +x "{tmp_path / Path(git_changes.__file__).name}"',
            "/repo",
        ): CommandResult("", 0),
    }
    handler, calls, created = make_handler(responses)
    handler.set_cwd("/repo")
    script_path = handler._create_python_script_file(git_changes.__file__)
    assert script_path == tmp_path / Path(git_changes.__file__).name
    assert created  # create_file_fn was invoked
    assert calls == [
        ("mktemp -d", "/repo"),
        (f'chmod +x "{script_path}"', "/repo"),
    ]
