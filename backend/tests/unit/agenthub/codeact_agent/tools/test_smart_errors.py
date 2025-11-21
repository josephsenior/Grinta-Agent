from __future__ import annotations

from forge.agenthub.codeact_agent.tools.smart_errors import (
    ErrorSuggestion,
    SmartErrorHandler,
)


def test_symbol_not_found_handles_common_typo() -> None:
    suggestion = SmartErrorHandler.symbol_not_found("functino", [])
    assert isinstance(suggestion, ErrorSuggestion)
    assert suggestion.auto_fixable is True
    assert suggestion.fix_code == "function"


def test_symbol_not_found_uses_fuzzy_matching_auto_fix() -> None:
    suggestion = SmartErrorHandler.symbol_not_found("ProcessData", ["ProcessData"])
    assert suggestion.auto_fixable is True
    assert suggestion.fix_code == "ProcessData"


def test_symbol_not_found_lists_available_symbols_when_no_match() -> None:
    available = [f"symbol{i}" for i in range(12)]
    suggestion = SmartErrorHandler.symbol_not_found(
        "unknown", available, max_suggestions=5
    )
    assert "Available symbols" in suggestion.message
    assert len(suggestion.suggestions) == 5


def test_create_available_symbols_message_handles_empty() -> None:
    suggestion = SmartErrorHandler._create_available_symbols_message("missing", [], 5)
    assert "no symbols are available" in suggestion.message.lower()


def test_create_fuzzy_match_suggestion_mid_similarity() -> None:
    suggestion = SmartErrorHandler._create_fuzzy_match_suggestion(
        "abcdef", ["abcxef"]
    )
    assert suggestion.auto_fixable is False
    assert "Similar symbols" in suggestion.message


def test_syntax_error_combines_multiple_analyzers() -> None:
    suggestion = SmartErrorHandler.syntax_error(
        "Invalid syntax: unexpected indent and unterminated string",
        line_number=42,
        code_context='if x == 1\n    print("hello"\nvalues = [1, 2\n',
    )
    assert "Syntax Error" in suggestion.message
    assert suggestion.suggestions


def test_syntax_error_handles_undefined_symbol() -> None:
    suggestion = SmartErrorHandler.syntax_error("NameError: foo is not defined")
    assert any("Check for typos" in s for s in suggestion.suggestions)


def test_file_not_found_with_matches() -> None:
    suggestion = SmartErrorHandler.file_not_found(
        "src/main.py",
        similar_files=["src/main_old.py", "src/app.py", "docs/main.md"],
    )
    assert suggestion.suggestions
    if suggestion.auto_fixable:
        assert suggestion.fix_code == suggestion.suggestions[0]


def test_file_not_found_without_matches() -> None:
    suggestion = SmartErrorHandler.file_not_found("missing.txt")
    assert suggestion.message.startswith("File not found: missing.txt")
    assert suggestion.suggestions == []


def test_file_not_found_with_non_matching_similar_list() -> None:
    suggestion = SmartErrorHandler.file_not_found("main.py", ["docs/readme.md"])
    assert "No similar files found" in suggestion.message


def test_whitespace_mismatch_reports_different_indent_styles() -> None:
    suggestion = SmartErrorHandler.whitespace_mismatch("\t", "    ", 10)
    assert "Indentation mismatch" in suggestion.message
    assert suggestion.auto_fixable is True


def test_whitespace_mismatch_reports_same_style_counts() -> None:
    suggestion = SmartErrorHandler.whitespace_mismatch("    ", "  ", 15)
    assert "Expected: 4 spaces" in suggestion.message


def test_suggest_similar_returns_matches() -> None:
    matches = SmartErrorHandler.suggest_similar(
        "update_config", ["update_config", "upgrade_config", "reset"]
    )
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
    assert suggestion and "did not change" in suggestion.message


def test_validate_edit_result_detects_dramatic_shrink() -> None:
    original = "\n".join(f"line {i}" for i in range(150))
    new = "print('small')"
    suggestion = SmartErrorHandler.validate_edit_result(original, new)
    assert suggestion and "shrank dramatically" in suggestion.message


def test_validate_edit_result_ok_returns_none() -> None:
    assert (
        SmartErrorHandler.validate_edit_result("print('hi')", "print('hello')") is None
    )


def test_symbol_grouping_and_context_helpers() -> None:
    functions, classes = SmartErrorHandler._group_symbols_by_type(["Foo", "bar"])
    assert classes == ["Foo"]
    assert functions == ["bar"]
    context = SmartErrorHandler._build_symbol_context(classes, functions)
    message = SmartErrorHandler._build_symbol_list_message(
        "missing", ["Foo", "bar"], context
    )
    assert "classes" in context and "functions" in context
    assert "Available symbols" in message


def test_build_symbol_context_functions_only() -> None:
    context = SmartErrorHandler._build_symbol_context([], ["do_work"])
    assert "functions" in context and "classes" not in context


def test_build_symbol_context_classes_only() -> None:
    context = SmartErrorHandler._build_symbol_context(["Foo"], [])
    assert "classes" in context and "functions" not in context


def test_create_fuzzy_match_suggestion_low_similarity() -> None:
    suggestion = SmartErrorHandler._create_fuzzy_match_suggestion("abc", ["xyz"])
    assert "Possible matches" in suggestion.message
    assert suggestion.auto_fixable is False


def test_syntax_error_handles_eof_and_brackets() -> None:
    suggestion = SmartErrorHandler.syntax_error(
        "Unexpected EOF while parsing", code_context="data = [1, 2\n"
    )
    assert any("brackets" in s for s in suggestion.suggestions)


def test_syntax_error_invalid_context_helpers() -> None:
    suggestion = SmartErrorHandler.syntax_error(
        "invalid syntax",
        code_context="if x:\n    call(\n    data = [1, 2\n",
    )
    joined = " ".join(suggestion.suggestions)
    assert "colon" in joined
    assert "parentheses" in joined
    assert "brackets" in joined


def test_syntax_error_without_additional_context() -> None:
    suggestion = SmartErrorHandler.syntax_error("invalid syntax", code_context="pass")
    assert suggestion.suggestions  # generic fallback present


def test_missing_colon_and_paren_helpers() -> None:
    assert (
        SmartErrorHandler._check_missing_colon("if x:")
        == "Check for missing colons after if/for/def/class statements"
    )
    assert SmartErrorHandler._check_missing_colon("print('hi')") is None
    assert (
        SmartErrorHandler._check_unmatched_parentheses("print(")
        == "You might have unmatched parentheses"
    )
    assert SmartErrorHandler._check_unmatched_parentheses("print()") is None


def test_unmatched_bracket_helper() -> None:
    assert (
        SmartErrorHandler._check_unmatched_brackets("[1, 2")
        == "You might have unmatched brackets"
    )
    assert SmartErrorHandler._check_unmatched_brackets("[1, 2]") is None


def test_build_error_message_without_suggestions() -> None:
    message = SmartErrorHandler._build_error_message(
        "oops", line_number=None, code_context=None, suggestions=[]
    )
    assert "Syntax Error" in message


def test_file_not_found_exact_match_auto_fix() -> None:
    suggestion = SmartErrorHandler.file_not_found("main.py", ["main.py"])
    assert suggestion.auto_fixable is True
    assert suggestion.fix_code == "main.py"

