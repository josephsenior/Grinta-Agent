import io

import pytest

from forge.core import io as core_io


def test_format_json_compact_and_pretty():
    data = {"name": "Forge", "count": 2}
    compact = core_io.format_json(data)
    assert compact == '{"name":"Forge","count":2}'
    pretty = core_io.format_json(data, pretty=True)
    assert "\n" in pretty and pretty.strip().startswith("{")


def test_format_json_ensure_ascii():
    data = {"symbol": "✔"}
    ascii_result = core_io.format_json(data, ensure_ascii=True)
    assert "\\u2714" in ascii_result
    unicode_result = core_io.format_json(data, ensure_ascii=False)
    assert "✔" in unicode_result


def test_format_json_error_returns_repr(monkeypatch):
    class Broken:
        def __repr__(self):
            return "<broken>"

    def failing_dumps(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(core_io.json, "dumps", failing_dumps)
    assert core_io.format_json(Broken()) == "<broken>"


def test_print_json_stdout_writes_and_flushes(monkeypatch):
    buffer = io.StringIO()
    monkeypatch.setattr(core_io.sys, "stdout", buffer)
    core_io.print_json_stdout({"v": 1})
    assert buffer.getvalue().strip() == '{"v":1}'


def test_print_json_stdout_handles_exceptions(monkeypatch):
    class FailingStdout:
        def write(self, *_args, **_kwargs):
            raise OSError("fail")

        def flush(self):
            raise OSError("fail")

    monkeypatch.setattr(core_io.sys, "stdout", FailingStdout())
    # Should not raise even though writing fails
    core_io.print_json_stdout({"v": 1})
