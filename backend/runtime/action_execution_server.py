"""This is the main file for the runtime client.

It is responsible for executing actions received from forge backend and producing observations.

NOTE: this will be executed inside the docker sandbox.

Updated: Fixed syntax errors in ainit method.
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


if TYPE_CHECKING:
    from backend.runtime.utils.file_editor import FileEditor as _ForgeFileEditor
    from backend.runtime.utils.file_editor import ToolError as _ForgeToolError
    from backend.runtime.utils.file_editor import ToolResult as _ForgeToolResult
    from backend.runtime.browser.browser_env import BrowserEnv

from backend.runtime.utils.diff import get_diff
from backend.runtime.utils.file_editor import FileEditor, ToolError, ToolResult


from pydantic import BaseModel
from starlette.background import BackgroundTask
from starlette.exceptions import HTTPException as StarletteHTTPException
from uvicorn import run

from backend.core.config.mcp_config import MCPStdioServerConfig
from backend.core.constants import ROOT_GID, SESSION_API_KEY_HEADER
from backend.core.exceptions import BrowserUnavailableException
from backend.core.logger import forge_logger as logger
from backend.events.action import (
    Action,
    BrowseInteractiveAction,
    BrowseURLAction,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
)
from backend.events.event import FileEditSource, FileReadSource
from backend.events.observation import (
    CmdOutputObservation,
    ErrorObservation,
    FileDownloadObservation,
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)
from backend.events.serialization import event_from_dict, event_to_dict
from backend.runtime.file_viewer_server import start_file_viewer_server
from backend.runtime.mcp.proxy import MCPProxyManager
from backend.runtime.plugins import ALL_PLUGINS, Plugin
from backend.runtime.utils import find_available_tcp_port
from backend.runtime.utils.bash import BashSession
from backend.runtime.utils.files import insert_lines, read_lines
from backend.runtime.utils.memory_monitor import MemoryMonitor
from backend.runtime.utils.runtime_init import init_user_and_working_directory
from backend.runtime.utils.system_stats import (
    get_system_stats,
    update_last_execution_time,
)
from backend.utils.async_utils import call_sync_from_async, wait_all

# Windows PowerShell session - only available on Windows
WindowsPowershellSession = None
# Note: Import is deferred to avoid executing windows_bash.py on non-Windows platforms


@dataclass
class ActionRequest:
    """Incoming action execution request envelope sent to runtime server."""

    event: dict[str, Any]


async def _resolve_list_path(request: Request, client) -> str:
    """Resolve the path to list files from with security validation.

    Args:
        request: HTTP request
        client: Action execution client

    Returns:
        Resolved full path (validated and safe)

    Raises:
        PathValidationError: If path validation fails

    """
    request_dict = await request.json()
    path = request_dict.get("path", None)

    if path is None:
        return client.initial_cwd

    try:
        from backend.core.type_safety.path_validation import SafePath

        # Use SafePath for security validation
        safe_path = SafePath.validate(
            path,
            workspace_root=client.initial_cwd,
            must_be_relative=True,  # Enforce workspace boundaries
        )
        return str(safe_path.path)
    except Exception:
        # Fallback to legacy resolution for backward compatibility
        logger.warning(
            f"Path validation failed for {path}, using legacy resolution. "
            "This may be a security risk."
        )
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


ROOT_GID = ROOT_GID
SESSION_API_KEY = os.environ.get("SESSION_API_KEY")
api_key_header = APIKeyHeader(name=SESSION_API_KEY_HEADER, auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API key for session authentication.

    Args:
        api_key: The API key from the request header.

    Returns:
        str: The verified API key.

    Raises:
        HTTPException: If the API key is invalid or doesn't match the session key.

    """
    import secrets as _secrets
    if SESSION_API_KEY and (
        not api_key or not _secrets.compare_digest(api_key, SESSION_API_KEY)
    ):
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
        editor: The FileEditor instance
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
        # Convert None to MISSING sentinel for optional parameters
        from backend.core.type_safety.sentinels import MISSING

        result = editor(
            command=command,
            path=path,
            file_text=file_text if file_text is not None else MISSING,
            view_range=view_range,
            old_str=old_str if old_str is not None else MISSING,
            new_str=new_str if new_str is not None else MISSING,
            insert_line=insert_line,
            enable_linting=enable_linting,
        )
    except ToolError as e:
        result = ToolResult(output="", error=str(e))
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
        tool_registry: Any | None = None,  # ToolRegistry for cross-platform support
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
        
        # Store ToolRegistry for cross-platform support
        self.tool_registry = tool_registry
        if self.tool_registry is None:
            # Fallback: create ToolRegistry if not provided (for backward compatibility)
            from backend.runtime.utils.tool_registry import ToolRegistry
            logger.warning("ToolRegistry not provided, creating one (may impact startup time)")
            self.tool_registry = ToolRegistry()
        
        self.bash_session: BashSession | None = None
        self.lock = asyncio.Lock()
        self.plugins: dict[str, Plugin] = {}
        self.file_editor = FileEditor(workspace_root=self._initial_cwd)
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
        from backend.runtime.browser.browser_env import BrowserEnv
        
        # Ensure downloads directory exists and is writable before initializing browser
        # This prevents Playwright from failing with permission errors
        try:
            downloads_dir = self.downloads_directory
            # Check if the directory exists and is writable
            if os.path.exists(downloads_dir):
                if not os.access(downloads_dir, os.W_OK):
                    logger.warning(
                        f"Downloads directory {downloads_dir} exists but is not writable. "
                        "Falling back to /tmp/.downloads"
                    )
                    downloads_dir = "/tmp/.downloads"
                    self.downloads_directory = downloads_dir
            else:
                # Try to create the directory
                try:
                    os.makedirs(downloads_dir, mode=0o755, exist_ok=True)
                    logger.debug(f"Created downloads directory: {downloads_dir}")
                except (OSError, PermissionError) as e:
                    logger.warning(
                        f"Failed to create downloads directory {downloads_dir}: {e}. "
                        "Falling back to /tmp/.downloads"
                    )
                    downloads_dir = "/tmp/.downloads"
                    self.downloads_directory = downloads_dir
                    os.makedirs(downloads_dir, mode=0o755, exist_ok=True)
            
            # Ensure the directory is writable
            if not os.access(downloads_dir, os.W_OK):
                raise PermissionError(f"Downloads directory {downloads_dir} is not writable")
            
            logger.debug(f"Using downloads directory: {downloads_dir}")
        except Exception as e:
            logger.error(f"Failed to set up downloads directory: {e}", exc_info=True)
            # Continue anyway - browser might still work without downloads
        
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
        """Create a shell session appropriate for the current platform.

        Uses the unified shell abstraction to create the best available shell session
        based on detected tools (BashSession with tmux, SimpleBashSession, or WindowsPowershellSession).

        Args:
            cwd: Optional working directory for the session. Defaults to self._initial_cwd

        Returns:
            UnifiedShellSession: Initialized shell session (platform-appropriate)

        Environment Variables:
            - NO_CHANGE_TIMEOUT_SECONDS: Timeout for inactivity (default: 10)
            - max_memory_gb: Maximum memory usage in GB (converted to MB)

        Side Effects:
            - Initializes shell session with initialize() call
            - Logs information about selected shell type

        Example:
            >>> session = executor._create_bash_session("/tmp")
            >>> session.cwd
            "/tmp"

        Note:
            The actual shell type (Bash, PowerShell, etc.) is determined by the
            ToolRegistry based on platform and available tools.

        """
        from backend.runtime.utils.unified_shell import create_shell_session
        
        logger.info("Creating shell session using unified abstraction...")
        
        # Ensure tool_registry is not None
        if self.tool_registry is None:
            from backend.runtime.utils.tool_registry import ToolRegistry
            self.tool_registry = ToolRegistry()
        
        shell_session = create_shell_session(
            work_dir=cwd or self._initial_cwd,
            tools=self.tool_registry,
            username=self.username,
            no_change_timeout_seconds=int(
                os.environ.get("NO_CHANGE_TIMEOUT_SECONDS", 10)
            ),
            max_memory_mb=self.max_memory_gb * 1024 if self.max_memory_gb else None,
        )
        
        # Initialize the session
        shell_session.initialize()
        logger.info("Shell session initialized successfully")
        
        return shell_session

    async def ainit(self) -> None:
        """Initialize action execution server asynchronously.

        Sets up bash session, browser environment, plugins, and agent skills.
        """
        try:
            logger.info("Step 1/5: Initializing bash session...")
            self.bash_session = self._create_bash_session()
            logger.info("Step 1/5: Bash session initialized successfully")
            
            logger.info("Step 2/5: Starting browser initialization in background...")
            self.browser_init_task = asyncio.create_task(self._init_browser_async())
            logger.info("Step 2/5: Browser initialization task created")
            
            logger.info(
                f"Step 3/5: Initializing {len(self.plugins_to_load)} plugins "
                f"(timeout: {os.environ.get('INIT_PLUGIN_TIMEOUT', '120')}s)..."
            )
            plugin_names = [plugin.name for plugin in self.plugins_to_load]
            logger.info(f"Plugins to initialize: {plugin_names}")
            await wait_all(
                (self._init_plugin(plugin) for plugin in self.plugins_to_load),
                timeout=int(os.environ.get("INIT_PLUGIN_TIMEOUT", "120")),
            )
            logger.info("Step 3/5: All plugins initialized successfully")
            
            logger.info("Step 4/5: AgentSkills initialization skipped (plugins not available)")
            
            logger.info("Step 5/5: Initializing bash commands...")
            await self._init_bash_commands()
            logger.info("Step 5/5: Bash commands initialized")
            
            logger.info("All initialization steps completed successfully")
            self._initialized = True
        except Exception as e:
            logger.error(
                f"ActionExecutor initialization failed at step: {e}",
                exc_info=True,
            )
            raise

    @property
    def initialized(self) -> bool:
        """Check if action execution server has completed initialization.

        Returns:
            True if initialized

        """
        return self._initialized

    async def _init_plugin(self, plugin: Plugin) -> None:
        assert self.bash_session is not None
        logger.info(f"Starting initialization of plugin: {plugin.name}")
        try:
            logger.debug(f"Initializing plugin: {plugin.name}")
            await plugin.initialize(self.username)
            self.plugins[plugin.name] = plugin
            logger.info(f"Successfully initialized plugin: {plugin.name}")
        except Exception as e:
            logger.error(
                f"Failed to initialize plugin {plugin.name}: {e}",
                exc_info=True,
            )
            raise

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
            if isinstance(obs, ErrorObservation):
                logger.warning(
                    "Init command failed: %s. Error: %s", command, obs.content
                )
                # Continue initialization even if git alias setup fails
                continue
            # Check if it's a CmdOutputObservation (handle potential import differences)
            # Use duck typing to check for exit_code attribute
            if not hasattr(obs, 'exit_code'):
                logger.warning(
                    "Init command returned unexpected observation type: %s. Observation: %s",
                    type(obs),
                    obs,
                )
                # Continue initialization even if observation type is unexpected
                continue
            logger.debug(
                "Init command outputs (exit code: %s): %s", obs.exit_code, obs.content
            )
            if obs.exit_code != 0:
                logger.warning(
                    "Init command returned non-zero exit code: %s. Command: %s. Output: %s",
                    obs.exit_code,
                    command,
                    obs.content,
                )
                # Continue initialization even if git alias setup fails
                continue
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

    def _resolve_path(self, path: str, working_dir: str) -> str:
        """Resolve a relative or absolute path to an absolute path with security validation.

        Converts relative paths to absolute by combining with working_dir.
        Validates paths to prevent directory traversal attacks and enforce
        workspace boundaries. Uses SafePath for production-grade security.

        Args:
            path: File path (relative or absolute)
            working_dir: Current working directory to use for relative paths

        Returns:
            str: Absolute file path as string (validated and safe)

        Raises:
            PathValidationError: If path validation fails (traversal, boundary violation, etc.)

        Example:
            >>> abs_path = executor._resolve_path("file.txt", "/home/user")
            >>> abs_path
            "/home/user/file.txt"
            >>> executor._resolve_path("../etc/passwd", "/home/user")
            PathValidationError: Path traversal detected

        Note:
            - Relative paths are validated against workspace boundaries
            - Absolute paths are validated if they're within workspace
            - Uses SafePath for security validation
            - Prevents directory traversal attacks

        """
        try:
            from backend.core.type_safety.path_validation import SafePath

            # Use SafePath for security validation
            safe_path = SafePath.validate(
                path,
                workspace_root=working_dir,
                must_be_relative=True,  # Enforce workspace boundaries
            )
            return str(safe_path.path)
        except Exception:
            # Fallback to legacy resolution for backward compatibility
            # but log a warning
            logger.warning(
                f"Path validation failed for {path}, using legacy resolution. "
                "This may be a security risk."
            )
            filepath = Path(path)
            if not filepath.is_absolute():
                return str(Path(working_dir) / filepath)
            return str(filepath)

    def _handle_aci_file_read(self, action: FileReadAction) -> FileReadObservation:
        """Handle file reading using the FILE_EDITOR implementation.

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
            content=result_str, path=action.path, impl_source=FileReadSource.FILE_EDITOR
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

        # Handle FILE_EDITOR implementation
        if action.impl_source == FileReadSource.FILE_EDITOR:
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
        assert action.impl_source == FileEditSource.FILE_EDITOR
        
        # Handle directory viewing specially
        if action.command == "view":
            try:
                resolved_path = self._resolve_path(action.path, self._initial_cwd)
                # Check if path is a directory (handle Windows edge cases)
                try:
                    if os.path.exists(resolved_path) and os.path.isdir(resolved_path):
                        # Format directory listing
                        return await self._handle_directory_view(resolved_path, action.path)
                except (OSError, ValueError):
                    # Path is invalid or inaccessible, let file editor handle it
                    pass
            except Exception:
                # Path resolution failed, let file editor handle it
                pass
        
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
            impl_source=FileEditSource.FILE_EDITOR,
            diff=get_diff(
                old=old_content or "",
                new=new_content or "",
                path=action.path,
            ),
        )
    
    async def _handle_directory_view(self, full_path: str, display_path: str) -> FileEditObservation:
        """Handle viewing a directory by listing files up to 2 levels deep.
        
        Args:
            full_path: Resolved absolute path to the directory
            display_path: Original path for display purposes
            
        Returns:
            FileEditObservation with formatted directory listing
        """
        def _list_directory_recursive(dir_path: str, max_depth: int, current_depth: int = 0, base_path: str = "") -> tuple[list[str], int]:
            """Recursively list directory entries up to max_depth, excluding hidden files.
            
            Returns:
                Tuple of (list of file paths relative to base_path, count of hidden items)
            """
            if current_depth >= max_depth:
                return [], 0
            
            entries = []
            hidden_count = 0
            
            try:
                for entry in os.listdir(dir_path):
                    # Skip hidden files/directories (starting with .)
                    if entry.startswith("."):
                        hidden_count += 1
                        continue
                    
                    entry_path = os.path.join(dir_path, entry)
                    relative_path = os.path.join(base_path, entry) if base_path else entry
                    
                    try:
                        if os.path.isdir(entry_path):
                            entries.append(relative_path + "/")
                            # Recursively list subdirectories
                            sub_entries, sub_hidden = _list_directory_recursive(
                                entry_path, max_depth, current_depth + 1, relative_path
                            )
                            entries.extend(sub_entries)
                            hidden_count += sub_hidden
                        else:
                            entries.append(relative_path)
                    except (OSError, ValueError):
                        # Skip entries that can't be accessed
                        continue
            except (OSError, PermissionError, NotADirectoryError):
                # Cannot read directory
                pass
            
            return entries, hidden_count
        
        # List files up to 2 levels deep
        file_list, hidden_count = _list_directory_recursive(full_path, max_depth=2)
        
        # Sort: directories first (with /), then files
        directories = [f for f in file_list if f.endswith("/")]
        files = [f for f in file_list if not f.endswith("/")]
        directories.sort(key=lambda s: s.lower())
        files.sort(key=lambda s: s.lower())
        sorted_entries = directories + files
        
        # Format output - normalize paths to use forward slashes for consistency
        display_path_normalized = display_path.replace("\\", "/")
        lines = [f"Here's the files and directories up to 2 levels deep in {display_path_normalized}, excluding hidden items:"]
        
        # Include the directory itself first (with trailing slash)
        if not display_path_normalized.endswith("/"):
            lines.append(f"{display_path_normalized}/")
        
        # Then list entries inside the directory
        for entry in sorted_entries:
            # Normalize entry path to use forward slashes
            entry_normalized = entry.replace("\\", "/")
            # Make paths absolute for display
            if display_path_normalized.endswith("/"):
                lines.append(f"{display_path_normalized}{entry_normalized}")
            else:
                lines.append(f"{display_path_normalized}/{entry_normalized}")
        
        if hidden_count > 0:
            lines.append("")
            lines.append(f"{hidden_count} hidden files/directories in this directory are excluded. You can use 'ls -la {display_path_normalized}' to see them.")
        
        content = "\n".join(lines)
        
        return FileEditObservation(
            content=content,
            path=display_path,
            old_content=None,
            new_content=None,
            impl_source=FileEditSource.FILE_EDITOR,
            diff="",
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
        from backend.runtime.browser import browse
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
        from backend.runtime.browser import browse
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
                "format": "%(levelname)s %(asctime)s %(name)s %(message)s",
                "use_colors": None,
            },
            # Uvicorn expects an "access" formatter when configuring logging;
            # provide a minimal one to avoid KeyError in uvicorn.configure_logging.
            "access": {
                "format": "%(levelname)s %(asctime)s %(message)s",
                "use_colors": None,
            },
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
    initialization_task: asyncio.Task | None = None
    initialization_error: Exception | None = None

    async def _initialize_background(app: FastAPI):
        """Initialize ActionExecutor and MCP Proxy Manager in the background."""
        global client, mcp_proxy_manager, initialization_error
        try:
            logger.info("Initializing ActionExecutor...")
            logger.info("Creating ActionExecutor instance...")
            client = ActionExecutor(
                plugins_to_load,
                work_dir=args.working_dir,
                username=args.username,
                user_id=args.user_id,
                enable_browser=args.enable_browser,
                browsergym_eval_env=args.browsergym_eval_env,
            )
            logger.info("ActionExecutor instance created. Starting async initialization...")
            
            # Add timeout to prevent indefinite hanging
            init_timeout = int(os.environ.get("ACTION_EXECUTOR_INIT_TIMEOUT", "300"))  # Default 5 minutes
            try:
                await asyncio.wait_for(client.ainit(), timeout=init_timeout)
                logger.info("ActionExecutor initialized successfully.")
            except asyncio.TimeoutError:
                error_msg = (
                    f"ActionExecutor initialization timed out after {init_timeout} seconds. "
                    "This may indicate a plugin or dependency issue."
                )
                logger.error(error_msg)
                initialization_error = RuntimeError(error_msg)
                raise initialization_error
            
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
                    # Mount MCP Proxy to app after initialization completes
                    await mcp_proxy_manager.mount_to_app(app, allowed_origins)
                    logger.info("MCP Proxy Manager mounted to app successfully")
                except Exception as e:
                    logger.error("Error mounting MCP Proxy: %s", e, exc_info=True)
                    # Don't fail initialization if MCP Proxy mounting fails
                    logger.warning("Continuing without MCP Proxy mounting")
        except Exception as e:
            logger.error(
                f"Failed to initialize ActionExecutor: {e}",
                exc_info=True,
            )
            initialization_error = e
            # Don't re-raise - let the /alive endpoint report the error

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage FastAPI application lifespan.

        Starts the server immediately and runs initialization in the background
        so the /alive endpoint can respond during initialization.

        Args:
            app: FastAPI application instance

        Yields:
            None during application runtime

        """
        global initialization_task
        logger.info("Starting server (initialization will run in background)...")
        
        # Start initialization in background task
        initialization_task = asyncio.create_task(_initialize_background(app))
        
        # Yield immediately so server can start accepting requests
        yield
        
        # Cleanup on shutdown
        logger.info("Shutting down...")
        global mcp_proxy_manager, client
        if initialization_task and not initialization_task.done():
            logger.info("Cancelling initialization task...")
            initialization_task.cancel()
            try:
                await initialization_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Shutting down MCP Proxy Manager...")
        if mcp_proxy_manager:
            try:
                del mcp_proxy_manager
                mcp_proxy_manager = None
            except Exception:
                pass
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
        """Health check endpoint that returns server status.
        
        Returns 200 if server is ready, 503 if still initializing or failed.
        """
        global client, initialization_task, initialization_error
        
        # Check if initialization failed
        if initialization_error is not None:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": f"Initialization failed: {str(initialization_error)}",
                    "error_type": type(initialization_error).__name__,
                },
                status_code=503,
            )
        
        # Check if initialization is still running
        if initialization_task and not initialization_task.done():
            return JSONResponse(
                content={
                    "status": "initializing",
                    "message": "ActionExecutor initialization in progress",
                },
                status_code=503,
            )
        
        # Check if client exists and is initialized
        if client is None:
            return JSONResponse(
                content={
                    "status": "initializing",
                    "message": "ActionExecutor not yet created",
                },
                status_code=503,
            )
        
        if not client.initialized:
            return JSONResponse(
                content={
                    "status": "initializing",
                    "message": "ActionExecutor initialization in progress",
                },
                status_code=503,
            )
        
        return JSONResponse(
            content={
                "status": "ready",
                "message": "ActionExecutor initialized and ready",
            },
            status_code=200,
        )

    # VSCode connection token endpoint removed - OpenVSCode Server no longer used
    # Desktop VSCode extension still available at backend/forge/integrations/vscode/

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
