"""Unit tests for `forge.io.io` helpers."""

from __future__ import annotations

import argparse
import builtins
from types import SimpleNamespace

import pytest

from forge.io import io


def test_read_input_single_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """read_input should strip trailing whitespace for single-line input."""
    monkeypatch.setattr(builtins, "input", lambda prompt="": "hello world  ")
    assert io.read_input() == "hello world"


def test_read_input_multiline_until_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """read_input should accumulate lines until the sentinel `/exit` is received."""
    inputs = iter(["first  ", "second", "/exit"])
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))
    assert io.read_input(cli_multiline_input=True) == "first\nsecond"


def test_read_task_prefers_file(tmp_path) -> None:
    """read_task should load the task from a provided --file argument."""
    task_file = tmp_path / "task.txt"
    task_file.write_text("from file", encoding="utf-8")
    args = argparse.Namespace(file=str(task_file), task=None)
    assert io.read_task(args, cli_multiline_input=False) == "from file"


def test_read_task_prefers_task_argument() -> None:
    """read_task should return the --task argument when provided."""
    args = argparse.Namespace(file=None, task="inline task")
    assert io.read_task(args, cli_multiline_input=False) == "inline task"


def test_read_task_falls_back_to_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no CLI arguments are provided, read_task should use stdin."""
    args = argparse.Namespace(file=None, task=None)
    monkeypatch.setattr(io, "read_input", lambda cli_multiline_input: "from stdin")
    monkeypatch.setattr(io.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert io.read_task(args, cli_multiline_input=True) == "from stdin"


def test_read_task_returns_empty_string_when_interactive(monkeypatch: pytest.MonkeyPatch) -> None:
    """If stdin is a TTY and no task arguments are provided, return an empty string."""
    args = argparse.Namespace(file=None, task=None)
    monkeypatch.setattr(io.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    assert io.read_task(args, cli_multiline_input=False) == ""


