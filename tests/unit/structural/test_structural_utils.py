"""Unit tests for forge.structural helper functions."""

from __future__ import annotations

import ast
from types import SimpleNamespace

import pytest

import forge.structural as structural


def test_available_always_true() -> None:
    assert structural.available() is True


def test_find_lang_lib_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(structural.os.path, "exists", lambda path: False)
    assert structural._find_lang_lib() is None


def test_find_lang_lib_custom_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    ext = {"windows": "dll", "darwin": "dylib"}.get(
        structural.platform.system().lower(), "so"
    )
    lib_path = tmp_path / f"my-langs.{ext}"
    lib_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(structural.os.path, "abspath", lambda path: str(tmp_path))
    monkeypatch.setattr(
        structural.os.path, "exists", lambda path: str(path) == str(lib_path)
    )
    assert structural._find_lang_lib() == str(lib_path)


def test_find_lang_lib_linux(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    lib_path = tmp_path / "my-langs.so"
    lib_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(structural.platform, "system", lambda: "Linux")
    monkeypatch.setattr(structural.os.path, "abspath", lambda path: str(tmp_path))
    monkeypatch.setattr(
        structural.os.path, "exists", lambda path: str(path) == str(lib_path)
    )
    assert structural._find_lang_lib() == str(lib_path)


def test_find_lang_lib_windows(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    lib_path = tmp_path / "my-langs.dll"
    lib_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(structural.platform, "system", lambda: "Windows")
    monkeypatch.setattr(structural.os.path, "abspath", lambda path: str(tmp_path))
    monkeypatch.setattr(
        structural.os.path, "exists", lambda path: str(path) == str(lib_path)
    )
    assert structural._find_lang_lib() == str(lib_path)


def test_find_lang_lib_darwin(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    lib_path = tmp_path / "my-langs.dylib"
    lib_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(structural.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(structural.os.path, "abspath", lambda path: str(tmp_path))
    monkeypatch.setattr(
        structural.os.path, "exists", lambda path: str(path) == str(lib_path)
    )
    assert structural._find_lang_lib() == str(lib_path)


def test_parse_python_source_ast_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(structural, "_HAS_TS", False)
    tree = structural.parse_python_source("x = 1")
    assert isinstance(tree, ast.AST)


def test_parse_python_source_tree_sitter_path(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNode:
        def __init__(self) -> None:
            self.type = "root"
            self.children = []

    class FakeTree:
        def __init__(self) -> None:
            self.root_node = FakeNode()

    class FakeParser:
        def set_language(self, lang) -> None:
            assert lang.name == "python"  # type: ignore[attr-defined]

        def parse(self, data: bytes):
            assert data.startswith(b"def")
            return FakeTree()

    class FakeLanguage:
        def __init__(self, lib, name) -> None:
            assert lib == "dummy"
            self.name = name

    monkeypatch.setattr(structural, "_HAS_TS", True)
    monkeypatch.setattr(structural, "Language", FakeLanguage)
    monkeypatch.setattr(structural, "Parser", FakeParser)
    monkeypatch.setattr(structural, "_find_lang_lib", lambda: "dummy")

    tree = structural.parse_python_source("def demo():\n    return 0")
    assert hasattr(tree, "root_node")


def test_node_type_counts_ast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(structural, "_HAS_TS", False)
    tree = ast.parse("a = 1\nb = 2")
    counts = structural.node_type_counts(tree)
    assert counts["Assign"] == 2


def test_node_type_counts_tree_sitter(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNode(SimpleNamespace):
        pass

    root = FakeNode(
        type="root",
        children=[
            FakeNode(type="child", children=[]),
            FakeNode(type="child", children=[]),
        ],
    )

    class FakeTree:
        root_node = root

    monkeypatch.setattr(structural, "_HAS_TS", True)
    counts = structural.node_type_counts(FakeTree())
    assert counts["root"] == 1
    assert counts["child"] == 2


def test_semantic_diff_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(structural, "_HAS_TS", False)
    diff = structural.semantic_diff_counts("a = 1", "a = 1\nb = 2")
    assert diff["Assign"] == 1
