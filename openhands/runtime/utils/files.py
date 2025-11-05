import os
from pathlib import Path, PurePosixPath

from openhands.events.observation import (
    ErrorObservation,
    FileReadObservation,
    FileWriteObservation,
    Observation,
)


def _normalize_posix_path(p: PurePosixPath) -> PurePosixPath:
    """Normalize a POSIX path by removing redundant components and resolving parent directory references.

    Args:
        p: The POSIX path to normalize.

    Returns:
        PurePosixPath: The normalized path.
    """
    parts = []
    for part in p.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if parts and parts[-1] != "..":
                parts.pop()
            else:
                parts.append("..")
        else:
            parts.append(part)

    if p.is_absolute():
        return PurePosixPath("/" + "/".join(parts))
    return PurePosixPath("/".join(parts) or ".")


def _validate_path_access(abs_path_in_sandbox: PurePosixPath, sandbox_root: PurePosixPath, file_path: str) -> None:
    """Validate that the resolved path is within the allowed sandbox directory.

    Args:
        abs_path_in_sandbox: The absolute path within the sandbox.
        sandbox_root: The root directory of the sandbox.
        file_path: The original file path for error reporting.

    Raises:
        PermissionError: If the path is outside the allowed sandbox directory.
    """
    try:
        if not abs_path_in_sandbox.is_relative_to(sandbox_root):
            msg = f"File access not permitted: {file_path}"
            raise PermissionError(msg)
    except Exception as e:
        # Fallback check for older Python versions that don't support is_relative_to
        if not str(abs_path_in_sandbox).startswith(str(sandbox_root)):
            msg = f"File access not permitted: {file_path}"
            raise PermissionError(msg) from e


def resolve_path(
    file_path: str,
    working_directory: str,
    workspace_base: str,
    workspace_mount_path_in_sandbox: str,
) -> Path:
    """Resolve a file path to a path on the host filesystem.

    Args:
        file_path: The path to resolve.
        working_directory: The working directory of the agent.
        workspace_base: The base path of the workspace on the host filesystem.
        workspace_mount_path_in_sandbox: The path to the workspace inside the sandbox.

    Returns:
        Path: The resolved path on the host filesystem.

    Raises:
        PermissionError: If the resolved path is outside the allowed sandbox directory.
    """
    # Convert to POSIX path and make absolute if needed
    posix_path = PurePosixPath(file_path)
    if not posix_path.is_absolute():
        posix_path = PurePosixPath(working_directory) / posix_path

    # Normalize the path
    abs_path_in_sandbox = _normalize_posix_path(posix_path)
    sandbox_root = PurePosixPath(workspace_mount_path_in_sandbox)

    # Validate path access
    _validate_path_access(abs_path_in_sandbox, sandbox_root, file_path)

    # Convert to host filesystem path
    path_in_workspace = abs_path_in_sandbox.relative_to(sandbox_root)
    return Path(workspace_base) / Path(*path_in_workspace.parts)


def read_lines(all_lines: list[str], start: int = 0, end: int = -1) -> list[str]:
    """Read a subset of lines from a list of lines.

    Args:
        all_lines: The complete list of lines to read from.
        start: Starting line index (inclusive).
        end: Ending line index (exclusive), -1 for all remaining lines.

    Returns:
        list[str]: The requested subset of lines.
    """
    start = max(start, 0)
    start = min(start, len(all_lines))
    end = -1 if end == -1 else max(end, 0)
    end = min(end, len(all_lines))
    if end == -1:
        return all_lines if start == 0 else all_lines[start:]
    num_lines = len(all_lines)
    begin = max(0, min(start, num_lines - 2))
    end = -1 if end > num_lines else max(begin + 1, end)
    return all_lines[begin:end]


async def read_file(
    path: str,
    workdir: str,
    workspace_base: str,
    workspace_mount_path_in_sandbox: str,
    start: int = 0,
    end: int = -1,
) -> Observation:
    """Read file content with optional line range.
    
    Resolves path and reads file content, handling various error conditions.
    
    Args:
        path: File path to read
        workdir: Current working directory
        workspace_base: Workspace base path
        workspace_mount_path_in_sandbox: Workspace mount path in sandbox
        start: Starting line number (0-indexed)
        end: Ending line number (-1 for end of file)
        
    Returns:
        FileReadObservation with content or ErrorObservation on failure
    """
    try:
        whole_path = resolve_path(path, workdir, workspace_base, workspace_mount_path_in_sandbox)
    except PermissionError:
        return ErrorObservation(
            f"You're not allowed to access this path: {path}. You can only access paths inside the workspace.",
        )
    try:
        with open(whole_path, encoding="utf-8") as file:
            lines = read_lines(file.readlines(), start, end)
    except FileNotFoundError:
        return ErrorObservation(f"File not found: {path}")
    except UnicodeDecodeError:
        return ErrorObservation(f"File could not be decoded as utf-8: {path}")
    except IsADirectoryError:
        return ErrorObservation(f"Path is a directory: {path}. You can only read files")
    code_view = "".join(lines)
    return FileReadObservation(path=path, content=code_view)


def insert_lines(to_insert: list[str], original: list[str], start: int = 0, end: int = -1) -> list[str]:
    """Insert the new content to the original content based on start and end."""
    new_lines = [""] if start == 0 else original[:start]
    new_lines += [i + "\n" for i in to_insert]
    new_lines += [""] if end == -1 else original[end:]
    return new_lines


async def write_file(
    path: str,
    workdir: str,
    workspace_base: str,
    workspace_mount_path_in_sandbox: str,
    content: str,
    start: int = 0,
    end: int = -1,
) -> Observation:
    """Write content to file with optional line range insertion.
    
    Resolves path and writes content, optionally inserting at specific line range.
    
    Args:
        path: File path to write
        workdir: Current working directory
        workspace_base: Workspace base path
        workspace_mount_path_in_sandbox: Workspace mount path in sandbox
        content: Content to write
        start: Starting line number for insertion (0-indexed)
        end: Ending line number for insertion (-1 for append)
        
    Returns:
        FileWriteObservation on success or ErrorObservation on failure
    """
    insert = content.split("\n")
    try:
        whole_path = resolve_path(path, workdir, workspace_base, workspace_mount_path_in_sandbox)
        if not os.path.exists(os.path.dirname(whole_path)):
            os.makedirs(os.path.dirname(whole_path))
        mode = "r+" if os.path.exists(whole_path) else "w"
        try:
            with open(whole_path, mode, encoding="utf-8") as file:
                if mode != "w":
                    all_lines = file.readlines()
                    new_file = insert_lines(insert, all_lines, start, end)
                else:
                    new_file = [i + "\n" for i in insert]
                file.seek(0)
                file.writelines(new_file)
                file.truncate()
        except FileNotFoundError:
            return ErrorObservation(f"File not found: {path}")
        except IsADirectoryError:
            return ErrorObservation(f"Path is a directory: {path}. You can only write to files")
        except UnicodeDecodeError:
            return ErrorObservation(f"File could not be decoded as utf-8: {path}")
    except PermissionError as e:
        return ErrorObservation(f"Permission error on {path}: {e}")
    return FileWriteObservation(content="", path=path)
