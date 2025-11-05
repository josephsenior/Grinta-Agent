"""Get git changes in the current working directory relative to the remote origin if possible.

NOTE: Since this is run as a script, there should be no imports from project files!
"""

from __future__ import annotations

import glob
import json
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path


def run(cmd: str, cwd: str) -> str:
    """Run a shell command and return its output.

    Args:
        cmd: The command to run.
        cwd: The working directory to run the command in.

    Returns:
        str: The command output.

    Raises:
        RuntimeError: If the command fails to execute.
    """
    # Use shlex.split() to safely parse the command and avoid shell=True
    result = subprocess.run(
        check=False,
        args=shlex.split(cmd),
        shell=False,
        capture_output=True,
        cwd=cwd,
    )
    byte_content = result.stderr or result.stdout or b""
    if result.returncode != 0:
        msg = f"error_running_cmd:{result.returncode}:{byte_content.decode()}"
        raise RuntimeError(
            msg,
        )
    return byte_content.decode().strip()


def get_valid_ref(repo_dir: str) -> str | None:
    """Get a valid git reference for comparison.

    Tries multiple git references in order of preference:
    1. Current branch origin
    2. Default branch references
    3. Empty tree reference

    Args:
        repo_dir: The repository directory.

    Returns:
        str | None: A valid git reference hash, or None if none found.
    """
    refs = []
    try:
        current_branch = run("git --no-pager rev-parse --abbrev-ref HEAD", repo_dir)
        refs.append(f"origin/{current_branch}")
    except RuntimeError:
        pass
    try:
        default_branch = run('git --no-pager remote show origin | grep "HEAD branch"', repo_dir).split()[-1].strip()
        ref_non_default_branch = (
            f'$(git --no-pager merge-base HEAD "$(git --no-pager rev-parse --abbrev-ref origin/{default_branch})")'
        )
        ref_default_branch = f"origin/{default_branch}"
        refs.extend((ref_non_default_branch, ref_default_branch))
    except RuntimeError:
        pass
    ref_new_repo = "$(git --no-pager rev-parse --verify 4b825dc642cb6eb9a060e54bf8d69288fbee4904)"
    refs.append(ref_new_repo)
    for ref in refs:
        try:
            return run(f"git --no-pager rev-parse --verify {ref}", repo_dir)
        except RuntimeError:
            continue
    return None


def _parse_git_status_line(line: str, changed_files: list[str]) -> list[dict[str, str]]:
    """Parse a single git status line and return changes."""
    if not line.strip():
        msg = f"unexpected_value_in_git_diff:{changed_files}"
        raise RuntimeError(msg)

    parts = line.split()
    if len(parts) < 2:
        msg = f"unexpected_value_in_git_diff:{changed_files}"
        raise RuntimeError(msg)

    status = parts[0].strip()

    # Handle rename (R)
    if status.startswith("R") and len(parts) == 3:
        old_path = parts[1].strip()
        new_path = parts[2].strip()
        return [{"status": "D", "path": old_path}, {"status": "A", "path": new_path}]

    # Handle copy (C)
    if status.startswith("C") and len(parts) == 3:
        new_path = parts[2].strip()
        return [{"status": "A", "path": new_path}]

    # Handle regular status
    if len(parts) == 2:
        path = parts[1].strip()
    else:
        msg = f"unexpected_value_in_git_diff:{changed_files}"
        raise RuntimeError(msg)

    return [_normalize_status(status, path, changed_files)]


def _normalize_status(
    status: str,
    path: str,
    changed_files: list[str],
) -> dict[str, str]:
    """Normalize git status to standard format."""
    if status == "??":
        status = "A"
    elif status == "*":
        status = "M"

    if status in {"M", "A", "D", "U"}:
        return {"status": status, "path": path}
    msg = f"unexpected_status_in_git_diff:{changed_files}"
    raise RuntimeError(msg)


def get_changes_in_repo(repo_dir: str) -> list[dict[str, str]]:
    """Get all changes in a git repository.

    Args:
        repo_dir: The repository directory to check for changes.

    Returns:
        list[dict[str, str]]: List of change dictionaries with 'status' and 'path' keys.
    """
    ref = get_valid_ref(repo_dir)
    if not ref:
        return []

    # Get changed files from git diff
    changed_files = run(
        f"git --no-pager diff --name-status {ref}",
        repo_dir,
    ).splitlines()
    changes = []
    for line in changed_files:
        line_changes = _parse_git_status_line(line, changed_files)
        changes.extend(line_changes)

    # Add untracked files
    untracked_files = run(
        "git --no-pager ls-files --others --exclude-standard",
        repo_dir,
    ).splitlines()
    changes.extend({"status": "A", "path": path} for path in untracked_files if path)

    return changes


def get_git_changes(cwd: str) -> list[dict[str, str]]:
    """Get git changes for the current directory and all subdirectories.

    Args:
        cwd: The current working directory to check for git changes.

    Returns:
        list[dict[str, str]]: List of change dictionaries with 'status' and 'path' keys.
    """
    git_dirs = {os.path.dirname(f)[2:] for f in glob.glob("./*/.git", root_dir=cwd, recursive=True)}
    changes = get_changes_in_repo(cwd)
    changes = [
        change
        for change in changes
        if next(
            iter(git_dir for git_dir in git_dirs if change["path"].startswith(git_dir)),
            None,
        )
        is None
    ]
    for git_dir in git_dirs:
        git_dir_changes = get_changes_in_repo(str(Path(cwd, git_dir)))
        for change in git_dir_changes:
            change["path"] = f"{git_dir}/" + change["path"]
            changes.append(change)
    changes.sort(key=lambda change: change["path"])
    return changes


if __name__ == "__main__":
    try:
        changes = get_git_changes(os.getcwd())
        try:
            from openhands.core.io import print_json_stdout
        except Exception:
            sys.stdout.write(json.dumps(changes) + "\n")
            sys.stdout.flush()
        else:
            print_json_stdout(changes)
    except Exception as e:
        logging.exception("Failed to compute git changes")
        try:
            from openhands.core.io import print_json_stdout
        except Exception:
            sys.stdout.write(json.dumps({"error": str(e)}) + "\n")
            sys.stdout.flush()
        else:
            print_json_stdout({"error": str(e)})
