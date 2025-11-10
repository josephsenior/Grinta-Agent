import pytest

from forge.utils.metrics_labels import sanitize_operation_label


@pytest.mark.parametrize(
    "input_value,expected",
    [
        (None, "unknown"),
        ("", "unknown"),
        ("___", "unknown"),
        ("  spaces  ", "spaces"),
        ("name-with-dash", "name_with_dash"),
        ("multiple---underscores", "multiple_underscores"),
        ("123start", "op_123start"),
    ],
)
def test_sanitize_operation_label_various_inputs(input_value, expected):
    assert sanitize_operation_label(input_value) == expected


def test_sanitize_operation_label_max_length():
    value = "a" * 150
    assert sanitize_operation_label(value, max_length=10) == "a" * 10


def test_sanitize_operation_label_preserves_valid():
    assert sanitize_operation_label("valid_name") == "valid_name"

