"""Additional coverage for the Forge CLI GUI launcher module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.cli import gui_launcher


@pytest.fixture
def captured_output(monkeypatch):
    """Capture formatted text output."""
    messages: list = []
    monkeypatch.setattr(
        gui_launcher,
        "print_formatted_text",
        lambda message="": messages.append(message),
    )
    return messages


def test_format_docker_command_for_logging():
    """Docker commands should be wrapped for HTML logging."""
    formatted = gui_launcher._format_docker_command_for_logging(
        ["docker", "pull", "image"]
    )
    assert formatted == "<grey>Running Docker command: docker pull image</grey>"


def test_check_docker_requirements_missing_binary(monkeypatch, captured_output):
    """check_docker_requirements should return False when docker is unavailable."""
    monkeypatch.setattr(gui_launcher.shutil, "which", lambda _: None)
    assert gui_launcher.check_docker_requirements() is False
    assert any("Docker is not installed" in str(msg) for msg in captured_output)


def test_check_docker_requirements_daemon_not_running(monkeypatch, captured_output):
    """Return False when docker info indicates the daemon is stopped."""
    monkeypatch.setattr(gui_launcher.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(
        gui_launcher.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    assert gui_launcher.check_docker_requirements() is False
    assert any("Docker daemon is not running" in str(msg) for msg in captured_output)


def test_check_docker_requirements_timeout(monkeypatch, captured_output):
    """Timeout or subprocess errors should be surfaced as failures."""
    monkeypatch.setattr(gui_launcher.shutil, "which", lambda _: "docker")

    def raise_timeout(*_, **__):
        raise subprocess.TimeoutExpired(cmd="docker info", timeout=5)

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_timeout)
    assert gui_launcher.check_docker_requirements() is False
    assert any("Failed to check Docker status" in str(msg) for msg in captured_output)


def test_check_docker_requirements_success(monkeypatch):
    """Successful docker availability check should return True."""
    monkeypatch.setattr(gui_launcher.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(
        gui_launcher.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    assert gui_launcher.check_docker_requirements() is True


def test_ensure_config_dir_exists(monkeypatch, tmp_path):
    """The configuration directory should be created relative to the user's home."""
    monkeypatch.setattr(gui_launcher.Path, "home", lambda: tmp_path)
    config_dir = gui_launcher.ensure_config_dir_exists()
    assert config_dir == tmp_path / ".Forge"
    assert config_dir.exists()


def test_pull_runtime_image_success(monkeypatch, captured_output):
    """_pull_runtime_image should invoke docker pull and succeed."""
    recorded: dict[str, list[str]] = {}
    monkeypatch.setattr(
        gui_launcher.subprocess,
        "run",
        lambda cmd, **kwargs: recorded.setdefault("cmd", cmd),
    )
    gui_launcher._pull_runtime_image("runtime:image")
    assert recorded["cmd"] == ["docker", "pull", "runtime:image"]
    assert any("Pulling required Docker images" in str(msg) for msg in captured_output)


def test_pull_runtime_image_failure(monkeypatch):
    """Failures during docker pull should exit with error."""

    def raise_error(*_, **__):
        raise subprocess.CalledProcessError(returncode=1, cmd="docker pull")

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_error)
    with pytest.raises(SystemExit) as exc:
        gui_launcher._pull_runtime_image("runtime:image")
    assert exc.value.code == 1


def test_pull_runtime_image_timeout(monkeypatch):
    """Timeouts during docker pull should exit with error."""

    def raise_timeout(*_, **__):
        raise subprocess.TimeoutExpired(cmd="docker pull", timeout=10)

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_timeout)
    with pytest.raises(SystemExit) as exc:
        gui_launcher._pull_runtime_image("runtime:image")
    assert exc.value.code == 1


def test_configure_gpu_support():
    """GPU support should inject flags and environment variables."""
    cmd = ["docker", "run", "-it"]
    gui_launcher._configure_gpu_support(cmd)
    assert "--gpus" in cmd
    assert "SANDBOX_ENABLE_GPU=true" in cmd


def test_configure_cwd_mount_posix(monkeypatch, tmp_path, captured_output):
    """CWD mounting should append sandbox volume and user id when not on Windows."""
    monkeypatch.setattr(gui_launcher.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(gui_launcher.os, "name", "posix")
    monkeypatch.setattr(
        gui_launcher.subprocess, "check_output", lambda *args, **kwargs: "1000\n"
    )

    cmd: list[str] = []
    gui_launcher._configure_cwd_mount(cmd)
    assert "-e" in cmd
    assert f"SANDBOX_VOLUMES={tmp_path}:/workspace:rw" in cmd
    assert f"SANDBOX_USER_ID=1000" in cmd
    assert any("Mounting current directory" in str(msg) for msg in captured_output)


def test_run_docker_container_success(monkeypatch):
    """Successful docker run should simply execute the command."""
    recorded: dict[str, list[str]] = {}
    monkeypatch.setattr(
        gui_launcher.subprocess,
        "run",
        lambda cmd, **kwargs: recorded.setdefault("cmd", cmd),
    )
    gui_launcher._run_docker_container(["docker", "run"])
    assert recorded["cmd"] == ["docker", "run"]


def test_run_docker_container_failure(monkeypatch):
    """Failures during docker run should exit with code 1."""

    def raise_error(*_, **__):
        raise subprocess.CalledProcessError(returncode=1, cmd="docker run")

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_error)
    with pytest.raises(SystemExit) as exc:
        gui_launcher._run_docker_container(["docker", "run"])
    assert exc.value.code == 1


def test_run_docker_container_keyboard_interrupt(monkeypatch):
    """KeyboardInterrupt should exit gracefully with code 0."""

    def raise_interrupt(*_, **__):
        raise KeyboardInterrupt

    monkeypatch.setattr(gui_launcher.subprocess, "run", raise_interrupt)
    with pytest.raises(SystemExit) as exc:
        gui_launcher._run_docker_container(["docker", "run"])
    assert exc.value.code == 0


def test_launch_gui_server_success(monkeypatch, tmp_path, captured_output):
    """launch_gui_server should orchestrate docker setup when requirements pass."""
    monkeypatch.setattr(gui_launcher, "check_docker_requirements", lambda: True)
    monkeypatch.setattr(gui_launcher, "ensure_config_dir_exists", lambda: tmp_path)

    called: dict[str, str | list[str] | None] = {"runtime": None, "docker": None}

    monkeypatch.setattr(
        gui_launcher,
        "_pull_runtime_image",
        lambda image: called.__setitem__("runtime", image),
    )
    monkeypatch.setattr(
        gui_launcher,
        "_configure_gpu_support",
        lambda cmd: called.__setitem__("gpu", list(cmd)),
    )
    monkeypatch.setattr(
        gui_launcher,
        "_configure_cwd_mount",
        lambda cmd: called.__setitem__("mount", list(cmd)),
    )
    monkeypatch.setattr(
        gui_launcher,
        "_run_docker_container",
        lambda cmd: called.__setitem__("docker", list(cmd)),
    )
    monkeypatch.setattr(gui_launcher, "__version__", "1.2.3")

    gui_launcher.launch_gui_server(mount_cwd=True, gpu=True)

    assert (
        called["runtime"] == "docker.all-hands.dev/all-hands-ai/runtime:1.2.3-nikolaik"
    )
    assert called["docker"][0:2] == ["docker", "run"]
    assert any("Launching Forge GUI server" in str(msg) for msg in captured_output)


def test_launch_gui_server_requires_docker(monkeypatch):
    """If docker requirements fail, launch_gui_server should exit with code 1."""
    monkeypatch.setattr(gui_launcher, "check_docker_requirements", lambda: False)
    with pytest.raises(SystemExit) as exc:
        gui_launcher.launch_gui_server()
    assert exc.value.code == 1
