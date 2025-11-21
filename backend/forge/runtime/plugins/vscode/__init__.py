"""Runtime plugin that provisions an OpenVSCode server inside the sandbox."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import uuid
from dataclasses import dataclass
import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from forge.core.logger import forge_logger as logger
from forge.runtime.plugins.requirement import Plugin, PluginRequirement
from forge.runtime.utils.system import check_port_available
from forge.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    from forge.events.action import Action
    from forge.events.observation import Observation


@dataclass
class VSCodeRequirement(PluginRequirement):
    """Plugin requirement metadata declaring support for the VSCode web IDE."""

    name: str = "vscode"


class VSCodePlugin(Plugin):
    """Runtime plugin that launches an OpenVSCode server inside the sandbox."""

    name: str = "vscode"
    vscode_port: int | None = None
    vscode_connection_token: str | None = None
    gateway_process: asyncio.subprocess.Process

    def _check_platform_support(self) -> bool:
        """Check if platform supports VSCode plugin."""
        os_name: str = os.name
        platform_name: str = sys.platform
        if os_name == "nt" or platform_name == "win32":
            self.vscode_port = None
            self.vscode_connection_token = None
            logger.warning(
                "VSCode plugin is not supported on Windows. Plugin will be disabled."
            )
            return False
        return True

    def _check_user_support(self, username: str) -> bool:
        """Check if user is supported for VSCode plugin."""
        if username not in ["root", "forge"]:
            self.vscode_port = None
            self.vscode_connection_token = None
            logger.warning(
                "VSCodePlugin is only supported for root or Forge user. It is not yet supported for other users (i.e., when running LocalRuntime).",
            )
            return False
        return True

    def _get_base_path_flag(self, runtime_id: str | None) -> str:
        """Get base path flag for VSCode server."""
        if explicit_base := os.getenv("OPENVSCODE_SERVER_BASE_PATH"):
            explicit_base = (
                explicit_base if explicit_base.startswith("/") else f"/{explicit_base}"
            )
            return f" --server-base-path {explicit_base.rstrip('/')}"

        runtime_url = os.getenv("RUNTIME_URL", "")
        if runtime_url and runtime_id:
            parsed = urlparse(runtime_url)
            path = parsed.path or "/"
            if path.startswith(f"/{runtime_id}"):
                return f" --server-base-path /{runtime_id}/vscode"

        return ""

    def _build_vscode_command(
        self, username: str, workspace_path: str, base_path_flag: str
    ) -> str:
        """Build command to start VSCode server."""
        # Validate and sanitize dynamic values before interpolation
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username):
            raise ValueError("Invalid username for VSCode server startup")
        safe_workspace = shlex.quote(workspace_path)
        safe_base_path_flag = ""
        if base_path_flag and re.fullmatch(r"\s*--server-base-path\s+/[A-Za-z0-9/_-]+\s*", base_path_flag):
            safe_base_path_flag = base_path_flag
        token = shlex.quote(str(self.vscode_connection_token))
        port = str(int(self.vscode_port)) if self.vscode_port is not None else "0"
        return (
            f"su - {username} -s /bin/bash << 'EOF'\n"
            f"sudo chown -R {username}:{username} /Forge/.openvscode-server\n"
            f"cd {safe_workspace}\n"
            f"exec /Forge/.openvscode-server/bin/openvscode-server --host 0.0.0.0 "
            f"--connection-token {token} --port {port} --disable-workspace-trust{safe_base_path_flag}\n"
            f"EOF"
        )

    async def _wait_for_server_start(self) -> str:
        """Wait for VSCode server to start and return output."""
        output = ""
        while should_continue() and self.gateway_process.stdout is not None:
            line_bytes = await self.gateway_process.stdout.readline()
            line = line_bytes.decode("utf-8")
            output += line
            if "at" in line:
                break
            await asyncio.sleep(1)
            logger.debug("Waiting for VSCode server to start...")
        return output

    async def initialize(self, username: str, runtime_id: str | None = None) -> None:
        """Bootstrap the VSCode server for the current runtime session."""
        # Check platform and user support
        if not self._check_platform_support():
            return
        if not self._check_user_support(username):
            return

        # Setup VSCode settings
        self._setup_vscode_settings()

        # Get and validate port
        try:
            self.vscode_port = int(os.environ["VSCODE_PORT"])
        except (KeyError, ValueError):
            logger.warning(
                "VSCODE_PORT environment variable not set or invalid. VSCode plugin will be disabled."
            )
            return

        self.vscode_connection_token = str(uuid.uuid4())

        if not check_port_available(self.vscode_port):
            logger.warning(
                "Port %s is not available. VSCode plugin will be disabled.",
                self.vscode_port,
            )
            return

        # Build and execute command
        workspace_path = os.getenv("WORKSPACE_MOUNT_PATH_IN_SANDBOX", "/workspace")
        base_path_flag = self._get_base_path_flag(runtime_id)
        cmd = self._build_vscode_command(username, workspace_path, base_path_flag)

        self.gateway_process = await asyncio.create_subprocess_exec(
            "/bin/bash",
            "-lc",
            cmd,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )

        # Wait for server to start
        output = await self._wait_for_server_start()
        logger.debug(
            "VSCode server started at port %s. Output: %s", self.vscode_port, output
        )

    def _setup_vscode_settings(self) -> None:
        """Set up VSCode settings by creating the .vscode directory in the workspace.

        and copying the settings.json file there.
        """
        current_dir = Path(__file__).parent
        settings_path = current_dir / "settings.json"
        workspace_dir = Path(os.getenv("WORKSPACE_BASE", "/workspace"))
        vscode_dir = workspace_dir / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)
        target_path = vscode_dir / "settings.json"
        shutil.copy(settings_path, target_path)
        os.chmod(target_path, 420)
        logger.debug("VSCode settings copied to %s", target_path)

    async def run(self, action: Action) -> Observation:
        """Run the plugin for a given action."""
        msg = "VSCodePlugin does not support run method"
        raise NotImplementedError(msg)
