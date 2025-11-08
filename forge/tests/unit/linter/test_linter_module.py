"""Tests for the `forge.linter` module."""

from __future__ import annotations

import importlib
import sys
import types

import pytest


def _clear_module(name: str) -> None:
    """Remove a module (and its submodules) from sys.modules if present."""
    to_delete = [mod for mod in sys.modules if mod == name or mod.startswith(f"{name}.")]
    for mod in to_delete:
        sys.modules.pop(mod, None)


def test_stub_linter_used_when_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """forge.linter should expose stub classes when forge_aci is unavailable."""
    _clear_module("forge.linter")
    _clear_module("forge_aci")
    _clear_module("forge_aci.linter")

    module = importlib.import_module("forge.linter")

    linter = module.DefaultLinter()
    result = linter.lint()
    assert isinstance(result, module.LintResult)
    assert result.errors == []
    assert result.warnings == []


def test_real_linter_imported_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """forge.linter should reuse forge_aci.linter when the dependency exists."""
    _clear_module("forge.linter")
    fake_package = types.ModuleType("forge_aci")
    fake_package.__path__ = []

    class RealLintResult:
        def __init__(self):
            self.errors = ["err"]
            self.warnings = ["warn"]

    class RealDefaultLinter:
        def lint(self, *args, **kwargs):
            return RealLintResult()

    fake_submodule = types.ModuleType("forge_aci.linter")
    fake_submodule.DefaultLinter = RealDefaultLinter
    fake_submodule.LintResult = RealLintResult

    monkeypatch.setitem(sys.modules, "forge_aci", fake_package)
    monkeypatch.setitem(sys.modules, "forge_aci.linter", fake_submodule)

    try:
        module = importlib.reload(importlib.import_module("forge.linter"))

        linter = module.DefaultLinter()
        result = linter.lint()
        assert isinstance(result, RealLintResult)
        assert result.errors == ["err"]
        assert result.warnings == ["warn"]
    finally:
        _clear_module("forge_aci")


