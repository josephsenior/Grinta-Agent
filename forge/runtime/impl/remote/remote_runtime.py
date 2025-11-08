"""Remote runtime implementation that orchestrates cloud-hosted sandboxes."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any, Callable, cast
from urllib.parse import urlparse

import httpx
import tenacity
from tenacity import RetryCallState

from forge.core.exceptions import (
    AgentRuntimeDisconnectedError,
    AgentRuntimeError,
    AgentRuntimeNotFoundError,
    AgentRuntimeNotReadyError,
    AgentRuntimeUnavailableError,
)
from forge.core.logger import forge_logger as logger
from forge.runtime.builder.remote import RemoteRuntimeBuilder
from forge.runtime.impl.action_execution.action_execution_client import (
    ActionExecutionClient,
)
from forge.runtime.runtime_status import RuntimeStatus
from forge.runtime.utils.command import (
    DEFAULT_MAIN_MODULE,
    get_action_execution_server_startup_command,
)
from forge.runtime.utils.request import send_request
from forge.runtime.utils.runtime_build import build_runtime_image
from forge.utils.async_utils import call_sync_from_async
from forge.utils.tenacity_metrics import (
    call_tenacity_hooks,
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)
from forge.utils.tenacity_stop import stop_if_should_exit

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events import EventStream
    from forge.integrations.provider import PROVIDER_TOKEN_TYPE
    from forge.llm.llm_registry import LLMRegistry
    from forge.runtime.plugins import PluginRequirement


def _before_sleep_action_request(retry_state: RetryCallState) -> None:
    """Emit retry metrics and warnings for remote action requests."""
    call_tenacity_hooks(
        tenacity_before_sleep_factory("runtime.remote.action_request"),
        None,
        retry_state,
    )
    tenacity.before_sleep_log(logger, logging.WARNING)(retry_state)


def _compose_stop_conditions(
    *conditions: Callable[[RetryCallState], bool],
) -> Callable[[RetryCallState], bool]:
    """Combine multiple tenacity stop predicates into a single callable."""

    def _composed(retry_state: RetryCallState) -> bool:
        return any(condition(retry_state) for condition in conditions)

    return _composed


class RemoteRuntime(ActionExecutionClient):
    """This runtime will connect to a remote oh-runtime-client."""

    port: int = 60000
    runtime_id: str | None = None
    runtime_url: str | None = None
    _runtime_initialized: bool = False
    runtime_builder: RemoteRuntimeBuilder
    container_image: str
    available_hosts: dict[str, int]
    main_module: str

    def __init__(
        self,
        config: ForgeConfig,
        event_stream: EventStream,
        llm_registry: LLMRegistry,
        sid: str = "default",
        plugins: list[PluginRequirement] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Callable[..., None] | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = True,
        user_id: str | None = None,
        git_provider_tokens: PROVIDER_TOKEN_TYPE | None = None,
        main_module: str = DEFAULT_MAIN_MODULE,
    ) -> None:
        """Initialize a remote runtime that connects to a cloud sandbox environment.
        
        Sets up credentials, validates configuration, and initializes the RemoteRuntimeBuilder
        for container orchestration on remote infrastructure. Requires API key for authentication
        and validates that remote runtime API URL is properly configured.
        
        Args:
            config: Forge configuration object containing sandbox settings, API keys, and runtime URL.
            event_stream: Event stream for logging and runtime status updates.
            llm_registry: Registry of language models for agent operations.
            sid: Session ID for this runtime instance (default "default"). Used to identify and reattach to existing runtimes.
            plugins: List of plugin requirements to install in the runtime (e.g., Jupyter, VSCode).
            env_vars: Environment variables to pass to the runtime startup.
            status_callback: Optional callback function for runtime status updates.
            attach_to_existing: If True, attempt to attach to existing runtime with same sid; if not found, raise error.
            headless_mode: If True, run in headless mode without browser UI.
            user_id: Optional user identifier for tracking and multi-user scenarios.
            git_provider_tokens: Git provider authentication tokens for SCM integration.
            main_module: Module name for action execution server (default DEFAULT_MAIN_MODULE).
        
        Raises:
            ValueError: If API key is None, remote_runtime_api_url is None, or invalid remote_runtime_class.
        
        Side Effects:
            - Initializes parent Runtime class with configuration
            - Creates RemoteRuntimeBuilder for image building and deployment
            - Sets up HTTP session headers with API key for authentication
            - Logs warnings if workspace_base is set (not supported in remote runtime)
            - Initializes empty host availability dict and session API key
        
        Notes:
            - Requires config.sandbox.api_key set via config.toml or SANDBOX_API_KEY env var
            - Remote runtime class must be None, "sysbox", or "gvisor" for container isolation
            - API URL typically points to orchestration service (e.g., Sandbox runtime API)
            - Host availability tracking enables load balancing across available resources
            - Session API key allows per-session authentication after initial setup
        
        Example:
            >>> config = ForgeConfig.from_file("config.toml")
            >>> runtime = RemoteRuntime(config, event_stream, llm_registry, sid="session1")
            >>> # Runtime will validate API credentials before initialization

        """
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
        logger.debug("RemoteRuntime.init user_id %s", user_id)
        if self.config.sandbox.api_key is None:
            msg = "API key is required to use the remote runtime. Please set the API key in the config (config.toml) or as an environment variable (SANDBOX_API_KEY)."
            raise ValueError(
                msg,
            )
        self.session.headers.update({"X-API-Key": self.config.sandbox.api_key})
        if self.config.workspace_base is not None:
            self.log("debug", "Setting workspace_base is not supported in the remote runtime.")
        if self.config.sandbox.remote_runtime_api_url is None:
            msg = "remote_runtime_api_url is required in the remote runtime."
            raise ValueError(msg)
        assert self.config.sandbox.remote_runtime_class in (None, "sysbox", "gvisor")
        self.main_module = main_module
        self.runtime_builder = RemoteRuntimeBuilder(
            self.config.sandbox.remote_runtime_api_url,
            self.config.sandbox.api_key,
            self.session,
        )
        self.available_hosts: dict[str, int] = {}
        self._session_api_key: str | None = None

    def log(self, level: str, message: str, exc_info: bool | None = None) -> None:
        """Log message with runtime context.
        
        Args:
            level: Log level
            message: Message to log
            exc_info: Whether to include exception info

        """
        getattr(logger, level)(
            message,
            stacklevel=2,
            exc_info=exc_info,
            extra={"session_id": self.sid, "runtime_id": self.runtime_id},
        )

    @property
    def action_execution_server_url(self) -> str:
        """Get action execution server URL.
        
        Returns:
            Server URL for action execution
            
        Raises:
            RuntimeError: If runtime URL not initialized

        """
        if self.runtime_url is None:
            msg = "Runtime URL is not initialized"
            raise NotImplementedError(msg)
        return self.runtime_url

    async def connect(self) -> None:
        """Connect to remote runtime environment.
        
        Starts or attaches to runtime and waits until ready.
        """
        try:
            await call_sync_from_async(self._start_or_attach_to_runtime)
        except Exception:
            self.close()
            self.log("error", "Runtime failed to start", exc_info=True)
            raise
        await call_sync_from_async(self.setup_initial_env)
        self._runtime_initialized = True

    def _start_or_attach_to_runtime(self) -> None:
        """Start a new remote runtime or attach to an existing one based on session ID.

        Implements the core orchestration logic:
        - Checks if runtime already exists for this session
        - If not found and attach_to_existing=True, raises error
        - Otherwise builds/starts new runtime as needed
        - Waits until runtime is alive and ready

        Args:
            None

        Returns:
            None

        Side Effects:
            - Sets self.runtime_id, self.runtime_url, self.container_image
            - Calls _build_runtime() or _start_runtime() to initialize
            - Calls _wait_until_alive() to block until runtime ready
            - Updates runtime status to READY

        Raises:
            AgentRuntimeNotFoundError: If attach_to_existing=True and no runtime found
            ValueError: If API response invalid or missing required fields

        Notes:
            - Core entry point for remote runtime setup
            - Handles state transitions: check -> build/start -> wait -> ready
            - Logs extensively for debugging connection issues

        """
        self.log("info", "Starting or attaching to runtime")
        if self._check_existing_runtime():
            self.log("info", f"Using existing runtime with ID: {self.runtime_id}")
        elif self.attach_to_existing:
            self.log("info", f"Failed to find existing runtime for SID: {self.sid}")
            msg = f"Could not find existing runtime for SID: {self.sid}"
            raise AgentRuntimeNotFoundError(msg)
        else:
            self.log("info", "No existing runtime found, starting a new one")
            if self.config.sandbox.runtime_container_image is None:
                self.log("info", f"Building remote runtime with base image: {self.config.sandbox.base_container_image}")
                self._build_runtime()
            else:
                self.log("info", f"Starting remote runtime with image: {self.config.sandbox.runtime_container_image}")
                self.container_image = self.config.sandbox.runtime_container_image
            self._start_runtime()
        assert self.runtime_id is not None, "Runtime ID is not set. This should never happen."
        assert self.runtime_url is not None, "Runtime URL is not set. This should never happen."
        if not self.attach_to_existing:
            self.log("info", "Waiting for runtime to be alive...")
        self._wait_until_alive()
        if not self.attach_to_existing:
            self.log("info", "Runtime is ready.")
        self.set_runtime_status(RuntimeStatus.READY)

    def _check_existing_runtime(self) -> bool:
        """Check if a runtime already exists for the current session ID.

        Queries the remote runtime API for existing runtime matching self.sid.
        If found, attempts to resume if paused.

        Args:
            None

        Returns:
            bool: True if runtime exists and is/can be running, False otherwise

        Side Effects:
            - Calls _parse_runtime_response() to populate self.runtime_id, self.runtime_url
            - Calls _resume_runtime() if runtime is paused
            - Logs status checks and state transitions

        Raises:
            httpx.HTTPError: If API request fails (except 404)
            json.JSONDecodeError: If API response is invalid JSON

        Notes:
            - Returns False for stopped runtimes (will be rebuilt)
            - Handles paused state by attempting resume
            - Part of attach_to_existing logic for session continuation

        Example:
            >>> found = runtime._check_existing_runtime()
            >>> if found:
            ...     print(f"Using runtime {runtime.runtime_id}")

        """
        self.log("info", f"Checking for existing runtime with session ID: {self.sid}")
        try:
            response = self._send_runtime_api_request(
                "GET",
                f"{self.config.sandbox.remote_runtime_api_url}/sessions/{self.sid}",
            )
            data = response.json()
            status = data.get("status")
            self.log("info", f"Found runtime with status: {status}")
            if status in ["running", "paused"]:
                self._parse_runtime_response(response)
        except httpx.HTTPError as e:
            error_response = getattr(e, "response", None)
            if error_response is not None and error_response.status_code == 404:
                self.log("info", f"No existing runtime found for session ID: {self.sid}")
                return False
            self.log("error", f"Error while looking for remote runtime: {e}")
            raise
        except json.decoder.JSONDecodeError as e:
            self.log(
                "error",
                f"Invalid JSON response from runtime API: {e}. URL: {
                    self.config.sandbox.remote_runtime_api_url}/sessions/{
                    self.sid}. Response: {response}",
            )
            raise
        if status == "running":
            self.log("info", "Found existing runtime in running state")
            return True
        if status == "stopped":
            self.log("info", "Found existing runtime, but it is stopped")
            return False
        if status == "paused":
            self.log("info", "Found existing runtime in paused state, attempting to resume")
            try:
                self._resume_runtime()
                self.log("info", "Successfully resumed paused runtime")
                return True
            except Exception as e:
                self.log("error", f"Failed to resume paused runtime: {e}", exc_info=True)
                return False
        else:
            self.log("error", f"Invalid response from runtime API: {data}")
            return False

    def _build_runtime(self) -> None:
        """Build the remote container image for the runtime environment.
        
        Orchestrates the container image building process:
        1. Retrieves registry prefix from remote API for image naming
        2. Sets environment variable for runtime image repository
        3. Validates base_container_image configuration
        4. Builds image using build_runtime_image() with extra deps
        5. Verifies built image exists in registry before returning
        
        Side Effects:
            - Sets runtime status to BUILDING_RUNTIME during operation
            - Updates OS environment variable OH_RUNTIME_RUNTIME_IMAGE_REPO
            - Stores container_image name in self.container_image
            - Sets status to ERROR on failure to prevent getting stuck
        
        Raises:
            ValueError: If base_container_image is not configured
            AgentRuntimeError: If built image doesn't exist in registry
            httpx.HTTPError: If API calls to registry fail
        
        Notes:
            - Image building can take several minutes depending on size and deps
            - Extra dependencies are installed from config.sandbox.runtime_extra_deps
            - Platform specification allows cross-platform builds (e.g., linux/amd64)
            - Force rebuild available via config.sandbox.force_rebuild_runtime
            - Browser support configured via config.enable_browser
        
        Example:
            >>> runtime._build_runtime()  # doctest: +SKIP
            >>> runtime.container_image
            'registry.example.com/runtime:sha256abcd1234'

        """
        try:
            self.log("debug", f"Building RemoteRuntime config:\n{self.config}")
            self.set_runtime_status(RuntimeStatus.BUILDING_RUNTIME)
            logger.info("Starting to build remote runtime container image...")
            
            response = self._send_runtime_api_request(
                "GET",
                f"{self.config.sandbox.remote_runtime_api_url}/registry_prefix",
            )
            response_json = response.json()
            registry_prefix = response_json["registry_prefix"]
            os.environ["OH_RUNTIME_RUNTIME_IMAGE_REPO"] = registry_prefix.rstrip("/") + "/runtime"
            self.log("debug", f"Runtime image repo: {os.environ['OH_RUNTIME_RUNTIME_IMAGE_REPO']}")
            if self.config.sandbox.base_container_image is None:
                msg = "base_container_image is required to build the runtime image. "
                raise ValueError(msg)
            if self.config.sandbox.runtime_extra_deps:
                self.log(
                    "debug",
                    f"Installing extra user-provided dependencies in the runtime image: {self.config.sandbox.runtime_extra_deps}",
                )
            self.container_image = build_runtime_image(
                self.config.sandbox.base_container_image,
                self.runtime_builder,
                platform=self.config.sandbox.platform,
                extra_deps=self.config.sandbox.runtime_extra_deps,
                force_rebuild=self.config.sandbox.force_rebuild_runtime,
                enable_browser=self.config.enable_browser,
            )
            response = self._send_runtime_api_request(
                "GET",
                f"{self.config.sandbox.remote_runtime_api_url}/image_exists",
                params={"image": self.container_image},
            )
            if not response.json()["exists"]:
                msg = f"Container image {self.container_image} does not exist"
                raise AgentRuntimeError(msg)
                
            logger.info("Successfully built remote runtime container image: %s", self.container_image)
            
        except Exception as e:
            logger.error("Failed to build remote runtime container image: %s", e)
            # Set status to ERROR to prevent getting stuck in BUILDING_RUNTIME
            self.set_runtime_status(RuntimeStatus.ERROR)
            # Re-raise the exception to let the caller handle it appropriately
            raise

    def _start_runtime(self) -> None:
        """Send start request to remote runtime API and parse response.
        
        Prepares and sends container start request to remote orchestration service:
        1. Sets runtime status to STARTING_RUNTIME
        2. Builds action execution server startup command
        3. Assembles start request with image, command, environment, and resources
        4. Adds runtime_class (sysbox/gvisor) if specified for container isolation
        5. Sends POST request to /start endpoint
        6. Parses response to extract runtime_id, runtime_url, and available hosts
        
        Side Effects:
            - Sets runtime status to STARTING_RUNTIME
            - Populates self.runtime_id from API response
            - Populates self.runtime_url from API response
            - Updates self.available_hosts with work_hosts from response
            - Merges session API key into request headers if provided
        
        Raises:
            httpx.HTTPError: If POST /start request fails
            AgentRuntimeUnavailableError: On HTTP errors
            KeyError: If response JSON missing expected fields
        
        Notes:
            - Environment includes DEBUG flag if config.debug or DEBUG env var set
            - Resource factor affects container resource limits (CPU/memory)
            - sysbox runtime provides stronger container isolation than gvisor
            - Session ID allows resuming this specific runtime later
            - Working directory defaults to /workspace in container
        
        Example:
            >>> runtime._start_runtime()  # doctest: +SKIP
            >>> runtime.runtime_id  # Now set with response value
            'runtime-abc123xyz'

        """
        self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)
        command = self.get_action_execution_server_startup_command()
        environment: dict[str, str] = {}
        if self.config.debug or os.environ.get("DEBUG", "false").lower() == "true":
            environment["DEBUG"] = "true"
        environment |= self.config.sandbox.runtime_startup_env_vars
        start_request: dict[str, Any] = {
            "image": self.container_image,
            "command": command,
            "working_dir": "/workspace",
            "environment": environment,
            "session_id": self.sid,
            "resource_factor": self.config.sandbox.remote_runtime_resource_factor,
        }
        if self.config.sandbox.remote_runtime_class == "sysbox":
            start_request["runtime_class"] = "sysbox-runc"
        try:
            response = self._send_runtime_api_request(
                "POST",
                f"{self.config.sandbox.remote_runtime_api_url}/start",
                json=start_request,
            )
            self._parse_runtime_response(response)
            self.log("debug", f"Runtime started. URL: {self.runtime_url}")
        except httpx.HTTPError as e:
            self.log("error", f"Unable to start runtime: {e!s}")
            raise AgentRuntimeUnavailableError from e

    def _resume_runtime(self) -> None:
        """Resume a stopped runtime.

        Steps:
        1. Show status update that runtime is being started.
        2. Send the runtime API a /resume request
        3. Poll for the runtime to be ready
        4. Update env vars
        """
        self.log("info", f"Attempting to resume runtime with ID: {self.runtime_id}")
        self.set_runtime_status(RuntimeStatus.STARTING_RUNTIME)
        try:
            response = self._send_runtime_api_request(
                "POST",
                f"{self.config.sandbox.remote_runtime_api_url}/resume",
                json={"runtime_id": self.runtime_id},
            )
            self.log("info", f"Resume API call successful with status code: {response.status_code}")
        except Exception as e:
            self.log("error", f"Failed to call /resume API: {e}", exc_info=True)
            raise
        self.log("info", "Runtime resume API call completed, waiting for it to be alive...")
        try:
            self._wait_until_alive()
            self.log("info", "Runtime is now alive after resume")
        except Exception as e:
            self.log("error", f"Runtime failed to become alive after resume: {e}", exc_info=True)
            raise
        try:
            self.setup_initial_env()
            self.log("info", "Successfully set up initial environment after resume")
        except Exception as e:
            self.log("error", f"Failed to set up initial environment after resume: {e}", exc_info=True)
            raise
        self.log("info", "Runtime successfully resumed and alive.")

    def _parse_runtime_response(self, response: httpx.Response) -> None:
        """Parse runtime API response and extract runtime identifiers and configuration.
        
        Extracts and stores runtime identifiers from successful start/resume API responses:
        - runtime_id: Unique identifier for this runtime instance
        - url: HTTP endpoint for connecting to the runtime
        - work_hosts: Dictionary of detected web server hosts and their ports
        - session_api_key: Optional per-session authentication token
        
        Args:
            response: HTTPX Response object from /start or /resume endpoint
        
        Side Effects:
            - Sets self.runtime_id from response['runtime_id']
            - Sets self.runtime_url from response['url']
            - Sets self.available_hosts from response.get('work_hosts', {})
            - Updates HTTP session headers with session API key if present
            - Stores session_api_key in self._session_api_key for later retrieval
            - Logs debug message when session API key is configured
        
        Raises:
            KeyError: If required fields (runtime_id, url) missing from response
            json.JSONDecodeError: If response body is not valid JSON
        
        Notes:
            - work_hosts defaults to empty dict if not provided in response
            - session_api_key provides session-specific authentication (more restricted than API key)
            - These values are typically set once per runtime lifecycle
            - Called after successful /start or /resume API calls
        
        Example:
            >>> response_data = {'runtime_id': 'rt-123', 'url': 'http://localhost:8080', 'work_hosts': {}}
            >>> runtime._parse_runtime_response(response)  # doctest: +SKIP
            >>> runtime.runtime_id
            'rt-123'

        """
        start_response = response.json()
        self.runtime_id = start_response["runtime_id"]
        self.runtime_url = start_response["url"]
        self.available_hosts = start_response.get("work_hosts", {})
        if "session_api_key" in start_response:
            self.session.headers.update({"X-Session-API-Key": start_response["session_api_key"]})
            self._session_api_key = start_response["session_api_key"]
            self.log("debug", "Session API key set")

    @property
    def session_api_key(self) -> str | None:
        """Get session API key for authentication.
        
        Returns:
            Session API key or None

        """
        return self._session_api_key

    @property
    def vscode_url(self) -> str | None:
        """Get VS Code server URL with authentication token.
        
        Returns:
            VS Code URL or None if not available

        """
        token = super().get_vscode_token()
        if not token:
            return None
        assert self.runtime_url is not None
        assert self.runtime_id is not None
        self.log("debug", f"runtime_url: {self.runtime_url}")
        parsed = urlparse(self.runtime_url)
        scheme, netloc, path = (parsed.scheme, parsed.netloc, parsed.path or "/")
        if path.startswith(f"/{self.runtime_id}"):
            vscode_url = f"{scheme}://{netloc}/{self.runtime_id}/vscode?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}"
        else:
            vscode_url = f"{scheme}://vscode-{netloc}/?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}"
        self.log("debug", f"VSCode URL: {vscode_url}")
        return vscode_url

    @property
    def web_hosts(self) -> dict[str, int]:
        """Get detected web server hosts from runtime.
        
        Returns:
            Dictionary mapping URLs to ports

        """
        return self.available_hosts

    def _wait_until_alive(self) -> None:
        """Retry polling until the remote runtime pod reaches ready state.
        
        Sets up a tenacity retry decorator with configurable timeout and polling interval.
        Delegates actual polling logic to _wait_until_alive_impl(), which is wrapped
        with automatic retry on AgentRuntimeNotReadyError exceptions.
        
        Retry Configuration:
        - Polling interval: 2 seconds between checks
        - Timeout: config.sandbox.remote_runtime_init_timeout
        - Max retries: Until timeout or pod becomes ready
        - Stop conditions: Timeout, exit signal, or _runtime_closed flag
        - Exception handling: Reraises final exception on timeout
        
        Side Effects:
            - Calls _wait_until_alive_impl() multiple times until success
            - Logs before_sleep and after messages for each retry via tenacity callbacks
            - Stops retrying immediately if close() is called (_runtime_closed=True)
            - Stops retrying if application shutdown signal received
        
        Raises:
            AgentRuntimeNotReadyError: If pod doesn't reach ready state before timeout
            AgentRuntimeUnavailableError: If pod status indicates permanent failure
        
        Notes:
            - Uses exponential jitter to avoid thundering herd in multi-instance scenarios
            - Typical initialization timeout: 5-10 minutes for container startup
            - Polling queries /runtime/{runtime_id} endpoint for pod status
            - Can be interrupted by close() or application shutdown
            - Part of the runtime startup orchestration sequence
        
        Example:
            >>> runtime._wait_until_alive()  # doctest: +SKIP
            >>> # Pod is now in 'ready' state and runtime is responsive

        """
        stop_conditions = _compose_stop_conditions(
            tenacity.stop_after_delay(self.config.sandbox.remote_runtime_init_timeout),
            stop_if_should_exit(),
            self._stop_if_closed,
        )
        retry_decorator = tenacity.retry(
            stop=cast(Any, stop_conditions),
            reraise=True,
            retry=tenacity.retry_if_exception_type(AgentRuntimeNotReadyError),
            wait=tenacity.wait_fixed(2),
            before_sleep=tenacity_before_sleep_factory("runtime.remote.wait_until_alive"),
            after=tenacity_after_factory("runtime.remote.wait_until_alive"),
        )
        retry_decorator(self._wait_until_alive_impl)()

    def _wait_until_alive_impl(self) -> None:
        """Poll remote runtime API to check pod status and verify readiness.
        
        Executes a single polling iteration that:
        1. Queries /runtime/{runtime_id} endpoint for current pod status
        2. Validates response contains expected runtime metadata
        3. Checks pod status (ready, pending, failed, etc.)
        4. Logs pod restart count and restart reasons if any
        5. Calls check_if_alive() to verify runtime is responsive (for ready status)
        6. Raises AgentRuntimeNotReadyError if pod not ready (triggers retry)
        7. Raises AgentRuntimeUnavailableError if pod failed permanently
        
        Side Effects:
            - Queries runtime API endpoint for status updates
            - Logs debug messages about pod status and restarts
            - Calls parent check_if_alive() method for responsive runtime checks
        
        Raises:
            AgentRuntimeNotReadyError: If pod status is 'pending' or unknown (triggers retry)
            AgentRuntimeUnavailableError: If pod status indicates failure (stops retries)
            AssertionError: If response missing required fields
            httpx.HTTPError: If API query fails
        
        Notes:
            - Called by _wait_until_alive() in a retry loop
            - Pod statuses: 'ready', 'pending', 'failed', 'unknown'
            - Restart count indicates if pod has been restarted (helpful for debugging)
            - check_if_alive() verifies actual server responsiveness beyond pod readiness
            - Typical transition: pending -> ready -> check_if_alive() succeeds
        
        Example:
            >>> runtime._wait_until_alive_impl()  # doctest: +SKIP
            >>> # Pod is ready and runtime server is responding

        """
        self.log("debug", f"Waiting for runtime to be alive at url: {self.runtime_url}")
        runtime_info_response = self._send_runtime_api_request(
            "GET",
            f"{self.config.sandbox.remote_runtime_api_url}/runtime/{self.runtime_id}",
        )
        runtime_data = runtime_info_response.json()
        assert "runtime_id" in runtime_data
        assert runtime_data["runtime_id"] == self.runtime_id
        assert "pod_status" in runtime_data
        pod_status = runtime_data["pod_status"].lower()
        self.log("debug", f"Pod status: {pod_status}")
        restart_count = runtime_data.get("restart_count", 0)
        if restart_count != 0:
            restart_reasons = runtime_data.get("restart_reasons")
            self.log("debug", f"Pod restarts: {restart_count}, reasons: {restart_reasons}")
        if pod_status == "ready":
            try:
                self.check_if_alive()
            except httpx.HTTPError as e:
                self.log("warning", f"Runtime /alive failed, but pod says it's ready: {e!s}")
                msg = f"Runtime /alive failed to respond with 200: {e!s}"
                raise AgentRuntimeNotReadyError(msg) from e
            return
        if pod_status in ["not found", "pending", "running"]:
            msg = f"Runtime (ID={self.runtime_id}) is not yet ready. Status: {pod_status}"
            raise AgentRuntimeNotReadyError(msg)
        if pod_status in ("failed", "unknown", "crashloopbackoff"):
            if pod_status == "crashloopbackoff":
                msg = "Runtime crashed and is being restarted, potentially due to memory usage. Please try again."
                raise AgentRuntimeUnavailableError(
                    msg,
                )
            msg = f"Runtime is unavailable (status: {pod_status}). Please try again."
            raise AgentRuntimeUnavailableError(msg)
        self.log("warning", f"Unknown pod status: {pod_status}")
        self.log("debug", f"Waiting for runtime pod to be active. Current status: {pod_status}")
        raise AgentRuntimeNotReadyError

    def close(self) -> None:
        """Close remote runtime connection and clean up resources."""
        if self.attach_to_existing:
            super().close()
            return
        if self.config.sandbox.keep_runtime_alive:
            if self.config.sandbox.pause_closed_runtimes:
                try:
                    if not self._runtime_closed:
                        self._send_runtime_api_request(
                            "POST",
                            f"{self.config.sandbox.remote_runtime_api_url}/pause",
                            json={"runtime_id": self.runtime_id},
                        )
                        self.log("info", "Runtime paused.")
                except Exception as e:
                    self.log("error", f"Unable to pause runtime: {e!s}")
                    raise
            super().close()
            return
        try:
            if not self._runtime_closed:
                self._send_runtime_api_request(
                    "POST",
                    f"{self.config.sandbox.remote_runtime_api_url}/stop",
                    json={"runtime_id": self.runtime_id},
                )
                self.log("info", "Runtime stopped.")
        except Exception as e:
            self.log("error", f"Unable to stop runtime: {e!s}")
            raise
        finally:
            super().close()

    def _send_runtime_api_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send HTTP request to remote runtime orchestration API with timeout.
        
        Wrapper around send_request() that applies configured timeout and logs timeout errors.
        Used for all orchestration API calls: /start, /stop, /pause, /resume, /runtime/{id}, etc.
        
        Args:
            method: HTTP method ('GET', 'POST', 'PUT', 'DELETE', etc.)
            url: Full URL to runtime API endpoint
            **kwargs: Additional arguments passed to send_request():
                     - json: Request body as dict (for POST/PUT)
                     - params: Query parameters
                     - headers: Additional HTTP headers
        
        Returns:
            HTTPX Response object with API response
        
        Raises:
            httpx.TimeoutException: If request exceeds remote_runtime_api_timeout
            httpx.HTTPError: For network errors, connection failures
        
        Side Effects:
            - Sets request timeout from config.sandbox.remote_runtime_api_timeout
            - Logs error on timeout with URL for debugging
            - Session includes API key header for authentication
        
        Notes:
            - Timeout typically 30-60 seconds for orchestration operations
            - API key set in session headers during __init__()
            - Used for control-plane operations (build, start, stop, resume)
            - Not used for data-plane operations (action execution)
            - Timeouts are common during high load; caller should implement retries
        
        Example:
            >>> response = runtime._send_runtime_api_request('GET', 'http://api.example.com/status')
            >>> response.json()
            {'runtime_id': 'rt-123', 'status': 'ready'}

        """
        try:
            kwargs["timeout"] = self.config.sandbox.remote_runtime_api_timeout
            return send_request(self.session, method, url, **kwargs)
        except httpx.TimeoutException:
            self.log("error", f"No response received within the timeout period for url: {url}")
            raise

    def _send_action_server_request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send HTTP request to action execution server with optional retry logic.
        
        Conditionally applies retry logic based on config.sandbox.remote_runtime_enable_retries:
        - If retries disabled: Calls _send_action_server_request_impl() directly
        - If retries enabled: Wraps with tenacity retry decorator for network resilience
        
        Args:
            method: HTTP method ('GET', 'POST', 'PUT', etc.)
            url: Full URL to action execution server endpoint
            **kwargs: Arguments passed to _send_action_server_request_impl()
        
        Returns:
            HTTPX Response object from action execution server
        
        Side Effects:
            - Implements exponential backoff retry on NetworkError (4-60 seconds)
            - Logs WARNING before each retry attempt
            - Stops retrying on close(), application shutdown, or after 3 attempts
            - Handles 503 (paused runtime) by triggering _resume_runtime()
        
        Raises:
            AgentRuntimeDisconnectedError: On 404, 502, 504, or unrecoverable errors
            AgentRuntimeUnavailableError: On 503 when keep_runtime_alive=False
            httpx.NetworkError: On persistent network failures after 3 retries
        
        Notes:
            - Data-plane requests to action execution server (not control-plane)
            - Retries tuned for transient network issues during agent execution
            - Exponential backoff helps during transient overload
            - 503 response (paused runtime) triggers automatic resume if enabled
            - Part of runtime robustness strategy for long-running agent sessions
        
        Example:
            >>> response = runtime._send_action_server_request('POST', 'http://runtime:8080/execute')
            >>> # Automatically retries on network errors with exponential backoff

        """
        if not self.config.sandbox.remote_runtime_enable_retries:
            return self._send_action_server_request_impl(method, url, **kwargs)
        stop_conditions = _compose_stop_conditions(
            tenacity.stop_after_attempt(3),
            stop_if_should_exit(),
            self._stop_if_closed,
        )
        retry_decorator = tenacity.retry(
            retry=tenacity.retry_if_exception_type(httpx.NetworkError),
            stop=cast(Any, stop_conditions),
            before_sleep=_before_sleep_action_request,
            wait=tenacity.wait_exponential(multiplier=1, min=4, max=60),
        )
        return retry_decorator(self._send_action_server_request_impl)(method, url, **kwargs)

    def _send_action_server_request_impl(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Send HTTP request to action execution server with error handling.
        
        Implements base runtime request with special handling for remote-specific errors:
        1. Catches timeouts and logs URL for debugging
        2. Handles 404/502/504 as runtime disconnection errors
        3. Handles 503 (paused runtime) by attempting automatic resume if enabled
        4. Re-raises other HTTP errors unchanged
        
        Args:
            method: HTTP method ('GET', 'POST', 'PUT', etc.)
            url: Full URL to action execution server endpoint
            **kwargs: Arguments passed to parent _send_action_server_request()
        
        Returns:
            HTTPX Response object from action execution server
        
        Raises:
            AgentRuntimeDisconnectedError: On 404 (not responding), 502/504 (bad gateway)
            AgentRuntimeDisconnectedError: On 503 if keep_runtime_alive=False or resume fails
            httpx.TimeoutException: On request timeout
            httpx.HTTPError: Other HTTP errors
        
        Side Effects:
            - Logs error messages for timeout and HTTP failures
            - Automatically calls _resume_runtime() on 503 if keep_runtime_alive=True
            - Updates session after automatic resume
            - Logs info when runtime detected as paused (503 status)
        
        Notes:
            - Errors 404/502/504 indicate runtime disconnection (agent-side action needed)
            - Error 503 indicates paused runtime (automatically resumable if configured)
            - Automatic resume only attempted if keep_runtime_alive=True
            - Used for all action execution server requests after connection established
            - Part of runtime resilience strategy for transient failures
        
        Example:
            >>> response = runtime._send_action_server_request_impl('POST', 'http://runtime:8080/act')
            >>> # Automatically resumes on 503 if keep_runtime_alive=True

        """
        try:
            return super()._send_action_server_request(method, url, **kwargs)
        except httpx.TimeoutException:
            self.log("error", f"No response received within the timeout period for url: {url}")
            raise
        except httpx.HTTPError as e:
            error_response = getattr(e, "response", None)
            if error_response is not None and error_response.status_code in (404, 502, 504):
                if error_response.status_code == 404:
                    msg = f"Runtime is not responding. This may be temporary, please try again. Original error: {e}"
                    raise AgentRuntimeDisconnectedError(
                        msg,
                    ) from e
                msg = f"Runtime is temporarily unavailable. This may be due to a restart or network issue, please try again. Original error: {e}"
                raise AgentRuntimeDisconnectedError(
                    msg,
                ) from e
            if error_response is not None and error_response.status_code == 503:
                if self.config.sandbox.keep_runtime_alive:
                    self.log(
                        "info",
                        f"Runtime appears to be paused (503 response). Runtime ID: {
                            self.runtime_id}, URL: {url}",
                    )
                    try:
                        self._resume_runtime()
                        self.log("info", "Successfully resumed runtime after 503 response")
                        return super()._send_action_server_request(method, url, **kwargs)
                    except Exception as resume_error:
                        self.log("error", f"Failed to resume runtime after 503 response: {resume_error}", exc_info=True)
                        msg = f"Runtime is paused and could not be resumed. Original error: {e}, Resume error: {resume_error}"
                        raise AgentRuntimeDisconnectedError(
                            msg,
                        ) from resume_error
                else:
                    self.log("info", "Runtime appears to be paused (503 response) but keep_runtime_alive is False")
                    msg = f"Runtime is temporarily unavailable. This may be due to a restart or network issue, please try again. Original error: {e}"
                    raise AgentRuntimeDisconnectedError(
                        msg,
                    ) from e
            else:
                raise

    def _stop_if_closed(self, retry_state: RetryCallState) -> bool:
        """Tenacity stop predicate that stops retrying when runtime is closed.
        
        Used as a stop condition in tenacity retry decorators to immediately abort
        retries when the runtime has been closed (e.g., due to user shutdown or errors).
        Implements the tenacity stop predicate interface: returns True to stop retrying.
        
        Args:
            retry_state: Tenacity RetryCallState object (unused; only _runtime_closed checked)
        
        Returns:
            True if runtime is closed (should stop retrying), False otherwise
        
        Notes:
            - Used in _wait_until_alive() and _send_action_server_request() retry decorators
            - Called before each retry attempt to check if retries should continue
            - Prevents wasting resources retrying after user has closed the runtime
            - Part of graceful shutdown mechanism during long-running operations
            - Typically combined with other stop conditions (timeout, attempt limit)
        
        Example:
            >>> runtime._runtime_closed = True
            >>> runtime._stop_if_closed(None)  # Returns True
            True

        """
        return self._runtime_closed

    def get_action_execution_server_startup_command(self):
        """Get command to start action execution server on remote runtime.
        
        Returns:
            Command list for starting server

        """
        return get_action_execution_server_startup_command(
            server_port=self.port,
            plugins=self.plugins,
            app_config=self.config,
            main_module=self.main_module,
        )
