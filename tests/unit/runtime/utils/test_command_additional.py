import importlib
import sys
import types
from types import SimpleNamespace

import pytest
if "tenacity.stop.stop_base" not in sys.modules:
    stub_tenacity = types.ModuleType("tenacity.stop.stop_base")
    stub_tenacity.StopBase = type("StopBase", (), {})
    sys.modules["tenacity.stop.stop_base"] = stub_tenacity



@pytest.fixture()
def command_module(monkeypatch):
    original_logger = sys.modules.get("forge.core.logger")
    stub_logger = types.ModuleType("forge.core.logger")

    class DummyLogger:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    stub_logger.forge_logger = DummyLogger()
    monkeypatch.setitem(sys.modules, "forge.core.logger", stub_logger)

    module = importlib.import_module("forge.runtime.utils.command")
    yield module

    sys.modules.pop("forge.runtime.utils.command", None)
    if original_logger is not None:
        sys.modules["forge.core.logger"] = original_logger
    else:
        sys.modules.pop("forge.core.logger", None)


def test_build_plugin_args(command_module):
    plugin_args = command_module._build_plugin_args([SimpleNamespace(name="alpha"), SimpleNamespace(name="beta")])
    assert plugin_args == ["--plugins", "alpha", "beta"]

    assert command_module._build_plugin_args([]) == []


def test_build_browsergym_args_validation(command_module):
    args = command_module._build_browsergym_args("env-id --flag")
    assert args == ["--browsergym-eval-env", "env-id", "--flag"]

    assert command_module._build_browsergym_args(None) == []
    assert command_module._build_browsergym_args("bad;rm -rf /") == ["--browsergym-eval-env", "-rf", "/"]


def test_validate_and_get_username(command_module):
    assert command_module._validate_and_get_username(None, True) == "forge"
    assert command_module._validate_and_get_username("safe_user", False) == "safe_user"

    result = command_module._validate_and_get_username("bad user", False)
    assert result == "root"


def test_get_action_execution_server_startup_command(command_module):
    plugins = [SimpleNamespace(name="example")]
    sandbox = SimpleNamespace(browsergym_eval_env="env-a env-b")
    app_config = SimpleNamespace(
        sandbox=sandbox,
        run_as_Forge=True,
        workspace_mount_path_in_sandbox="/sandbox/workspace",
        enable_browser=False,
    )

    cmd = command_module.get_action_execution_server_startup_command(
        server_port=8080,
        plugins=plugins,
        app_config=app_config,
        python_prefix=["python3"],
        override_user_id=42,
        override_username="bad name",
        main_module="module.main",
        python_executable="python",
    )

    assert cmd[:5] == ["python3", "python", "-u", "-m", "module.main"]
    assert "--plugins" in cmd
    assert "--no-enable-browser" in cmd
    assert cmd[cmd.index("--username") + 1] == "forge"

