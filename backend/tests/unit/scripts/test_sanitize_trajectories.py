"""Unit tests for backend.scripts.sanitize_trajectories."""

from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.sanitize_trajectories import (
    _is_jsonl_file,
    _parse_arguments,
    _print_summary,
    _process_files,
    _read_file_content,
    _sanitize_primitive,
    find_candidate_files,
    main,
    process_file,
    sanitize_json_content,
)



def test_find_candidate_files_non_existent(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist"
    assert find_candidate_files(non_existent) == []


def test_find_candidate_files_filters_extensions(tmp_path: Path) -> None:
    d = tmp_path / "trajs"
    d.mkdir()
    f1 = d / "t1.json"
    f2 = d / "t2.jsonl"
    f3 = d / "t3.txt"
    f1.write_text("{}", encoding="utf-8")
    f2.write_text("{}", encoding="utf-8")
    f3.write_text("text", encoding="utf-8")

    found = find_candidate_files(d)
    filenames = {f.name for f in found}
    assert filenames == {"t1.json", "t2.jsonl"}


def test_sanitize_json_content_null_event() -> None:
    # Event with action: "null" should be dropped
    obj = {"action": "null", "details": "some info"}
    assert sanitize_json_content(obj) is None

    # Event with observation: "null" should be dropped
    obj2 = {"observation": "null"}
    assert sanitize_json_content(obj2) is None


def test_sanitize_json_content_list_filtering() -> None:
    data = [
        {"action": "click", "target": "btn"},
        {"action": "null"},
        {"observation": "null"},
        {"action": "type", "text": "hello"},
    ]
    sanitized = sanitize_json_content(data)
    assert isinstance(sanitized, list)
    assert len(sanitized) == 2
    assert sanitized[0]["action"] == "click"
    assert sanitized[1]["action"] == "type"


def test_sanitize_primitive() -> None:
    assert _sanitize_primitive("null") is None
    assert _sanitize_primitive("valid") == "valid"
    assert _sanitize_primitive(123) == 123


def test_read_file_content_missing() -> None:
    assert _read_file_content("/non/existent/path/file.json") is None


def test_process_file_jsonl(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "test.jsonl"
    jsonl_file.write_text(
        '{"action": "click"}\n{"action": "null"}\n{"action": "type"}\n',
        encoding="utf-8",
    )

    # Dry run
    changed = process_file(jsonl_file, apply=False)
    assert changed is True
    # Content unchanged on disk
    assert "null" in jsonl_file.read_text(encoding="utf-8")

    # Apply
    changed_apply = process_file(jsonl_file, apply=True)
    assert changed_apply is True
    new_text = jsonl_file.read_text(encoding="utf-8")
    assert "null" not in new_text


def test_process_file_json_trajectory_list(tmp_path: Path) -> None:
    json_file = tmp_path / "traj.json"
    data = {
        "id": "conv-1",
        "trajectory": [
            {"action": "step1"},
            {"action": "null"},
            {"action": "step2"},
        ],
    }
    json_file.write_text(json.dumps(data), encoding="utf-8")

    changed = process_file(json_file, apply=True)
    assert changed is True

    new_data = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(new_data["trajectory"]) == 2


def test_process_file_invalid_json(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")
    assert process_file(bad_file, apply=True) is False


def test_main_script_execution(tmp_path: Path, capsys) -> None:
    d = tmp_path / "trajs"
    d.mkdir()
    f1 = d / "sample.json"
    f1.write_text('{"action": "null"}', encoding="utf-8")

    exit_code = main(["--paths", str(d), "--apply"])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "Scanned 1 files; 1 were modified." in out
