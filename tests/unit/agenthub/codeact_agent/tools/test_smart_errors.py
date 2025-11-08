"""Tests for the smart error helper utilities used by CodeAct tools."""

from __future__ import annotations

from forge.agenthub.codeact_agent.tools.smart_errors import ErrorSuggestion, SmartErrorHandler


def test_symbol_not_found_handles_common_typo() -> None:
    suggestion = SmartErrorHandler.symbol_not_found("functino", [])
    assert isinstance(suggestion, ErrorSuggestion)
    assert suggestion.auto_fixable is True
    assert "Did you mean 'function'" in suggestion.message


def test_symbol_not_found_uses_fuzzy_matching() -> None:
    suggestion = SmartErrorHandler.symbol_not_found("functino", ["function", "functor"])
    assert suggestion.suggestions[0] == "function"
    assert suggestion.fix_code == "function"


def test_symbol_not_found_lists_available_symbols_when_no_match() -> None:
    available = [f"symbol{i}" for i in range(12)]
    suggestion = SmartErrorHandler.symbol_not_found("unknown", available, max_suggestions=5)
    assert "Available symbols" in suggestion.message
    assert len(suggestion.suggestions) == 5


def test_syntax_error_combines_multiple_analyzers() -> None:
    suggestion = SmartErrorHandler.syntax_error(
        "Invalid syntax: unexpected indent and unterminated string",
        line_number=42,
        code_context="if x == 1\n    print(\"hello\"\n"
    )
    text = suggestion.message
    # Ensure several analyzers contributed hints
    assert "Syntax Error" in text
    assert "Check your indentation" in text
    assert "unclosed string" in text or "Check for missing colons" in text
    assert suggestion.suggestions  # aggregated hints


def test_file_not_found_with_matches() -> None:
    suggestion = SmartErrorHandler.file_not_found(
        "src/main.py",
        similar_files=["src/main_old.py", "src/app.py", "docs/main.md"],
    )
    assert suggestion.suggestions  # close matches returned
    assert "Did you mean one of these" in suggestion.message


def test_file_not_found_without_matches() -> None:
    suggestion = SmartErrorHandler.file_not_found("missing.txt")
    assert "File not found: missing.txt" in suggestion.message
    assert suggestion.suggestions == []


def test_whitespace_mismatch_reports_different_indent_styles() -> None:
    suggestion = SmartErrorHandler.whitespace_mismatch("\t", "    ", 10)
    assert "Indentation mismatch" in suggestion.message
    assert suggestion.auto_fixable is True


def test_whitespace_mismatch_reports_same_style_counts() -> None:
    suggestion = SmartErrorHandler.whitespace_mismatch("    ", "  ", 15)
    assert "Indentation error" in suggestion.message
    assert "Expected: 4 spaces" in suggestion.message


def test_suggest_similar_returns_matches() -> None:
    matches = SmartErrorHandler.suggest_similar("update_config", ["update_config", "upgrade_config", "reset"])
    assert "update_config" in matches


def test_format_edit_conflict_includes_details() -> None:
    suggestion = SmartErrorHandler.format_edit_conflict(
        "src/app.py",
        "Rename function foo()",
        "Delete function foo()",
    )
    assert "Edit conflict in src/app.py" in suggestion.message
    assert len(suggestion.suggestions) == 3


def test_validate_edit_result_detects_no_change() -> None:
    suggestion = SmartErrorHandler.validate_edit_result("print('hi')", "print('hi')")
    assert suggestion and "did not change anything" in suggestion.message


def test_validate_edit_result_detects_dramatic_shrink() -> None:
    original = "\n".join(f"line {i}" for i in range(150))
    new = "print('small')"
    suggestion = SmartErrorHandler.validate_edit_result(original, new)
    assert suggestion and "File shrank dramatically" in suggestion.message

