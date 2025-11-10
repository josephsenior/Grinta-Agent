from __future__ import annotations

import pytest

from forge.controller.error_recovery import ErrorRecoveryStrategy, ErrorType, AuthenticationError
from forge.core.exceptions import FunctionCallValidationError
from forge.events.action import AgentThinkAction, CmdRunAction, MessageAction


def test_classify_error_by_exception_type():
    assert ErrorRecoveryStrategy.classify_error(ModuleNotFoundError("foo")) == ErrorType.MODULE_NOT_FOUND
    assert ErrorRecoveryStrategy.classify_error(PermissionError("nope")) == ErrorType.PERMISSION_ERROR
    assert ErrorRecoveryStrategy.classify_error(TimeoutError("slow")) == ErrorType.TIMEOUT_ERROR
    assert ErrorRecoveryStrategy.classify_error(FileNotFoundError("missing")) == ErrorType.FILESYSTEM_ERROR
    assert (
        ErrorRecoveryStrategy.classify_error(FunctionCallValidationError("bad call"))
        == ErrorType.TOOL_CALL_ERROR
    )


def test_classify_error_by_message_patterns():
    runtime = RuntimeError("Container crash detected: runtime terminated")
    network = RuntimeError("Connection refused during git clone")
    filesystem = RuntimeError("No space left on device")
    permission = RuntimeError("Filesystem failure: permission denied")

    assert ErrorRecoveryStrategy.classify_error(runtime) == ErrorType.RUNTIME_CRASH
    assert ErrorRecoveryStrategy.classify_error(network) == ErrorType.NETWORK_ERROR
    assert ErrorRecoveryStrategy.classify_error(filesystem) == ErrorType.DISK_FULL_ERROR
    assert ErrorRecoveryStrategy.classify_error(permission) == ErrorType.PERMISSION_ERROR


def test_authentication_error_supports_flexible_init():
    error = AuthenticationError("simple authentication failure")
    assert isinstance(error, AuthenticationError)


def test_recovery_actions_for_module_not_found():
    error = ModuleNotFoundError("No module named 'requests.auth'")
    actions = ErrorRecoveryStrategy.get_recovery_actions(ErrorType.MODULE_NOT_FOUND, error)
    assert isinstance(actions[0], AgentThinkAction)
    pip_action = next(act for act in actions if isinstance(act, CmdRunAction))
    assert pip_action.command == "pip install requests"


def test_recovery_actions_for_module_not_found_without_match():
    error = ModuleNotFoundError("module missing but not named")
    actions = ErrorRecoveryStrategy.get_recovery_actions(ErrorType.MODULE_NOT_FOUND, error)
    assert len(actions) == 1
    assert isinstance(actions[0], AgentThinkAction)


def test_recovery_actions_runtime_crash():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.RUNTIME_CRASH,
        RuntimeError("runtime crashed unexpectedly"),
    )
    assert any(isinstance(action, CmdRunAction) for action in actions)
    assert any(isinstance(action, MessageAction) for action in actions)


def test_recovery_actions_network_git_error():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.NETWORK_ERROR,
        RuntimeError("git clone failed: connection timeout"),
    )
    git_commands = [act.command for act in actions if isinstance(act, CmdRunAction)]
    assert "git config --global http.postBuffer 524288000" in git_commands


def test_recovery_actions_network_general_error():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.NETWORK_ERROR,
        RuntimeError("connection timeout"),
    )
    assert any(act.command == "sleep 2" for act in actions if isinstance(act, CmdRunAction))


def test_recovery_actions_filesystem_error():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.FILESYSTEM_ERROR,
        RuntimeError("general filesystem error"),
    )
    commands = [act.command for act in actions if isinstance(act, CmdRunAction)]
    assert "pwd" in commands and "ls -la" in commands


def test_recovery_actions_permission_error():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.PERMISSION_ERROR,
        PermissionError("Permission denied: '/etc/passwd'"),
    )
    assert isinstance(actions[0], AgentThinkAction)
    assert any("/etc/passwd" in act.command for act in actions if isinstance(act, CmdRunAction))


def test_tool_call_authentication_error_returns_empty():
    error = AuthenticationError("provider", "model", Exception("authentication failure"))
    assert (
        ErrorRecoveryStrategy.get_recovery_actions(ErrorType.TOOL_CALL_ERROR, error)
        == []
    )


def test_tool_call_non_authentication_error_returns_empty_list():
    actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.TOOL_CALL_ERROR,
        RuntimeError("invalid parameters"),
    )
    assert actions == []


def test_recovery_actions_timeout_and_disk_full():
    timeout_actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.TIMEOUT_ERROR,
        TimeoutError("operation timed out"),
    )
    assert any(isinstance(act, MessageAction) for act in timeout_actions)

    disk_actions = ErrorRecoveryStrategy.get_recovery_actions(
        ErrorType.DISK_FULL_ERROR,
        RuntimeError("disk full"),
    )
    assert any("df -h" == act.command for act in disk_actions if isinstance(act, CmdRunAction))


def test_recovery_actions_unknown_error():
    error = RuntimeError("some unexpected issue")
    actions = ErrorRecoveryStrategy.get_recovery_actions(ErrorType.UNKNOWN_ERROR, error)
    assert isinstance(actions[0], AgentThinkAction)


def test_get_recovery_actions_handles_unknown_error_type():
    actions = ErrorRecoveryStrategy.get_recovery_actions("not-a-type", RuntimeError("fail"))  # type: ignore[arg-type]
    assert actions == []


def test_classify_error_unknown_triggers_debug(monkeypatch):
    captured = {}

    def fake_debug(message):
        captured["message"] = message

    monkeypatch.setattr("forge.controller.error_recovery.logger.debug", fake_debug)
    error_type = ErrorRecoveryStrategy.classify_error(RuntimeError("unmatched error pattern"))
    assert error_type == ErrorType.UNKNOWN_ERROR
    assert "could not be classified" in captured["message"]

