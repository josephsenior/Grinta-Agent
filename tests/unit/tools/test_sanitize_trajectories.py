from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from forge.tools import sanitize_trajectories as st


def test_find_candidate_files_filters_json(tmp_path: Path) -> None:
    json_path = tmp_path / "data.json"
    json_path.write_text("{}", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    jsonl_path = sub / "data.jsonl"
    jsonl_path.write_text("{}", encoding="utf-8")
    (tmp_path / "ignore.txt").write_text("", encoding="utf-8")

    candidates = st.find_candidate_files(tmp_path)
    assert sorted(candidates) == sorted([json_path, jsonl_path])
    assert st.find_candidate_files(tmp_path / "missing") == []


def test_sanitize_json_content_cleans_nested_structures() -> None:
    data = {
        "trajectory": [
            {"observation": "null"},
            {"details": {"action": "null"}},
            "null",
            {"details": {"value": 1}},
        ],
        "meta": "keep",
    }
    cleaned = st.sanitize_json_content(data)
    assert cleaned["meta"] == "keep"
    assert cleaned["trajectory"] == [{}, {"details": {"value": 1}}]


def test_helpers_for_special_cases() -> None:
    assert st._should_drop_cleaned_value(None, "x", "observation") is True
    assert st._should_drop_cleaned_value(None, [], "anything") is True
    assert st._should_drop_cleaned_value("value", "value", "key") is False
    assert st._sanitize_primitive("null") is None
    assert st._sanitize_primitive("value") == "value"


def test_process_jsonl_content_detects_changes() -> None:
    raw = "\n".join(
        [
            json.dumps({"observation": "null"}),
            json.dumps({"value": 1}),
        ],
    )
    parsed, sanitized, changed = st._process_jsonl_content(raw)
    assert len(parsed) == 2
    assert sanitized == [{"value": 1}]
    assert changed is True


def test_process_trajectory_data_and_write_helpers(tmp_path: Path) -> None:
    payload = {"trajectory": [{"observation": "null"}], "meta": "info"}
    updated, changed = st._process_trajectory_data(payload)
    assert updated["trajectory"] == []
    assert changed is True

    jsonl_target = tmp_path / "out.jsonl"
    st._write_jsonl_file(jsonl_target, [{"a": 1}])
    assert jsonl_target.read_text(encoding="utf-8").strip() == '{"a": 1}'

    json_target = tmp_path / "out.json"
    st._write_json_file(json_target, None)
    assert json_target.read_text(encoding="utf-8").strip() == "{}"


def test_process_jsonl_and_json_files(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "data.jsonl"
    jsonl_raw = "\n".join(
        [
            json.dumps({"observation": "null"}),
            json.dumps({"value": 2}),
        ],
    )
    jsonl_path.write_text(jsonl_raw, encoding="utf-8")
    assert st._process_jsonl_file(jsonl_raw, str(jsonl_path), apply=True) is True
    assert jsonl_path.read_text(encoding="utf-8").strip() == '{"value": 2}'

    json_path = tmp_path / "data.json"
    json_payload = {"observation": "null", "keep": "value"}
    json_path.write_text(json.dumps(json_payload), encoding="utf-8")
    assert st._process_json_file(json_path.read_text(encoding="utf-8"), str(json_path), apply=True) is True
    assert json.loads(json_path.read_text(encoding="utf-8")) == {}


def test_process_file_router_and_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    json_path = tmp_path / "doc.json"
    json_path.write_text(json.dumps({"observation": "null"}), encoding="utf-8")
    jsonl_path = tmp_path / "doc.jsonl"
    jsonl_path.write_text(json.dumps({"observation": "null"}), encoding="utf-8")

    assert st.process_file(str(json_path), apply=True) is True
    assert st.process_file(str(jsonl_path), apply=True) is True

    broken = tmp_path / "broken.json"
    broken.write_text("not-json", encoding="utf-8")
    assert st.process_file(str(broken), apply=True) is False

    monkeypatch.setattr(st, "_read_file_content", lambda path: None)
    assert st.process_file("missing.json") is False

    monkeypatch.setattr(st, "_read_file_content", lambda path: "{}")
    monkeypatch.setattr(st, "_is_jsonl_file", lambda path: False)
    monkeypatch.setattr(st, "_process_json_file", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    assert st.process_file("error.json") is False


def test_private_utilities_behave_as_expected(tmp_path: Path) -> None:
    with patch("builtins.open", side_effect=OSError):
        assert st._read_file_content("missing.json") is None
    assert st._is_jsonl_file("foo.JSONL") is True
    assert st._is_jsonl_file("foo.json") is False

    file_a = str(tmp_path / "a.json")
    file_b = str(tmp_path / "b.json")
    with patch.object(st, "process_file", side_effect=[True, False]):
        changed = st._process_files([file_a, file_b], apply=False)
    assert changed == [os.path.relpath(file_a)]

    st._print_summary(["a", "b"], ["a"])
    st._print_summary(["a"], [])


def test_main_and_argument_parsing(tmp_path: Path) -> None:
    args = st._parse_arguments(["--paths", "foo", "bar", "--apply"])
    assert args.paths == ["foo", "bar"]
    assert args.apply is True

    with patch.object(st, "find_candidate_files", return_value=[]):
        assert st.main(["--paths", "foo"]) == 0

    dummy = str(tmp_path / "file.json")
    with (
        patch.object(st, "find_candidate_files", return_value=[dummy]) as finder,
        patch.object(st, "_process_files", return_value=[dummy]) as processor,
        patch.object(st, "_print_summary") as printer,
    ):
        rc = st.main(["--paths", str(tmp_path), "--apply"])

    assert rc == 0
    finder.assert_called_once()
    processor.assert_called_once_with([dummy], True)
    printer.assert_called_once_with([dummy], [dummy])
