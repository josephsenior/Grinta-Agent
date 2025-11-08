from __future__ import annotations

import json
from pathlib import Path

import pytest

from forge.tools import sanitize_trajectories as sanitize


def test_find_candidate_files_handles_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert sanitize.find_candidate_files(missing) == []


def test_find_candidate_files_returns_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    target = data_dir / "event.json"
    target.write_text("{}", encoding="utf-8")
    other = data_dir / "note.txt"
    other.write_text("", encoding="utf-8")
    result = sanitize.find_candidate_files(data_dir)
    assert target in result
    assert other not in result


def test_sanitize_json_content_drops_null_event() -> None:
    obj = {"action": "null", "other": "value"}
    assert sanitize.sanitize_json_content(obj) is None


def test_sanitize_list_removes_null_entries() -> None:
    payload = ["keep", "null", {"observation": "null"}, {"value": 1}]
    cleaned = sanitize.sanitize_json_content(payload)
    assert cleaned == ["keep", {"value": 1}]


def test_sanitize_dict_removes_nested_nulls() -> None:
    obj = {"inner": {"observation": "null"}, "value": "ok"}
    cleaned = sanitize.sanitize_json_content(obj)
    assert cleaned == {"value": "ok"}


def test_sanitize_dict_returns_same_object() -> None:
    obj = {"value": "ok"}
    cleaned = sanitize.sanitize_json_content(obj)
    assert cleaned is obj

def test_sanitize_primitive_null() -> None:
    assert sanitize.sanitize_json_content("null") is None


def test_process_jsonl_file(tmp_path: Path) -> None:
    payload = tmp_path / "events.jsonl"
    payload.write_text('{"observation": "null"}\n{"value": 1}\n', encoding="utf-8")
    assert sanitize.process_file(str(payload), apply=False) is True
    sanitize.process_file(str(payload), apply=True)
    processed = payload.read_text(encoding="utf-8").strip().splitlines()
    assert processed == ['{"value": 1}']


def test_process_json_file_with_trajectory(tmp_path: Path) -> None:
    payload = tmp_path / "trajectory.json"
    payload.write_text(json.dumps({"trajectory": [{"observation": "null"}, {"value": 1}]}), encoding="utf-8")
    assert sanitize.process_file(str(payload), apply=True) is True
    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data["trajectory"] == [{"value": 1}]


def test_process_json_file_regular(tmp_path: Path) -> None:
    payload = tmp_path / "event.json"
    payload.write_text(json.dumps({"observation": "null", "extra": "value"}), encoding="utf-8")
    assert sanitize.process_file(str(payload), apply=True) is True
    data = json.loads(payload.read_text(encoding="utf-8"))
    assert data == {}


def test_process_file_handles_invalid_json(tmp_path: Path) -> None:
    payload = tmp_path / "broken.json"
    payload.write_text("{not json", encoding="utf-8")
    assert sanitize.process_file(str(payload)) is False


def test_process_file_handles_generic_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanitize, "_read_file_content", lambda path: "{}")
    monkeypatch.setattr(sanitize, "_is_jsonl_file", lambda path: True)

    def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(sanitize, "_process_jsonl_file", boom)
    assert sanitize.process_file("file.jsonl") is False

def test_process_file_missing_contents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sanitize, "_read_file_content", lambda path: None)
    assert sanitize.process_file("missing.json") is False


def test_main_returns_zero_when_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sanitize, "_parse_arguments", lambda argv: sanitize.argparse.Namespace(paths=[tmp_path], apply=False, dry_run=False)
    )
    monkeypatch.setattr(sanitize, "find_candidate_files", lambda paths: [])
    assert sanitize.main([]) == 0


def test_process_files_collects_changed(tmp_path: Path) -> None:
    target = tmp_path / "event.json"
    target.write_text(json.dumps({"observation": "null"}), encoding="utf-8")
    changed = sanitize._process_files([str(target)], apply=False)
    assert len(changed) == 1
    assert changed[0].endswith("event.json")


def test_print_summary_handles_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    sanitize._print_summary(["a"], ["a"])


def test_print_summary_no_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: None)
    sanitize._print_summary(["a"], [])


def test_should_drop_cleaned_value_helpers() -> None:
    assert sanitize._should_drop_cleaned_value(None, {}, "key") is True
    assert sanitize._should_drop_cleaned_value("value", {}, "key") is False


def test_sanitize_list_returns_same_object() -> None:
    data = ["keep"]
    assert sanitize._sanitize_list(data) is data

