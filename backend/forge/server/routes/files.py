"""Routes for file browsing, reading, and uploading within conversations."""

from __future__ import annotations

import os
import posixpath
import sys
from typing import TYPE_CHECKING, Annotated, Any, cast, Union
from pathlib import Path as PathLib

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi import Path
from fastapi.responses import FileResponse, JSONResponse
from forge.server.utils.responses import error
from starlette.background import BackgroundTask

from forge.core.exceptions import AgentRuntimeUnavailableError
from forge.core.logger import forge_logger as logger
from forge.core.security.sentinels import MISSING, Sentinel, is_missing
from forge.events.action import FileReadAction
from forge.events.action.files import FileWriteAction
from forge.events.observation import ErrorObservation, FileReadObservation
from forge.integrations.provider import ProviderToken, ProviderType, PROVIDER_TOKEN_TYPE
from forge.runtime.utils.git_changes import get_git_changes
from forge.server.dependencies import get_dependencies
from forge.server.file_config import FILES_TO_IGNORE
from forge.server.files import POSTUploadFilesModel
from forge.server.user_auth import get_user_id
from forge.server.shared import conversation_manager, get_conversation_manager
from forge.server.utils import get_conversation, get_conversation_store
from forge.utils.async_utils import call_sync_from_async

if TYPE_CHECKING:
    from typing import Protocol

    from forge.runtime.base import Runtime
    from forge.server.session.conversation import ServerConversation
    from forge.storage.conversation.conversation_store import ConversationStore

    class RuntimeFileOps(Protocol):
        """Protocol describing runtime operations used by file routes."""

        config: Any  # pragma: no cover - protocol attribute

        def list_files(
            self, path: str | None = None
        ) -> list[str]:  # pragma: no cover - protocol method
            ...

        def copy_from(
            self, path: str
        ) -> str | os.PathLike[str]:  # pragma: no cover - protocol method
            ...

        def get_git_diff(
            self, path: str, cwd: str
        ) -> dict[str, Any]:  # pragma: no cover - protocol method
            ...

        def run_action(self, action: Any) -> Any:  # pragma: no cover - protocol method
            ...


app: APIRouter
if "pytest" in sys.modules:

    class NoOpAPIRouter(APIRouter):
        """Router stub used during tests to skip FastAPI registration."""

        def add_api_route(self, path: str, endpoint, **kwargs):  # type: ignore[override]
            """Return endpoint without registering to allow direct invocation in tests."""
            return endpoint

    app = cast(
        APIRouter,
        NoOpAPIRouter(
            prefix="/api/conversations/{conversation_id}/files",
            dependencies=get_dependencies(),
        ),
    )
else:
    app = APIRouter(
        prefix="/api/conversations/{conversation_id}/files",
        dependencies=get_dependencies(),
    )


def _unlink_path(path: PathLib) -> None:
    """Background helper to remove temporary archive files."""
    path.unlink(missing_ok=True)


# Note: _sanitize_file_path() has been replaced with direct SafePath.validate() usage
# in route handlers where we have workspace_root context. SafePath provides
# production-grade path validation with security boundaries.


def _get_conversation_manager_instance():
    manager: Any = conversation_manager
    if manager is not None:
        return manager
    try:
        return get_conversation_manager()
    except Exception:
        return None


def _require_conversation_manager():
    manager = _get_conversation_manager_instance()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Conversation manager is not initialized",
        )
    return manager


@app.get(
    "/list-files",
    response_model=None,
    responses={
        200: {"description": "List of file paths"},
        404: {"description": "Runtime not initialized"},
        500: {"description": "Error listing or filtering files"},
    },
)
async def list_files(
    path: str | None = Query(None, description="Optional path to list files from"),
    conversation: ServerConversation = Depends(get_conversation),
) -> Any:
    """List files in the specified path.

    This function retrieves a list of files from the agent's runtime file store,
    excluding certain system and hidden files/directories.

    To list files:
    ```sh
    curl http://localhost:3000/api/conversations/{conversation_id}/list-files
    ```

    Args:
        conversation (ServerConversation): The conversation object containing runtime information.
        path (str, optional): The path to list files from. Defaults to None.

    Returns:
        list: A list of file names in the specified path.

    Raises:
        HTTPException: If there's an error listing the files.

    """
    # If runtime is not ready, try to wait for it (it might be initializing)
    if not conversation.runtime:
        logger.warning(
            f"list-files request for conversation {conversation.sid} received before runtime ready. "
            "This indicates the runtime failed to initialize or is still starting."
        )
        # Wait a bit for runtime to be created (it might be in the process of initialization)
        import asyncio
        max_wait = 5  # Wait up to 5 seconds
        wait_interval = 0.2
        waited = 0.0
        while waited < max_wait and not conversation.runtime:
            await asyncio.sleep(wait_interval)
            waited += wait_interval
            # Runtime might have been set by now if initialization completed
            # Re-check the conversation object
            if hasattr(conversation, 'runtime') and conversation.runtime:
                logger.info(f"Runtime for conversation {conversation.sid} became available after {waited}s")
                break
        
        if not conversation.runtime:
            logger.error(
                f"list-files request: runtime for conversation {conversation.sid} still not ready after {max_wait}s. "
                "This likely indicates the local runtime failed to initialize. Check backend logs for initialization errors."
            )
            return error(
                message=(
                    "⏳ Workspace is still starting up\n\n"
                    "Your development environment is being initialized. This usually takes a few seconds.\n\n"
                    "**If this persists, the local runtime may have failed to initialize.**\n\n"
                    "**What you can do:**\n"
                    "• Wait a moment and try again\n"
                    "• Refresh the page\n"
                    "• Check the backend logs for runtime initialization errors\n"
                    "• Try starting a new conversation\n\n"
                    "**Note:** Check the backend console for detailed error messages about why the runtime failed to initialize."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="RUNTIME_NOT_READY",
            )
    
    runtime = cast("RuntimeFileOps", conversation.runtime)
    workspace_root = runtime.config.workspace_mount_path_in_sandbox

    # Validate path using SafePath if provided
    if path is not None:
        try:
            from forge.core.security.path_validation import PathValidationError, SafePath

            # Validate and sanitize path using SafePath
            # path is guaranteed to be str here (not MISSING) due to is_missing check above
            safe_path = SafePath.validate(
                str(path),  # Type narrowing: path is str here
                workspace_root=workspace_root,
                must_be_relative=True,  # Enforce workspace boundaries
            )
            path = safe_path.relative_to_workspace()
        except PathValidationError as e:
            logger.warning("Invalid path provided to list_files: %s - %s", path, e.message)
            return error(
                message=f"Invalid path: {e.message}",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_PATH",
            )
    
    # Check if runtime is actually connected/alive
    try:
        # Try to check if the runtime is alive before listing files
        if hasattr(runtime, "check_if_alive"):
            await call_sync_from_async(runtime.check_if_alive)
    except Exception as health_check_error:
        logger.warning(
            "Runtime health check failed before listing files: %s",
            health_check_error,
        )
        # Continue anyway - the list_files call will handle the error
    
    try:
        # Use path directly (None if not provided)
        list_path = path
        file_list = await call_sync_from_async(runtime.list_files, list_path)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error(
            "Runtime container unavailable when listing files: %s (type: %s)",
            e,
            type(e).__name__,
            exc_info=True,
        )
        
        # Check if container is still running (for DockerRuntime)
        container_status = "unknown"
        if hasattr(runtime, "container") and runtime.container is not None:
            try:
                runtime.container.reload()
                container_status = runtime.container.status
            except Exception:
                pass
        
        if container_status == "running":
            return error(
                message=(
                    "⚠️ Workspace connection issue\n\n"
                    "The workspace container is running but not responding to requests.\n\n"
                    "**What you can do:**\n"
                    "• Wait 30 seconds and try again (the server may still be starting)\n"
                    "• Refresh the page\n"
                    "• Start a new conversation if the problem persists\n\n"
                    "**Note:** This usually resolves itself as the workspace finishes initializing."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="RUNTIME_CONNECTION_ERROR",
            )
        else:
            return error(
                message=(
                    "❌ Workspace unavailable\n\n"
                    "The workspace container is not running or has stopped.\n\n"
                    "**What you can do:**\n"
                    "• Start a new conversation to create a fresh workspace\n"
                    "• Check if the container crashed (check logs)\n"
                    "• Wait a moment and refresh the page\n\n"
                    "**Note:** Your conversation data is saved, but you'll need a new workspace."
                ),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code="RUNTIME_UNAVAILABLE",
            )
    except httpx.TimeoutException as e:
        logger.error(
            "Timeout listing files: %s",
            e,
            exc_info=True,
        )
        return error(
            message=(
                "⏱️ Request timeout\n\n"
                "The workspace took too long to respond when listing files.\n\n"
                "**What you can do:**\n"
                "• Wait a moment and try again\n"
                "• The workspace may be under heavy load\n"
                "• Try refreshing the page\n\n"
                "**Note:** This is usually temporary."
            ),
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_code="RUNTIME_TIMEOUT",
        )
    except Exception as e:
        # Catch any other exceptions that might occur
        logger.error(
            "Unexpected error listing files: %s (type: %s)",
            e,
            type(e).__name__,
            exc_info=True,
        )
        if isinstance(e, AgentRuntimeUnavailableError):
            return error(
                message=(
                    "❌ Workspace error\n\n"
                    f"An error occurred while listing files: {e}\n\n"
                    "**What you can do:**\n"
                    "• Try again in a moment\n"
                    "• Start a new conversation if the problem persists\n"
                    "• Check the workspace status\n\n"
                    "**Technical details:** Runtime unavailable"
                ),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="LIST_FILES_ERROR",
            )
        # For other exceptions, return 503 as well
        return error(
            message=(
                "❌ Workspace unavailable\n\n"
                "Unable to connect to the workspace. The container may have stopped or crashed.\n\n"
                "**What you can do:**\n"
                "• Start a new conversation to create a fresh workspace\n"
                "• Wait a moment and refresh the page\n"
                "• Check if the workspace is still initializing\n\n"
                "**Note:** Your conversation data is saved."
            ),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_UNAVAILABLE",
        )
    # Only prefix with path if it was explicitly provided
    if path is not None:
        # Type narrowing: path is str here
        file_list = [os.path.join(str(path), f) for f in file_list]
    file_list = [f for f in file_list if f not in FILES_TO_IGNORE]

    return file_list


@app.get(
    "/select-file",
    response_model=None,
    responses={
        200: {"description": "File content returned as JSON", "model": dict[str, str]},
        500: {"description": "Error opening file", "model": dict},
        415: {"description": "Unsupported media type", "model": dict},
    },
)
async def select_file(
    file: Annotated[str, Field(..., min_length=1, description="File path to retrieve")],
    conversation: ServerConversation = Depends(get_conversation),
) -> Any:
    """Retrieve the content of a specified file.

    To select a file:
    ```sh
    curl http://localhost:3000/api/conversations/{conversation_id}select-file?file=<file_path>
    ```

    Args:
        file (str): The path of the file to be retrieved.
            Expect path to be absolute inside the runtime.
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        dict: A dictionary containing the file content.

    Raises:
        HTTPException: If there's an error opening the file.

    """
    # Check if runtime is ready before accessing it
    if not conversation.runtime:
        logger.warning(
            "select-file request received before runtime ready for file: %s", file
        )
        return error(
            message="Runtime not ready yet, please try again",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_NOT_READY",
        )

    runtime = cast("RuntimeFileOps", conversation.runtime)
    workspace_root = runtime.config.workspace_mount_path_in_sandbox

    # Use SafePath for production-grade path validation with workspace boundaries
    try:
        from forge.core.security.path_validation import PathValidationError, SafePath

        # Validate and sanitize path using SafePath
        safe_path = SafePath.validate(
            file,
            workspace_root=workspace_root,
            must_be_relative=True,  # Enforce workspace boundaries
        )
        file = str(safe_path.path)
    except PathValidationError as e:
        logger.warning("Invalid file path provided: %s - %s", file, e.message)
        return error(
            message=f"Invalid file path: {e.message}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILE_PATH",
        )
    read_action = FileReadAction(file)
    try:
        observation = await call_sync_from_async(runtime.run_action, read_action)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when opening file %s: %s", file, e)
        return error(
            message="Runtime container is unavailable. Please start a new conversation.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_UNAVAILABLE",
        )
    except AgentRuntimeUnavailableError as e:
        logger.error("Error opening file %s: %s", file, e)
        return error(
            message=f"Error opening file: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FILE_OPEN_ERROR",
        )
    if isinstance(observation, FileReadObservation):
        content = observation.content
        return JSONResponse(content={"code": content})
    if isinstance(observation, ErrorObservation):
        logger.error("Error opening file %s: %s", file, observation)
        if "ERROR_BINARY_FILE" in observation.message:
            return error(
                message=f"Unable to open binary file: {file}",
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                error_code="BINARY_FILE_ERROR",
            )
        return error(
            message=f"Error opening file: {observation}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FILE_OBSERVATION_ERROR",
        )
    return error(
        message=f"Unexpected observation type: {type(observation)}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="UNEXPECTED_OBSERVATION",
    )


@app.get(
    "/zip-directory",
    response_model=None,
    responses={
        200: {"description": "Zipped workspace returned as FileResponse"},
        500: {"description": "Error zipping workspace", "model": dict},
    },
)
def zip_current_workspace(
    conversation: ServerConversation = Depends(get_conversation),
) -> Any:
    """Zip the current workspace and return it as a downloadable file.

    Args:
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        FileResponse: A file response containing the zipped workspace.
        JSONResponse: An error response if zipping fails.

    """
    try:
        logger.debug("Zipping workspace")
        runtime = cast("RuntimeFileOps", conversation.runtime)
        path = runtime.config.workspace_mount_path_in_sandbox
        try:
            zip_file_path = PathLib(runtime.copy_from(path))
        except AgentRuntimeUnavailableError as e:
            logger.error("Error zipping workspace: %s", e)
            return error(
                message=f"Error zipping workspace: {e}",
                status_code=500,
                error_code="ZIP_ERROR",
            )
        return FileResponse(
            path=str(zip_file_path),
            filename="workspace.zip",
            media_type="application/zip",
            background=BackgroundTask(_unlink_path, zip_file_path),
        )
    except Exception as e:
        logger.error("Error zipping workspace: %s", e)
        raise HTTPException(status_code=500, detail="Failed to zip workspace") from e


@app.get(
    "/git/changes",
    response_model=None,
    responses={
        200: {"description": "List of git changes"},
        404: {"description": "Not a git repository"},
        500: {"description": "Error getting changes"},
    },
)
async def git_changes(
    conversation_id: str,
) -> Any:
    """Get list of git-tracked file changes in the workspace.

    Retrieves the conversation's runtime and queries it for modified files
    compared to the git repository. Returns empty list if not a git repository
    or if git is unavailable in the runtime container.

    Args:
        conversation_id: Conversation identifier to query runtime

    Returns:
        list[dict[str, str]]: List of changed file dictionaries with metadata, or
        JSONResponse with error details if operation fails

    Raises:
        HTTPException: If runtime is unavailable or operation fails

    Example:
        GET /api/conversations/{conversation_id}/files/git/changes
        Response: [{"path": "src/main.py", "status": "modified"}, ...]

    """
    manager = _require_conversation_manager()
    try:
        conversation = await manager.attach_to_conversation(
            conversation_id, "dev-user"
        )
        if not conversation:
            return JSONResponse(
                content={"error": "Conversation not found"}, status_code=404
            )

        runtime = cast("RuntimeFileOps", conversation.runtime)
        cwd = runtime.config.workspace_mount_path_in_sandbox
        logger.info("Getting git changes in %s", cwd)

        # Check if the workspace directory exists
        if not os.path.exists(cwd):
            logger.warning("Workspace directory %s does not exist", cwd)
            return JSONResponse(status_code=200, content=[])

        try:
            changes = await call_sync_from_async(get_git_changes, cwd)
            await manager.detach_from_conversation(conversation)

            if changes is None:
                return JSONResponse(
                    status_code=404, content={"error": "Not a git repository"}
                )
            return changes
        except FileNotFoundError as e:
            if "git" in str(e):
                logger.warning(
                    "Git not available in container, returning empty changes list"
                )
                await manager.detach_from_conversation(conversation)
                return JSONResponse(status_code=200, content=[])
            else:
                raise
    except AgentRuntimeUnavailableError as e:
        logger.error("Runtime unavailable: %s", e)
        return JSONResponse(
            status_code=500, content={"error": f"Error getting changes: {e}"}
        )
    except Exception as e:
        logger.error("Error getting changes: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get(
    "/git/diff",
    response_model=None,
    responses={
        200: {"description": "Git diff data"},
        500: {"description": "Error getting diff"},
    },
)
async def git_diff(
    path: Annotated[str, Field(..., min_length=1, description="Path to get git diff for")],
    conversation_store: Any = Depends(get_conversation_store),
    conversation: ServerConversation = Depends(get_conversation),
) -> Any:
    """Get git diff for a specific path in the workspace.

    Args:
        path (str): The path to get the git diff for.
        conversation_store (Any): The conversation store for persistence.
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        dict[str, Any]: A dictionary containing the git diff information.
        JSONResponse: An error response if git operations fail.

    """
    # Check if runtime is ready
    if not conversation.runtime:
        logger.warning("git_diff request received before runtime ready for path: %s", path)
        return error(
            message="Runtime not ready yet, please try again",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_NOT_READY",
        )

    runtime = cast("RuntimeFileOps", conversation.runtime)
    workspace_root = runtime.config.workspace_mount_path_in_sandbox

    # Use SafePath for production-grade path validation with workspace boundaries
    try:
        from forge.core.security.path_validation import PathValidationError, SafePath

        # Validate and sanitize path using SafePath
        safe_path = SafePath.validate(
            path.strip(),
            workspace_root=workspace_root,
            must_be_relative=True,  # Enforce workspace boundaries
        )
        sanitized_path = safe_path.relative_to_workspace()
    except PathValidationError as e:
        logger.warning("Invalid file path provided to git_diff: %s - %s", path, e.message)
        return error(
            message=f"Invalid file path: {e.message}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILE_PATH",
        )

    cwd = workspace_root
    try:
        return await call_sync_from_async(runtime.get_git_diff, sanitized_path, cwd)
    except AgentRuntimeUnavailableError as e:
        logger.error("Error getting diff: %s", e)
        return error(
            message=f"Error getting diff: {e}",
            status_code=500,
            error_code="GIT_DIFF_ERROR",
        )


@app.post("/upload-files", response_model=POSTUploadFilesModel)
async def upload_files(
    files: list[UploadFile],
    conversation: ServerConversation = Depends(get_conversation),
):
    """Upload files to the workspace.

    Args:
        files (list[UploadFile]): The list of files to upload.
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        JSONResponse: A response containing lists of uploaded and skipped files.

    """
    uploaded_files = []
    skipped_files = []
    
    # Check if runtime is ready
    if not conversation.runtime:
        return error(
            message="Runtime not ready yet, please try again",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_NOT_READY",
        )
    
    runtime = cast("RuntimeFileOps", conversation.runtime)
    workspace_root = runtime.config.workspace_mount_path_in_sandbox
    
    for file in files:
        try:
            # Validate filename is not empty
            if not file.filename:
                raise ValueError("Filename cannot be empty")
            
            # Use SafePath for production-grade path validation with workspace boundaries
            from forge.core.security.path_validation import PathValidationError, SafePath

            # Validate and sanitize filename using SafePath
            safe_path = SafePath.validate(
                str(file.filename),
                workspace_root=workspace_root,
                must_be_relative=True,  # Enforce workspace boundaries
            )
            sanitized_filename = safe_path.relative_to_workspace()
        except (ValueError, PathValidationError) as e:
            error_message = e.message if isinstance(e, PathValidationError) else str(e)
            skipped_files.append({"name": file.filename or "<unknown>", "reason": error_message})
            continue

        file_path = os.path.join(
            runtime.config.workspace_mount_path_in_sandbox, sanitized_filename
        )
        try:
            file_content = await file.read()
            write_action = FileWriteAction(
                path=file_path, content=file_content.decode("utf-8", errors="replace")
            )
            await call_sync_from_async(runtime.run_action, write_action)
            uploaded_files.append(file_path)
        except Exception as e:
            skipped_files.append({"name": file.filename, "reason": str(e)})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"uploaded_files": uploaded_files, "skipped_files": skipped_files},
    )
