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

from forge.core.exceptions import AgentRuntimeUnavailableError
from forge.core.logger import forge_logger as logger
from forge.events.action import FileReadAction
from forge.events.action.files import FileWriteAction
from forge.events.observation import ErrorObservation, FileReadObservation
from forge.runtime.utils.git_changes import get_git_changes
from forge.server.dependencies import get_dependencies
from forge.server.file_config import FILES_TO_IGNORE
from forge.server.files import POSTUploadFilesModel
from forge.server.user_auth import get_user_id
from forge.server.utils import get_conversation, get_conversation_store
from forge.utils.async_utils import call_sync_from_async

if TYPE_CHECKING:
    from forge.runtime.base import Runtime
    from forge.server.session.conversation import ServerConversation
    from forge.storage.conversation.conversation_store import ConversationStore

app = APIRouter(
    prefix="/api/conversations/{conversation_id}/files", dependencies=get_dependencies()
)


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
        logger.debug(
            "list-files request received before runtime ready; returning empty list"
        )
        return []
    runtime: Runtime = conversation.runtime
    try:
        file_list = await call_sync_from_async(runtime.list_files, path)
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when listing files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Runtime container is unavailable. Please start a new conversation."
            },
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
            spec = PathSpec.from_lines(
                GitWildMatchPattern, observation.content.splitlines()
            )
        except FileNotFoundError:
            # Common case: no .gitignore in workspace yet
            logger.debug(
                "No .gitignore found at %s; skipping gitignore filtering",
                gitignore_runtime_path,
            )
            return file_list
        except Exception as e:
            logger.warning(
                "Failed to load %s for gitignore filtering: %s",
                gitignore_runtime_path,
                e,
            )
            return file_list
        return [entry for entry in file_list if not spec.match_file(entry)]

    try:
        file_list = await filter_for_gitignore(file_list, "")
    except (httpx.ConnectError, ConnectionRefusedError) as e:
        # Runtime container is unavailable (crashed or stopped)
        logger.error("Runtime container unavailable when filtering files: %s", e)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "Runtime container is unavailable. Please start a new conversation."
            },
        )
    return file_list
