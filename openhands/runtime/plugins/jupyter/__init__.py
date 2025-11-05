from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from dataclasses import dataclass

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import Action, IPythonRunCellAction
from openhands.events.observation import IPythonRunCellObservation
from openhands.runtime.plugins.jupyter.execute_server import JupyterKernel
from openhands.runtime.plugins.requirement import Plugin, PluginRequirement
from openhands.runtime.utils import find_available_tcp_port
from openhands.utils.shutdown_listener import should_continue


@dataclass
class JupyterRequirement(PluginRequirement):
    name: str = "jupyter"


class JupyterPlugin(Plugin):
    name: str = "jupyter"
    kernel_gateway_port: int
    kernel_id: str
    gateway_process: asyncio.subprocess.Process | subprocess.Popen
    python_interpreter_path: str

    async def initialize(self, username: str, kernel_id: str = "openhands-default") -> None:
        """Initialize Jupyter kernel gateway.

        Args:
            username: Username for su command
            kernel_id: Kernel identifier

        Raises:
            ValueError: If OPENHANDS_REPO_PATH not set for local runtime
        """
        self.kernel_gateway_port = find_available_tcp_port(40000, 49999)
        self.kernel_id = kernel_id

        is_local_runtime = os.environ.get("LOCAL_RUNTIME_MODE") == "1"
        is_windows = sys.platform == "win32"

        prefix, poetry_prefix = self._get_command_prefixes(username, is_local_runtime)

        if is_windows:
            output = await self._launch_jupyter_windows(poetry_prefix)
        else:
            output = await self._launch_jupyter_unix(prefix, poetry_prefix)

        logger.debug("Jupyter kernel gateway started at port %s. Output: %s", self.kernel_gateway_port, output)

        _obs = await self.run(IPythonRunCellAction(code="import sys; print(sys.executable)"))
        self.python_interpreter_path = _obs.content.strip()

    def _get_command_prefixes(self, username: str, is_local_runtime: bool) -> tuple[str, str]:
        """Get command prefixes for Jupyter launch.

        Args:
            username: Username for su command
            is_local_runtime: Whether in local runtime mode

        Returns:
            Tuple of (prefix, poetry_prefix)

        Raises:
            ValueError: If OPENHANDS_REPO_PATH not set for local runtime
        """
        if not is_local_runtime:
            prefix = f"su - {username} -s "
            poetry_prefix = (
                "cd /openhands/code\n"
                "export POETRY_VIRTUALENVS_PATH=/openhands/poetry;\n"
                "export PYTHONPATH=/openhands/code:$PYTHONPATH;\n"
                "export MAMBA_ROOT_PREFIX=/openhands/micromamba;\n"
                "/openhands/micromamba/bin/micromamba run -n openhands "
            )
        else:
            code_repo_path = os.environ.get("OPENHANDS_REPO_PATH")
            if not code_repo_path:
                msg = (
                    "OPENHANDS_REPO_PATH environment variable is not set. "
                    "This is required for the jupyter plugin to work with LocalRuntime."
                )
                raise ValueError(
                    msg,
                )
            prefix = ""
            poetry_prefix = f"cd {code_repo_path}\n"

        return prefix, poetry_prefix

    async def _launch_jupyter_windows(self, code_repo_path: str | None = None) -> str:
        """Launch Jupyter on Windows.

        Args:
            code_repo_path: Code repository path

        Returns:
            Launch output
        """
        if not code_repo_path:
            code_repo_path = os.environ.get("OPENHANDS_REPO_PATH")

        jupyter_launch_command = [
            sys.executable,
            "-m",
            "jupyter",
            "kernelgateway",
            "--KernelGatewayApp.ip=0.0.0.0",
            f"--KernelGatewayApp.port={self.kernel_gateway_port}",
        ]

        logger.debug("Jupyter launch command (Windows): %s", jupyter_launch_command)
        self.gateway_process = subprocess.Popen(
            jupyter_launch_command,
            cwd=code_repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            text=True,
        )

        return await self._wait_for_jupyter_sync()

    async def _launch_jupyter_unix(self, prefix: str, poetry_prefix: str) -> str:
        """Launch Jupyter on Unix systems.

        Args:
            prefix: Shell prefix command
            poetry_prefix: Poetry environment prefix

        Returns:
            Launch output
        """
        jupyter_launch_command = (
            f"""{prefix}/bin/bash << 'EOF'\n"""
            f"""{poetry_prefix}"{sys.executable}" -m jupyter kernelgateway """
            f"""--KernelGatewayApp.ip=0.0.0.0 --KernelGatewayApp.port={self.kernel_gateway_port}\nEOF"""
        )

        logger.debug("Jupyter launch command: %s", jupyter_launch_command)
        self.gateway_process = await asyncio.create_subprocess_shell(
            jupyter_launch_command,
            stderr=asyncio.subprocess.STDOUT,
            stdout=asyncio.subprocess.PIPE,
        )

        return await self._wait_for_jupyter_async()

    async def _wait_for_jupyter_sync(self) -> str:
        """Wait for Jupyter to start (sync version for Windows).

        Returns:
            Startup output
        """
        output = ""
        while should_continue():
            if self.gateway_process.stdout is None:
                time.sleep(1)
                continue
            line = self.gateway_process.stdout.readline()
            if not line:
                time.sleep(1)
                continue
            output += line
            if "at" in line:
                break
            time.sleep(1)
            logger.debug("Waiting for jupyter kernel gateway to start...")
        return output

    async def _wait_for_jupyter_async(self) -> str:
        """Wait for Jupyter to start (async version for Unix).

        Returns:
            Startup output
        """
        output = ""
        while should_continue() and self.gateway_process.stdout is not None:
            line_bytes = await self.gateway_process.stdout.readline()
            line = line_bytes.decode("utf-8")
            output += line
            if "at" in line:
                break
            await asyncio.sleep(1)
            logger.debug("Waiting for jupyter kernel gateway to start...")
        return output

    async def _run(self, action: Action) -> IPythonRunCellObservation:
        """Internal method to run a code cell in the jupyter kernel."""
        if not isinstance(action, IPythonRunCellAction):
            msg = f"Jupyter plugin only supports IPythonRunCellAction, but got {action}"
            raise ValueError(msg)
        if not hasattr(self, "kernel"):
            self.kernel = JupyterKernel(f"localhost:{self.kernel_gateway_port}", self.kernel_id)
        if not self.kernel.initialized:
            await self.kernel.initialize()
        output = await self.kernel.execute(action.code, timeout=action.timeout)
        text_content = output.get("text", "")
        image_urls = output.get("images", [])
        return IPythonRunCellObservation(content=text_content, code=action.code, image_urls=image_urls or None)

    async def run(self, action: Action) -> IPythonRunCellObservation:
        return await self._run(action)
