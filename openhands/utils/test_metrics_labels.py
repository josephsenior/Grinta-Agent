from openhands.utils.metrics_labels import sanitize_operation_label


def test_sanitize_basic_symbols_and_spaces() -> None:
    inp = "My Op/Name 123!"
    out = sanitize_operation_label(inp)
    assert out == "My_Op_Name_123"


def test_sanitize_leading_digits_prefix() -> None:
    inp = "123start"
    out = sanitize_operation_label(inp)
    assert out.startswith("op_")
    assert out == "op_123start"


def test_sanitize_none_and_empty() -> None:
    assert sanitize_operation_label(None) == "unknown"
    assert sanitize_operation_label("") == "unknown"


def test_sanitize_collapse_and_trim() -> None:
    inp = "a__b--c"
    out = sanitize_operation_label(inp)
    assert out == "a_b_c"
    long_inp = "x" * 150
    out2 = sanitize_operation_label(long_inp, max_length=50)
    assert len(out2) <= 50
