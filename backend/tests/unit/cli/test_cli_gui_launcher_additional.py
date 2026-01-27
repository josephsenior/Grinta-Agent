"""Additional coverage for the Forge CLI GUI launcher module."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.cli import gui_launcher


@pytest.fixture
def captured_output(monkeypatch):
    """Capture printed text output."""
    messages: list = []
    monkeypatch.setattr(
        "builtins.print",
        lambda *args, **kwargs: messages.append(" ".join(map(str, args))),
    )
    return messages


def test_ensure_config_dir_exists(monkeypatch, tmp_path):
    """The configuration directory should be created relative to the user's home."""
    monkeypatch.setattr(gui_launcher.Path, "home", lambda: tmp_path)
    config_dir = gui_launcher.ensure_config_dir_exists()
    assert config_dir == tmp_path / ".Forge"
    assert config_dir.exists()


def test_launch_gui_server_success(monkeypatch, captured_output):
    """launch_gui_server should invoke uvicorn and succeed."""
    recorded: dict[str, list[str]] = {}
    
    def mock_run(cmd, **kwargs):
        recorded["cmd"] = cmd
        recorded["env"] = kwargs.get("env", {})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(gui_launcher.subprocess, "run", mock_run)
    monkeypatch.setattr(gui_launcher, "ensure_config_dir_exists", lambda: Path("/tmp/.Forge"))
    
    gui_launcher.launch_gui_server()
    
    assert "uvicorn" in recorded["cmd"]
    assert "forge.server.listen:base_app" in recorded["cmd"]
    assert recorded["env"].get("FORGE_RUNTIME") == "local"
    assert recorded["env"].get("SERVE_FRONTEND") == "true"
    assert any("Starting local Forge server" in msg for msg in captured_output)


def test_launch_gui_server_failure(monkeypatch, captured_output):
    """Failures during server launch should exit with error."""

    def raise_error(*_, **__):
        raise subprocess.CalledProcessError(1, "uvicorn")

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_error)
    monkeypatch.setattr(gui_launcher, "ensure_config_dir_exists", lambda: Path("/tmp/.Forge"))
    
    with pytest.raises(SystemExit) as exc_info:
        gui_launcher.launch_gui_server()
    
    assert exc_info.value.code == 1
    assert any("Failed to start Forge GUI server" in msg for msg in captured_output)
