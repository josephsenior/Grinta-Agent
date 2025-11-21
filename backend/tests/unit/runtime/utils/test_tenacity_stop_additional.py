from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


shutdown_mod = sys.modules.setdefault(
    "forge.utils.shutdown_listener", types.ModuleType("forge.utils.shutdown_listener")
)
if not hasattr(shutdown_mod, "should_exit"):

    def should_exit():
        return False

    setattr(shutdown_mod, "should_exit", should_exit)


MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "forge"
    / "runtime"
    / "utils"
    / "tenacity_stop.py"
)
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.tenacity_stop", MODULE_PATH
)
assert spec and spec.loader
tenacity_stop = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.tenacity_stop"] = tenacity_stop
spec.loader.exec_module(tenacity_stop)


def test_stop_if_should_exit_true(monkeypatch):
    monkeypatch.setattr(tenacity_stop, "should_exit", lambda: True, raising=False)
    stopper = tenacity_stop.stop_if_should_exit()
    assert stopper(retry_state=None) is True


def test_stop_if_should_exit_false(monkeypatch):
    monkeypatch.setattr(tenacity_stop, "should_exit", lambda: False, raising=False)
    stopper = tenacity_stop.stop_if_should_exit()
    assert stopper(retry_state=None) is False
