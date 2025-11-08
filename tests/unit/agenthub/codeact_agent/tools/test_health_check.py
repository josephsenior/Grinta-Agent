"""Tests for the production health check utilities."""

from __future__ import annotations

import types

import pytest

from forge.agenthub.codeact_agent.tools import health_check


def _install_tree_sitter_stubs(monkeypatch: pytest.MonkeyPatch, should_parse: bool = True) -> None:
    class DummyRoot:
        def __init__(self, node_type: str) -> None:
            self.type = node_type

    class DummyTree:
        def __init__(self, node_type: str) -> None:
            self.root_node = DummyRoot(node_type)

    class DummyParser:
        def __init__(self, node_type: str = "module") -> None:
            self._node_type = node_type

        def parse(self, code: bytes) -> DummyTree:
            if not should_parse:
                raise RuntimeError("parse failure")
            return DummyTree(self._node_type)

    tree_sitter_module = types.SimpleNamespace(Language=object, Parser=lambda: DummyParser())
    language_pack_module = types.SimpleNamespace(
        get_language=lambda name: object(),
        get_parser=lambda name: DummyParser(),
    )
    monkeypatch.setitem(sys_modules := __import__("sys").modules, "tree_sitter", tree_sitter_module)
    monkeypatch.setitem(sys_modules, "tree_sitter_language_pack", language_pack_module)


def test_check_ultimate_editor_dependencies_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tree_sitter_stubs(monkeypatch, should_parse=True)
    ok, message = health_check.check_ultimate_editor_dependencies()
    assert ok is True
    assert "Ultimate Editor" in message


def test_check_ultimate_editor_dependencies_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_tree_sitter_stubs(monkeypatch, should_parse=False)
    ok, message = health_check.check_ultimate_editor_dependencies()
    assert ok is False
    assert "Tree-sitter functionality test failed" in message


def test_check_atomic_refactor_dependencies_success(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_module = types.ModuleType("forge.agenthub.codeact_agent.tools.atomic_refactor")

    class AtomicRefactor:
        def __init__(self) -> None:
            self.initialized = True

    stub_module.AtomicRefactor = AtomicRefactor
    monkeypatch.setitem(__import__("sys").modules, "forge.agenthub.codeact_agent.tools.atomic_refactor", stub_module)

    ok, message = health_check.check_atomic_refactor_dependencies()
    assert ok is True
    assert "Atomic refactoring fully operational" in message


def test_check_atomic_refactor_dependencies_initialization_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_module = types.ModuleType("forge.agenthub.codeact_agent.tools.atomic_refactor")

    class AtomicRefactor:
        def __init__(self) -> None:
            raise RuntimeError("boom")

    stub_module.AtomicRefactor = AtomicRefactor
    monkeypatch.setitem(__import__("sys").modules, "forge.agenthub.codeact_agent.tools.atomic_refactor", stub_module)

    ok, message = health_check.check_atomic_refactor_dependencies()
    assert ok is False
    assert "initialization failed" in message


def test_run_production_health_check_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_check, "check_ultimate_editor_dependencies", lambda: (True, "OK"))
    monkeypatch.setattr(health_check, "check_atomic_refactor_dependencies", lambda: (True, "OK"))

    results = health_check.run_production_health_check(raise_on_failure=False)
    assert results["overall_status"] == "HEALTHY"
    assert results["ultimate_editor"]["status"] == "PASS"
    assert results["atomic_refactor"]["status"] == "PASS"


def test_run_production_health_check_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_check, "check_ultimate_editor_dependencies", lambda: (False, "missing"))
    monkeypatch.setattr(health_check, "check_atomic_refactor_dependencies", lambda: (True, "OK"))

    results = health_check.run_production_health_check(raise_on_failure=False)
    assert results["overall_status"] == "CRITICAL_FAILURE"
    assert results["ultimate_editor"]["status"] == "FAIL"


def test_run_production_health_check_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health_check, "check_ultimate_editor_dependencies", lambda: (False, "missing"))
    monkeypatch.setattr(health_check, "check_atomic_refactor_dependencies", lambda: (True, "OK"))

    with pytest.raises(RuntimeError):
        health_check.run_production_health_check(raise_on_failure=True)

