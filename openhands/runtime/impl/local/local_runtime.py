"""This runtime runs the action_execution_server directly on the local machine without Docker."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable
from urllib.parse import urlparse

import httpx
import tenacity

import openhands
from openhands.core.exceptions import AgentRuntimeDisconnectedError
from openhands.core.logger import openhands_logger as logger
from openhands.events.serialization import event_to_dict, observation_from_dict
from openhands.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)
from openhands.runtime.impl.docker.docker_runtime import (
    APP_PORT_RANGE_1,
    APP_PORT_RANGE_2,
    EXECUTION_SERVER_PORT_RANGE,
    VSCODE_PORT_RANGE,
)
from openhands.runtime.plugins.vscode import VSCodeRequirement
from openhands.runtime.runtime_status import RuntimeStatus
from openhands.runtime.utils import find_available_tcp_port
from openhands.runtime.utils.command import get_action_execution_server_startup_command
from openhands.utils.async_utils import call_sync_from_async
from openhands.utils.tenacity_metrics import (
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)
from openhands.utils.tenacity_stop import stop_if_should_exit

if TYPE_CHECKING:
    from openhands.core.config import OpenHandsConfig
    from openhands.events import EventStream
    from openhands.events.action import Action
    from openhands.events.observation import Observation
    from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
    from openhands.llm.llm_registry import LLMRegistry
    from openhands.runtime.plugins import PluginRequirement


@dataclass
class ActionExecutionServerInfo:
    """Information about a running server process."""

    process: subprocess.Popen
    execution_server_port: int
    vscode_port: int
    app_ports: list[int]
    log_thread: threading.Thread
    log_thread_exit_event: threading.Event
    temp_workspace: str | None
    workspace_mount_path: str


_RUNNING_SERVERS: dict[str, ActionExecutionServerInfo] = {}
_WARM_SERVERS: list[ActionExecutionServerInfo] = []


def get_user_info() -> tuple[int, str | None]:
    """Get user ID and username in a cross-platform way."""
    username = os.getenv("USER")
    return (1000, username) if sys.platform == "win32" else (os.getuid(), username)


def check_dependencies(code_repo_path: str, check_browser: bool) -> None:
    """Check that required dependencies are installed for local runtime.
    
    Verifies Jupyter, libtmux (non-Windows), and optionally Chromium are available.
    
    Args:
        code_repo_path: Path to code repository
        check_browser: Whether to check for browser dependencies
        
    Raises:
        ValueError: If dependencies are missing or paths invalid
    """
    ERROR_MESSAGE = "Please follow the instructions in https://github.com/All-Hands-AI/OpenHands/blob/main/Development.md to install OpenHands."
    if not os.path.exists(code_repo_path):
        msg = f"Code repo path {code_repo_path} does not exist. {ERROR_MESSAGE}"
        raise ValueError(msg)
    logger.debug("Checking dependencies: Jupyter")
    output = subprocess.check_output([sys.executable, "-m", "jupyter", "--version"], text=True, cwd=code_repo_path)
    logger.debug("Jupyter output: %s", output)
    if "jupyter" not in output.lower():
        msg = f"Jupyter is not properly installed. {ERROR_MESSAGE}"
        raise ValueError(msg)
    if sys.platform != "win32":
        logger.debug("Checking dependencies: libtmux")
        import libtmux

        server = libtmux.Server()
        try:
            session = server.new_session(session_name="test-session")
        except Exception as e:
            msg = "tmux is not properly installed or available on the path."
            raise ValueError(msg) from e
        pane = session.attached_pane
        pane.send_keys('echo "test"')
        pane_output = "\n".join(pane.cmd("capture-pane", "-p").stdout)
        session.kill_session()
        if "test" not in pane_output:
            msg = f"libtmux is not properly installed. {ERROR_MESSAGE}"
            raise ValueError(msg)
    if check_browser:
        logger.debug("Checking dependencies: browser")
        from openhands.runtime.browser.browser_env import BrowserEnv

        browser = BrowserEnv()
        browser.close()


class LocalRuntime(ActionExecutionClient):
    """This runtime will run the action_execution_server directly on the local machine.

    When receiving an event, it will send the event to the server via HTTP.

    Args:
        config (OpenHandsConfig): The application configuration.
        event_stream (EventStream): The event stream to subscribe to.
        sid (str, optional): The session ID. Defaults to 'default'.
        plugins (list[PluginRequirement] | None, optional): list of plugin requirements. Defaults to None.
        env_vars (dict[str, str] | None, optional): Environment variables to set. Defaults to None.
    """

    def __init__(
        self,
        config: OpenHandsConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[[str, RuntimeStatus, str], None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> None:
        self.is_windows = sys.platform == "win32"
        if self.is_windows:
            logger.warning(
                "Running on Windows - some features that require tmux will be limited. For full functionality, please consider using WSL or Docker runtime.",
            )
        self.config = config
        self._user_id, self._username = get_user_info()
        logger.warning(
            "Initializing LocalRuntime. WARNING: NO SANDBOX IS USED. This is an experimental feature, please report issues to https://github.com/All-Hands-AI/OpenHands/issues. `run_as_openhands` will be ignored since the current user will be used to launch the server. We highly recommend using a sandbox (eg. DockerRuntime) unless you are running in a controlled environment.\nUser ID: %s. Username: %s.",
            self._user_id,
            self._username,
        )
        self._temp_workspace: str | None = None
        self._execution_server_port = -1
        self._vscode_port = -1
        self._app_ports: list[int] = []
        self.api_url = f"{self.config.sandbox.local_runtime_url}:{self._execution_server_port}"
        self.status_callback = status_callback
        self.server_process: subprocess.Popen[str] | None = None
        self.action_semaphore = threading.Semaphore(1)
        self._log_thread_exit_event = threading.Event()
        if self.config.sandbox.runtime_startup_env_vars:
            os.environ |= self.config.sandbox.runtime_startup_env_vars
        super().__init__(
            config,
            event_stream,
            llm_registry,
            sid,
            plugins,
            env_vars,
            status_callback,
            attach_to_existing,
            headless_mode,
            user_id,
            git_provider_tokens,
        )
        session_api_key = os.getenv("SESSION_API_KEY")
        self._session_api_key: str | None = None
        if session_api_key:
            self.session.headers["X-Session-API-Key"] = session_api_key
            self._session_api_key = session_api_key

    @property
    def session_api_key(self) -> str | None:
        return self._session_api_key

    @property
    def action_execution_server_url(self) -> str:
        return self.api_url

    def _connect_to_existing_server(self) -> None:
        """Connect to an existing server for this session."""
        self.log("info", f"Connecting to existing server for session {self.sid}")
        server_info = _RUNNING_SERVERS[self.sid]
        self.server_process = server_info.process
        self._execution_server_port = server_info.execution_server_port
        self._log_thread = server_info.log_thread
        self._log_thread_exit_event = server_info.log_thread_exit_event
        self._vscode_port = server_info.vscode_port
        self._app_ports = server_info.app_ports
        self._temp_workspace = server_info.temp_workspace
        self.config.workspace_mount_path_in_sandbox = server_info.workspace_mount_path
        self.api_url = f"{self.config.sandbox.local_runtime_url}:{self._execution_server_port}"

    def _setup_workspace_directory(self) -> None:
        """Setup workspace directory for the runtime."""
        if self.config.workspace_base is not None:
            logger.warning(
                "Workspace base path is set to %s. It will be used as the path for the agent to run in. Be careful, the agent can EDIT files in this directory!",
                self.config.workspace_base,
            )
            self.config.workspace_mount_path_in_sandbox = self.config.workspace_base
            self._temp_workspace = None
        else:
            logger.warning("Workspace base path is NOT set. Agent will run in a temporary directory.")
            self._temp_workspace = tempfile.mkdtemp(prefix=f"openhands_workspace_{self.sid}")
            self.config.workspace_mount_path_in_sandbox = self._temp_workspace
        logger.info("Using workspace directory: %s", self.config.workspace_mount_path_in_sandbox)

    def _use_warm_server(self) -> bool:
        """Try to use a warm server if available."""
        if not _WARM_SERVERS or self.attach_to_existing:
            return False

        try:
            self.log("info", "Using a warm server")
            server_info = _WARM_SERVERS.pop(0)
            self.server_process = server_info.process
            self._execution_server_port = server_info.execution_server_port
            self._log_thread = server_info.log_thread
            self._log_thread_exit_event = server_info.log_thread_exit_event
            self._vscode_port = server_info.vscode_port
            self._app_ports = server_info.app_ports

            if server_info.temp_workspace:
                shutil.rmtree(server_info.temp_workspace)
            if self._temp_workspace is None and self.config.workspace_base is None:
                self._temp_workspace = tempfile.mkdtemp(prefix=f"openhands_workspace_{self.sid}")
                self.config.workspace_mount_path_in_sandbox = self._temp_workspace

            self.api_url = f"{self.config.sandbox.local_runtime_url}:{self._execution_server_port}"
            _RUNNING_SERVERS[self.sid] = ActionExecutionServerInfo(
                process=self.server_process,
                execution_server_port=self._execution_server_port,
                vscode_port=self._vscode_port,
                app_ports=self._app_ports,
                log_thread=self._log_thread,
                log_thread_exit_event=self._log_thread_exit_event,
                temp_workspace=self._temp_workspace,
                workspace_mount_path=self.config.workspace_mount_path_in_sandbox,
            )
            return True
        except IndexError:
            self.log("info", "No warm servers available, starting a new server")
            return False
        except Exception as e:
            self.log("error", f"Error using warm server: {e}")
            return False

    def _create_new_server(self) -> None:
        """Create a new server for this session."""
        server_info, api_url = _create_server(config=self.config, plugins=self.plugins, workspace_prefix=self.sid)
        self.server_process = server_info.process
        self._execution_server_port = server_info.execution_server_port
        self._vscode_port = server_info.vscode_port
        self._app_ports = server_info.app_ports
        self._log_thread = server_info.log_thread
        self._log_thread_exit_event = server_info.log_thread_exit_event

        if server_info.temp_workspace and server_info.temp_workspace != self._temp_workspace:
            shutil.rmtree(server_info.temp_workspace)

        self.api_url = api_url
        _RUNNING_SERVERS[self.sid] = ActionExecutionServerInfo(
            process=self.server_process,
            execution_server_port=self._execution_server_port,
            vscode_port=self._vscode_port,
            app_ports=self._app_ports,
            log_thread=self._log_thread,
            log_thread_exit_event=self._log_thread_exit_event,
            temp_workspace=self._temp_workspace,
            workspace_mount_path=self.config.workspace_mount_path_in_sandbox,
        )

    def _create_additional_warm_servers(self, desired_num_warm_servers: int) -> None:
        """Create additional warm servers if needed."""
        if desired_num_warm_servers > 0 and len(_WARM_SERVERS) < desired_num_warm_servers:
            num_to_create = desired_num_warm_servers - len(_WARM_SERVERS)
            self.log("info", f"Creating {num_to_create} additional warm servers to reach desired count")
            for _ in range(num_to_create):
                _create_warm_server_in_background(self.config, self.plugins)

    async def connect(self) -> None:
        """Start the action_execution_server on the local machine or connect to an existing one."""
        import time

        start_time = time.time()
        used_warm_server = False

        self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)
        desired_num_warm_servers = int(os.getenv("DESIRED_NUM_WARM_SERVERS", "0"))

        if self.sid in _RUNNING_SERVERS:
            self._connect_to_existing_server()
        elif self.attach_to_existing:
            self.log("error", f"No existing server found for session {self.sid}")
            msg = f"No existing server found for session {self.sid}"
            raise AgentRuntimeDisconnectedError(msg)
        else:
            self._setup_workspace_directory()

            if not self._use_warm_server():
                self._create_new_server()
            else:
                used_warm_server = True

        self.log("info", f"Waiting for server to become ready at {self.api_url}...")
        self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)
        await call_sync_from_async(self._wait_until_alive)

        if not self.attach_to_existing:
            await call_sync_from_async(self.setup_initial_env)

        self.log("debug", f"Server initialized with plugins: {[plugin.name for plugin in self.plugins]}")
        if not self.attach_to_existing:
            self.set_runtime_status(RuntimeStatus.READY)

        self._runtime_initialized = True

        # Log performance metrics
        elapsed = time.time() - start_time
        self.log(
            "info",
            f"🚀 Runtime ready in {elapsed:.2f}s (warm_server={used_warm_server}, pool_size={len(_WARM_SERVERS)})",
        )

        self._create_additional_warm_servers(desired_num_warm_servers)

    @classmethod
    def setup(cls, config: OpenHandsConfig, headless_mode: bool = False) -> None:
        should_check_dependencies = os.getenv("SKIP_DEPENDENCY_CHECK", "") != "1"
        if should_check_dependencies:
            code_repo_path = os.path.dirname(os.path.dirname(openhands.__file__))
            check_browser = config.enable_browser and sys.platform != "win32"
            check_dependencies(code_repo_path, check_browser)
        initial_num_warm_servers = int(os.getenv("INITIAL_NUM_WARM_SERVERS", "0"))
        if initial_num_warm_servers > 0 and len(_WARM_SERVERS) == 0:
            plugins = _get_plugins(config)
            if not headless_mode:
                plugins.append(VSCodeRequirement())
            for _ in range(initial_num_warm_servers):
                _create_warm_server(config, plugins)

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_delay(120) | stop_if_should_exit(),
        before_sleep=lambda retry_state: (
            __import__("openhands.utils.tenacity_metrics").utils.tenacity_metrics.call_tenacity_hooks(
                tenacity_before_sleep_factory("runtime.local.wait_until_alive"),
                None,
                retry_state,
            ),
            logger.debug("Waiting for server to be ready... (attempt %s)", retry_state.attempt_number),
        ),
    )
    def _wait_until_alive(self) -> bool:
        """Wait until the server is ready to accept requests."""
        if self.server_process and self.server_process.poll() is not None:
            msg = "Server process died"
            raise RuntimeError(msg)
        try:
            response = self.session.get(f"{self.api_url}/alive")
            response.raise_for_status()
            return True
        except Exception as e:
            self.log("debug", f"Server not ready yet: {e}")
            raise

    async def execute_action(self, action: Action) -> Observation:
        """Execute an action by sending it to the server."""
        if not self.runtime_initialized:
            msg = "Runtime not initialized"
            raise AgentRuntimeDisconnectedError(msg)
        if self.server_process is None:
            if self.sid in _RUNNING_SERVERS:
                self.server_process = _RUNNING_SERVERS[self.sid].process
            else:
                msg = "Server process not found"
                raise AgentRuntimeDisconnectedError(msg)
        if self.server_process.poll() is not None:
            if self.sid in _RUNNING_SERVERS:
                del _RUNNING_SERVERS[self.sid]
            msg = "Server process died"
            raise AgentRuntimeDisconnectedError(msg)
        with self.action_semaphore:
            try:
                response = await call_sync_from_async(
                    lambda: self.session.post(f"{self.api_url}/execute_action", json={"action": event_to_dict(action)}),
                )
                desired_num_warm_servers = int(os.getenv("DESIRED_NUM_WARM_SERVERS", "0"))
                if desired_num_warm_servers > 0 and len(_WARM_SERVERS) < desired_num_warm_servers:
                    self.log(
                        "info",
                        f"Creating a new warm server to maintain desired count of {desired_num_warm_servers}",
                    )
                    _create_warm_server_in_background(self.config, self.plugins)
                return observation_from_dict(response.json())
            except httpx.NetworkError as e:
                msg = "Server connection lost"
                raise AgentRuntimeDisconnectedError(msg) from e

    def close(self) -> None:
        """Stop the server process if not in attach_to_existing mode."""
        if self.attach_to_existing:
            self.log("info", f"Not closing server for session {self.sid} (attach_to_existing=True)")
            self.server_process = None
            super().close()
            return
        self._log_thread_exit_event.set()
        if self.sid in _RUNNING_SERVERS:
            del _RUNNING_SERVERS[self.sid]
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            self._log_thread.join(timeout=5)
        if self._temp_workspace and (not self.attach_to_existing):
            shutil.rmtree(self._temp_workspace)
            self._temp_workspace = None
        super().close()

    @classmethod
    async def delete(cls, conversation_id: str) -> None:
        """Delete the runtime for a conversation."""
        if conversation_id in _RUNNING_SERVERS:
            logger.info("Deleting LocalRuntime for conversation %s", conversation_id)
            server_info = _RUNNING_SERVERS[conversation_id]
            server_info.log_thread_exit_event.set()
            if server_info.process:
                server_info.process.terminate()
                try:
                    server_info.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_info.process.kill()
            server_info.log_thread.join(timeout=5)
            del _RUNNING_SERVERS[conversation_id]
            logger.info("LocalRuntime for conversation %s deleted", conversation_id)
        if not _RUNNING_SERVERS:
            logger.info("No active conversations, cleaning up warm servers")
            for server_info in _WARM_SERVERS[:]:
                server_info.log_thread_exit_event.set()
                if server_info.process:
                    server_info.process.terminate()
                    try:
                        server_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        server_info.process.kill()
                server_info.log_thread.join(timeout=5)
                if server_info.temp_workspace:
                    shutil.rmtree(server_info.temp_workspace)
                _WARM_SERVERS.remove(server_info)
            logger.info("All warm servers cleaned up")

    @property
    def runtime_url(self) -> str:
        if runtime_url := os.getenv("RUNTIME_URL"):
            return runtime_url
        runtime_url_pattern = os.getenv("RUNTIME_URL_PATTERN")
        runtime_id = os.getenv("RUNTIME_ID")
        if runtime_url_pattern and runtime_id:
            return runtime_url_pattern.format(runtime_id=runtime_id)
        return self.config.sandbox.local_runtime_url

    def _create_url(self, prefix: str, port: int) -> str:
        runtime_url = self.runtime_url
        logger.debug("runtime_url is %s", runtime_url)
        if "localhost" in runtime_url:
            url = f"{self.runtime_url}:{self._vscode_port}"
        else:
            runtime_id = os.getenv("RUNTIME_ID")
            parsed = urlparse(self.runtime_url)
            scheme, netloc, path = (parsed.scheme, parsed.netloc, parsed.path or "/")
            path_mode = path.startswith(f"/{runtime_id}") if runtime_id else False
            if path_mode:
                url = f"{scheme}://{netloc}/{runtime_id}/{prefix}"
            else:
                url = f"{scheme}://{prefix}-{netloc}"
        logger.debug("_create_url url is %s", url)
        return url

    @property
    def vscode_url(self) -> str | None:
        token = super().get_vscode_token()
        if not token:
            return None
        vscode_url = self._create_url("vscode", self._vscode_port)
        return f"{vscode_url}/?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}"

    @property
    def web_hosts(self) -> dict[str, int]:
        hosts: dict[str, int] = {}
        for index, port in enumerate(self._app_ports):
            url = self._create_url(f"work-{index + 1}", port)
            hosts[url] = port
        return hosts


def _python_bin_path():
    interpreter_path = sys.executable
    return os.path.dirname(interpreter_path)


def _create_server(
    config: OpenHandsConfig,
    plugins: list[PluginRequirement],
    workspace_prefix: str,
) -> tuple[ActionExecutionServerInfo, str]:
    logger.info("Creating a server")
    temp_workspace = tempfile.mkdtemp(prefix=f"openhands_workspace_{workspace_prefix}")
    workspace_mount_path = temp_workspace
    execution_server_port = find_available_tcp_port(*EXECUTION_SERVER_PORT_RANGE)
    vscode_port = int(os.getenv("VSCODE_PORT") or str(find_available_tcp_port(*VSCODE_PORT_RANGE)))
    app_ports = [
        int(os.getenv("WORK_PORT_1") or os.getenv("APP_PORT_1") or str(find_available_tcp_port(*APP_PORT_RANGE_1))),
        int(os.getenv("WORK_PORT_2") or os.getenv("APP_PORT_2") or str(find_available_tcp_port(*APP_PORT_RANGE_2))),
    ]
    user_id, username = get_user_info()
    cmd = get_action_execution_server_startup_command(
        server_port=execution_server_port,
        plugins=plugins,
        app_config=config,
        python_prefix=[],
        python_executable=sys.executable,
        override_user_id=user_id,
        override_username=username,
    )
    logger.info("Starting server with command: %s", cmd)
    env = os.environ.copy()
    code_repo_path = os.path.dirname(os.path.dirname(openhands.__file__))
    env["PYTHONPATH"] = os.pathsep.join([code_repo_path, env.get("PYTHONPATH", "")])
    env["OPENHANDS_REPO_PATH"] = code_repo_path
    env["LOCAL_RUNTIME_MODE"] = "1"
    env["VSCODE_PORT"] = str(vscode_port)
    env["PATH"] = f"{_python_bin_path()}{os.pathsep}{env.get('PATH', '')}"
    logger.debug("Updated PATH for subprocesses: %s", env["PATH"])
    server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        env=env,
        cwd=code_repo_path,
    )
    log_thread_exit_event = threading.Event()

    def log_output() -> None:
        if not server_process or not server_process.stdout:
            logger.error("server process or stdout not available for logging.")
            return
        try:
            while server_process.poll() is None:
                if log_thread_exit_event.is_set():
                    logger.info("server log thread received exit signal.")
                    break
                line = server_process.stdout.readline()
                if not line:
                    break
                logger.info("server: %s", line.strip())
            if not log_thread_exit_event.is_set():
                logger.info("server process exited, reading remaining output.")
                for line in server_process.stdout:
                    if log_thread_exit_event.is_set():
                        break
                    logger.info("server (remaining): %s", line.strip())
        except Exception as e:
            logger.error("Error reading server output: %s", e)
        finally:
            logger.info("server log output thread finished.")

    log_thread = threading.Thread(target=log_output, daemon=True)
    log_thread.start()
    server_info = ActionExecutionServerInfo(
        process=server_process,
        execution_server_port=execution_server_port,
        vscode_port=vscode_port,
        app_ports=app_ports,
        log_thread=log_thread,
        log_thread_exit_event=log_thread_exit_event,
        temp_workspace=temp_workspace,
        workspace_mount_path=workspace_mount_path,
    )
    api_url = f"{config.sandbox.local_runtime_url}:{execution_server_port}"
    return (server_info, api_url)


def _create_warm_server(config: OpenHandsConfig, plugins: list[PluginRequirement]) -> None:
    """Create a warm server in the background."""
    try:
        server_info, api_url = _create_server(config=config, plugins=plugins, workspace_prefix="warm")
        session = httpx.Client(timeout=30)

        @tenacity.retry(
            wait=tenacity.wait_fixed(2),
            stop=tenacity.stop_after_delay(120) | stop_if_should_exit(),
            before_sleep=lambda retry_state: (
                tenacity_before_sleep_factory("runtime.local.warm_wait")(retry_state),
                tenacity_after_factory("runtime.local.warm_wait")(retry_state) if False else None,
                logger.debug("Waiting for warm server to be ready... (attempt %s)", retry_state.attempt_number),
            ),
        )
        def wait_until_alive() -> bool:
            if server_info.process.poll() is not None:
                msg = "Warm server process died"
                raise RuntimeError(msg)
            try:
                response = session.get(f"{api_url}/alive")
                response.raise_for_status()
                return True
            except Exception as e:
                logger.debug("Warm server not ready yet: %s", e)
                raise

        wait_until_alive()
        logger.info("Warm server ready at port %s", server_info.execution_server_port)
        _WARM_SERVERS.append(server_info)
    except Exception as e:
        logger.error("Failed to create warm server: %s", e)
        if "server_info" in locals():
            server_info.log_thread_exit_event.set()
            if server_info.process:
                server_info.process.terminate()
                try:
                    server_info.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_info.process.kill()
            server_info.log_thread.join(timeout=5)
            if server_info.temp_workspace:
                shutil.rmtree(server_info.temp_workspace)


def _create_warm_server_in_background(config: OpenHandsConfig, plugins: list[PluginRequirement]) -> None:
    """Start a new thread to create a warm server."""
    thread = threading.Thread(target=_create_warm_server, daemon=True, args=(config, plugins))
    thread.start()


def _get_plugins(config: OpenHandsConfig) -> list[PluginRequirement]:
    from openhands.controller.agent import Agent

    return Agent.get_cls(config.default_agent).sandbox_plugins
