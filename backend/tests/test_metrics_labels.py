"""Tests for metric label normalization utilities."""

from __future__ import annotations

from backend.utils.metrics_labels import sanitize_operation_label


def test_sanitize_basic_symbols_and_spaces() -> None:
    """Ensure punctuation and spaces are normalized to underscore-separated label."""
    inp = "My Op/Name 123!"
    out = sanitize_operation_label(inp)
    assert out == "My_Op_Name_123"


def test_sanitize_leading_digits_prefix() -> None:
    """Verify labels starting with digits gain the `op_` prefix."""
    inp = "123start"
    out = sanitize_operation_label(inp)
    assert out.startswith("op_")
    assert out == "op_123start"


def test_sanitize_none_and_empty() -> None:
    """Handle missing or empty input by returning the fallback label."""
    assert sanitize_operation_label(None) == "unknown"
    assert sanitize_operation_label("") == "unknown"


def test_sanitize_collapse_and_trim() -> None:
    """Collapse repeated separators and enforce optional max length."""
    inp = "a__b--c"
    out = sanitize_operation_label(inp)
    assert out == "a_b_c"
    long_inp = "x" * 150
    out2 = sanitize_operation_label(long_inp, max_length=50)
    assert len(out2) <= 50
