from openhands.metasop.failure_taxonomy import classify_failure


def test_json_parse_detection() -> None:
    ftype, _meta = classify_failure("s1", "qa", validation_err="JSON parse/repair failed: unexpected token")
    assert ftype == "json_parse"


def test_schema_validation_detection() -> None:
    ftype, _meta = classify_failure("s1", "pm", validation_err="Schema validation failed: missing required property")
    assert ftype == "schema_validation"


def test_qa_test_fail_detection_from_stdout() -> None:
    out = "... FAILED test_example (tests/test_x.py)\nAssertionError: expected 2 but got 3"
    ftype, _meta = classify_failure("s1", "qa", stdout=out, stderr="")
    assert ftype == "qa_test_fail"


def test_build_error_detection() -> None:
    err = 'Traceback (most recent call last):\n  ModuleNotFoundError: No module named "foo"'
    ftype, _meta = classify_failure("s1", "engineer", stderr=err)
    assert ftype == "build_error"


def test_runtime_error_detection() -> None:
    err = 'Traceback (most recent call last):\n  File "x.py", line 10, in <module>\nTypeError: unsupported operand type(s)'
    ftype, _meta = classify_failure("s1", "engineer", stderr=err)
    assert ftype == "runtime_error"


def test_dependency_detection() -> None:
    err = "Could not resolve: version conflict on package xyz"
    ftype, _meta = classify_failure("s1", "engineer", stderr=err)
    assert ftype == "dependency_error"


def test_retries_exhausted_flag() -> None:
    ftype, _meta = classify_failure("s1", "engineer", retries_exhausted=True)
    assert ftype == "retries_exhausted"
