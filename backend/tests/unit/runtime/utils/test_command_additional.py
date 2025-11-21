from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any, cast

import pytest


if "forge.core.logger" not in sys.modules:
    logger_stub = types.ModuleType("forge.core.logger")

    class DummyLogger:
        def __init__(self):
            self.debug_calls = []
            self.warning_calls = []

        def debug(self, msg, *args):
            self.debug_calls.append((msg, args))

        def warning(self, msg, *args):
            self.warning_calls.append((msg, args))

    cast_logger = cast(Any, logger_stub)
    cast_logger.forge_logger = DummyLogger()
    sys.modules["forge.core.logger"] = logger_stub


MODULE_PATH = (
    Path(__file__).resolve().parents[4] / "forge" / "runtime" / "utils" / "command.py"
)
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.command", MODULE_PATH
)
assert spec and spec.loader
command_mod = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.command"] = command_mod
spec.loader.exec_module(command_mod)


def test_build_plugin_args():
    plugins = [types.SimpleNamespace(name="alpha"), types.SimpleNamespace(name="beta")]
    assert command_mod._build_plugin_args(plugins) == ["--plugins", "alpha", "beta"]
    assert command_mod._build_plugin_args([]) == []
    assert command_mod._build_plugin_args(None) == []


@pytest.mark.parametrize(
    ("part", "expected"),
    [("SAFE_VALUE", True), ("bad;value", False), ("", False)],
)
def test_validate_env_part(part, expected):
    assert command_mod._validate_env_part(part) is expected


def test_build_browsergym_args_filters_invalid():
    env = "level easy;"
    assert command_mod._build_browsergym_args(env) == ["--browsergym-eval-env", "level"]


def test_build_browsergym_args_all_invalid():
    env = "bad;value"
    assert command_mod._build_browsergym_args(env) == []


def test_build_browsergym_args_empty():
    assert command_mod._build_browsergym_args("") == []
    assert command_mod._build_browsergym_args(None) == []


def test_validate_and_get_username_defaults(monkeypatch):
    logger = types.SimpleNamespace(warning_messages=[])

    def warning(msg, *args):
        logger.warning_messages.append(msg)

    monkeypatch.setattr(
        command_mod, "logger", types.SimpleNamespace(warning=warning), raising=False
    )
    assert command_mod._validate_and_get_username(None, True) == "forge"
    assert command_mod._validate_and_get_username(None, False) == "root"
    assert command_mod._validate_and_get_username("user", False) == "user"
    assert command_mod._validate_and_get_username("bad user", True) == "forge"
    assert logger.warning_messages, "warning expected for invalid username"


def make_config(
    run_as_forge=True,
    enable_browser=True,
    browsergym_env="mode easy",
    workspace="/tmp/workspace",
):
    sandbox = types.SimpleNamespace(browsergym_eval_env=browsergym_env)
    return types.SimpleNamespace(
        sandbox=sandbox,
        run_as_Forge=run_as_forge,
        workspace_mount_path_in_sandbox=workspace,
        enable_browser=enable_browser,
    )


def test_get_action_execution_server_startup_command(monkeypatch):
    config = make_config()
    plugins = [types.SimpleNamespace(name="alpha")]
    cmd = command_mod.get_action_execution_server_startup_command(
        server_port=12345,
        plugins=plugins,
        app_config=config,
        python_prefix=["python"],
        override_user_id=None,
    )
    assert cmd[:5] == ["python", "python", "-u", "-m", command_mod.DEFAULT_MAIN_MODULE]
    assert "--plugins" in cmd
    assert "--browsergym-eval-env" in cmd
    assert "--no-enable-browser" not in cmd


def test_get_action_execution_server_startup_command_disable_browser(monkeypatch):
    config = make_config(run_as_forge=False, enable_browser=False, browsergym_env=None)
    cmd = command_mod.get_action_execution_server_startup_command(
        server_port=54321,
        plugins=[],
        app_config=config,
        python_prefix=["python"],
        override_user_id=99,
        override_username="admin",
        python_executable="py",
    )
    assert "--no-enable-browser" in cmd
    assert "--user-id" in cmd and cmd[cmd.index("--user-id") + 1] == "99"
    assert "--username" in cmd and cmd[cmd.index("--username") + 1] == "admin"
