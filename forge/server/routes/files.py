"""Routes for file browsing, reading, and uploading within conversations."""

from __future__ import annotations

import os
import posixpath
import sys
from typing import TYPE_CHECKING, Annotated, Any, cast
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from forge.server.utils.responses import error
from starlette.background import BackgroundTask

from forge.core.exceptions import AgentRuntimeUnavailableError
from forge.core.logger import forge_logger as logger
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


def _unlink_path(path: Path) -> None:
    """Background helper to remove temporary archive files."""
    path.unlink(missing_ok=True)


def _sanitize_file_path(file_path: str) -> str:
    """Sanitize file path to prevent path traversal attacks.

    Args:
        file_path: The file path to sanitize

    Returns:
        str: Sanitized file path

    Raises:
        ValueError: If the path contains directory traversal sequences

    """
    if not file_path:
        raise ValueError("File path cannot be empty")

    # Normalize the path and check for directory traversal
    normalized_path = posixpath.normpath(file_path)

    # Check for directory traversal attempts
    if ".." in normalized_path or normalized_path.startswith("/"):
        raise ValueError(f"Invalid file path: {file_path}")

    # Ensure path doesn't start with current or parent directory markers
    if normalized_path.startswith("./") or normalized_path.startswith("../"):
        raise ValueError(f"Invalid file path: {file_path}")

    return normalized_path


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
    response_model=list[str],
    responses={
        404: {"description": "Runtime not initialized", "model": dict},
        500: {"description": "Error listing or filtering files", "model": dict},
    },
)
async def list_files(
    path: str | None = None,
    conversation: ServerConversation = Depends(get_conversation),
) -> list[str] | JSONResponse:
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
    if not conversation.runtime:
        logger.debug(
            "list-files request received before runtime ready; returning empty list"
        )
        return []
    runtime = cast("RuntimeFileOps", conversation.runtime)
    try:
        file_list = await call_sync_from_async(runtime.list_files, path)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when listing files: %s", e)
        return error(
            message="Runtime container is unavailable. Please start a new conversation.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="RUNTIME_UNAVAILABLE",
        )
    except AgentRuntimeUnavailableError as e:
        logger.error("Error listing files: %s", e)
        return error(
            message=f"Error listing files: {e}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="LIST_FILES_ERROR",
        )
    if path:
        file_list = [os.path.join(path, f) for f in file_list]
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
    file: str,
    conversation: ServerConversation = Depends(get_conversation),
) -> FileResponse | JSONResponse:
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
    try:
        # Sanitize the file path to prevent path traversal attacks
        sanitized_file = _sanitize_file_path(file)
    except ValueError as e:
        logger.warning("Invalid file path provided: %s", file)
        return error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILE_PATH",
        )

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
    file = os.path.join(runtime.config.workspace_mount_path_in_sandbox, sanitized_file)
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
) -> FileResponse | JSONResponse:
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
            zip_file_path = Path(runtime.copy_from(path))
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
    response_model=list[dict[str, str]],
    responses={
        404: {"description": "Not a git repository", "model": dict},
        500: {"description": "Error getting changes", "model": dict},
    },
)
async def git_changes(
    conversation_id: str,
) -> list[dict[str, str]] | JSONResponse:
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
    response_model=dict[str, Any],
    responses={500: {"description": "Error getting diff", "model": dict}},
)
async def git_diff(
    path: str,
    conversation_store: Any = Depends(get_conversation_store),
    conversation: ServerConversation = Depends(get_conversation),
) -> dict[str, Any] | JSONResponse:
    """Get git diff for a specific path in the workspace.

    Args:
        path (str): The path to get the git diff for.
        conversation_store (Any): The conversation store for persistence.
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        dict[str, Any]: A dictionary containing the git diff information.
        JSONResponse: An error response if git operations fail.

    """
    # Validate path parameter
    if not path or not isinstance(path, str) or not path.strip():
        logger.warning("Invalid path parameter provided to git_diff endpoint: %s", path)
        return error(
            message="Path parameter is required and must be a non-empty string",
            status_code=422,
            error_code="INVALID_PATH",
        )

    try:
        # Sanitize the path to prevent path traversal attacks
        sanitized_path = _sanitize_file_path(path.strip())
    except ValueError as e:
        logger.warning("Invalid file path provided to git_diff: %s", path)
        return error(
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_FILE_PATH",
        )

    runtime = cast("RuntimeFileOps", conversation.runtime)
    cwd = runtime.config.workspace_mount_path_in_sandbox
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
    runtime = cast("RuntimeFileOps", conversation.runtime)
    for file in files:
        try:
            # Sanitize the filename to prevent path traversal attacks
            sanitized_filename = _sanitize_file_path(str(file.filename))
        except ValueError as e:
            skipped_files.append({"name": file.filename, "reason": str(e)})
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
