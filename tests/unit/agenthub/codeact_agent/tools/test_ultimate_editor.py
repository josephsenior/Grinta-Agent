from __future__ import annotations

import builtins
from types import SimpleNamespace
from pathlib import Path

import pytest

import forge.agenthub.codeact_agent.tools.ultimate_editor as ultimate_editor
from forge.agenthub.codeact_agent.tools.atomic_refactor import (
    RefactorResult,
    RefactorTransaction,
)
from forge.agenthub.codeact_agent.tools.smart_errors import ErrorSuggestion
from forge.agenthub.codeact_agent.tools.universal_editor import (
    EditResult,
    SymbolLocation,
)
from forge.agenthub.codeact_agent.tools.whitespace_handler import (
    IndentConfig,
    IndentStyle,
)


class DummyUniversal:
    def __init__(self):
        self.detect_language_return = "python"
        self.edit_result = EditResult(success=True, message="edited")
        self.rename_result = EditResult(success=True, message="renamed")
        self.find_symbol_result: SymbolLocation | None = SymbolLocation(
            file_path="file.py",
            line_start=1,
            line_end=2,
            byte_start=0,
            byte_end=10,
            node_type="function_definition",
            symbol_name="foo",
        )
        self.parse_file_data = None
        self.supported = ["python"]
        self.edit_calls: list[tuple] = []
        self.clear_cache_called = False

    def get_supported_languages(self):
        return self.supported

    def detect_language(self, file_path):
        return self.detect_language_return

    def edit_function(self, *args, **kwargs):
        self.edit_calls.append(("edit_function", args, kwargs))
        return self.edit_result

    def rename_symbol(self, *args, **kwargs):
        return self.rename_result

    def find_symbol(self, *args, **kwargs):
        return self.find_symbol_result

    def _validate_syntax(self, new_content, file_path, language):
        if "INVALID" in new_content:
            return False, "boom"
        return True, ""

    def parse_file(self, file_path):
        if self.parse_file_data:
            return self.parse_file_data
        raise RuntimeError("no parse data")

    def _get_name_node(self, node):
        return SimpleNamespace(start_byte=node.start, end_byte=node.end)

    def clear_cache(self):
        self.clear_cache_called = True


class DummyWhitespace:
    def __init__(self):
        self.cleaned_contents: list[str] = []
        self.normalized_input: str | None = None
        self.raise_on_clean = False

    def detect_indent(self, content, language):
        return IndentConfig(style=IndentStyle.SPACES, size=4, line_ending="\n")

    def auto_indent_block(self, new_body, base_indent, config, language):
        prefix = base_indent if isinstance(base_indent, str) else " " * (
            config.size * base_indent
        )
        lines = [prefix + line.strip() for line in new_body.splitlines()]
        return "\n".join(lines) or prefix + new_body

    def clean_whitespace(self, content, language):
        if self.raise_on_clean:
            raise RuntimeError("clean failed")
        self.cleaned_contents.append(content)
        return content.replace("  ", " ")

    def get_line_indent(self, line, config):
        return " " * config.size

    def normalize_indent(self, original, target_config, language):
        self.normalized_input = original
        return "normalized"

    def clear_cache(self):
        pass


class DummyTransaction(RefactorTransaction):
    def __init__(self, transaction_id: str):
        super().__init__(transaction_id=transaction_id)
        self.backup_dir = f"/tmp/{transaction_id}"


class DummyAtomicRefactor:
    def __init__(self):
        self.transactions: list[DummyTransaction] = []
        self.commits: list[tuple[RefactorTransaction, bool]] = []
        self.cleaned: list[RefactorTransaction] = []
        self.dry_run_result = RefactorResult(True, "dry ok", 0, "txn")
        self.rollback_calls: list[RefactorTransaction] = []
        self.commit_result: RefactorResult | None = None

    def begin_transaction(self):
        txn = DummyTransaction(f"txn_{len(self.transactions)+1}")
        self.transactions.append(txn)
        return txn

    def dry_run(self, transaction):
        return self.dry_run_result

    def commit(self, transaction, validate=True):
        self.commits.append((transaction, validate))
        if self.commit_result is not None:
            return self.commit_result
        return RefactorResult(True, "committed", 1, transaction.transaction_id)

    def rollback(self, transaction):
        self.rollback_calls.append(transaction)
        return RefactorResult(True, "rolled", 0, transaction.transaction_id)

    def cleanup_transaction(self, transaction):
        self.cleaned.append(transaction)


class DummyErrorHandler:
    def __init__(self):
        self.raise_symbol = False

    def symbol_not_found(self, name, available):
        if self.raise_symbol:
            raise RuntimeError("error")
        return ErrorSuggestion(
            message=f"Similar: {', '.join(available)}",
            suggestions=available,
            confidence=0.5,
        )


@pytest.fixture
def editor_factory(monkeypatch, tmp_path):
    def _build(config=None):
        dummy_universal = DummyUniversal()
        dummy_whitespace = DummyWhitespace()
        dummy_refactor = DummyAtomicRefactor()
        dummy_errors = DummyErrorHandler()

        monkeypatch.setattr(
            ultimate_editor, "UniversalEditor", lambda: dummy_universal
        )
        monkeypatch.setattr(
            ultimate_editor, "WhitespaceHandler", lambda: dummy_whitespace
        )
        monkeypatch.setattr(
            ultimate_editor, "AtomicRefactor", lambda: dummy_refactor
        )
        monkeypatch.setattr(
            ultimate_editor, "SmartErrorHandler", lambda: dummy_errors
        )

        editor = ultimate_editor.UltimateEditor(config)
        return editor, dummy_universal, dummy_whitespace, dummy_refactor, dummy_errors

    return _build


def _write_file(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_edit_function_auto_indent_and_cleanup(editor_factory, tmp_path):
    editor, universal, whitespace, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "def foo():\n    return 1\n")

    result = editor.edit_function(str(file_path), "foo", "return 2")

    assert result.success is True
    assert universal.edit_calls
    assert whitespace.cleaned_contents


def test_edit_function_language_detection_failure(editor_factory, tmp_path):
    editor, universal, *_ = editor_factory()
    universal.detect_language_return = None
    file_path = _write_file(tmp_path / "foo.py", "print('x')\n")

    result = editor.edit_function(str(file_path), "foo", "pass")
    assert result.success is False
    assert "Cannot detect language" in result.message


def test_edit_function_appends_suggestion(editor_factory, tmp_path, monkeypatch):
    editor, universal, *_ = editor_factory()
    universal.edit_result = EditResult(success=False, message="Function not found")
    monkeypatch.setattr(
        ultimate_editor.UltimateEditor,
        "_get_available_symbols",
        lambda self, *_args, **_kwargs: ["foo_alt"],
    )
    file_path = _write_file(tmp_path / "foo.py", "pass\n")

    result = editor.edit_function(str(file_path), "missing", "return 1")
    assert "foo_alt" in result.message


def test_rename_symbol_runs_whitespace_cleanup(editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "def foo():\n    pass\n")

    result = editor.rename_symbol(str(file_path), "foo", "bar")

    assert result.success is True
    assert whitespace.cleaned_contents


def test_replace_code_range_success(editor_factory, tmp_path):
    editor, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "line1\nline2\nline3\n")

    result = editor.replace_code_range(str(file_path), 2, 2, "replacement")

    assert result.success
    assert "Replaced lines 2-2" in result.message
    assert "replacement" in file_path.read_text(encoding="utf-8")


def test_replace_code_range_invalid(editor_factory, tmp_path):
    editor, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "only\none\n")

    result = editor.replace_code_range(str(file_path), 5, 1, "x")
    assert result.success is False
    assert "Invalid line range" in result.message


def test_replace_code_range_syntax_error(editor_factory, tmp_path):
    editor, universal, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "line1\nline2\n")
    universal.detect_language_return = "python"

    result = editor.replace_code_range(str(file_path), 1, 1, "INVALID")
    assert result.success is False
    assert "Syntax error" in result.message


def test_begin_and_commit_refactoring_with_dry_run(editor_factory):
    config = ultimate_editor.EditorConfig(dry_run_first=True)
    editor, _, _, refactor, _ = editor_factory(config=config)

    txn = editor.begin_refactoring()
    result = editor.commit_refactoring(txn)

    assert result.success
    assert refactor.commits
    assert txn in refactor.cleaned


def test_commit_refactoring_stops_on_failed_dry_run(editor_factory):
    config = ultimate_editor.EditorConfig(dry_run_first=True)
    editor, _, _, refactor, _ = editor_factory(config=config)
    refactor.dry_run_result = RefactorResult(False, "dry fail", 0, "txn")

    txn = editor.begin_refactoring()
    result = editor.commit_refactoring(txn)

    assert result.success is False
    assert not refactor.commits


def test_rollback_refactoring_cleans_transaction(editor_factory):
    editor, _, _, refactor, _ = editor_factory()
    txn = editor.begin_refactoring()

    result = editor.rollback_refactoring(txn)

    assert result.success
    assert txn in refactor.rollback_calls
    assert txn in refactor.cleaned


def test_get_available_symbols_extracts_entries(editor_factory):
    editor, universal, *_ = editor_factory()

    class DummyNode:
        def __init__(self, type_, children=None, start=0, end=3):
            self.type = type_
            self.children = children or []
            self.start = start
            self.end = end

    file_bytes = b"def foo(): pass\nclass Bar:\n    pass\n"
    func_start = file_bytes.index(b"foo")
    func_end = func_start + len("foo")
    class_start = file_bytes.index(b"Bar")
    class_end = class_start + len("Bar")

    root = DummyNode(
        "root",
        children=[
            DummyNode("function_definition", start=func_start, end=func_end),
            DummyNode("class_definition", start=class_start, end=class_end),
        ],
    )
    universal.parse_file_data = (SimpleNamespace(root_node=root), file_bytes, "python")

    symbols = editor._get_available_symbols("foo.py")
    assert set(symbols) == {"foo", "Bar"}


def test_normalize_file_indent_uses_whitespace_handler(editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    file_path = _write_file(tmp_path / "foo.py", "  line\n")

    result = editor.normalize_file_indent(str(file_path))

    assert result.success
    assert whitespace.normalized_input is not None
    assert file_path.read_text(encoding="utf-8") == "normalized"


def test_clear_caches_delegates(editor_factory):
    editor, universal, *_ = editor_factory()

    editor.clear_caches()

    assert universal.clear_cache_called


def test_edit_function_without_auto_indent(editor_factory, tmp_path):
    config = ultimate_editor.EditorConfig(auto_indent=False)
    editor, _, whitespace, *_ = editor_factory(config=config)
    file_path = _write_file(tmp_path / "bar.py", "print('x')\n")

    result = editor.edit_function(str(file_path), "foo", "body")

    assert result.success
    assert whitespace.cleaned_contents


def test_edit_function_auto_indent_failure(monkeypatch, editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    file_path = _write_file(tmp_path / "auto.py", "def foo():\n    pass\n")
    call_state = {"raised": False}
    real_open = builtins.open

    def fake_open(path, mode="r", *args, **kwargs):
        if not call_state["raised"] and mode == "r" and str(path).endswith("auto.py"):
            call_state["raised"] = True
            raise OSError("boom")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    result = editor.edit_function(str(file_path), "foo", "return 1")

    assert result.success
    assert whitespace.cleaned_contents


def test_edit_function_whitespace_cleanup_failure(editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    whitespace.raise_on_clean = True
    file_path = _write_file(tmp_path / "cleanup.py", "def foo():\n    pass\n")

    result = editor.edit_function(str(file_path), "foo", "return 1")

    assert result.success


def test_edit_function_symbol_suggestion_error(
    editor_factory, tmp_path, monkeypatch
):
    editor, universal, _, _, errors = editor_factory()
    universal.edit_result = EditResult(False, "function not found")
    errors.raise_symbol = True
    file_path = _write_file(tmp_path / "missing.py", "pass\n")

    result = editor.edit_function(str(file_path), "foo", "body")
    assert result.success is False


def test_rename_symbol_without_cleanup(editor_factory, tmp_path):
    config = ultimate_editor.EditorConfig(clean_whitespace=False)
    editor, _, whitespace, *_ = editor_factory(config=config)
    file_path = _write_file(tmp_path / "foo.py", "def foo():\n    pass\n")

    editor.rename_symbol(str(file_path), "foo", "bar")

    assert not whitespace.cleaned_contents


def test_rename_symbol_cleanup_failure(editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    whitespace.raise_on_clean = True
    file_path = _write_file(tmp_path / "foo.py", "def foo():\n    pass\n")

    editor.rename_symbol(str(file_path), "foo", "bar")


def test_find_symbol_missing_with_suggestion(editor_factory):
    editor, universal, *_ = editor_factory()
    universal.find_symbol_result = None

    result = editor.find_symbol("foo.py", "missing")
    assert result is None


def test_find_symbol_missing_without_suggestions(editor_factory, monkeypatch):
    editor, universal, *_ = editor_factory()
    universal.find_symbol_result = None
    monkeypatch.setattr(
        ultimate_editor.UltimateEditor,
        "_get_available_symbols",
        lambda self, *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("fail")),
    )

    result = editor.find_symbol("foo.py", "missing")
    assert result is None


def test_apply_auto_indent_disabled(editor_factory):
    config = ultimate_editor.EditorConfig(auto_indent=False)
    editor, *_ = editor_factory(config=config)

    assert editor._apply_auto_indent("code", ["line\n"], 1, "file") == "code"


def test_apply_auto_indent_out_of_range(editor_factory):
    editor, *_ = editor_factory()
    lines = ["one\n"]

    result = editor._apply_auto_indent("new", lines, 5, "file")
    assert result == "new"


def test_validate_syntax_after_edit_disabled(editor_factory):
    config = ultimate_editor.EditorConfig(validate_syntax=False)
    editor, *_ = editor_factory(config=config)

    ok, _ = editor._validate_syntax_after_edit("code", ["x"], "file")
    assert ok is True


def test_write_and_clean_file_without_clean(editor_factory, tmp_path):
    config = ultimate_editor.EditorConfig(clean_whitespace=False)
    editor, _, whitespace, *_ = editor_factory(config=config)
    target = tmp_path / "file.py"

    editor._write_and_clean_file(str(target), "text")

    assert target.read_text(encoding="utf-8") == "text"
    assert not whitespace.cleaned_contents


def test_replace_code_range_exception(editor_factory, tmp_path):
    editor, *_ = editor_factory()
    # remove file to trigger exception path
    missing = tmp_path / "missing.py"

    result = editor.replace_code_range(str(missing), 1, 1, "code")
    assert result.success is False


def test_commit_refactoring_handles_commit_failure(editor_factory):
    editor, _, _, refactor, _ = editor_factory()
    txn = editor.begin_refactoring()
    refactor.commit_result = RefactorResult(False, "fail", 0, txn.transaction_id)

    result = editor.commit_refactoring(txn)
    assert result.success is False
    assert txn not in refactor.cleaned


def test_get_available_symbols_handles_failure(editor_factory):
    editor, universal, *_ = editor_factory()

    def raising(_file):
        raise RuntimeError("parse")

    universal.parse_file = raising  # type: ignore[assignment]
    symbols = editor._get_available_symbols("foo.py")
    assert symbols == []


def test_get_supported_languages_proxy(editor_factory):
    editor, universal, *_ = editor_factory()
    assert editor.get_supported_languages() == universal.supported


def test_normalize_file_indent_with_target(editor_factory, tmp_path):
    editor, _, whitespace, *_ = editor_factory()
    file_path = _write_file(tmp_path / "indent.py", "line\n")

    result = editor.normalize_file_indent(str(file_path), target_style="tabs", target_size=2)

    assert result.success
    assert whitespace.normalized_input is not None


def test_normalize_file_indent_failure(editor_factory, tmp_path):
    editor, *_ = editor_factory()
    missing = tmp_path / "nope.py"

    result = editor.normalize_file_indent(str(missing))
    assert result.success is False

