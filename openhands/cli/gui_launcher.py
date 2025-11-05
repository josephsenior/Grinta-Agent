"""GUI launcher for OpenHands CLI."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from openhands import __version__


def _format_docker_command_for_logging(cmd: list[str]) -> str:
    """Format a Docker command for logging with grey color.

    Args:
        cmd (list[str]): The Docker command as a list of strings

    Returns:
        str: The formatted command string in grey HTML color
    """
    cmd_str = " ".join(cmd)
    return f"<grey>Running Docker command: {cmd_str}</grey>"


def check_docker_requirements() -> bool:
    """Check if Docker is installed and running.

    Returns:
        bool: True if Docker is available and running, False otherwise.
    """
    if not shutil.which("docker"):
        print_formatted_text(HTML("<ansired>❌ Docker is not installed or not in PATH.</ansired>"))
        print_formatted_text(HTML("<grey>Please install Docker first: https://docs.docker.com/get-docker/</grey>"))
        return False
    try:
        result = subprocess.run(["docker", "info"], check=False, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print_formatted_text(HTML("<ansired>❌ Docker daemon is not running.</ansired>"))
            print_formatted_text(HTML("<grey>Please start Docker and try again.</grey>"))
            return False
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        print_formatted_text(HTML("<ansired>❌ Failed to check Docker status.</ansired>"))
        print_formatted_text(HTML(f"<grey>Error: {e}</grey>"))
        return False
    return True


def ensure_config_dir_exists() -> Path:
    """Ensure the OpenHands configuration directory exists and return its path."""
    config_dir = Path.home() / ".openhands"
    config_dir.mkdir(exist_ok=True)
    return config_dir


def _pull_runtime_image(runtime_image: str) -> None:
    """Pull the Docker runtime image."""
    print_formatted_text(HTML("<grey>Pulling required Docker images...</grey>"))
    pull_cmd = ["docker", "pull", runtime_image]
    print_formatted_text(HTML(_format_docker_command_for_logging(pull_cmd)))
    try:
        subprocess.run(pull_cmd, check=True, timeout=300)
    except subprocess.CalledProcessError:
        print_formatted_text(HTML("<ansired>❌ Failed to pull runtime image.</ansired>"))
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print_formatted_text(HTML("<ansired>❌ Timeout while pulling runtime image.</ansired>"))
        sys.exit(1)


def _configure_gpu_support(docker_cmd: list[str]) -> None:
    """Configure GPU support for Docker command."""
    print_formatted_text(HTML("<ansigreen>🖥️ Enabling GPU support via nvidia-docker...</ansigreen>"))
    docker_cmd.insert(2, "--gpus")
    docker_cmd.insert(3, "all")
    docker_cmd.extend(["-e", "SANDBOX_ENABLE_GPU=true"])


def _configure_cwd_mount(docker_cmd: list[str]) -> None:
    """Configure current working directory mount for Docker command."""
    cwd = Path.cwd()
    docker_cmd.extend(["-e", f"SANDBOX_VOLUMES={cwd}:/workspace:rw"])
    if os.name != "nt":
        try:
            user_id = subprocess.check_output(["id", "-u"], text=True).strip()
            docker_cmd.extend(["-e", f"SANDBOX_USER_ID={user_id}"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    print_formatted_text(
        HTML(
            f"<ansigreen>📂 Mounting current directory:</ansigreen> <ansiyellow>{cwd}</ansiyellow> <ansigreen>to</ansigreen> <ansiyellow>/workspace</ansiyellow>",
        ),
    )


def _run_docker_container(docker_cmd: list[str]) -> None:
    """Run the Docker container with error handling."""
    try:
        print_formatted_text(HTML(_format_docker_command_for_logging(docker_cmd)))
        subprocess.run(docker_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print_formatted_text("")
        print_formatted_text(HTML("<ansired>❌ Failed to start OpenHands GUI server.</ansired>"))
        print_formatted_text(HTML(f"<grey>Error: {e}</grey>"))
        sys.exit(1)
    except KeyboardInterrupt:
        print_formatted_text("")
        print_formatted_text(HTML("<ansigreen>✓ OpenHands GUI server stopped successfully.</ansigreen>"))
        sys.exit(0)


def launch_gui_server(mount_cwd: bool = False, gpu: bool = False) -> None:
    """Launch the OpenHands GUI server using Docker.

    Args:
        mount_cwd: If True, mount the current working directory into the container.
        gpu: If True, enable GPU support by mounting all GPUs into the container via nvidia-docker.
    """
    print_formatted_text(HTML("<ansiblue>🚀 Launching OpenHands GUI server...</ansiblue>"))
    print_formatted_text("")

    if not check_docker_requirements():
        sys.exit(1)

    config_dir = ensure_config_dir_exists()
    version = __version__
    runtime_image = f"docker.all-hands.dev/all-hands-ai/runtime:{version}-nikolaik"
    app_image = f"docker.all-hands.dev/all-hands-ai/openhands:{version}"

    _pull_runtime_image(runtime_image)

    print_formatted_text("")
    print_formatted_text(HTML("<ansigreen>✅ Starting OpenHands GUI server...</ansigreen>"))
    print_formatted_text(HTML("<grey>The server will be available at: http://localhost:3000</grey>"))
    print_formatted_text(HTML("<grey>Press Ctrl+C to stop the server.</grey>"))
    print_formatted_text("")

    docker_cmd = [
        "docker",
        "run",
        "-it",
        "--rm",
        "--pull=always",
        "-e",
        f"SANDBOX_RUNTIME_CONTAINER_IMAGE={runtime_image}",
        "-e",
        "LOG_ALL_EVENTS=true",
        "-v",
        "/var/run/docker.sock:/var/run/docker.sock",
        "-v",
        f"{config_dir}:/.openhands",
    ]

    if gpu:
        _configure_gpu_support(docker_cmd)

    if mount_cwd:
        _configure_cwd_mount(docker_cmd)

    docker_cmd.extend(
        ["-p", "3000:3000", "--add-host", "host.docker.internal:host-gateway", "--name", "openhands-app", app_image],
    )

    _run_docker_container(docker_cmd)
