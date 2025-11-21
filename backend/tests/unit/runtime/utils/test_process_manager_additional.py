from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

if "forge.runtime.utils" not in sys.modules:
    sys.modules["forge.runtime.utils"] = types.ModuleType("forge.runtime.utils")

logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)
if not hasattr(logger_mod, "forge_logger"):

    class DummyLogger:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    setattr(logger_mod, "forge_logger", DummyLogger())

spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.process_manager",
    ROOT / "forge" / "runtime" / "utils" / "process_manager.py",
)
assert spec and spec.loader
process_manager = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.process_manager"] = process_manager
spec.loader.exec_module(process_manager)

ProcessManager = process_manager.ProcessManager
ManagedProcess = process_manager.ManagedProcess


class DummyRuntime:
    def __init__(self):
        self.commands: list[str] = []

    def run(self, action):
        self.commands.append(action.command)
        return True


@pytest.fixture(autouse=True)
def patch_sleep(monkeypatch):
    async def immediate_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr(process_manager.asyncio, "sleep", immediate_sleep)
    yield


def test_extract_process_name():
    manager = ProcessManager()
    assert manager._extract_process_name("python script.py") == "python"
    assert manager._extract_process_name("python3 app.py") == "python3"
    assert manager._extract_process_name("npm run dev") == "npm"
    assert manager._extract_process_name("node server.js") == "node"
    assert manager._extract_process_name("yarn start") == "yarn"
    assert manager._extract_process_name("pnpm start") == "pnpm"
    assert manager._extract_process_name("custom command") == "custom"
    assert manager._extract_process_name("") == "unknown"


def test_register_and_unregister_process():
    manager = ProcessManager()
    manager.register_process("python app.py", "cmd1")
    assert manager.count() == 1
    manager.unregister_process("cmd1")
    assert manager.count() == 0


def test_get_running_processes_returns_copy():
    manager = ProcessManager()
    manager.register_process("python app.py", "cmd1")
    processes = manager.get_running_processes()
    assert isinstance(processes[0], ManagedProcess)
    assert processes[0].command == "python app.py"


@pytest.mark.asyncio
async def test_cleanup_all_no_processes(monkeypatch):
    manager = ProcessManager()
    result = await manager.cleanup_all(runtime=None)
    assert result == {}


@pytest.fixture
def stub_cmd_action(monkeypatch):
    action_module = types.ModuleType("forge.events.action")

    @dataclass
    class CmdRunAction:
        command: str

    setattr(action_module, "CmdRunAction", CmdRunAction)
    monkeypatch.setitem(sys.modules, "forge.events.action", action_module)
    return CmdRunAction


@pytest.mark.asyncio
async def test_cleanup_all_with_runtime(monkeypatch, stub_cmd_action):
    recorded = []

    async def fake_call_sync(fn, action):
        recorded.append(action.command)
        fn(action)

    monkeypatch.setattr(process_manager, "call_sync_from_async", fake_call_sync)
    manager = ProcessManager()
    command = "python 'app.py'"
    manager.register_process(command, "cmd1")
    runtime = DummyRuntime()
    results = await manager.cleanup_all(runtime=runtime)
    assert results == {"cmd1": True}
    assert manager.count() == 0
    assert len(recorded) == 2
    assert "pkill -TERM -f 'python '\\''app.py'\\''' || true" == recorded[0]
    assert "pkill -9 -f 'python '\\''app.py'\\''' || true" == recorded[1]


@pytest.mark.asyncio
async def test_cleanup_all_handles_errors(monkeypatch, stub_cmd_action):
    async def failing_call_sync(fn, action):
        raise RuntimeError("fail")

    monkeypatch.setattr(process_manager, "call_sync_from_async", failing_call_sync)
    manager = ProcessManager()
    manager.register_process("python app.py", "cmd1")
    runtime = DummyRuntime()
    results = await manager.cleanup_all(runtime=runtime)
    assert results["cmd1"] is False
    assert manager.count() == 0
