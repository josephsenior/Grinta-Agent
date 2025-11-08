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
from tenacity import RetryCallState

import forge
from forge.core.exceptions import AgentRuntimeDisconnectedError
from forge.core.logger import forge_logger as logger
from forge.events.serialization import event_to_dict, observation_from_dict
from forge.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)
from forge.runtime.impl.docker.docker_runtime import (
    APP_PORT_RANGE_1,
    APP_PORT_RANGE_2,
    EXECUTION_SERVER_PORT_RANGE,
    VSCODE_PORT_RANGE,
)
from forge.runtime.plugins.vscode import VSCodeRequirement
from forge.runtime.runtime_status import RuntimeStatus
from forge.runtime.utils import find_available_tcp_port
from forge.runtime.utils.command import get_action_execution_server_startup_command
from forge.utils.async_utils import call_sync_from_async
from forge.utils.tenacity_metrics import (
    call_tenacity_hooks,
    tenacity_before_sleep_factory,
)
from forge.utils.tenacity_stop import stop_if_should_exit

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events import EventStream
    from forge.events.action import Action
    from forge.events.observation import Observation
    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement


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


def _before_sleep_wait_until_alive(retry_state: RetryCallState) -> None:
    """Emit metrics and log retries while waiting for the runtime to become ready."""
    call_tenacity_hooks(
        tenacity_before_sleep_factory("runtime.local.wait_until_alive"),
        None,
        retry_state,
    )
    logger.debug("Waiting for server to be ready... (attempt %s)", getattr(retry_state, "attempt_number", None))


def _before_sleep_warm_wait(retry_state: RetryCallState) -> None:
    """Emit metrics and log retries while warming background servers."""
    call_tenacity_hooks(
        tenacity_before_sleep_factory("runtime.local.warm_wait"),
        None,
        retry_state,
    )
    logger.debug(
        "Waiting for warm server to be ready... (attempt %s)",
        getattr(retry_state, "attempt_number", None),
    )


def get_user_info() -> tuple[int, str | None]:
    """Get user ID and username in a cross-platform way."""
    username = os.getenv("USER") or os.getenv("USERNAME")
    uid_getter = getattr(os, "getuid", None)
    user_id = uid_getter() if callable(uid_getter) else 1000
    return user_id, username


def check_dependencies(code_repo_path: str, check_browser: bool) -> None:
    """Check that required dependencies are installed for local runtime.
    
    Verifies Jupyter, libtmux (non-Windows), and optionally Chromium are available.
    
    Args:
        code_repo_path: Path to code repository
        check_browser: Whether to check for browser dependencies
        
    Raises:
        ValueError: If dependencies are missing or paths invalid

    """
    ERROR_MESSAGE = "Please follow the instructions in https://github.com/All-Hands-AI/Forge/blob/main/Development.md to install forge."
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
        from forge.runtime.browser.browser_env import BrowserEnv

        browser = BrowserEnv()
        browser.close()


class LocalRuntime(ActionExecutionClient):
    """This runtime will run the action_execution_server directly on the local machine.

    When receiving an event, it will send the event to the server via HTTP.

    Args:
        config (ForgeConfig): The application configuration.
        event_stream (EventStream): The event stream to subscribe to.
        sid (str, optional): The session ID. Defaults to 'default'.
        plugins (list[PluginRequirement] | None, optional): list of plugin requirements. Defaults to None.
        env_vars (dict[str, str] | None, optional): Environment variables to set. Defaults to None.

    """

    def __init__(
        self,
        config: ForgeConfig,
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
        """Initialize a local (unsandboxed) runtime for local development and testing.
        
        WARNING: This runtime has NO SANDBOX and runs with the current user privileges.
        It's experimental and not recommended for untrusted code. Use DockerRuntime or 
        RemoteRuntime for production and security-sensitive scenarios.
        
        Initializes server process, port management, and local runtime infrastructure:
        1. Detects Windows platform (limited features due to lack of tmux support)
        2. Logs extensive warnings about sandbox limitations
        3. Sets up temporary workspace, port allocation, and threading infrastructure
        4. Applies startup environment variables to current process
        5. Initializes parent Runtime with full configuration
        
        Args:
            config: Forge configuration with sandbox and runtime settings
            event_stream: Event stream for status updates and logging
            llm_registry: Language model registry for agent operations
            sid: Session identifier for this runtime instance (default "default")
            plugins: List of plugins to install (Jupyter, VSCode, etc.)
            env_vars: Environment variables for runtime startup
            status_callback: Optional callback for runtime status updates
            attach_to_existing: If True, attempt to attach to existing runtime (not supported locally)
            headless_mode: If True, run without browser UI
            user_id: Optional user identifier (ignored; current user always used)
            git_provider_tokens: Git provider authentication tokens
        
        Side Effects:
            - Detects and warns if running on Windows (tmux features unavailable)
            - Initializes subprocess-related attributes (_execution_server_port, _vscode_port, etc.)
            - Sets up threading infrastructure (action_semaphore, _log_thread_exit_event)
            - Applies config.sandbox.runtime_startup_env_vars to os.environ
            - Initializes parent Runtime class with provided configuration
            - Retrieves SESSION_API_KEY from environment if available
        
        Raises:
            (No specific exceptions; parent initialization may raise on invalid config)
        
        Notes:
            - user_id parameter is ignored; current process user always used
            - run_as_Forge configuration is ignored (current user is always used)
            - Windows platform lacks tmux support; full functionality requires WSL or Docker
            - Workspace is created in temp directory (not persistent)
            - Action execution uses semaphore to serialize operations
            - Log thread exit event enables graceful shutdown of logging thread
        
        Example:
            >>> config = ForgeConfig.from_file("config.toml")
            >>> runtime = LocalRuntime(config, event_stream, llm_registry)
            >>> # Warning messages logged about sandbox limitations

        """
        self.is_windows = sys.platform == "win32"
        if self.is_windows:
            logger.warning(
                "Running on Windows - some features that require tmux will be limited. For full functionality, please consider using WSL or Docker runtime.",
            )
        self.config = config
        self._user_id, self._username = get_user_info()
        logger.warning(
            "Initializing LocalRuntime. WARNING: NO SANDBOX IS USED. This is an experimental feature, please report issues to https://github.com/All-Hands-AI/Forge/issues. `run_as_Forge` will be ignored since the current user will be used to launch the server. We highly recommend using a sandbox (eg. DockerRuntime) unless you are running in a controlled environment.\nUser ID: %s. Username: %s.",
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
        """Get session API key for authentication.
        
        Returns:
            Session API key or None

        """
        return self._session_api_key

    @property
    def action_execution_server_url(self) -> str:
        """Get action execution server URL.
        
        Returns:
            Server URL for action execution

        """
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
            self._temp_workspace = tempfile.mkdtemp(prefix=f"FORGE_workspace_{self.sid}")
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
                self._temp_workspace = tempfile.mkdtemp(prefix=f"FORGE_workspace_{self.sid}")
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
    def setup(cls, config: ForgeConfig, headless_mode: bool = False) -> None:
        """Set up local runtime environment.
        
        Checks dependencies and optionally pre-warms server instances.
        
        Args:
            config: Forge configuration
            headless_mode: Whether to run in headless mode

        """
        should_check_dependencies = os.getenv("SKIP_DEPENDENCY_CHECK", "") != "1"
        if should_check_dependencies:
            code_repo_path = os.path.dirname(os.path.dirname(forge.__file__))
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
        before_sleep=_before_sleep_wait_until_alive,
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
        """Get runtime URL for local runtime.
        
        Returns:
            Runtime URL from environment or default

        """
        if runtime_url := os.getenv("RUNTIME_URL"):
            return runtime_url
        runtime_url_pattern = os.getenv("RUNTIME_URL_PATTERN")
        runtime_id = os.getenv("RUNTIME_ID")
        if runtime_url_pattern and runtime_id:
            return runtime_url_pattern.format(runtime_id=runtime_id)
        return self.config.sandbox.local_runtime_url

    def _create_url(self, prefix: str, port: int) -> str:
        """Generate runtime service URL based on runtime URL pattern and prefix.
        
        Creates appropriate URL for runtime services (vscode, web apps) by handling
        two runtime URL patterns:
        1. Localhost pattern: Direct http://localhost:port usage
        2. Remote pattern: URL-based routing with runtime_id path or subdomain prefix
        
        Args:
            prefix: Service prefix for URL construction ('vscode', 'app1', 'app2', etc.)
            port: Port number for service (only used in localhost pattern, ignored otherwise)
        
        Returns:
            Fully formed URL for accessing the service
        
        Notes:
            - Localhost pattern: Returns runtime_url with port appended
            - Remote path pattern (/{runtime_id}/...): Inserts prefix after runtime_id
            - Remote subdomain pattern: Prepends prefix as subdomain
            - Respects existing URL structure from runtime_url
            - Used for VSCode, browser app ports, and other development services
        
        Example:
            >>> runtime.runtime_url = 'http://localhost:8000'
            >>> runtime._create_url('vscode', 8080)
            'http://localhost:8000:8080'
            
            >>> runtime.runtime_url = 'http://api.example.com/rt-123'
            >>> runtime._create_url('vscode', 8080)
            'http://api.example.com/rt-123/vscode'

        """
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
        """Get VS Code server URL with authentication token.
        
        Returns:
            VS Code URL or None if not available

        """
        token = super().get_vscode_token()
        if not token:
            return None
        vscode_url = self._create_url("vscode", self._vscode_port)
        return f"{vscode_url}/?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}"

    @property
    def web_hosts(self) -> dict[str, int]:
        """Get detected web server hosts from runtime.
        
        Returns:
            Dictionary mapping URLs to ports

        """
        hosts: dict[str, int] = {}
        for index, port in enumerate(self._app_ports):
            url = self._create_url(f"work-{index + 1}", port)
            hosts[url] = port
        return hosts


def _python_bin_path():
    """Get the directory containing the current Python interpreter.

    Returns:
        str: Directory path containing python executable (dirname of sys.executable)

    Example:
        >>> path = _python_bin_path()
        >>> os.path.exists(path)
        True
        >>> os.path.isfile(os.path.join(path, "python"))  # Or python.exe on Windows
        True

    """
    interpreter_path = sys.executable
    return os.path.dirname(interpreter_path)


def _create_server(
    config: ForgeConfig,
    plugins: list[PluginRequirement],
    workspace_prefix: str,
) -> tuple[ActionExecutionServerInfo, str]:
    """Create and start a local action execution server process with workspace setup.
    
    Orchestrates the complete server startup:
    1. Creates temporary workspace directory with prefix
    2. Finds available TCP ports for server, VSCode, and app services
    3. Builds startup command with plugins and configuration
    4. Sets up Python environment with repo path and local runtime flag
    5. Spawns server as subprocess with stdout/stderr logging thread
    6. Manages server lifecycle through daemon logging thread
    
    Args:
        config: Forge configuration for server startup
        plugins: List of plugins (Jupyter, VSCode, file_ops, etc.) to enable
        workspace_prefix: Prefix for temporary workspace directory name (e.g., session ID)
    
    Returns:
        Tuple of (ActionExecutionServerInfo, workspace_path):
        - ActionExecutionServerInfo: Contains process, ports, logging thread, and exit event
        - str: Path to temporary workspace directory
    
    Side Effects:
        - Creates temporary directory at tempfile.mkdtemp(prefix=f"FORGE_workspace_{workspace_prefix}")
        - Finds available TCP ports from configured port ranges
        - Spawns subprocess.Popen with inherited environment
        - Starts daemon logging thread to capture server output
        - Modifies environment (PYTHONPATH, FORGE_REPO_PATH, LOCAL_RUNTIME_MODE, etc.)
        - Updates PATH to include Python binary directory
    
    Raises:
        OSError: If port finding fails or subprocess creation fails
        ValueError: If required configuration is invalid
    
        Environment Variables:
            - PYTHONPATH: Prepended with code_repo_path for module resolution
            - FORGE_REPO_PATH: Forge repository root directory
            - LOCAL_RUNTIME_MODE: Set to "1" to indicate local runtime
            - VSCODE_PORT: Port for VSCode server
            - PATH: Updated to include Python binary directory
            - DEBUG: Inherited from parent if set
    
    Notes:
        - Server process spawned with shell=False for security
        - Output buffered line-by-line (bufsize=1) for real-time logging
        - Logging thread is daemon, so process termination doesn't block
        - Log thread exit event allows graceful shutdown
        - Handles both Windows and Unix platforms
        - Typical port ranges: execution server 8001-8010, vscode 3000-3100, apps 7000-8000
        - Workspace remains on disk after runtime closes (for debugging)
    
    Example:
        >>> server_info, workspace = _create_server(config, plugins, "test_session")
        >>> server_info.execution_server_port
        8001
        >>> os.path.exists(workspace)
        True

    """
    logger.info("Creating a server")
    temp_workspace = tempfile.mkdtemp(prefix=f"FORGE_workspace_{workspace_prefix}")
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
    code_repo_path = os.path.dirname(os.path.dirname(forge.__file__))
    env["PYTHONPATH"] = os.pathsep.join([code_repo_path, env.get("PYTHONPATH", "")])
    env["FORGE_REPO_PATH"] = code_repo_path
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
        """Log server process output in background thread."""
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


def _create_warm_server(config: ForgeConfig, plugins: list[PluginRequirement]) -> None:
    """Create a warm server in the background for future use.

    Warm servers are pre-started ActionExecutionServers that are pooled and reused
    for new sessions to avoid startup latency. Runs server creation and initialization
    in a background thread, then adds to the global _WARM_SERVERS pool if successful.

    Args:
        config: ForgeConfig with sandbox settings
        plugins: List of plugin requirements to load in the server

    Side Effects:
        - Spawns background thread that creates server process
        - Adds to _WARM_SERVERS global list on success
        - Logs errors if creation or initialization fails (non-fatal)

    Note:
        Failures are logged but don't propagate; ensures warm server creation
        doesn't block or crash the main application.

    """
    try:
        server_info, api_url = _create_server(config=config, plugins=plugins, workspace_prefix="warm")
        session = httpx.Client(timeout=30)

        @tenacity.retry(
            wait=tenacity.wait_fixed(2),
            stop=tenacity.stop_after_delay(120) | stop_if_should_exit(),
            before_sleep=_before_sleep_warm_wait,
        )
        def wait_until_alive() -> bool:
            """Wait for warm server to become alive and ready.
            
            Returns:
                True if server is alive, raises RuntimeError if process died

            """
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


def _create_warm_server_in_background(config: ForgeConfig, plugins: list[PluginRequirement]) -> None:
    """Start a new thread to create a warm server."""
    thread = threading.Thread(target=_create_warm_server, daemon=True, args=(config, plugins))
    thread.start()


def _get_plugins(config: ForgeConfig) -> list[PluginRequirement]:
    """Retrieve the list of sandbox plugins required by the configured agent class.
    
    Looks up the agent class specified in config.default_agent and returns its
    sandbox_plugins property, which defines which runtime plugins (Jupyter, VSCode, etc.)
    should be installed in the execution environment.
    
    Args:
        config: Forge configuration containing the default_agent class name
    
    Returns:
        List of PluginRequirement instances needed by the agent
    
    Side Effects:
        - Imports Agent and its registry from forge.controller.agent module
        - May trigger lazy loading of agent class implementation
    
    Notes:
        - Each agent class defines its required plugins via sandbox_plugins property
        - Common plugins: Jupyter for notebook execution, VSCode for development
        - Used during runtime initialization to configure environment
        - Allows different agents to have different plugin requirements
    
    Example:
        >>> config = ForgeConfig.from_file("config.toml")
        >>> config.default_agent = "DefaultAgent"
        >>> plugins = _get_plugins(config)
        >>> [p.name for p in plugins]  # doctest: +SKIP
        ['Jupyter', 'VSCode']

    """
    from forge.controller.agent import Agent

    return Agent.get_cls(config.default_agent).sandbox_plugins
