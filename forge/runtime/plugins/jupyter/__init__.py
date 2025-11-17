"""Runtime plugin that provisions a Jupyter kernel gateway for notebook actions."""

from __future__ import annotations

import asyncio
import getpass
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx

from forge.core.logger import forge_logger as logger
from forge.events.action import Action, IPythonRunCellAction
from forge.events.observation import IPythonRunCellObservation
from forge.runtime.plugins.jupyter.execute_server import JupyterKernel
from forge.runtime.plugins.requirement import Plugin, PluginRequirement
from forge.runtime.utils import find_available_tcp_port
from forge.runtime.utils.command import MICROMAMBA_ENV_NAME
from forge.utils.shutdown_listener import should_continue


@dataclass
class JupyterRequirement(PluginRequirement):
    """Plugin requirement metadata for enabling the Jupyter runtime plugin."""

    name: str = "jupyter"


class JupyterPlugin(Plugin):
    """Runtime plugin that launches and proxies a Jupyter kernel gateway."""

    name: str = "jupyter"
    kernel_gateway_port: int
    kernel_id: str
    gateway_process: asyncio.subprocess.Process | subprocess.Popen[str] | None = None
    python_interpreter_path: str

    async def initialize(self, username: str, kernel_id: str = "Forge-default") -> None:
        """Initialize Jupyter kernel gateway.

        Args:
            username: Username for su command
            kernel_id: Kernel identifier

        Raises:
            ValueError: If FORGE_REPO_PATH not set for local runtime

        """
        self.kernel_gateway_port = find_available_tcp_port(40000, 49999)
        self.kernel_id = kernel_id

        is_local_runtime = os.environ.get("LOCAL_RUNTIME_MODE") == "1"
        platform_name: str = sys.platform
        is_windows = platform_name == "win32"

        prefix, poetry_prefix = self._get_command_prefixes(username, is_local_runtime)

        if is_windows:
            output = await self._launch_jupyter_windows(poetry_prefix)
        else:
            output = await self._launch_jupyter_unix(prefix, poetry_prefix)

        logger.debug(
            "Jupyter kernel gateway started at port %s. Output: %s",
            self.kernel_gateway_port,
            output,
        )

        _obs = await self.run(
            IPythonRunCellAction(code="import sys; print(sys.executable)")
        )
        self.python_interpreter_path = _obs.content.strip()

    def _get_command_prefixes(
        self, username: str, is_local_runtime: bool
    ) -> tuple[str, str]:
        """Get command prefixes for Jupyter launch.

        Args:
            username: Username for su command
            is_local_runtime: Whether in local runtime mode

        Returns:
            Tuple of (prefix, poetry_prefix)

        Raises:
            ValueError: If FORGE_REPO_PATH not set for local runtime

        """
        should_use_su = False
        platform_name: str = sys.platform
        if not is_local_runtime and platform_name != "win32":
            geteuid = getattr(os, "geteuid", None)
            if callable(geteuid) and geteuid() == 0:
                current_user = None
                try:
                    current_user = getpass.getuser()
                except Exception:
                    logger.debug("Unable to determine current user for Jupyter launch")
                if current_user != username:
                    should_use_su = True
        if should_use_su:
            prefix = f"su - {username} -s "
        else:
            prefix = ""
        if not is_local_runtime:
            poetry_prefix = (
                "cd /Forge/code\n"
                "export POETRY_VIRTUALENVS_PATH=/Forge/poetry;\n"
                "export PYTHONPATH=/Forge/code:$PYTHONPATH;\n"
                "export MAMBA_ROOT_PREFIX=/Forge/micromamba;\n"
                f"/Forge/micromamba/bin/micromamba run -n {MICROMAMBA_ENV_NAME} "
            )
        else:
            code_repo_path = os.environ.get("FORGE_REPO_PATH")
            if not code_repo_path:
                msg = (
                    "FORGE_REPO_PATH environment variable is not set. "
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
            code_repo_path = os.environ.get("FORGE_REPO_PATH")

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

    def _gateway_is_ready_sync(self) -> bool:
        """Check synchronously whether the kernel gateway is responding."""
        url = f"http://127.0.0.1:{self.kernel_gateway_port}/_api/kernels"
        try:
            resp = httpx.get(url, timeout=2.0)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def _gateway_is_ready_async(self) -> bool:
        """Check asynchronously whether the kernel gateway is responding."""
        url = f"http://127.0.0.1:{self.kernel_gateway_port}/_api/kernels"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(url)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False

    async def _wait_for_jupyter_sync(self) -> str:
        """Wait for Jupyter to start (sync version for Windows).

        Returns:
            Startup output

        """
        if self.gateway_process is None:
            msg = "Gateway process has not been started"
            raise RuntimeError(msg)
        process = cast(subprocess.Popen[str], self.gateway_process)
        output = ""
        while should_continue():
            stdout = process.stdout
            if stdout is None:
                time.sleep(1)
                continue
            line = stdout.readline()
            if not line:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Jupyter kernel gateway exited early: {output}"
                    )
                time.sleep(1)
                continue
            output += line
            if "at" in line or self._gateway_is_ready_sync():
                break
            time.sleep(1)
            logger.debug("Waiting for jupyter kernel gateway to start...")
        return output

    async def _wait_for_jupyter_async(self) -> str:
        """Wait for Jupyter to start (async version for Unix).

        Returns:
            Startup output

        """
        if self.gateway_process is None:
            msg = "Gateway process has not been started"
            raise RuntimeError(msg)
        process = cast(asyncio.subprocess.Process, self.gateway_process)
        output = ""
        while should_continue():
            stdout = process.stdout
            if stdout is None:
                await asyncio.sleep(1)
                continue
            line_bytes = await stdout.readline()
            if not line_bytes:
                if process.returncode is not None:
                    raise RuntimeError(
                        f"Jupyter kernel gateway exited early: {output}"
                    )
                await asyncio.sleep(1)
                continue
            line = line_bytes.decode("utf-8")
            output += line
            if "at" in line or await self._gateway_is_ready_async():
                break
            await asyncio.sleep(1)
            logger.debug("Waiting for jupyter kernel gateway to start...")
        return output

    async def _run(self, action: Action) -> IPythonRunCellObservation:
        """Internal method to run a code cell in the jupyter kernel."""
        ipython_action = self._ensure_ipython_action(action)
        await self._ensure_kernel_initialized()
        timeout = self._extract_timeout(ipython_action)
        output = await self._execute_kernel_code(ipython_action, timeout)
        text_content = self._normalize_text_output(output)
        image_urls = self._normalize_image_output(output)
        return self._build_ipython_observation(
            ipython_action, text_content, image_urls
        )

    async def run(self, action: Action) -> IPythonRunCellObservation:
        """Execute an IPython cell action through the active Jupyter kernel."""
        return await self._run(action)

    def _ensure_ipython_action(self, action: Action) -> IPythonRunCellAction:
        if not isinstance(action, IPythonRunCellAction):
            msg = f"Jupyter plugin only supports IPythonRunCellAction, but got {action}"
            raise ValueError(msg)
        return action

    async def _ensure_kernel_initialized(self) -> None:
        if not hasattr(self, "kernel"):
            self.kernel = JupyterKernel(
                f"localhost:{self.kernel_gateway_port}", self.kernel_id
            )
        if not self.kernel.initialized:
            await self.kernel.initialize()

    def _extract_timeout(self, action: IPythonRunCellAction) -> int:
        default_timeout = 120
        if action.timeout is None:
            return default_timeout
        try:
            return int(action.timeout)
        except (TypeError, ValueError):
            return default_timeout

    async def _execute_kernel_code(
        self, action: IPythonRunCellAction, timeout: int
    ) -> dict[str, Any]:
        return await self.kernel.execute(action.code, timeout=timeout)

    def _normalize_text_output(self, output: dict[str, Any]) -> str:
        text_raw = output.get("text", "")
        if isinstance(text_raw, list):
            return "".join(text_raw)
        if isinstance(text_raw, str):
            return text_raw
        return str(text_raw)

    def _normalize_image_output(self, output: dict[str, Any]) -> list[str]:
        images_raw = output.get("images", [])
        if isinstance(images_raw, list):
            return images_raw
        if images_raw:
            return [str(images_raw)]
        return []

    def _build_ipython_observation(
        self, action: IPythonRunCellAction, text: str, image_urls: list[str]
    ) -> IPythonRunCellObservation:
        return IPythonRunCellObservation(
            content=text, code=action.code, image_urls=image_urls or None
        )
