"""Tests for the `forge.linter` import wrapper."""

from __future__ import annotations

import importlib
import sys
import types

import pytest


def reload_module() -> types.ModuleType:
    """Helper to reload the forge.linter module and return it."""
    return importlib.reload(
        sys.modules.get("forge.linter", importlib.import_module("forge.linter"))
    )


@pytest.fixture(autouse=True)
def reset_modules():
    """Ensure forge.linter is reloaded fresh for each test."""
    import forge.linter as linter_module

    yield

    sys.modules.pop("forge_aci", None)
    sys.modules.pop("forge_aci.linter", None)
    importlib.reload(linter_module)


def test_import_uses_real_module_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When forge_aci.linter exists we should expose its classes."""
    fake_package = types.ModuleType("forge_aci")
    fake_module = types.ModuleType("forge_aci.linter")

    class RealLintResult:
        pass

    class RealDefaultLinter:
        pass

    fake_module.LintResult = RealLintResult
    fake_module.DefaultLinter = RealDefaultLinter

    monkeypatch.setitem(sys.modules, "forge_aci", fake_package)
    monkeypatch.setitem(sys.modules, "forge_aci.linter", fake_module)

    module = reload_module()

    assert module.LintResult is RealLintResult
    assert module.DefaultLinter is RealDefaultLinter
    assert set(module.__all__) == {"DefaultLinter", "LintResult"}


def test_import_falls_back_to_stub_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If forge_aci is missing we should expose lightweight stub implementations."""
    monkeypatch.delitem(sys.modules, "forge_aci", raising=False)
    monkeypatch.delitem(sys.modules, "forge_aci.linter", raising=False)

    module = reload_module()

    stub_linter = module.DefaultLinter()
    result = stub_linter.lint()

    assert hasattr(result, "errors") and result.errors == []
    assert hasattr(result, "warnings") and result.warnings == []
    assert set(module.__all__) == {"DefaultLinter", "LintResult"}
