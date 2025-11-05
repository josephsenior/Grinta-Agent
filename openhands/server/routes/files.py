from __future__ import annotations

import os
import posixpath
from typing import TYPE_CHECKING, Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from starlette.background import BackgroundTask

from openhands.core.exceptions import AgentRuntimeUnavailableError
from openhands.core.logger import openhands_logger as logger
from openhands.events.action import FileReadAction
from openhands.events.action.files import FileWriteAction
from openhands.events.observation import ErrorObservation, FileReadObservation
from openhands.runtime.utils.git_changes import get_git_changes
from openhands.server.dependencies import get_dependencies
from openhands.server.file_config import FILES_TO_IGNORE
from openhands.server.files import POSTUploadFilesModel
from openhands.server.user_auth import get_user_id
from openhands.server.utils import get_conversation, get_conversation_store
from openhands.utils.async_utils import call_sync_from_async

if TYPE_CHECKING:
    from openhands.runtime.base import Runtime
    from openhands.server.session.conversation import ServerConversation
    from openhands.storage.conversation.conversation_store import ConversationStore

app = APIRouter(prefix="/api/conversations/{conversation_id}/files", dependencies=get_dependencies())


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
        logger.debug("list-files request received before runtime ready; returning empty list")
        return []
    runtime: Runtime = conversation.runtime
    try:
        file_list = await call_sync_from_async(runtime.list_files, path)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when listing files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Runtime container is unavailable. Please start a new conversation."},
        )
    except AgentRuntimeUnavailableError as e:
        logger.error("Error listing files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error listing files: {e}"},
        )
    if path:
        file_list = [os.path.join(path, f) for f in file_list]
    file_list = [f for f in file_list if f not in FILES_TO_IGNORE]

    async def filter_for_gitignore(file_list: list[str], base_path: str) -> list[str]:
        workspace_root = runtime.config.workspace_mount_path_in_sandbox or "/workspace"
        gitignore_runtime_path = os.path.join(workspace_root, base_path, ".gitignore")
        try:
            read_action = FileReadAction(gitignore_runtime_path)
            observation = await call_sync_from_async(runtime.run_action, read_action)
            if not isinstance(observation, FileReadObservation):
                logger.debug(
                    "Skipping gitignore filtering; unable to read %s (observation=%s)",
                    gitignore_runtime_path,
                    type(observation).__name__,
                )
                return file_list
            spec = PathSpec.from_lines(GitWildMatchPattern, observation.content.splitlines())
        except FileNotFoundError:
            # Common case: no .gitignore in workspace yet
            logger.debug("No .gitignore found at %s; skipping gitignore filtering", gitignore_runtime_path)
            return file_list
        except Exception as e:
            logger.warning("Failed to load %s for gitignore filtering: %s", gitignore_runtime_path, e)
            return file_list
        return [entry for entry in file_list if not spec.match_file(entry)]

    try:
        file_list = await filter_for_gitignore(file_list, "")
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when filtering files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Runtime container is unavailable. Please start a new conversation."},
        )
    except AgentRuntimeUnavailableError as e:
        logger.error("Error filtering files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error filtering files: {e}"},
        )
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
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)},
        )
    
    # Check if runtime is ready before accessing it
    if not conversation.runtime:
        logger.warning("select-file request received before runtime ready for file: %s", file)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Runtime not ready yet, please try again"},
        )
    
    runtime: Runtime = conversation.runtime
    file = os.path.join(runtime.config.workspace_mount_path_in_sandbox, sanitized_file)
    read_action = FileReadAction(file)
    try:
        observation = await call_sync_from_async(runtime.run_action, read_action)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when opening file %s: %s", file, e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"error": "Runtime container is unavailable. Please start a new conversation."},
        )
    except AgentRuntimeUnavailableError as e:
        logger.error("Error opening file %s: %s", file, e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error opening file: {e}"},
        )
    if isinstance(observation, FileReadObservation):
        content = observation.content
        return JSONResponse(content={"code": content})
    if isinstance(observation, ErrorObservation):
        logger.error("Error opening file %s: %s", file, observation)
        if "ERROR_BINARY_FILE" in observation.message:
            return JSONResponse(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                content={"error": f"Unable to open binary file: {file}"},
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Error opening file: {observation}"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": f"Unexpected observation type: {type(observation)}"},
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
        runtime: Runtime = conversation.runtime
        path = runtime.config.workspace_mount_path_in_sandbox
        try:
            zip_file_path = runtime.copy_from(path)
        except AgentRuntimeUnavailableError as e:
            logger.error("Error zipping workspace: %s", e)
            return JSONResponse(status_code=500, content={"error": f"Error zipping workspace: {e}"})
        return FileResponse(
            path=zip_file_path,
            filename="workspace.zip",
            media_type="application/zip",
            background=BackgroundTask(lambda: os.unlink(zip_file_path)),
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
    """Get git changes for the current workspace.

    Args:
        conversation_id (str): The conversation ID.

    Returns:
        list[dict[str, str]]: A list of dictionaries containing git changes.
        JSONResponse: An error response if git operations fail.
    """
    try:
        from openhands.server.shared import conversation_manager
        conversation = await conversation_manager.attach_to_conversation(conversation_id, "dev-user")
        if not conversation:
            return JSONResponse(content={"error": "Conversation not found"}, status_code=404)
        
        runtime: Runtime = conversation.runtime
        cwd = runtime.config.workspace_mount_path_in_sandbox
        logger.info("Getting git changes in %s", cwd)
        
        # Check if the workspace directory exists
        if not os.path.exists(cwd):
            logger.warning("Workspace directory %s does not exist", cwd)
            return JSONResponse(status_code=200, content=[])
        
        try:
            changes = await call_sync_from_async(get_git_changes, cwd)
            await conversation_manager.detach_from_conversation(conversation)
            
            if changes is None:
                return JSONResponse(status_code=404, content={"error": "Not a git repository"})
            return changes
        except FileNotFoundError as e:
            if "git" in str(e):
                logger.warning("Git not available in container, returning empty changes list")
                await conversation_manager.detach_from_conversation(conversation)
                return JSONResponse(status_code=200, content=[])
            else:
                raise
    except AgentRuntimeUnavailableError as e:
        logger.error("Runtime unavailable: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Error getting changes: {e}"})
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
        return JSONResponse(
            status_code=422,
            content={"error": "Path parameter is required and must be a non-empty string"},
        )

    try:
        # Sanitize the path to prevent path traversal attacks
        sanitized_path = _sanitize_file_path(path.strip())
    except ValueError as e:
        logger.warning("Invalid file path provided to git_diff: %s", path)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(e)},
        )

    runtime: Runtime = conversation.runtime
    cwd = runtime.config.workspace_mount_path_in_sandbox
    try:
        return await call_sync_from_async(runtime.get_git_diff, sanitized_path, cwd)
    except AgentRuntimeUnavailableError as e:
        logger.error("Error getting diff: %s", e)
        return JSONResponse(status_code=500, content={"error": f"Error getting diff: {e}"})


@app.post("/upload-files", response_model=POSTUploadFilesModel)
async def upload_files(files: list[UploadFile], conversation: ServerConversation = Depends(get_conversation)):
    """Upload files to the workspace.

    Args:
        files (list[UploadFile]): The list of files to upload.
        conversation (ServerConversation): The conversation object containing runtime information.

    Returns:
        JSONResponse: A response containing lists of uploaded and skipped files.
    """
    uploaded_files = []
    skipped_files = []
    runtime: Runtime = conversation.runtime
    for file in files:
        try:
            # Sanitize the filename to prevent path traversal attacks
            sanitized_filename = _sanitize_file_path(str(file.filename))
        except ValueError as e:
            skipped_files.append({"name": file.filename, "reason": str(e)})
            continue
            
        file_path = os.path.join(runtime.config.workspace_mount_path_in_sandbox, sanitized_filename)
        try:
            file_content = await file.read()
            write_action = FileWriteAction(path=file_path, content=file_content.decode("utf-8", errors="replace"))
            await call_sync_from_async(runtime.run_action, write_action)
            uploaded_files.append(file_path)
        except Exception as e:
            skipped_files.append({"name": file.filename, "reason": str(e)})
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"uploaded_files": uploaded_files, "skipped_files": skipped_files},
    )
