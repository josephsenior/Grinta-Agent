from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

import forge.agenthub.codeact_agent.tools.universal_editor as universal_editor


def _make_node(
    node_type: str,
    *,
    children: list | None = None,
    start_byte: int = 0,
    end_byte: int | None = None,
    start_point: tuple[int, int] = (0, 0),
    end_point: tuple[int, int] = (0, 0),
    is_missing: bool = False,
):
    return SimpleNamespace(
        type=node_type,
        children=list(children or []),
        start_byte=start_byte,
        end_byte=start_byte if end_byte is None else end_byte,
        start_point=start_point,
        end_point=end_point,
        is_missing=is_missing,
    )


def _make_tree(root):
    return SimpleNamespace(root_node=root)


@pytest.fixture
def editor(monkeypatch):
    created = []

    class DummyParser:
        def __init__(self, lang):
            created.append(lang)
            self.lang = lang

        def parse(self, data: bytes):
            return _make_tree(
                _make_node(
                    "module",
                    children=[],
                    start_byte=0,
                    end_byte=len(data),
                    end_point=(0, len(data)),
                )
            )

    monkeypatch.setattr(universal_editor, "TREE_SITTER_AVAILABLE", True)
    monkeypatch.setattr(universal_editor, "_get_language", lambda lang: f"lang:{lang}")
    monkeypatch.setattr(universal_editor, "_RuntimeParser", DummyParser)

    editor = universal_editor.UniversalEditor()
    editor._created_parsers = created  # type: ignore[attr-defined]
    return editor


def test_init_requires_tree_sitter(monkeypatch):
    monkeypatch.setattr(universal_editor, "TREE_SITTER_AVAILABLE", False)
    with pytest.raises(ImportError):
        universal_editor.UniversalEditor()


def test_get_parser_creates_and_caches(editor):
    parser = editor.get_parser("python")
    assert parser.lang == "lang:python"
    parser_again = editor.get_parser("python")
    assert parser_again is parser
    assert editor._created_parsers.count("lang:python") == 1  # type: ignore[attr-defined]


def test_get_parser_missing_runtime_returns_none(monkeypatch):
    monkeypatch.setattr(universal_editor, "TREE_SITTER_AVAILABLE", True)
    monkeypatch.setattr(universal_editor, "_get_language", None)
    editor = universal_editor.UniversalEditor()
    assert editor.get_parser("python") is None


def test_parse_file_uses_cache(editor, tmp_path):
    file_path = tmp_path / "sample.py"
    file_path.write_text("def foo():\n    return 1", encoding="utf-8")

    tree1, file_bytes1, language1 = editor.parse_file(str(file_path))
    assert language1 == "python"
    file_path.write_text("mutated content", encoding="utf-8")
    tree2, file_bytes2, language2 = editor.parse_file(str(file_path))

    assert tree1 is tree2  # cached
    assert file_bytes1 == file_bytes2  # cached bytes
    assert language2 == "python"


def test_parse_file_returns_none_when_parser_missing(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("text", encoding="utf-8")
    monkeypatch.setattr(editor, "detect_language", lambda *_: "python")
    monkeypatch.setattr(editor, "get_parser", lambda *_: None)
    assert editor.parse_file(str(file_path)) is None


def test_parse_file_handles_parse_exception(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("text", encoding="utf-8")
    monkeypatch.setattr(editor, "detect_language", lambda *_: "python")

    class BadParser:
        def parse(self, data):
            raise ValueError("boom")

    monkeypatch.setattr(editor, "get_parser", lambda *_: BadParser())
    assert editor.parse_file(str(file_path)) is None


def test_parse_file_unknown_extension(editor, tmp_path):
    file_path = tmp_path / "sample.unknown"
    file_path.write_text("noop", encoding="utf-8")
    assert editor.parse_file(str(file_path)) is None


def test_parse_file_missing_file(editor, tmp_path):
    missing_file = tmp_path / "missing.py"
    assert editor.parse_file(str(missing_file)) is None


def test_find_symbol_method_notation(editor, monkeypatch):
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(editor, "parse_file", lambda *args, **kwargs: (tree, b"", "python"))
    monkeypatch.setattr(editor, "_find_method_in_class", lambda *args, **kwargs: "found")

    result = editor.find_symbol("foo.py", "MyClass.my_method")
    assert result == "found"


def test_find_symbol_generic_search(editor, monkeypatch):
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(editor, "parse_file", lambda *args, **kwargs: (tree, b"", "python"))
    monkeypatch.setattr(editor, "_search_tree_for_symbol", lambda *args, **kwargs: "symbol")

    result = editor.find_symbol("foo.py", "plain_symbol")
    assert result == "symbol"


def test_edit_function_success(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("def foo():\n    pass", encoding="utf-8")
    tree = _make_tree(_make_node("root"))

    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"old", "python")
    )
    monkeypatch.setattr(editor, "_find_function_node", lambda *args, **kwargs: _make_node("func"))
    body_node = _make_node("block", start_byte=0, end_byte=0)
    monkeypatch.setattr(editor, "_get_function_body_node", lambda *args, **kwargs: body_node)
    monkeypatch.setattr(
        editor,
        "_replace_node_content",
        lambda original, node, content, preserve_indentation=True: "new-code",
    )
    monkeypatch.setattr(editor, "_validate_syntax", lambda *args, **kwargs: (True, "ok"))

    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "new-code"
    assert str(file_path) not in editor.tree_cache


def test_edit_function_validation_failure(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("text", encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"old", "python")
    )
    monkeypatch.setattr(editor, "_find_function_node", lambda *args, **kwargs: _make_node("func"))
    body_node = _make_node("block", start_byte=0, end_byte=0)
    monkeypatch.setattr(editor, "_get_function_body_node", lambda *args, **kwargs: body_node)
    monkeypatch.setattr(editor, "_replace_node_content", lambda *args, **kwargs: "new")
    monkeypatch.setattr(editor, "_validate_syntax", lambda *args, **kwargs: (False, "bad"))

    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False
    assert result.syntax_valid is False
    assert file_path.read_text(encoding="utf-8") == "text"


def test_edit_function_missing_body(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("text", encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"old", "python")
    )
    monkeypatch.setattr(editor, "_find_function_node", lambda *args, **kwargs: _make_node("func"))
    monkeypatch.setattr(editor, "_get_function_body_node", lambda *args, **kwargs: None)

    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False
    assert "Could not locate function body" in result.message


def test_rename_symbol_success(editor, monkeypatch, tmp_path):
    original = "alpha foo beta foo"
    file_path = tmp_path / "foo.py"
    file_path.write_text(original, encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, original.encode(), "python")
    )

    occurrences = [
        _make_node("identifier", start_byte=6, end_byte=9),
        _make_node("identifier", start_byte=15, end_byte=18),
    ]
    monkeypatch.setattr(
        editor, "_find_all_symbol_occurrences", lambda *args, **kwargs: occurrences
    )
    monkeypatch.setattr(editor, "_validate_syntax", lambda *args, **kwargs: (True, "ok"))

    result = editor.rename_symbol(str(file_path), "foo", "bar")
    assert result.success is True
    assert file_path.read_text(encoding="utf-8") == "alpha bar beta bar"


def test_rename_symbol_validation_failure(editor, monkeypatch, tmp_path):
    original = "alpha foo"
    file_path = tmp_path / "foo.py"
    file_path.write_text(original, encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, original.encode(), "python")
    )
    occurrences = [_make_node("identifier", start_byte=6, end_byte=9)]
    monkeypatch.setattr(
        editor, "_find_all_symbol_occurrences", lambda *args, **kwargs: occurrences
    )
    monkeypatch.setattr(editor, "_validate_syntax", lambda *args, **kwargs: (False, "bad"))

    result = editor.rename_symbol(str(file_path), "foo", "bar")
    assert result.success is False
    assert result.syntax_valid is False


def test_get_name_node_with_nested_identifier(editor):
    inner = _make_node("identifier")
    outer = _make_node("function_declarator", children=[inner])
    node = _make_node("function_definition", children=[outer])
    assert editor._get_name_node(node) is inner


def test_find_function_node_matches(editor):
    identifier = _make_node("identifier", start_byte=4, end_byte=7)
    func = _make_node("function_definition", children=[identifier])
    tree = _make_tree(_make_node("module", children=[func]))
    file_bytes = b"def foo(): pass"
    found = editor._find_function_node(tree, file_bytes, "foo", "python")
    assert found is func


def test_find_method_in_class(editor):
    method_identifier = _make_node("identifier", start_byte=3, end_byte=6)
    method_node = _make_node(
        "function_definition",
        children=[method_identifier],
        start_point=(1, 4),
        end_point=(3, 0),
        start_byte=3,
        end_byte=9,
    )
    class_identifier = _make_node("identifier", start_byte=0, end_byte=3)
    class_node = _make_node(
        "class_definition",
        children=[class_identifier, method_node],
        start_point=(0, 0),
        end_point=(3, 0),
    )
    tree = _make_tree(_make_node("module", children=[class_node]))
    file_bytes = b"Foobar"

    result = editor._find_method_in_class(
        tree, file_bytes, "Foo", "bar", "file.py", "python"
    )
    assert isinstance(result, universal_editor.SymbolLocation)
    assert result.symbol_name == "bar"
    assert result.parent_name == "Foo"


def test_get_function_body_node(editor):
    body = _make_node("block")
    node = _make_node("function", children=[body])
    assert editor._get_function_body_node(node, "python") is body


def test_search_tree_for_symbol_variants(editor):
    identifier_func = _make_node("identifier", start_byte=0, end_byte=3)
    func = _make_node(
        "function_definition",
        children=[identifier_func],
        start_point=(0, 0),
        end_point=(1, 0),
    )
    identifier_class = _make_node("identifier", start_byte=4, end_byte=7)
    class_node = _make_node(
        "class_definition",
        children=[identifier_class],
        start_point=(2, 0),
        end_point=(4, 0),
    )
    root = _make_node("module", children=[func, class_node])
    tree = _make_tree(root)
    file_bytes = b"foo Bar"

    func_result = editor._search_tree_for_symbol(
        tree, file_bytes, "foo", "file.py", "python", symbol_type="function"
    )
    class_result = editor._search_tree_for_symbol(
        tree, file_bytes, "Bar", "file.py", "python", symbol_type="class"
    )
    either_result = editor._search_tree_for_symbol(
        tree, file_bytes, "Bar", "file.py", "python", symbol_type=None
    )

    assert func_result is not None
    assert class_result is not None
    assert either_result is not None


def test_replace_node_content_preserves_indentation(editor):
    original = "def foo():\n    pass\n"
    node = _make_node("block", start_byte=15, end_byte=19)
    result = editor._replace_node_content(
        original, node, "return 1\nnext_line", preserve_indentation=True
    )
    assert "    next_line" in result


def test_validate_syntax_with_error_nodes(editor):
    error_node = _make_node("ERROR")
    root = _make_node("module", children=[error_node])
    tree = _make_tree(root)

    parser = editor.get_parser("python")
    parser.parse = lambda _: tree  # type: ignore[assignment]
    valid, message = editor._validate_syntax("code", "file.py", "python")
    assert valid is False
    assert "syntax errors" in message


def test_has_syntax_errors_nested(editor):
    child = _make_node("identifier", is_missing=True)
    parent = _make_node("module", children=[child])
    assert editor._has_syntax_errors(parent) is True


def test_find_all_symbol_occurrences(editor):
    node = _make_node(
        "module",
        children=[
            _make_node("identifier", start_byte=0, end_byte=3),
            _make_node(
                "child",
                children=[_make_node("identifier", start_byte=4, end_byte=7)],
            ),
        ],
    )
    tree = _make_tree(node)
    file_bytes = b"foobar"
    occurrences = editor._find_all_symbol_occurrences(tree, file_bytes, "foo", "python")
    assert len(occurrences) == 1


def test_find_node_by_name_matches(editor):
    identifier = _make_node("identifier", start_byte=0, end_byte=3)
    func = _make_node("function_definition", children=[identifier])
    root = _make_node("module", children=[func])
    tree = _make_tree(root)
    file_bytes = b"foo"
    found = editor._find_node_by_name(root, file_bytes, "foo", ["function_definition"])
    assert found is func


def test_search_tree_for_symbol(editor):
    identifier = _make_node("identifier", start_byte=0, end_byte=3)
    func = _make_node(
        "function_definition",
        children=[identifier],
        start_point=(0, 0),
        end_point=(1, 0),
    )
    root = _make_node("module", children=[func])
    tree = _make_tree(root)
    result = editor._search_tree_for_symbol(
        tree, b"foo", "foo", "file.py", "python", symbol_type="function"
    )
    assert isinstance(result, universal_editor.SymbolLocation)
    assert result.symbol_name == "foo"


def test_get_supported_languages_and_clear_cache(editor):
    languages = editor.get_supported_languages()
    assert "python" in languages

    editor.tree_cache["foo.py"] = "tree"
    editor.file_cache["foo.py"] = b"bytes"
    editor.clear_cache()
    assert editor.tree_cache == {}
    assert editor.file_cache == {}


def test_edit_function_parse_failure(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("code", encoding="utf-8")
    monkeypatch.setattr(editor, "parse_file", lambda *args, **kwargs: None)
    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False
    assert "Failed to parse" in result.message


def test_edit_function_function_not_found(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("code", encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"code", "python")
    )
    monkeypatch.setattr(editor, "_find_function_node", lambda *args, **kwargs: None)
    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False
    assert "Function 'foo' not found" in result.message


def test_edit_function_exception_path(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("def foo():\n    pass\n", encoding="utf-8")
    tree = _make_tree(_make_node("root"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"code", "python")
    )
    monkeypatch.setattr(editor, "_find_function_node", lambda *args, **kwargs: _make_node("func"))
    body_node = _make_node("block", start_byte=0, end_byte=0)
    monkeypatch.setattr(editor, "_get_function_body_node", lambda *args, **kwargs: body_node)

    def boom(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(editor, "_replace_node_content", boom)
    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False
    assert "Error: boom" in result.message


def test_edit_function_full_flow(editor, monkeypatch, tmp_path):
    source = "def foo():\n    pass\n"
    file_path = tmp_path / "foo.py"
    file_path.write_text(source, encoding="utf-8")
    body_node = _make_node("block", start_byte=15, end_byte=len(source))
    func_node = _make_node(
        "function_definition",
        children=[
            _make_node("identifier", start_byte=4, end_byte=7),
            body_node,
        ],
    )
    tree = _make_tree(_make_node("module", children=[func_node]))
    file_bytes = source.encode()

    def fake_parse(file_path: str, use_cache: bool = False):
        return tree, file_bytes, "python"

    monkeypatch.setattr(editor, "parse_file", fake_parse)
    result = editor.edit_function(str(file_path), "foo", "return 42")
    assert result.success is True
    assert "return 42" in file_path.read_text(encoding="utf-8")


def test_rename_symbol_parse_failure(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("code", encoding="utf-8")
    monkeypatch.setattr(editor, "parse_file", lambda *args, **kwargs: None)
    result = editor.rename_symbol(str(file_path), "foo", "bar")
    assert result.success is False
    assert "Failed to parse" in result.message


def test_rename_symbol_not_found(editor, monkeypatch, tmp_path):
    file_path = tmp_path / "foo.py"
    file_path.write_text("code", encoding="utf-8")
    tree = _make_tree(_make_node("module"))
    monkeypatch.setattr(
        editor, "parse_file", lambda *args, **kwargs: (tree, b"code", "python")
    )
    monkeypatch.setattr(
        editor, "_find_all_symbol_occurrences", lambda *args, **kwargs: []
    )
    result = editor.rename_symbol(str(file_path), "foo", "bar")
    assert result.success is False
    assert "Symbol 'foo' not found" in result.message


def test_rename_symbol_full_flow(editor, monkeypatch, tmp_path):
    source = "foo = foo\nfoo()"
    file_path = tmp_path / "foo.py"
    file_path.write_text(source, encoding="utf-8")
    identifiers = [
        _make_node("identifier", start_byte=0, end_byte=3),
        _make_node("identifier", start_byte=6, end_byte=9),
        _make_node("identifier", start_byte=10, end_byte=13),
    ]
    tree = _make_tree(_make_node("module", children=identifiers))
    file_bytes = source.encode()

    def fake_parse(file_path: str, use_cache: bool = False):
        return tree, file_bytes, "python"

    monkeypatch.setattr(editor, "parse_file", fake_parse)
    result = editor.rename_symbol(str(file_path), "foo", "bar")
    assert result.success is True
    assert "bar = bar" in file_path.read_text(encoding="utf-8")


def test_find_symbol_returns_none_when_parse_fails(editor, monkeypatch):
    monkeypatch.setattr(editor, "parse_file", lambda *args, **kwargs: None)
    assert editor.find_symbol("foo.py", "symbol") is None


def test_find_method_in_class_missing_class(editor):
    tree = _make_tree(_make_node("module", children=[]))
    file_bytes = b""
    result = editor._find_method_in_class(
        tree, file_bytes, "Foo", "bar", "file.py", "python"
    )
    assert result is None


def test_find_method_in_class_missing_method(editor):
    class_identifier = _make_node("identifier", start_byte=0, end_byte=3)
    class_node = _make_node("class_definition", children=[class_identifier])
    tree = _make_tree(_make_node("module", children=[class_node]))
    file_bytes = b"Foo"
    result = editor._find_method_in_class(
        tree, file_bytes, "Foo", "bar", "file.py", "python"
    )
    assert result is None


def test_find_node_by_name_recurses(editor):
    identifier = _make_node("identifier", start_byte=0, end_byte=3)
    nested = _make_node("wrapper", children=[_make_node("function_definition", children=[identifier])])
    root = _make_node("module", children=[nested])
    file_bytes = b"foo"
    found = editor._find_node_by_name(root, file_bytes, "foo", ["function_definition"])
    assert found is nested.children[0]


def test_get_name_node_returns_none(editor):
    node = _make_node("function_definition", children=[_make_node("other")])
    assert editor._get_name_node(node) is None


def test_search_tree_for_symbol_returns_none(editor):
    tree = _make_tree(_make_node("module", children=[]))
    assert (
        editor._search_tree_for_symbol(tree, b"", "missing", "file.py", "python")
        is None
    )


def test_validate_syntax_parser_missing(monkeypatch):
    monkeypatch.setattr(universal_editor, "TREE_SITTER_AVAILABLE", True)
    monkeypatch.setattr(universal_editor, "_get_language", lambda lang: lang)
    monkeypatch.setattr(universal_editor, "_RuntimeParser", None)
    editor = universal_editor.UniversalEditor()
    monkeypatch.setattr(editor, "get_parser", lambda *_: None)
    valid, message = editor._validate_syntax("code", "file.py", "python")
    assert valid is True
    assert "skipping" in message


def test_validate_syntax_exception(editor, monkeypatch):
    class BadParser:
        def parse(self, data):
            raise ValueError("boom")

    monkeypatch.setattr(editor, "get_parser", lambda *_: BadParser())
    valid, message = editor._validate_syntax("code", "file.py", "python")
    assert valid is True
    assert "Validation skipped" in message

