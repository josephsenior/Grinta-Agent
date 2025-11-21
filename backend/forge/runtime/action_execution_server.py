"""This is the main file for the runtime client.

It is responsible for executing actions received from forge backend and producing observations.

NOTE: this will be executed inside the docker sandbox.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import os
import shutil
import sys
import tempfile
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile
from typing import TYPE_CHECKING, Any

import puremagic
from binaryornot.check import is_binary
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader


def _module_attr(name: str):
    """Return the latest attribute from this module for monkeypatched helpers."""
    return getattr(sys.modules[__name__], name)

ToolError: type[Exception]
ToolResult: type[Any]
OHEditor: type[Any]

if TYPE_CHECKING:
    from forge_aci.editor.editor import OHEditor as _ForgeOHEditor
    from forge_aci.editor.exceptions import ToolError as _ForgeToolError
    from forge_aci.editor.results import ToolResult as _ForgeToolResult

try:
    from forge_aci.editor.editor import OHEditor as _RuntimeOHEditor
    from forge_aci.editor.exceptions import ToolError as _RuntimeToolError
    from forge_aci.editor.results import ToolResult as _RuntimeToolResult
    from forge_aci.utils.diff import get_diff
except ImportError:
    # Stubs for when forge_aci is not installed
    class _StubToolError(Exception):
        """Stub ToolError for testing."""

        def __init__(self, message: str = "") -> None:
            """Store an optional error message for the fallback stub."""
            super().__init__(message)
            self.message = message

    class _StubToolResult:
        """Stub ToolResult for testing."""

        def __init__(
            self,
            *,
            output: str | None = None,
            error: str | None = None,
            old_content: str | None = None,
            new_content: str | None = None,
        ) -> None:
            """Initialize stubbed tool execution result fields."""
            self.output = output or ""
            self.error = error
            self.old_content = old_content
            self.new_content = new_content

    class _StubOHEditor:
        """Stub OHEditor for testing when forge_aci is unavailable."""

        def __init__(self, workspace_root: str | None = None, *args, **kwargs) -> None:
            """Record the workspace root for file operations in fallback mode."""
            self.workspace_root = workspace_root

        def __call__(
            self,
            *,
            command: str,
            path: str,
            file_text: str | None = None,
            view_range: list[int] | None = None,
            old_str: str | None = None,
            new_str: str | None = None,
            insert_line: int | None = None,
            enable_linting: bool = False,
            **_: Any,
        ) -> _StubToolResult:
            """Simulate a minimal editor command for fallback testing scenarios."""
            try:
                if command == "view":
                    return self._handle_view_command(path, view_range)
                if command in {"edit", "apply_edit"}:
                    return self._handle_edit_command(path, file_text, new_str)
                if command == "write":
                    return self._handle_write_command(path, file_text, new_str)
            except Exception as exc:  # pragma: no cover - safeguard for stub
                return _StubToolResult(error=str(exc))
            return _StubToolResult(output="", old_content=None, new_content=None)

        def _handle_view_command(
            self, path: str, view_range: list[int] | None
        ) -> _StubToolResult:
            """Return selected view of the file if it exists."""
            if not os.path.exists(path) or os.path.isdir(path):
                return _StubToolResult(output="", old_content=None, new_content=None)
            content = self._read_file(path)
            selected = self._slice_content(content, view_range)
            return _StubToolResult(
                output=selected, old_content=content, new_content=content
            )

        def _handle_edit_command(
            self, path: str, file_text: str | None, new_str: str | None
        ) -> _StubToolResult:
            """Apply edits to a file, returning previous and updated contents."""
            previous = self._read_file(path) if os.path.exists(path) else ""
            updated = new_str if new_str is not None else file_text or previous
            self._write_file(path, updated)
            return _StubToolResult(
                output="File updated", old_content=previous, new_content=updated
            )

        def _handle_write_command(
            self, path: str, file_text: str | None, new_str: str | None
        ) -> _StubToolResult:
            """Write new content to a file regardless of previous contents."""
            content = file_text or new_str or ""
            self._write_file(path, content)
            return _StubToolResult(
                output="File written", old_content=None, new_content=content
            )

        def _slice_content(
            self, content: str, view_range: list[int] | None
        ) -> str:
            """Return either full content or the requested line range."""
            if not view_range:
                return content
            start, end = view_range
            lines = content.splitlines(True)
            return "".join(lines[max(start - 1, 0) : end])

        def _read_file(self, path: str) -> str:
            """Read file contents with fallback encoding handling."""
            with open(path, encoding="utf-8", errors="replace") as handle:
                return handle.read()

        def _write_file(self, path: str, content: str) -> None:
            """Write content to disk, ensuring directories exist."""
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _stub_get_diff(
        old: str | None = None,
        new: str | None = None,
        *,
        old_contents: str = "",
        new_contents: str = "",
        **__: Any,
    ) -> str:
        """Stub diff function when forge_aci is unavailable."""
        previous = old if old is not None else old_contents
        updated = new if new is not None else new_contents
        return "\n".join(
            [
                "--- old",
                "+++ new",
                "@@ -1 +1 @@",
                f"-{previous}",
                f"+{updated}",
            ]
        )

    ToolError = _StubToolError
    ToolResult = _StubToolResult
    OHEditor = _StubOHEditor
    get_diff = _stub_get_diff
else:
    ToolError = _RuntimeToolError
    ToolResult = _RuntimeToolResult
    OHEditor = _RuntimeOHEditor


from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn import run

from forge.core.config.mcp_config import MCPStdioServerConfig
from forge.core.exceptions import BrowserUnavailableException
from forge.core.logger import forge_logger as logger
from forge.events.action import (
    Action,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    IPythonRunCellAction,
)
from forge.events.event import FileEditSource, FileReadSource
from forge.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileDownloadObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    IPythonRunCellObservation,
    Observation,
)
from forge.events.serialization import event_from_dict, event_to_dict
from forge.runtime.browser import browse
from forge.runtime.browser.browser_env import BrowserEnv
from forge.runtime.file_viewer_server import start_file_viewer_server
from forge.runtime.mcp.proxy import MCPProxyManager
from forge.runtime.plugins import ALL_PLUGINS, JupyterPlugin, Plugin, VSCodePlugin
from forge.runtime.utils import find_available_tcp_port
from forge.runtime.utils.bash import BashSession
from forge.runtime.utils.files import insert_lines, read_lines
from forge.runtime.utils.memory_monitor import MemoryMonitor
from forge.runtime.utils.runtime_init import init_user_and_working_directory
from forge.runtime.utils.system_stats import (
    get_system_stats,
    update_last_execution_time,
)
from forge.utils.async_utils import call_sync_from_async, wait_all

# Windows PowerShell session - only available on Windows
WindowsPowershellSession = None
# Note: Import is deferred to avoid executing windows_bash.py on non-Windows platforms


@dataclass
class ActionRequest:
    """Incoming action execution request envelope sent to runtime server."""

    event: dict[str, Any]


async def _resolve_list_path(request: Request, client) -> str:
    """Resolve the path to list files from.

    Args:
        request: HTTP request
        client: Action execution client

    Returns:
        Resolved full path

    """
    request_dict = await request.json()
    path = request_dict.get("path", None)

    if path is None:
        return client.initial_cwd
    if os.path.isabs(path):
        return path
    return os.path.join(client.initial_cwd, path)


def _get_sorted_directory_entries(full_path: str) -> list[str]:
    """Get sorted list of directory entries.

    Args:
        full_path: Directory path to list

    Returns:
        Sorted list of entries (directories first with /, then files)

    """
    entries = os.listdir(full_path)
    directories = []
    files = []

    for entry in entries:
        entry_relative = entry.lstrip("/").split("/")[-1]
        full_entry_path = os.path.join(full_path, entry_relative)

        if os.path.exists(full_entry_path):
            if os.path.isdir(full_entry_path):
                directories.append(entry.rstrip("/") + "/")
            else:
                files.append(entry)

    directories.sort(key=lambda s: s.lower())
    files.sort(key=lambda s: s.lower())

    return directories + files


ROOT_GID = 0
SESSION_API_KEY = os.environ.get("SESSION_API_KEY")
api_key_header = APIKeyHeader(name="X-Session-API-Key", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API key for session authentication.

    Args:
        api_key: The API key from the request header.

    Returns:
        str: The verified API key.

    Raises:
        HTTPException: If the API key is invalid or doesn't match the session key.

    """
    if SESSION_API_KEY and api_key != SESSION_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


def _execute_file_editor(
    editor: Any,
    command: str,
    path: str,
    file_text: str | None = None,
    view_range: list[int] | None = None,
    old_str: str | None = None,
    new_str: str | None = None,
    insert_line: int | str | None = None,
    enable_linting: bool = False,
) -> tuple[str, tuple[str | None, str | None]]:
    """Execute file editor command and handle exceptions.

    Args:
        editor: The OHEditor instance
        command: Editor command to execute
        path: File path
        file_text: Optional file text content
        view_range: Optional view range tuple (start, end)
        old_str: Optional string to replace
        new_str: Optional replacement string
        insert_line: Optional line number for insertion (can be int or str)
        enable_linting: Whether to enable linting

    Returns:
        tuple: A tuple containing the output string and a tuple of old and new file content

    """
    result: Any | None = None
    if insert_line is not None and isinstance(insert_line, str):
        try:
            insert_line = int(insert_line)
        except ValueError:
            return (
                f"ERROR:\nInvalid insert_line value: '{insert_line}'. Expected an integer.",
                (None, None),
            )
    try:
        result = editor(
            command=command,
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
            enable_linting=enable_linting,
        )
    except ToolError as e:
        result = ToolResult(error=str(e))
    except TypeError as e:
        return (f"ERROR:\n{e!s}", (None, None))
    if result.error:
        return (f"ERROR:\n{result.error}", (None, None))
    if not result.output:
        logger.warning("No output from file_editor for %s", path)
        return ("", (None, None))
    return (result.output, (result.old_content, result.new_content))


class ActionExecutor:
    """ActionExecutor is running inside docker sandbox.

    It is responsible for executing actions received from forge backend and producing observations.
    """

    def __init__(
        self,
        plugins_to_load: list[Plugin],
        work_dir: str,
        username: str,
        user_id: int,
        enable_browser: bool,
        browsergym_eval_env: str | None,
    ) -> None:
        """Create sandbox executor, initialize workspace, and prepare tooling integrations."""
        self.plugins_to_load = plugins_to_load
        self._initial_cwd = work_dir
        self.username = username
        self.user_id = user_id
        _updated_user_id = init_user_and_working_directory(
            username=username,
            user_id=self.user_id,
            initial_cwd=work_dir,
        )
        if _updated_user_id is not None:
            self.user_id = _updated_user_id
        self.bash_session: BashSession | None = None
        self.lock = asyncio.Lock()
        self.plugins: dict[str, Plugin] = {}
        self.file_editor = OHEditor(workspace_root=self._initial_cwd)
        self.enable_browser = enable_browser
        self.browser: BrowserEnv | None = None
        self.browser_init_task: asyncio.Task | None = None
        self.browsergym_eval_env = browsergym_eval_env
        if not self.enable_browser and self.browsergym_eval_env:
            msg = "Browser environment is not enabled in config, but browsergym_eval_env is set"
            raise BrowserUnavailableException(
                msg,
            )
        self.start_time = time.time()
        self.last_execution_time = self.start_time
        self._initialized = False
        self.downloaded_files: list[str] = []
        self.downloads_directory = "/workspace/.downloads"
        self.max_memory_gb: int | None = None
        if _override_max_memory_gb := os.environ.get("RUNTIME_MAX_MEMORY_GB", None):
            self.max_memory_gb = int(_override_max_memory_gb)
            logger.info(
                "Setting max memory to %sGB (according to the RUNTIME_MAX_MEMORY_GB environment variable)",
                self.max_memory_gb,
            )
        else:
            logger.info("No max memory limit set, using all available system memory")
        self.memory_monitor = MemoryMonitor(
            enable=os.environ.get("RUNTIME_MEMORY_MONITOR", "False").lower()
            in ["true", "1", "yes"],
        )
        self.memory_monitor.start_monitoring()

    @property
    def initial_cwd(self):
        """Get the initial working directory for the action execution server.

        Returns:
            Initial working directory path

        """
        return self._initial_cwd

    async def _init_browser_async(self) -> None:
        """Initialize the browser asynchronously."""
        platform_name = sys.platform
        if not self.enable_browser:
            logger.info("Browser environment is not enabled in config")
            return
        if platform_name == "win32":
            logger.warning("Browser environment not supported on windows")
            return
        logger.debug("Initializing browser asynchronously")
        try:
            self.browser = BrowserEnv(self.browsergym_eval_env)
            logger.debug("Browser initialized asynchronously")
        except Exception as e:
            logger.error("Failed to initialize browser: %s", e)
            self.browser = None

    async def _ensure_browser_ready(self) -> None:
        """Ensure the browser is ready for use."""
        if self.browser is None:
            if self.browser_init_task is None or (
                self.browser_init_task is not None and self.browser_init_task.done()
            ):
                self.browser_init_task = asyncio.create_task(self._init_browser_async())
            if self.browser_init_task:
                logger.debug("Waiting for browser to be ready...")
                await self.browser_init_task
        if self.browser is None:
            msg = "Browser initialization failed"
            raise BrowserUnavailableException(msg)
        logger.debug("Browser is ready")

    def _create_bash_session(self, cwd: str | None = None):
        """Create a bash session appropriate for the current platform.

        Creates either a WindowsPowershell session on Windows (with fallback to Unix bash)
        or a standard BashSession on Unix-like systems. Initializes the session with
        environment-specific settings including working directory, username, and resource limits.

        Args:
            cwd: Optional working directory for the session. Defaults to self._initial_cwd

        Returns:
            BashSession or WindowsPowershellSession: Initialized shell session

        Environment Variables:
            - NO_CHANGE_TIMEOUT_SECONDS: Timeout for inactivity (default: 10)
            - max_memory_gb: Maximum memory usage in GB (converted to MB)

        Side Effects:
            - Initializes bash session with initialize() call
            - Logs warning if Windows PowerShell fallback is used

        Example:
            >>> session = executor._create_bash_session("/tmp")
            >>> isinstance(session, BashSession)
            True
            >>> session.cwd
            "/tmp"

        Note:
            On Windows, attempts to use WindowsPowershellSession first, falls back to
            BashSession if PowerShell is unavailable. This provides Windows compatibility.

        """
        platform_name = sys.platform
        if platform_name == "win32":
            # Import Windows PowerShell session only when actually needed on Windows
            try:
                from forge.runtime.utils.windows_bash import WindowsPowershellSession

                return WindowsPowershellSession(
                    work_dir=cwd or self._initial_cwd,
                    username=self.username,
                    no_change_timeout_seconds=int(
                        os.environ.get("NO_CHANGE_TIMEOUT_SECONDS", 10)
                    ),
                    max_memory_mb=self.max_memory_gb * 1024
                    if self.max_memory_gb
                    else None,
                )
            except Exception as e:
                logger.warning(
                    "Failed to create Windows PowerShell session, falling back to bash: %s",
                    e,
                )
        bash_session = BashSession(
            work_dir=cwd or self._initial_cwd,
            username=self.username,
            no_change_timeout_seconds=int(
                os.environ.get("NO_CHANGE_TIMEOUT_SECONDS", 10)
            ),
            max_memory_mb=self.max_memory_gb * 1024 if self.max_memory_gb else None,
        )
        bash_session.initialize()
        return bash_session

    async def ainit(self) -> None:
        """Initialize action execution server asynchronously.

        Sets up bash session, browser environment, plugins, and agent skills.
        """
        logger.debug("Initializing bash session")
        self.bash_session = self._create_bash_session()
        logger.debug("Bash session initialized")
        self.browser_init_task = asyncio.create_task(self._init_browser_async())
        logger.debug("Browser initialization started in background")
        await wait_all(
            (self._init_plugin(plugin) for plugin in self.plugins_to_load),
            timeout=int(os.environ.get("INIT_PLUGIN_TIMEOUT", "120")),
        )
        logger.debug("All plugins initialized")
        logger.debug("Initializing AgentSkills")
        if "agent_skills" in self.plugins and "jupyter" in self.plugins:
            obs = await self.run_ipython(
                IPythonRunCellAction(
                    code="from forge.runtime.plugins.agent_skills.agentskills import *\n"
                ),
            )
            logger.debug("AgentSkills initialized: %s", obs)
        logger.debug("Initializing bash commands")
        await self._init_bash_commands()
        logger.debug("Runtime client initialized.")
        self._initialized = True

    @property
    def initialized(self) -> bool:
        """Check if action execution server has completed initialization.

        Returns:
            True if initialized

        """
        return self._initialized

    async def _init_plugin(self, plugin: Plugin) -> None:
        assert self.bash_session is not None
        if isinstance(plugin, VSCodePlugin):
            runtime_id = os.environ.get("RUNTIME_ID")
            await plugin.initialize(self.username, runtime_id=runtime_id)
        else:
            await plugin.initialize(self.username)
        self.plugins[plugin.name] = plugin
        logger.debug("Initializing plugin: %s", plugin.name)
        if isinstance(plugin, JupyterPlugin):
            cwd = self.bash_session.cwd.replace("\\", "/")
            await self.run_ipython(
                IPythonRunCellAction(code=f'import os; os.chdir(r"{cwd}")')
            )

    async def _init_bash_commands(self) -> None:
        is_windows = sys.platform == "win32"
        if is_windows:
            no_pager_cmd = "function git { git.exe --no-pager $args }"
        else:
            no_pager_cmd = 'alias git="git --no-pager"'
        INIT_COMMANDS = [no_pager_cmd]
        logger.info("Initializing by running %s bash commands...", len(INIT_COMMANDS))
        for command in INIT_COMMANDS:
            action = CmdRunAction(command=command)
            action.set_hard_timeout(300)
            logger.debug("Executing init command: %s", command)
            obs = await self.run(action)
            assert isinstance(obs, CmdOutputObservation)
            logger.debug(
                "Init command outputs (exit code: %s): %s", obs.exit_code, obs.content
            )
            assert obs.exit_code == 0
        logger.debug("Bash init commands completed")

    async def run_action(self, action) -> Observation:
        """Execute any action through action execution server.

        Args:
            action: Action to execute

        Returns:
            Observation resulting from action execution

        """
        async with self.lock:
            action_type = action.action
            return await getattr(self, action_type)(action)

    async def run(
        self, action: CmdRunAction
    ) -> CmdOutputObservation | ErrorObservation:
        """Execute bash/shell command.

        Args:
            action: Command run action

        Returns:
            Command output or error observation

        """
        try:
            bash_session = self.bash_session
            if action.is_static:
                bash_session = self._create_bash_session(action.cwd)
            assert bash_session is not None
            observation = await call_sync_from_async(bash_session.execute, action)

            # Check for detected servers and add to observation extras
            detected_server = bash_session.get_detected_server()
            if detected_server:
                logger.info(
                    f"🚀 Adding detected server to observation extras: {detected_server.url}"
                )
                # Add server info to observation extras for frontend processing
                if not hasattr(observation, "extras") or observation.extras is None:
                    observation.extras = {}
                observation.extras["server_ready"] = {
                    "port": detected_server.port,
                    "url": detected_server.url,
                    "protocol": detected_server.protocol,
                    "health_status": detected_server.health_status,
                }

            return observation
        except Exception as e:
            logger.error("Error running command: %s", e)
            return ErrorObservation(str(e))

    async def run_ipython(self, action: IPythonRunCellAction) -> Observation:
        """Execute Python code in IPython/Jupyter environment.

        Args:
            action: IPython run cell action

        Returns:
            Observation with execution results

        """
        assert self.bash_session is not None
        if "jupyter" not in self.plugins:
            msg = "JupyterRequirement not found. Unable to run IPython action."
            raise RuntimeError(msg)
        plugin = self.plugins["jupyter"]
        if not isinstance(plugin, JupyterPlugin):
            raise RuntimeError("Registered jupyter plugin is not a JupyterPlugin")
        _jupyter_plugin = plugin
        jupyter_cwd = getattr(self, "_jupyter_cwd", None)
        if self.bash_session.cwd != jupyter_cwd:
            logger.debug(
                "%s != %s -> reset Jupyter PWD", self.bash_session.cwd, jupyter_cwd
            )
            cwd = self.bash_session.cwd.replace("\\", "/")
            reset_jupyter_cwd_code = f'import os; os.chdir("{cwd}")'
            _aux_action = IPythonRunCellAction(code=reset_jupyter_cwd_code)
            _reset_obs: IPythonRunCellObservation = await _jupyter_plugin.run(
                _aux_action
            )
            logger.debug(
                "Changed working directory in IPython to: %s. Output: %s",
                self.bash_session.cwd,
                _reset_obs,
            )
            self._jupyter_cwd = self.bash_session.cwd
        obs: IPythonRunCellObservation = await _jupyter_plugin.run(action)
        obs.content = obs.content.rstrip()
        if action.include_extra:
            obs.content += (
                f"\n[Jupyter current working directory: {self.bash_session.cwd}]"
            )
            obs.content += f"\n[Jupyter Python interpreter: {_jupyter_plugin.python_interpreter_path}]"
        return obs

    def _resolve_path(self, path: str, working_dir: str) -> str:
        """Resolve a relative or absolute path to an absolute path.

        Converts relative paths to absolute by combining with working_dir.
        Absolute paths are returned unchanged. This is used for consistent
        path handling across file operations.

        Args:
            path: File path (relative or absolute)
            working_dir: Current working directory to use for relative paths

        Returns:
            str: Absolute file path as string

        Example:
            >>> abs_path = executor._resolve_path("file.txt", "/home/user")
            >>> abs_path
            "/home/user/file.txt"
            >>> abs_path2 = executor._resolve_path("/tmp/file.txt", "/home/user")
            >>> abs_path2
            "/tmp/file.txt"

        Note:
            - Relative paths are joined with working_dir
            - Absolute paths are returned as-is
            - Uses pathlib.Path for cross-platform compatibility

        """
        filepath = Path(path)
        if not filepath.is_absolute():
            return str(Path(working_dir) / filepath)
        return str(filepath)

    def _handle_aci_file_read(self, action: FileReadAction) -> FileReadObservation:
        """Handle file reading using the OH_ACI implementation.

        Args:
            action: The file read action.

        Returns:
            FileReadObservation: The observation with file content.

        """
        result_str, _ = _execute_file_editor(
            self.file_editor,
            command="view",
            path=action.path,
            view_range=action.view_range,
        )
        return FileReadObservation(
            content=result_str, path=action.path, impl_source=FileReadSource.OH_ACI
        )

    def _encode_binary_file(
        self,
        filepath: str,
        file_data: bytes,
        mime_type: str | None,
        default_mime: str,
    ) -> str:
        """Encode binary file data as base64 data URL.

        Args:
            filepath: The file path.
            file_data: The binary file data.
            mime_type: The detected MIME type.
            default_mime: Default MIME type if detection fails.

        Returns:
            str: Base64 encoded data URL.

        """
        encoded_data = base64.b64encode(file_data).decode("utf-8")
        effective_mime = mime_type or default_mime
        return f"data:{effective_mime};base64,{encoded_data}"

    def _read_image_file(self, filepath: str) -> FileReadObservation:
        """Read and encode an image file.

        Args:
            filepath: The path to the image file.

        Returns:
            FileReadObservation: The observation with encoded image content.

        """
        with open(filepath, "rb") as file:
            image_data = file.read()
            mime_type, _ = mimetypes.guess_type(filepath)
            encoded_image = self._encode_binary_file(
                filepath, image_data, mime_type, "image/png"
            )
        return FileReadObservation(path=filepath, content=encoded_image)

    def _read_pdf_file(self, filepath: str) -> FileReadObservation:
        """Read and encode a PDF file.

        Args:
            filepath: The path to the PDF file.

        Returns:
            FileReadObservation: The observation with encoded PDF content.

        """
        with open(filepath, "rb") as file:
            pdf_data = file.read()
            encoded_pdf = self._encode_binary_file(
                filepath, pdf_data, "application/pdf", "application/pdf"
            )
        return FileReadObservation(path=filepath, content=encoded_pdf)

    def _read_video_file(self, filepath: str) -> FileReadObservation:
        """Read and encode a video file.

        Args:
            filepath: The path to the video file.

        Returns:
            FileReadObservation: The observation with encoded video content.

        """
        with open(filepath, "rb") as file:
            video_data = file.read()
            mime_type, _ = mimetypes.guess_type(filepath)
            encoded_video = self._encode_binary_file(
                filepath, video_data, mime_type, "video/mp4"
            )
        return FileReadObservation(path=filepath, content=encoded_video)

    def _read_text_file(
        self, filepath: str, action: FileReadAction
    ) -> FileReadObservation:
        """Read a text file with optional line range.

        Args:
            filepath: The path to the text file.
            action: The file read action with start/end line parameters.

        Returns:
            FileReadObservation: The observation with file content.

        Raises:
            IsADirectoryError: If filepath is a directory.

        """
        # Safety check: Prevent reading directories as files
        if os.path.isdir(filepath):
            raise IsADirectoryError(f"{filepath} is a directory, not a file")

        with open(filepath, encoding="utf-8") as file:
            lines = read_lines(file.readlines(), action.start, action.end)
        code_view = "".join(lines)
        return FileReadObservation(path=filepath, content=code_view)

    def _handle_file_read_errors(
        self, filepath: str, working_dir: str
    ) -> ErrorObservation:
        """Handle file reading errors with appropriate error messages.

        Args:
            filepath: The file path that caused the error.
            working_dir: The current working directory.

        Returns:
            ErrorObservation: The appropriate error observation.

        """
        try:
            raise  # Re-raise the current exception to check its type
        except FileNotFoundError:
            return ErrorObservation(
                f"File not found: {filepath}. Your current working directory is {working_dir}."
            )
        except UnicodeDecodeError:
            return ErrorObservation(f"File could not be decoded as utf-8: {filepath}.")
        except IsADirectoryError:
            return ErrorObservation(
                f"Path is a directory: {filepath}. You can only read files"
            )
        except Exception:
            return ErrorObservation(f"Unexpected error reading file: {filepath}.")

    async def read(self, action: FileReadAction) -> Observation:
        """Read a file and return its content as an observation.

        Args:
            action: The file read action containing file path and parameters.

        Returns:
            Observation: FileReadObservation with content or ErrorObservation if failed.

        """
        assert self.bash_session is not None

        # Check for binary files
        if is_binary(action.path):
            return ErrorObservation("ERROR_BINARY_FILE")

        # Handle OH_ACI implementation
        if action.impl_source == FileReadSource.OH_ACI:
            return self._handle_aci_file_read(action)

        # Resolve file path
        working_dir = self.bash_session.cwd
        filepath = self._resolve_path(action.path, working_dir)

        try:
            # Handle different file types
            if filepath.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                return self._read_image_file(filepath)
            if filepath.lower().endswith(".pdf"):
                return self._read_pdf_file(filepath)
            if filepath.lower().endswith((".mp4", ".webm", ".ogg")):
                return self._read_video_file(filepath)
            return self._read_text_file(filepath, action)
        except Exception:
            return self._handle_file_read_errors(filepath, working_dir)

    async def write(self, action: FileWriteAction) -> Observation:
        """Write content to a file with proper error handling.

        Reduced complexity: 13 → 5 by extracting file operations to helper methods.
        """
        assert self.bash_session is not None
        working_dir = self.bash_session.cwd
        filepath = self._resolve_path(action.path, working_dir)

        # Ensure directory exists
        self._ensure_directory_exists(filepath)

        # Prepare file metadata
        file_exists = os.path.exists(filepath)
        file_stat = os.stat(filepath) if file_exists else None

        # Write file content
        write_result = self._write_file_content(filepath, action, file_exists)
        if isinstance(write_result, ErrorObservation):
            return write_result

        # Set file permissions and ownership
        permission_result = self._set_file_permissions(filepath, file_exists, file_stat)
        if isinstance(permission_result, ErrorObservation):
            return permission_result

        return FileWriteObservation(content="", path=filepath)

    def _ensure_directory_exists(self, filepath: str) -> None:
        """Ensure the directory for the file exists, creating parent directories as needed.

        Creates all parent directories recursively if they don't exist. This is called
        before writing files to ensure the target directory is available.

        Args:
            filepath: Full file path (including filename)

        Side Effects:
            - Creates directories on filesystem via os.makedirs()

        Example:
            >>> executor._ensure_directory_exists("/tmp/nested/path/file.txt")
            >>> os.path.exists("/tmp/nested/path")
            True

        """
        dir_path = os.path.dirname(filepath)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def _write_file_content(
        self,
        filepath: str,
        action: FileWriteAction,
        file_exists: bool,
    ) -> Observation | None:
        """Write content to file, handling both new and existing files with proper line insertion.

        For new files, writes all content. For existing files, inserts/replaces lines at the
        specified start/end positions. Uses line-based insertion semantics for precise control.

        Args:
            filepath: Full path to target file
            action: FileWriteAction with content, start, end line numbers
            file_exists: Boolean indicating if file already exists

        Returns:
            Observation | None: ErrorObservation if operation fails, None on success

        Raises ErrorObservation for:
            - FileNotFoundError: File path is invalid
            - IsADirectoryError: filepath is actually a directory
            - UnicodeDecodeError: File cannot be decoded as UTF-8

        Implementation Details:
            - Uses "r+" mode for existing files (read-write), "w" for new files
            - Splits content by newlines and preserves line structure
            - Uses file.truncate() to remove extra content after overwrites

        Example:
            >>> action = FileWriteAction(content="new line", start=1, end=1)
            >>> result = executor._write_file_content("/tmp/file.txt", action, True)
            >>> result is None  # Success
            True

        """
        insert = action.content.split("\n")
        mode = "r+" if file_exists else "w"

        try:
            with open(filepath, mode, encoding="utf-8") as file:
                if mode != "w":
                    # Existing file: insert/replace lines
                    all_lines = file.readlines()
                    new_file = insert_lines(insert, all_lines, action.start, action.end)
                else:
                    # New file: write all content
                    new_file = [i + "\n" for i in insert]

                file.seek(0)
                file.writelines(new_file)
                file.truncate()

            return None  # Success

        except FileNotFoundError:
            return ErrorObservation(f"File not found: {filepath}")
        except IsADirectoryError:
            return ErrorObservation(
                f"Path is a directory: {filepath}. You can only write to files"
            )
        except UnicodeDecodeError:
            return ErrorObservation(f"File could not be decoded as utf-8: {filepath}")

    def _set_file_permissions(
        self,
        filepath: str,
        file_exists: bool,
        file_stat: os.stat_result | None,
    ) -> Observation | None:
        """Set file permissions and ownership with preservation for existing files.

        For existing files, restores original permissions and ownership (preserves).
        For new files, sets default permissions (0o664) and owns by current user.
        This ensures consistent file permissions in the runtime environment.

        Args:
            filepath: Full path to file
            file_exists: Boolean indicating if file already existed
            file_stat: os.stat_result from before write (needed to preserve permissions)

        Returns:
            Observation | None: ErrorObservation if permission changes fail, None on success

        Raises ErrorObservation for:
            - PermissionError: Failed to change ownership or permissions (but file was written)

        Behavior:
            - Existing files: chmod to original, chown to original uid/gid
            - New files: chmod 0o664 (user read/write, group read/write, others read)
                         chown to self.user_id
            - PermissionErrors are non-fatal (file still written)

        Example:
            >>> stat_result = os.stat("/tmp/file.txt")
            >>> result = executor._set_file_permissions("/tmp/file.txt", True, stat_result)
            >>> result is None  # Success (permissions preserved)
            True

        """
        try:
            if file_exists:
                # Preserve original permissions
                assert file_stat is not None
                os.chmod(filepath, file_stat.st_mode)
                chown_fn = getattr(os, "chown", None)
                if callable(chown_fn):
                    chown_fn(filepath, file_stat.st_uid, file_stat.st_gid)
            else:
                # Set default permissions for new file (0o644)
                os.chmod(filepath, 0o644)
                chown_fn = getattr(os, "chown", None)
                if callable(chown_fn):
                    chown_fn(filepath, self.user_id, self.user_id)

            return None  # Success

        except PermissionError as e:
            return ErrorObservation(
                f"File {filepath} written, but failed to change ownership and permissions: {e}",
            )

    async def edit(self, action: FileEditAction) -> Observation:
        """Execute file edit operation.

        Args:
            action: File edit action with edit details

        Returns:
            File edit observation with diff

        """
        assert action.impl_source == FileEditSource.OH_ACI
        result_str, (old_content, new_content) = _execute_file_editor(
            self.file_editor,
            command=action.command,
            path=action.path,
            file_text=action.file_text,
            old_str=action.old_str,
            new_str=action.new_str,
            insert_line=action.insert_line,
            enable_linting=False,
        )
        return FileEditObservation(
            content=result_str,
            path=action.path,
            old_content=action.old_str,
            new_content=action.new_str,
            impl_source=FileEditSource.OH_ACI,
            diff=get_diff(
                old_contents=old_content or "",
                new_contents=new_content or "",
                filepath=action.path,
            ),
        )

    async def browse(self, action: BrowseURLAction) -> Observation:
        """Browse URL and return page content.

        Args:
            action: Browse URL action

        Returns:
            Browser observation with page content or error

        """
        if self.browser is None:
            return ErrorObservation(
                "Browser functionality is not supported or disabled."
            )
        await self._ensure_browser_ready()
        return await browse(action, self.browser, self.initial_cwd)

    async def browse_interactive(self, action: BrowseInteractiveAction) -> Observation:
        """Execute interactive browser commands via BrowserGym.

        Args:
            action: Browse interactive action with browser commands

        Returns:
            Browser observation with command results or error

        """
        if self.browser is None:
            return ErrorObservation(
                "Browser functionality is not supported or disabled."
            )
        await self._ensure_browser_ready()
        browser_observation = await browse(action, self.browser, self.initial_cwd)
        if not browser_observation.error:
            return browser_observation
        curr_files = os.listdir(self.downloads_directory)
        new_download = False
        for file in curr_files:
            if file not in self.downloaded_files:
                new_download = True
                self.downloaded_files.append(file)
                break
        if not new_download:
            return browser_observation
        src_path = os.path.join(self.downloads_directory, self.downloaded_files[-1])
        file_ext = ""
        try:
            guesses = puremagic.magic_file(src_path)
            if len(guesses) > 0:
                ext = guesses[0].extension.strip()
                if len(ext) > 0:
                    file_ext = ext
        except Exception:
            pass
        tgt_path = os.path.join(
            "/workspace", f"file_{len(self.downloaded_files)}{file_ext}"
        )
        shutil.copy(src_path, tgt_path)
        return FileDownloadObservation(
            content=f"Execution of the previous action {
                action.browser_actions
            } resulted in a file download. The downloaded file is saved at location: {
                tgt_path
            }",
            file_path=tgt_path,
        )

    def close(self) -> None:
        """Close action execution server and clean up resources.

        Shuts down bash session, browser, and memory monitoring.
        """
        self.memory_monitor.stop_monitoring()
        if self.bash_session is not None:
            self.bash_session.close()
        if self.browser is not None:
            self.browser.close()


def get_uvicorn_json_log_config() -> dict[str, Any]:
    """Return a minimal uvicorn log configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(levelprefix)s %(asctime)s %(name)s %(message)s",
                "use_colors": None,
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO"},
        },
    }


if __name__ == "__main__":
    logger.warning("Starting Action Execution Server")
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Port to listen on")
    parser.add_argument("--working-dir", type=str, help="Working directory")
    parser.add_argument("--plugins", type=str, help="Plugins to initialize", nargs="+")
    parser.add_argument("--username", type=str, help="User to run as", default="forge")
    parser.add_argument("--user-id", type=int, help="User ID to run as", default=1000)
    parser.add_argument(
        "--enable-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable the browser environment",
    )
    parser.add_argument(
        "--browsergym-eval-env",
        type=str,
        help="BrowserGym environment used for browser evaluation",
        default=None,
    )
    args = parser.parse_args()
    logger.info("Starting file viewer server")
    _file_viewer_port = find_available_tcp_port(
        min_port=args.port + 1, max_port=min(args.port + 1024, 65535)
    )
    server_url, _ = start_file_viewer_server(port=_file_viewer_port)
    logger.info("File viewer server started at %s", server_url)
    plugins_to_load: list[Plugin] = []
    if args.plugins:
        for plugin in args.plugins:
            if plugin not in ALL_PLUGINS:
                msg = f"Plugin {plugin} not found"
                raise ValueError(msg)
            plugins_to_load.append(ALL_PLUGINS[plugin]())
    client: ActionExecutor | None = None
    mcp_proxy_manager: MCPProxyManager | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage FastAPI application lifespan.

        Handles initialization and cleanup of ActionExecutor and MCP Proxy Manager.

        Args:
            app: FastAPI application instance

        Yields:
            None during application runtime

        """
        global client, mcp_proxy_manager
        logger.info("Initializing ActionExecutor...")
        client = ActionExecutor(
            plugins_to_load,
            work_dir=args.working_dir,
            username=args.username,
            user_id=args.user_id,
            enable_browser=args.enable_browser,
            browsergym_eval_env=args.browsergym_eval_env,
        )
        await client.ainit()
        logger.info("ActionExecutor initialized.")
        is_windows = sys.platform == "win32"
        if is_windows:
            logger.info("Skipping MCP Proxy initialization on Windows")
            mcp_proxy_manager = None
        else:
            logger.info("Initializing MCP Proxy Manager...")
            mcp_proxy_manager = MCPProxyManager(
                auth_enabled=bool(SESSION_API_KEY),
                api_key=SESSION_API_KEY,
                logger_level=logger.getEffectiveLevel(),
            )
            mcp_proxy_manager.initialize()
            allowed_origins = ["*"]
            try:
                await mcp_proxy_manager.mount_to_app(app, allowed_origins)
            except Exception as e:
                logger.error("Error mounting MCP Proxy: %s", e, exc_info=True)
                msg = f"Cannot mount MCP Proxy: {e}"
                raise RuntimeError(msg) from e
        yield
        logger.info("Shutting down MCP Proxy Manager...")
        if mcp_proxy_manager:
            del mcp_proxy_manager
            mcp_proxy_manager = None
        else:
            logger.info("MCP Proxy Manager instance not found for shutdown.")
        logger.info("Closing ActionExecutor...")
        if client:
            try:
                client.close()
                logger.info("ActionExecutor closed successfully.")
            except Exception as e:
                logger.error("Error closing ActionExecutor: %s", e, exc_info=True)
        else:
            logger.info("ActionExecutor instance not found for closing.")
        logger.info("Shutdown complete.")

    app = FastAPI(lifespan=lifespan)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions.

        Args:
            request: Incoming request
            exc: Exception that was raised

        Returns:
            JSON response with 500 status code

        """
        logger.exception("Unhandled exception occurred:")
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions.

        Args:
            request: Incoming request
            exc: HTTP exception

        Returns:
            JSON response with appropriate status code

        """
        logger.error("HTTP exception occurred: %s", exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle request validation errors.

        Args:
            request: Incoming request
            exc: Validation error

        Returns:
            JSON response with 422 status code and error details

        """
        logger.error("Validation error occurred: %s", exc)
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Invalid request parameters",
                "errors": str(exc.errors()),
            },
        )

    @app.middleware("http")
    async def authenticate_requests(request: Request, call_next):
        """Authenticate incoming requests using session API key.

        Skips authentication for public endpoints (/alive, /server_info).

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response from next middleware or error response

        """
        if request.url.path not in ["/alive", "/server_info"]:
            try:
                _module_attr("verify_api_key")(
                    request.headers.get("X-Session-API-Key")
                )
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code, content={"detail": e.detail}
                )
        return await call_next(request)

    @app.get("/server_info")
    async def get_server_info():
        """Get server status information including uptime and resource usage.

        Returns:
            Dictionary with uptime, idle_time, and system resource stats

        """
        assert client is not None
        current_time = time.time()
        uptime = current_time - client.start_time
        idle_time = current_time - client.last_execution_time
        stats_fetcher = _module_attr("get_system_stats")
        response = {
            "uptime": uptime,
            "idle_time": idle_time,
            "resources": stats_fetcher(),
        }
        logger.info("Server info endpoint response: %s", response)
        return response

    @app.post("/execute_action")
    async def execute_action(action_request: ActionRequest):
        """Execute an agent action and return observation.

        Args:
            action_request: Action request containing action data

        Returns:
            Serialized observation dictionary

        Raises:
            HTTPException: If action is invalid or execution fails

        """
        assert client is not None
        try:
            action = event_from_dict(action_request.event)
            if not isinstance(action, Action):
                raise HTTPException(status_code=400, detail="Invalid action type")
            client.last_execution_time = time.time()
            observation = await client.run_action(action)
            return event_to_dict(observation)
        except Exception as e:
            logger.error("Error while running /execute_action: %s", str(e))
            raise HTTPException(status_code=500, detail=traceback.format_exc()) from e
        finally:
            update_last_execution_time()

    @app.post("/update_mcp_server")
    async def update_mcp_server(request: Request):
        """Update MCP server configuration with new tools.

        Disabled on Windows. Updates and remounts MCP proxy with new stdio servers.

        Args:
            request: Request containing list of MCP tools to sync

        Returns:
            JSON response with update status

        Raises:
            HTTPException: If MCP not initialized or invalid request

        """
        is_windows = sys.platform == "win32"
        global mcp_proxy_manager
        if is_windows:
            logger.info(
                "MCP server update request received on Windows - skipping as MCP is disabled"
            )
            return JSONResponse(
                status_code=200,
                content={
                    "detail": "MCP server update skipped (MCP is disabled on Windows)",
                    "router_error_log": "",
                },
            )
        if mcp_proxy_manager is None:
            raise HTTPException(
                status_code=500, detail="MCP Proxy Manager is not initialized"
            )
        mcp_tools_to_sync = await request.json()
        if not isinstance(mcp_tools_to_sync, list):
            raise HTTPException(
                status_code=400, detail="Request must be a list of MCP tools to sync"
            )
        logger.info(
            "Updating MCP server with tools: %s",
            json.dumps(mcp_tools_to_sync, indent=2),
        )
        mcp_tools_to_sync = [MCPStdioServerConfig(**tool) for tool in mcp_tools_to_sync]
        try:
            await mcp_proxy_manager.update_and_remount(app, mcp_tools_to_sync, ["*"])
            logger.info("MCP Proxy Manager updated and remounted successfully")
            router_error_log = ""
        except Exception as e:
            logger.error("Error updating MCP Proxy Manager: %s", e, exc_info=True)
            router_error_log = str(e)
        return JSONResponse(
            status_code=200,
            content={
                "detail": "MCP server updated successfully",
                "router_error_log": router_error_log,
            },
        )

    @app.post("/upload_file")
    async def upload_file(
        file: UploadFile, destination: str = "/", recursive: bool = False
    ):
        """Upload file to sandbox filesystem.

        Supports both single file upload and recursive directory upload via zip.

        Args:
            file: File to upload
            destination: Absolute destination path in sandbox
            recursive: Whether to extract zip file recursively

        Returns:
            JSON response with upload details

        Raises:
            HTTPException: If path invalid or upload fails

        """
        assert client is not None
        try:
            filename = file.filename
            if not filename:
                raise HTTPException(
                    status_code=400, detail="Uploaded file must have a filename"
                )
            if not os.path.isabs(destination):
                raise HTTPException(
                    status_code=400, detail="Destination must be an absolute path"
                )
            full_dest_path = destination
            if not os.path.exists(full_dest_path):
                os.makedirs(full_dest_path, exist_ok=True)
            if recursive or (not recursive and filename.endswith(".zip")):
                if not filename.endswith(".zip"):
                    raise HTTPException(
                        status_code=400, detail="Recursive uploads must be zip files"
                    )
                zip_path = os.path.join(full_dest_path, filename)
                with open(zip_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                shutil.unpack_archive(zip_path, full_dest_path)
                os.remove(zip_path)
                logger.debug(
                    "Uploaded file %s and extracted to %s",
                    filename,
                    full_dest_path,
                )
            else:
                file_path = os.path.join(full_dest_path, filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                logger.debug("Uploaded file %s to %s", filename, full_dest_path)
            return JSONResponse(
                content={
                    "filename": filename,
                    "destination": full_dest_path,
                    "recursive": recursive,
                },
                status_code=200,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/download_files")
    def download_file(path: str):
        """Download files from sandbox as a zip archive.

        Creates a zip archive of the specified path for download.

        Args:
            path: Absolute path to file or directory to download

        Returns:
            Streaming response with zip file

        Raises:
            HTTPException: If path invalid or not found

        """
        logger.debug("Downloading files")
        try:
            if not os.path.isabs(path):
                raise HTTPException(
                    status_code=400, detail="Path must be an absolute path"
                )
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail="File not found")
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
                with ZipFile(temp_zip, "w") as zipf:
                    for root, _, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zipf.write(
                                file_path, arcname=os.path.relpath(file_path, path)
                            )
                return FileResponse(
                    path=temp_zip.name,
                    media_type="application/zip",
                    filename=f"{os.path.basename(path)}.zip",
                    background=BackgroundTask(lambda: os.unlink(temp_zip.name)),
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/alive")
    async def alive():
        """Health check endpoint.

        Returns:
            Status dictionary indicating if client is initialized

        """
        if client is None or not client.initialized:
            return {"status": "not initialized"}
        return {"status": "ok"}

    @app.get("/vscode/connection_token")
    async def get_vscode_connection_token():
        """Get VSCode connection token for code-server integration.

        Returns:
            Dictionary with token or None if VSCode plugin not loaded

        """
        assert client is not None
        if "vscode" not in client.plugins:
            return {"token": None}
        plugin = client.plugins["vscode"]
        if not isinstance(plugin, VSCodePlugin):
            return {"token": None}
        return {"token": plugin.vscode_connection_token}

    @app.post("/list_files")
    async def list_files(request: Request):
        """List files in the specified path.

        This function retrieves a list of files from the agent's runtime file store,
        excluding certain system and hidden files/directories.

        To list files:
        ```sh
        curl -X POST -d '{"path": "/"}' http://localhost:3000/list_files
        ```

        Args:
            request: The incoming request object

        Returns:
            JSONResponse with list of file names

        """
        assert client is not None

        try:
            resolver = _module_attr("_resolve_list_path")
            full_path = await resolver(request, client)
            if (
                not full_path
                or not os.path.exists(full_path)
                or not os.path.isdir(full_path)
            ):
                return JSONResponse(content=[])

            sorter = _module_attr("_get_sorted_directory_entries")
            sorted_entries = sorter(full_path)
            return JSONResponse(content=sorted_entries)

        except Exception as e:
            logger.error("Error listing files: %s", e)
            return JSONResponse(content=[])

    logger.debug(f"Starting action execution API on port {args.port}")
    # When LOG_JSON=1, provide a JSON log config to Uvicorn so error/access logs are structured
    log_config = None
    if os.getenv("LOG_JSON", "0") in ("1", "true", "True"):
        log_config = get_uvicorn_json_log_config()
    run(app, host="0.0.0.0", port=args.port, log_config=log_config, use_colors=False)
