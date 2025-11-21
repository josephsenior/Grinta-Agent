import json
from forge.core.io import format_json, print_json_stdout


def test_print_json_stdout_happy_path(capsys):
    obj = {"a": 1, "b": "x"}
    formatted = format_json(obj, pretty=False)
    parsed = json.loads(formatted)
    assert parsed == obj
    print_json_stdout(obj, pretty=False)
    captured = capsys.readouterr()
    assert captured.out.strip() == formatted


class NonSerializable:
    def __repr__(self):
        return "<NS>"


def test_print_json_stdout_non_serializable(capsys):
    obj = {"ok": NonSerializable()}
    formatted = format_json(obj, pretty=False)
    try:
        parsed = json.loads(formatted)
        assert parsed.get("ok") in ("<NS>",)
    except json.JSONDecodeError:
        assert "<NS>" in formatted
    print_json_stdout(obj, pretty=False)
    captured = capsys.readouterr()
    assert captured.out.strip() == formatted


def test_format_json_pretty():
    obj = {"outer": {"inner": [1, 2, {"k": "v"}]}}
    pretty = format_json(obj, pretty=True)
    assert "\n" in pretty
    assert '\n  "outer"' in pretty or pretty.strip().startswith('"outer"')
    assert '\n    "inner"' in pretty
    assert "\n      1" in pretty or "\n      1," in pretty
    assert '\n        "k"' in pretty
    parsed = json.loads(pretty)
    assert parsed == obj


def test_format_json_ensure_ascii(capsys):
    obj = {"greeting": "café"}
    escaped = format_json(obj, pretty=False, ensure_ascii=True)
    assert "\\u00e9" in escaped
    parsed = json.loads(escaped)
    assert parsed == obj
    preserved = format_json(obj, pretty=False, ensure_ascii=False)
    assert "café" in preserved
    parsed2 = json.loads(preserved)
    assert parsed2 == obj
    print_json_stdout(obj, pretty=False, ensure_ascii=True)
    captured = capsys.readouterr()
    assert captured.out.strip() == escaped
