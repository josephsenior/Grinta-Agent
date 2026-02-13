"""Workspace-level git operations.

Provides a thin service layer around ``git`` subprocess calls so that
routes, conversation managers, and other consumers can share one
tested, timeout-aware implementation instead of duplicating raw
subprocess logic.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field

from backend.core.logger import forge_logger as logger

# Default timeout for git subprocess calls (seconds).
_GIT_TIMEOUT = 10


@dataclass(frozen=True, slots=True)
class FileChange:
    """A single entry from ``git status --porcelain``."""

    status: str
    path: str


@dataclass(frozen=True, slots=True)
class GitChangesResult:
    """Result of a ``git status`` call."""

    changes: list[FileChange] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True, slots=True)
class GitDiffResult:
    """Result of a ``git diff`` call for a single file."""

    diff: str = ""
    path: str = ""
    error: str | None = None


def get_changes(workspace_dir: str, *, timeout: int = _GIT_TIMEOUT) -> GitChangesResult:
    """Run ``git status --porcelain`` in *workspace_dir*.

    Returns:
        :class:`GitChangesResult` — always non-raising.
    """
    if not os.path.isdir(workspace_dir):
        return GitChangesResult()

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning("git status failed in %s: %s", workspace_dir, result.stderr)
            return GitChangesResult(error=f"git status failed: {result.stderr.strip()}")

        changes: list[FileChange] = []
        for line in result.stdout.strip().splitlines():
            if len(line) < 4:
                continue
            changes.append(FileChange(status=line[:2].strip(), path=line[3:]))
        return GitChangesResult(changes=changes)

    except FileNotFoundError:
        return GitChangesResult(error="git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        logger.warning("git status timed out in %s", workspace_dir)
        return GitChangesResult(error="git status timed out")
    except Exception as exc:
        logger.warning("git status error in %s: %s", workspace_dir, exc)
        return GitChangesResult(error=str(exc))


def get_diff(
    workspace_dir: str, file_path: str, *, timeout: int = _GIT_TIMEOUT
) -> GitDiffResult:
    """Run ``git diff -- <file_path>`` in *workspace_dir*.

    Returns:
        :class:`GitDiffResult` — always non-raising.
    """
    if not os.path.isdir(workspace_dir):
        return GitDiffResult(path=file_path, error="workspace not found")

    try:
        result = subprocess.run(
            ["git", "diff", "--", file_path],
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return GitDiffResult(diff=result.stdout, path=file_path)
    except FileNotFoundError:
        return GitDiffResult(path=file_path, error="git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        logger.warning("git diff timed out in %s for %s", workspace_dir, file_path)
        return GitDiffResult(path=file_path, error="git diff timed out")
    except Exception as exc:
        logger.warning("git diff error in %s/%s: %s", workspace_dir, file_path, exc)
        return GitDiffResult(path=file_path, error=str(exc))
