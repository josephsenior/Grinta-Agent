"""Unit tests for `forge.tools.sanitize_trajectories` utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from forge.tools import sanitize_trajectories as st


def test_find_candidate_files_filters_json(tmp_path: Path) -> None:
    """Only JSON/JSONL files under the tree should be returned."""
    json_path = tmp_path / "data.json"
    json_path.write_text("{}", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    jsonl_path = tmp_path / "sub" / "data.jsonl"
    jsonl_path.write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("noop", encoding="utf-8")

    candidates = st.find_candidate_files(tmp_path)

    assert sorted(candidates) == sorted([json_path, jsonl_path])
    assert st.find_candidate_files(tmp_path / "missing") == []


def test_sanitize_json_content_removes_null_events() -> None:
    """Events containing `observation` or `action` null markers should be dropped."""
    event = {"observation": "null", "foo": "bar"}
    assert st.sanitize_json_content(event) is None


def test_sanitize_json_content_cleans_nested_structures() -> None:
    """Nested lists/dicts should have their null elements removed."""
    data = {
        "trajectory": [
            {"action": "null"},
            {"details": {"observation": "null"}},
            "null",
            {"details": {"value": 1}},
        ],
        "note": "keep",
    }

    cleaned = st.sanitize_json_content(data)

    assert cleaned["note"] == "keep"
    assert cleaned["trajectory"] == [{}, {"details": {"value": 1}}]


def test_should_drop_cleaned_value_on_special_keys() -> None:
    """Special keys like observation/action should be removed when sanitized to None."""
    assert st._should_drop_cleaned_value(None, "original", "observation") is True
    assert st._should_drop_cleaned_value(None, [], "anything") is True
    assert st._should_drop_cleaned_value("value", "value", "key") is False


def test_sanitize_primitive_drops_null_string() -> None:
    """The literal string 'null' is treated as an empty value."""
    assert st._sanitize_primitive("null") is None
    assert st._sanitize_primitive("value") == "value"


def test_process_jsonl_content_detects_changes() -> None:
    """JSONL processing should drop null events and flag modifications."""
    raw = "\n".join(
        [
            json.dumps({"observation": "null"}),
            json.dumps({"value": 1}),
        ]
    )
    parsed, sanitized, changed = st._process_jsonl_content(raw)

    assert len(parsed) == 2
    assert sanitized == [{"value": 1}]
    assert changed is True


def test_process_trajectory_data_rebuilds_list() -> None:
    """Trajectory lists should be sanitized, replacing null entries with [] if required."""
    payload = {"trajectory": [{"observation": "null"}], "meta": "info"}

    updated, changed = st._process_trajectory_data(payload)

    assert updated["trajectory"] == []
    assert changed is True


def test_write_jsonl_file(tmp_path: Path) -> None:
    """Writing JSONL should render one object per line."""
    target = tmp_path / "file.jsonl"
    st._write_jsonl_file(target, [{"a": 1}, {"b": 2}])

    content = target.read_text(encoding="utf-8").splitlines()
    assert content == ['{"a": 1}', '{"b": 2}']


def test_write_json_file_handles_none(tmp_path: Path) -> None:
    """Writing JSON with None should emit an empty object."""
    target = tmp_path / "file.json"
    st._write_json_file(target, None)
    assert target.read_text(encoding="utf-8").strip() == "{}"


def test_process_jsonl_file_applies_changes(tmp_path: Path) -> None:
    """When changes are detected they should be written when apply=True."""
    raw = "\n".join(
        [
            json.dumps({"observation": "null"}),
            json.dumps({"value": 1}),
        ]
    )
    target = tmp_path / "data.jsonl"
    target.write_text(raw, encoding="utf-8")

    changed = st._process_jsonl_file(raw, str(target), apply=True)

    assert changed is True
    assert target.read_text(encoding="utf-8").strip() == '{"value": 1}'


def test_process_json_file_handles_trajectory(tmp_path: Path) -> None:
    """Trajectory-containing JSON files should be sanitized and rewritten."""
    payload = {"trajectory": [{"observation": "null"}, {"value": 2}]}
    target = tmp_path / "data.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    changed = st._process_json_file(target.read_text(encoding="utf-8"), str(target), apply=True)

    assert changed is True
    rewritten = json.loads(target.read_text(encoding="utf-8"))
    assert rewritten["trajectory"] == [{"value": 2}]


def test_process_json_file_regular_dict(tmp_path: Path) -> None:
    """Regular JSON documents should drop null-valued fields."""
    payload = {"observation": "null", "keep": "value"}
    target = tmp_path / "regular.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    changed = st._process_json_file(target.read_text(encoding="utf-8"), str(target), apply=True)

    assert changed is True
    # Sanitizing removes the offending field entirely, resulting in an empty object.
    assert json.loads(target.read_text(encoding="utf-8")) == {}


def test_process_file_router_handles_json_and_jsonl(tmp_path: Path) -> None:
    """process_file should delegate to JSON/JSONL helpers and report changes."""
    json_path = tmp_path / "doc.json"
    json_path.write_text(json.dumps({"observation": "null"}), encoding="utf-8")
    jsonl_path = tmp_path / "doc.jsonl"
    jsonl_path.write_text(json.dumps({"observation": "null"}), encoding="utf-8")

    assert st.process_file(str(json_path), apply=True) is True
    assert st.process_file(str(jsonl_path), apply=True) is True


def test_process_file_handles_invalid_json(tmp_path: Path) -> None:
    """Invalid JSON should be ignored gracefully."""
    target = tmp_path / "broken.json"
    target.write_text("not-json", encoding="utf-8")

    assert st.process_file(str(target), apply=True) is False


def test_process_file_handles_missing_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """If reading fails, process_file should short-circuit with False."""
    monkeypatch.setattr(st, "_read_file_content", lambda path: None)
    assert st.process_file("ignored.json") is False


def test_process_file_handles_generic_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected errors inside processors should be swallowed."""
    monkeypatch.setattr(st, "_read_file_content", lambda path: "{}")
    monkeypatch.setattr(st, "_is_jsonl_file", lambda path: False)

    def _boom(*_args, **_kwargs) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(st, "_process_json_file", _boom)

    assert st.process_file("data.json") is False


def test_read_file_content_guarded() -> None:
    """File read errors should return None without raising."""
    with patch("builtins.open", side_effect=OSError):
        assert st._read_file_content("missing.json") is None


def test_is_jsonl_file() -> None:
    """File suffix detection should be case-insensitive."""
    assert st._is_jsonl_file("foo.JSONL") is True
    assert st._is_jsonl_file("foo.json") is False


def test_process_files_collects_changed(tmp_path: Path) -> None:
    """_process_files should accumulate relative paths for changed files."""
    file_a = str(tmp_path / "a.json")
    file_b = str(tmp_path / "b.json")
    with patch.object(st, "process_file", side_effect=[True, False]):
        changed = st._process_files([file_a, file_b], apply=False)

    assert changed == [os.path.relpath(file_a)]


def test_print_summary_handles_changed_and_empty() -> None:
    """_print_summary should iterate over changed files without error."""
    st._print_summary(["a", "b"], ["a"])
    st._print_summary(["a"], [])


def test_parse_arguments_and_main_no_files() -> None:
    """Argument parsing should wire into main's control flow."""
    args = st._parse_arguments(["--paths", "foo", "bar", "--apply"])
    assert args.paths == ["foo", "bar"]
    assert args.apply is True

    with patch.object(st, "find_candidate_files", return_value=[]):
        assert st.main(["--paths", "foo"]) == 0


def test_main_processes_files(tmp_path: Path) -> None:
    """main should process files and forward apply flag."""
    dummy_file = str(tmp_path / "file.json")
    with patch.object(st, "find_candidate_files", return_value=[dummy_file]) as finder, patch.object(
        st, "_process_files", return_value=[dummy_file]
    ) as processor, patch.object(st, "_print_summary") as printer:
        rc = st.main(["--paths", str(tmp_path), "--apply"])

    assert rc == 0
    finder.assert_called_once()
    processor.assert_called_once_with([dummy_file], True)
    printer.assert_called_once_with([dummy_file], [dummy_file])


def test_module_entry_point_main_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Running the module as a script should exit cleanly."""
    import argparse
    import runpy

    def fake_parse_args(self, argv):
        return argparse.Namespace(paths=tmp_path, apply=False, dry_run=False)

    monkeypatch.setattr("argparse.ArgumentParser.parse_args", fake_parse_args, raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("forge.tools.sanitize_trajectories", run_name="__main__")

    assert exc.value.code == 0


