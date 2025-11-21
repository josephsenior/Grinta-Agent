from __future__ import annotations

import builtins
import sys
import runpy
from types import ModuleType, SimpleNamespace

import pytest

import forge.agenthub.codeact_agent.tools.health_check as health_check


def _install_tree_sitter(monkeypatch, root_type: str = "module"):
    fake_ts = ModuleType("tree_sitter")
    fake_ts.Language = object
    fake_ts.Parser = object

    class DummyParser:
        def parse(self, code: bytes):
            return SimpleNamespace(root_node=SimpleNamespace(type=root_type))

    fake_pack = ModuleType("tree_sitter_language_pack")
    fake_pack.get_language = lambda name: SimpleNamespace(name=name)
    fake_pack.get_parser = lambda name: DummyParser()

    monkeypatch.setitem(sys.modules, "tree_sitter", fake_ts)
    monkeypatch.setitem(sys.modules, "tree_sitter_language_pack", fake_pack)


def _install_faulty_tree_sitter(monkeypatch, error: Exception):
    fake_ts = ModuleType("tree_sitter")
    fake_ts.Language = object
    fake_ts.Parser = object

    class DummyParser:
        def parse(self, code: bytes):
            raise error

    fake_pack = ModuleType("tree_sitter_language_pack")
    fake_pack.get_language = lambda name: SimpleNamespace(name=name)
    fake_pack.get_parser = lambda name: DummyParser()

    monkeypatch.setitem(sys.modules, "tree_sitter", fake_ts)
    monkeypatch.setitem(sys.modules, "tree_sitter_language_pack", fake_pack)


def _install_atomic_refactor_stub(monkeypatch, initializer=None):
    module_name = "forge.agenthub.codeact_agent.tools.atomic_refactor"
    fake_module = ModuleType(module_name)

    class DummyRefactor:
        def __init__(self):
            if initializer:
                initializer()

    fake_module.AtomicRefactor = DummyRefactor
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_check_ultimate_editor_dependencies_success(monkeypatch):
    _install_tree_sitter(monkeypatch)
    success, message = health_check.check_ultimate_editor_dependencies()
    assert success is True
    assert "Ultimate Editor" in message


def test_check_ultimate_editor_dependencies_import_failure(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("tree_sitter"):
            raise ImportError("missing module")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    success, message = health_check.check_ultimate_editor_dependencies()
    assert success is False
    assert "Ultimate Editor dependencies missing" in message


def test_check_ultimate_editor_dependencies_parse_failure(monkeypatch):
    _install_tree_sitter(monkeypatch, root_type="not-module")
    success, message = health_check.check_ultimate_editor_dependencies()
    assert success is False
    assert "parse test failed" in message


def test_check_ultimate_editor_dependencies_inner_exception(monkeypatch):
    _install_faulty_tree_sitter(monkeypatch, RuntimeError("boom"))
    success, message = health_check.check_ultimate_editor_dependencies()
    assert success is False
    assert "functionality test failed" in message


def test_check_atomic_refactor_dependencies_success(monkeypatch):
    fake_module = ModuleType("forge.agenthub.codeact_agent.tools.atomic_refactor")

    class DummyRefactor:
        pass

    fake_module.AtomicRefactor = DummyRefactor
    monkeypatch.setitem(
        sys.modules,
        "forge.agenthub.codeact_agent.tools.atomic_refactor",
        fake_module,
    )
    success, message = health_check.check_atomic_refactor_dependencies()
    assert success is True
    assert "Atomic refactoring" in message


def test_check_atomic_refactor_dependencies_failure(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "forge.agenthub.codeact_agent.tools.atomic_refactor":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    success, message = health_check.check_atomic_refactor_dependencies()
    assert success is False
    assert "not available" in message or "not installed" in message


def test_check_atomic_refactor_dependencies_init_failure(monkeypatch):
    def initializer():
        raise RuntimeError("boom")

    _install_atomic_refactor_stub(monkeypatch, initializer=initializer)
    success, message = health_check.check_atomic_refactor_dependencies()
    assert success is False
    assert "initialization failed" in message


def test_run_production_health_check_failure(monkeypatch):
    monkeypatch.setattr(
        health_check,
        "check_ultimate_editor_dependencies",
        lambda: (False, "missing tree sitter"),
    )
    monkeypatch.setattr(
        health_check,
        "check_atomic_refactor_dependencies",
        lambda: (True, "ok"),
    )
    with pytest.raises(RuntimeError):
        health_check.run_production_health_check(raise_on_failure=True)


def test_run_production_health_check_success(monkeypatch):
    monkeypatch.setattr(
        health_check,
        "check_ultimate_editor_dependencies",
        lambda: (True, "ready"),
    )
    monkeypatch.setattr(
        health_check,
        "check_atomic_refactor_dependencies",
        lambda: (False, "optional missing"),
    )
    results = health_check.run_production_health_check(raise_on_failure=False)
    assert results["overall_status"] == "HEALTHY"
    assert results["atomic_refactor"]["status"] == "FAIL"


def test_run_production_health_check_critical_no_raise(monkeypatch):
    monkeypatch.setattr(
        health_check,
        "check_ultimate_editor_dependencies",
        lambda: (False, "missing"),
    )
    monkeypatch.setattr(
        health_check,
        "check_atomic_refactor_dependencies",
        lambda: (True, "ok"),
    )
    results = health_check.run_production_health_check(raise_on_failure=False)
    assert results["overall_status"] == "CRITICAL_FAILURE"


def test_main_entrypoint(monkeypatch, capsys):
    _install_tree_sitter(monkeypatch)
    _install_atomic_refactor_stub(monkeypatch)
    runpy.run_module(
        "forge.agenthub.codeact_agent.tools.health_check", run_name="__main__"
    )
    captured = capsys.readouterr().out
    assert "HEALTH CHECK RESULTS" in captured
