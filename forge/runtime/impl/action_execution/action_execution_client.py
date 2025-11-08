"""Runtime base class that proxies actions to the sandbox action execution server."""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zipfile import ZipFile

import httpcore
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from forge.core.config.mcp_config import (
    MCPConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from forge.core.exceptions import AgentRuntimeTimeoutError
from forge.core.pydantic_compat import model_dump_with_options
from forge.events.action import (
    ActionConfirmationStatus,
    AgentThinkAction,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from forge.events.action.files import FileEditSource
from forge.events.observation import (
    AgentThinkObservation,
    ErrorObservation,
    NullObservation,
    Observation,
    UserRejectObservation,
)
from forge.events.serialization import event_to_dict, observation_from_dict
from forge.events.serialization.action import ACTION_TYPE_TO_CLASS
from forge.runtime.base import Runtime
from forge.runtime.utils.request import send_request
from forge.runtime.utils.system_stats import update_last_execution_time
from forge.utils.http_session import HttpSession
from forge.utils.tenacity_metrics import (
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)
from forge.utils.tenacity_stop import stop_if_should_exit

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events import EventStream
    from forge.events.action.action import Action
    from forge.events.action.mcp import MCPAction
    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement


def _is_retryable_error(exception):
    """Check if an exception is retryable for HTTP requests.

    Args:
        exception: The exception to check.

    Returns:
        bool: True if the exception is retryable, False otherwise.

    """
    return isinstance(exception, (httpx.RemoteProtocolError, httpcore.RemoteProtocolError))


class ActionExecutionClient(Runtime):
    """Base class for runtimes that interact with the action execution server.

    This class contains shared logic between DockerRuntime and RemoteRuntime
    for interacting with the HTTP server defined in action_execution_server.py.
    """

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Any | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
    ) -> None:
        """Initialize HTTP session state before delegating to the runtime base class."""
        self.session = HttpSession()
        self.action_semaphore = threading.Semaphore(1)
        self._runtime_closed: bool = False
        self._vscode_token: str | None = None
        self._last_updated_mcp_stdio_servers: list[MCPStdioServerConfig] = []
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

    @property
    def action_execution_server_url(self) -> str:
        """Get action execution server URL (must be implemented by subclass).
        
        Returns:
            Server URL
            
        Raises:
            NotImplementedError: Must be implemented by subclass

        """
        msg = "Action execution server URL is not implemented"
        raise NotImplementedError(msg)

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(5) | stop_if_should_exit(),
        wait=wait_exponential(multiplier=1, min=4, max=15),
        before_sleep=tenacity_before_sleep_factory("runtime.action_execution.send_request"),
        after=tenacity_after_factory("runtime.action_execution.send_request"),
    )
    def _send_action_server_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Send a request to the action execution server.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to send the request to
            **kwargs: Additional arguments to pass to requests.request()

        Returns:
            Response from the server

        Raises:
            AgentRuntimeError: If the request fails

        """
        return send_request(self.session, method, url, **kwargs)

    def check_if_alive(self) -> None:
        """Check if action execution server is alive and responding.
        
        Raises:
            Exception: If server not responding or unhealthy

        """
        response = self._send_action_server_request("GET", f"{self.action_execution_server_url}/alive", timeout=5)
        assert response.is_closed

    def list_files(self, path: str | None = None) -> list[str]:
        """List files in the sandbox.

        If path is None, list files in the sandbox's initial working directory (e.g., /workspace).
        """
        try:
            data = {}
            if path is not None:
                data["path"] = path
            response = self._send_action_server_request(
                "POST",
                f"{self.action_execution_server_url}/list_files",
                json=data,
                timeout=10,
            )
            assert response.is_closed
            response_json = response.json()
            assert isinstance(response_json, list)
            return response_json
        except httpx.TimeoutException as e:
            msg = "List files operation timed out"
            raise TimeoutError(msg) from e

    def copy_from(self, path: str) -> Path:
        """Zip all files in the sandbox and return as a stream of bytes."""
        try:
            params = {"path": path}
            with self.session.stream(
                "GET",
                f"{self.action_execution_server_url}/download_files",
                params=params,
                timeout=30,
            ) as response:
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
                    for chunk in response.iter_bytes():
                        temp_file.write(chunk)
                    temp_file.flush()
                    return Path(temp_file.name)
        except httpx.TimeoutException as e:
            msg = "Copy operation timed out"
            raise TimeoutError(msg) from e

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False) -> None:
        """Copy file or directory from host to sandbox.

        Args:
            host_src: Source path on host
            sandbox_dest: Destination path in sandbox
            recursive: Whether to copy recursively (zips directory)

        Raises:
            FileNotFoundError: If source doesn't exist

        """
        if not os.path.exists(host_src):
            msg = f"Source file {host_src} does not exist"
            raise FileNotFoundError(msg)

        temp_zip_path = None
        file_to_upload = None

        try:
            if recursive:
                temp_zip_path, file_to_upload = self._prepare_recursive_copy(host_src)
            else:
                file_to_upload = open(host_src, "rb")

            self._upload_file_to_sandbox(file_to_upload, sandbox_dest, recursive, host_src)
        finally:
            self._cleanup_copy_resources(file_to_upload, temp_zip_path)

    def _prepare_recursive_copy(self, host_src: str) -> tuple[str, object]:
        """Prepare recursive directory copy by creating zip.

        Args:
            host_src: Source directory path

        Returns:
            Tuple of (temp_zip_path, file_handle)

        Raises:
            Exception: If zip creation fails

        """
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            temp_zip_path = temp_zip.name

        try:
            with ZipFile(temp_zip_path, "w") as zipf:
                for root, _, files in os.walk(host_src):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(host_src))
                        zipf.write(file_path, arcname)

            self.log("debug", f"Opening temporary zip file for upload: {temp_zip_path}")
            return temp_zip_path, open(temp_zip_path, "rb")
        except Exception:
            if temp_zip_path and os.path.exists(temp_zip_path):
                os.unlink(temp_zip_path)
            raise

    def _upload_file_to_sandbox(self, file_handle, sandbox_dest: str, recursive: bool, host_src: str) -> None:
        """Upload file to sandbox via API.

        Args:
            file_handle: File handle to upload
            sandbox_dest: Destination path
            recursive: Whether recursive copy
            host_src: Original source path

        """
        params = {"destination": sandbox_dest, "recursive": str(recursive).lower()}
        upload_data = {"file": file_handle}

        response = self._send_action_server_request(
            "POST",
            f"{self.action_execution_server_url}/upload_file",
            files=upload_data,
            params=params,
            timeout=300,
        )

        self.log("debug", f"Copy completed: host:{host_src} -> runtime:{sandbox_dest}. Response: {response.text}")

    def _cleanup_copy_resources(self, file_to_upload, temp_zip_path: str | None) -> None:
        """Cleanup resources after copy operation.

        Args:
            file_to_upload: File handle to close
            temp_zip_path: Temporary zip file path to delete

        """
        if file_to_upload:
            file_to_upload.close()

        if temp_zip_path and os.path.exists(temp_zip_path):
            try:
                os.unlink(temp_zip_path)
            except Exception as e:
                self.log("error", f"Failed to delete temporary zip file {temp_zip_path}: {e}")

    def get_vscode_token(self) -> str:
        """Get VS Code authentication token from server.
        
        Returns:
            VS Code token or empty string if not available

        """
        if not self._vscode_enabled or not self.runtime_initialized:
            return ""
        if self._vscode_token is not None:
            return self._vscode_token
        response = self._send_action_server_request(
            "GET",
            f"{self.action_execution_server_url}/vscode/connection_token",
            timeout=10,
        )
        response_json = response.json()
        assert isinstance(response_json, dict)
        if response_json["token"] is None:
            return ""
        self._vscode_token = response_json["token"]
        return response_json["token"]

    def _validate_action_timeout(self, action: Action) -> None:
        """Validate and set action timeout if not set."""
        if action.timeout is None:
            if isinstance(action, CmdRunAction) and action.blocking:
                msg = "Blocking command with no timeout set"
                raise RuntimeError(msg)
            action.set_hard_timeout(self.config.sandbox.timeout, blocking=False)

    def _check_action_runnable(self, action: Action) -> Observation | None:
        """Check if action is runnable, return observation if not."""
        if not action.runnable:
            if isinstance(action, AgentThinkAction):
                return AgentThinkObservation("Your thought has been logged.")
            return NullObservation("")

        if (
            hasattr(action, "confirmation_state")
            and action.confirmation_state == ActionConfirmationStatus.AWAITING_CONFIRMATION
        ):
            return NullObservation("")

        if getattr(action, "confirmation_state", None) == ActionConfirmationStatus.REJECTED:
            return UserRejectObservation("Action has been rejected by the user! Waiting for further user input.")

        return None

    def _validate_action_type(self, action: Action) -> None:
        """Validate that action type is supported."""
        action_type = action.action
        if action_type not in ACTION_TYPE_TO_CLASS:
            msg = f"Action {action_type} does not exist."
            raise ValueError(msg)
        
        # Agent-level actions that should not be executed by runtime
        agent_level_actions = {
            "change_agent_state",
            "message", 
            "recall",
            "think",
            "finish",
            "reject",
            "delegate",
            "condensation",
            "condensation_request",
            "task_tracking",
            "system"
        }
        
        if action_type in agent_level_actions:
            # These actions are handled by the agent system, not the runtime
            return
            
        if not hasattr(self, action_type):
            msg = f"Action {action_type} is not supported in the current runtime."
            raise ValueError(msg)

    def _execute_action_on_server(self, action: Action) -> Observation:
        """Execute action on the action execution server."""
        execution_action_body: dict[str, Any] = {"action": event_to_dict(action)}
        response = self._send_action_server_request(
            "POST",
            f"{self.action_execution_server_url}/execute_action",
            json=execution_action_body,
            timeout=action.timeout + 5,
        )
        assert response.is_closed
        output = response.json()
        if getattr(action, "hidden", False):
            output.get("extras")["hidden"] = True
        obs = observation_from_dict(output)
        obs._cause = action.id
        return obs

    def send_action_for_execution(self, action: Action) -> Observation:
        """Send action to execution server and return observation.
        
        Args:
            action: Action to execute
            
        Returns:
            Observation with execution results

        """
        if isinstance(action, FileEditAction) and action.impl_source == FileEditSource.LLM_BASED_EDIT:
            return self.llm_based_edit(action)

        self._validate_action_timeout(action)

        with self.action_semaphore:
            # Check if action can run
            early_return = self._check_action_runnable(action)
            if early_return is not None:
                return early_return

            # Validate action type
            try:
                self._validate_action_type(action)
            except ValueError as e:
                return ErrorObservation(str(e), error_id="AGENT_ERROR$BAD_ACTION")

            # Execute action
            assert action.timeout is not None
            try:
                return self._execute_action_on_server(action)
            except httpx.TimeoutException as e:
                msg = f"Runtime failed to return execute_action before the requested timeout of {action.timeout}s"
                raise AgentRuntimeTimeoutError(
                    msg,
                ) from e
            finally:
                update_last_execution_time()

    def run(self, action: CmdRunAction) -> Observation:
        """Execute bash/shell command via action execution server."""
        return self.send_action_for_execution(action)

    def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        """Execute Python code in IPython via action execution server."""
        return self.send_action_for_execution(action)

    def read(self, action: FileReadAction) -> Observation:
        """Read file via action execution server."""
        return self.send_action_for_execution(action)

    def write(self, action: FileWriteAction) -> Observation:
        """Write file via action execution server."""
        return self.send_action_for_execution(action)

    def edit(self, action: FileEditAction) -> Observation:
        """Execute file edit via action execution server."""
        return self.send_action_for_execution(action)

    def browse(self, action: BrowseURLAction) -> Observation:
        """Browse URL via action execution server."""
        return self.send_action_for_execution(action)

    def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        """Execute interactive browser command via action execution server."""
        return self.send_action_for_execution(action)

    def get_mcp_config(self, extra_stdio_servers: list[MCPStdioServerConfig] | None = None) -> MCPConfig:
        """Get MCP configuration with optional extra stdio servers.

        Args:
            extra_stdio_servers: Additional stdio servers to include

        Returns:
            MCPConfig with updated server list

        """
        import sys

        if sys.platform == "win32":
            self.log("debug", "MCP is disabled on Windows, returning empty config")
            return MCPConfig(sse_servers=[], stdio_servers=[])

        updated_mcp_config = self.config.mcp.model_copy()
        current_stdio_servers = self._merge_stdio_servers(updated_mcp_config.stdio_servers, extra_stdio_servers)
        new_servers = self._identify_new_servers(current_stdio_servers)

        if new_servers:
            self._update_mcp_servers(new_servers, current_stdio_servers)
        else:
            self.log("debug", "No new stdio servers to update")

        if len(self._last_updated_mcp_stdio_servers) > 0:
            updated_mcp_config.sse_servers.append(
                MCPSSEServerConfig(
                    url=self.action_execution_server_url.rstrip("/") + "/mcp/sse",
                    api_key=self.session_api_key,
                ),
            )

        return updated_mcp_config

    def _merge_stdio_servers(self, base_servers: list, extra_servers: list | None) -> list[MCPStdioServerConfig]:
        """Merge base and extra stdio servers.

        Args:
            base_servers: Base server list
            extra_servers: Extra servers to add

        Returns:
            Merged server list

        """
        current = list(base_servers)
        if extra_servers:
            current.extend(extra_servers)
        return current

    def _identify_new_servers(self, current_servers: list[MCPStdioServerConfig]) -> list[MCPStdioServerConfig]:
        """Identify new servers not in last update.

        Args:
            current_servers: Current server list

        Returns:
            List of new servers

        """
        new_servers = [s for s in current_servers if s not in self._last_updated_mcp_stdio_servers]
        self.log("debug", f"adding {len(new_servers)} new stdio servers to MCP config: {new_servers}")
        return new_servers

    def _update_mcp_servers(self, new_servers: list, current_servers: list) -> None:
        """Update MCP servers via API.

        Args:
            new_servers: New servers to add
            current_servers: All current servers

        """
        combined_servers = current_servers.copy()
        for server in self._last_updated_mcp_stdio_servers:
            if server not in combined_servers:
                combined_servers.append(server)

        stdio_tools = [model_dump_with_options(server, mode="json") for server in combined_servers]
        stdio_tools.sort(key=lambda x: x.get("name", ""))

        self.log(
            "debug", f"Updating MCP server with {len(new_servers)} new stdio servers (total: {len(combined_servers)})",
        )

        response = self._send_action_server_request(
            "POST",
            f"{self.action_execution_server_url}/update_mcp_server",
            json=stdio_tools,
            timeout=60,
        )

        self._handle_update_response(response, combined_servers)

    def _handle_update_response(self, response, combined_servers: list) -> None:
        """Handle MCP server update response.

        Args:
            response: HTTP response from update request
            combined_servers: Combined server list

        """
        result = response.json()

        if response.status_code != 200:
            self.log("warning", f"Failed to update MCP server: {response.text}")
        else:
            if result.get("router_error_log"):
                self.log("warning", f"Some MCP servers failed to be added: {result['router_error_log']}")

            self._last_updated_mcp_stdio_servers = combined_servers.copy()
            self.log("debug", f"Successfully updated MCP stdio servers, now tracking {len(combined_servers)} servers")

        self.log("info", f"Updated MCP config: {self.config.mcp.sse_servers}")

    async def call_tool_mcp(self, action: MCPAction) -> Observation:
        """Call MCP tool via action execution server.
        
        Args:
            action: MCP action to execute
            
        Returns:
            Observation from MCP tool execution

        """
        import sys

        from forge.events.observation import ErrorObservation

        if sys.platform == "win32":
            self.log("info", "MCP functionality is disabled on Windows")
            return ErrorObservation("MCP functionality is not available on Windows")
        from forge.mcp_client.utils import call_tool_mcp as call_tool_mcp_handler
        from forge.mcp_client.utils import create_mcp_clients

        updated_mcp_config = self.get_mcp_config()
        self.log("debug", f"Creating MCP clients with servers: {updated_mcp_config.sse_servers}")
        mcp_clients = await create_mcp_clients(
            updated_mcp_config.sse_servers,
            updated_mcp_config.shttp_servers,
            self.sid,
        )
        return await call_tool_mcp_handler(mcp_clients, action)

    def close(self) -> None:
        """Close action execution client and clean up resources."""
        if self._runtime_closed:
            return
        self._runtime_closed = True
        self.session.close()
